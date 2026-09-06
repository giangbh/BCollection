"""Single transactional writer for case, exposure, posted payment and PTP state.

Inbound financial commands are simulation-only until authenticated Core ingress exists.
"""
import hashlib
import json
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from bc_domain.case_rules import vnd, instant, lifecycle_after_balance
from database import get_connection


class CaseConflict(ValueError):
    pass


class CaseNotFound(LookupError):
    pass


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


class CaseService:
    def __init__(self, clock=None):
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def execute(self, case_id, command_id, expected_version, kind, payload):
        if not isinstance(command_id, str) or not command_id.strip() or len(command_id) > 128:
            raise ValueError("command_id is required (max 128 characters)")
        if type(expected_version) is not int or expected_version < 0:
            raise ValueError("expected_version must be a nonnegative integer")
        conn = get_connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            # A balance-check command has no client financial payload: evidence is fetched server-side.
            fingerprint = digest({"kind": kind, "payload": {} if kind == "balance_check" else payload})
            previous = conn.execute("SELECT * FROM case_commands WHERE case_id=? AND command_id=?", (case_id, command_id)).fetchone()
            if previous:
                if previous["payload_hash"] != fingerprint:
                    raise CaseConflict("command_id reused with different content")
                return {**json.loads(previous["result_json"]), "replayed": True}
            row = conn.execute("SELECT * FROM cases WHERE case_id=?", (case_id,)).fetchone()
            if not row:
                raise CaseNotFound(case_id)
            c = dict(row)
            if not self._exposures(conn, c):
                raise CaseConflict("Case has no exposure; apply the migration before issuing commands")
            if expected_version != c["case_version"]:
                raise CaseConflict(f"Stale case_version; current={c['case_version']}")
            now = instant(self.clock())
            before = (c["lifecycle"], c["resolution"])
            if kind == "wrapup":
                self._wrapup(conn, c, payload, now)
            elif kind in {"balance", "balance_check"}:
                snapshots = payload["snapshots"]
                if not isinstance(snapshots, list) or not snapshots:
                    raise ValueError("At least one Core snapshot required")
                if len({s["loan_id"] for s in snapshots}) != len(snapshots):
                    raise ValueError("Duplicate snapshot loan_id")
                for snapshot in snapshots:
                    self._snapshot(conn, c, snapshot, now)
                if payload.get("recent_payment"):
                    c["contact_hold_reason"] = "PAYMENT_RECONCILIATION"
            elif kind == "payment":
                if not self._payment(conn, c, payload, now):
                    result = {"case_id": case_id, "case_version": c["case_version"], "new_case_status": c["status"], "lifecycle": c["lifecycle"], "resolution": c["resolution"], "contact_hold_reason": c["contact_hold_reason"], "replayed": True, "committed": True}
                    conn.execute("INSERT INTO case_commands VALUES(?,?,?,?)", (case_id, command_id, fingerprint, json.dumps(result)))
                    conn.commit()
                    return result
                c["contact_hold_reason"] = "PAYMENT_RECONCILIATION"
            elif kind == "observe_ptp":
                through = instant(payload["payments_complete_through"])
                if through > now:
                    raise ValueError("Completeness watermark cannot be in the future")
                p = self._ptp(conn, c, payload["ptp_id"])
                if p["observed_through"] and through < instant(p["observed_through"]):
                    raise CaseConflict("Completeness watermark cannot move backwards")
                conn.execute("UPDATE ptps SET observed_through=? WHERE ptp_id=?", (through.isoformat(), p["ptp_id"]))
            elif kind == "link_exposure":
                if c["lifecycle"] != "OPEN" or payload["debtor_cif"] != c["debtor_cif"]:
                    raise CaseConflict("Only an open case and the same debtor can be linked")
                if conn.execute("SELECT 1 FROM case_exposures WHERE loan_id=?", (payload["loan_id"],)).fetchone():
                    raise CaseConflict("Loan already linked; automatic merge is not supported")
                conn.execute("INSERT INTO case_exposures(case_id,loan_id,debtor_cif,overdue_vnd,principal_vnd,interest_vnd,dpd) VALUES(?,?,?,0,0,0,0)", (case_id, payload["loan_id"], c["debtor_cif"]))
                c["contact_hold_reason"] = "UNVERIFIED_EXPOSURE"
            elif kind == "reconcile":
                if not payload.get("reason", "").strip():
                    raise ValueError("Reconciliation reason required")
                exposures = self._exposures(conn, c)
                if not exposures or any(not e["balance_verified"] or now - instant(e["source_as_of"]) > timedelta(minutes=15) for e in exposures):
                    raise CaseConflict("Fresh verified balances for every exposure required")
                latest_payment = conn.execute("SELECT MAX(occurred_at) FROM payment_ledger WHERE case_id=?", (case_id,)).fetchone()[0]
                if latest_payment and any(instant(e["source_as_of"]) < instant(latest_payment) for e in exposures):
                    raise CaseConflict("Balance predates a payment; reconcile with Core again")
                c["contact_hold_reason"] = None
                if c["lifecycle"] == "PROBATION":
                    c["lifecycle"] = "OPEN"
            else:
                raise ValueError("Unsupported command")
            self._recompute_ptps(conn, c)
            exposures = self._exposures(conn, c)
            # Only a verified balance command may resolve/reopen a financial case.
            if kind in {"balance", "balance_check", "reconcile"}:
                fresh = all(e["source_as_of"] and now - instant(e["source_as_of"]) <= timedelta(minutes=15) for e in exposures)
                if fresh:
                    c["lifecycle"], c["resolution"] = lifecycle_after_balance(c["lifecycle"], c["resolution"], exposures)
                if before == ("CLOSED", "CURED") and c["lifecycle"] == "PROBATION":
                    c["contact_hold_reason"] = "RECONCILIATION_REQUIRED"
            overdue = sum(e["overdue_vnd"] for e in exposures)
            total = sum(e["principal_vnd"] + e["interest_vnd"] for e in exposures)
            dpd = max((e["dpd"] for e in exposures), default=c["dpd"])
            active = conn.execute("SELECT * FROM ptps WHERE case_id=? AND status IN ('SCHEDULED','PARTIALLY_KEPT') ORDER BY created_at DESC", (case_id,)).fetchone()
            status = "CURED" if c["resolution"] == "CURED" and c["lifecycle"] == "CLOSED" else c["lifecycle"] if c["lifecycle"] != "OPEN" else "PTP_SCHEDULED" if active else "IN_TREATMENT"
            version = c["case_version"] + 1
            conn.execute("""UPDATE cases SET lifecycle=?,resolution=?,contact_hold_reason=?,status=?,
                overdue_amount=?,total_balance=?,dpd=?,case_version=?,updated_at=?,ptp_amount=?,ptp_date=? WHERE case_id=?""",
                (c["lifecycle"], c["resolution"], c["contact_hold_reason"], status, overdue, total, dpd, version, now.isoformat(), active["amount_vnd"] if active else None, active["due_at"] if active else None, case_id))
            conn.execute("INSERT INTO case_transition_log VALUES(?,?,?,?,?,?,?,?,?,?)", (str(uuid4()), case_id, command_id, before[0], c["lifecycle"], before[1], c["resolution"], kind + (":" + payload["reason"] if kind == "reconcile" else ""), version, now.isoformat()))
            result = {"case_id": case_id, "case_version": version, "new_case_status": status, "lifecycle": c["lifecycle"], "resolution": c["resolution"], "contact_hold_reason": c["contact_hold_reason"], "replayed": False, "committed": True}
            conn.execute("INSERT INTO case_commands VALUES(?,?,?,?)", (case_id, command_id, fingerprint, json.dumps(result)))
            conn.commit()
            return result
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _exposures(self, conn, c):
        return [dict(r) for r in conn.execute("SELECT * FROM case_exposures WHERE case_id=?", (c["case_id"],))]

    def _ptp(self, conn, c, ptp_id):
        p = conn.execute("SELECT * FROM ptps WHERE ptp_id=? AND case_id=?", (ptp_id, c["case_id"])).fetchone()
        if not p or p["status"] in {"UNVERIFIED", "CANCELLED"}:
            raise ValueError("Verified PTP in this case required")
        return p

    def _snapshot(self, conn, c, s, now):
        e = conn.execute("SELECT * FROM case_exposures WHERE case_id=? AND loan_id=?", (c["case_id"], s["loan_id"])).fetchone()
        if not e or s["debtor_cif"] != c["debtor_cif"]:
            raise ValueError("Core snapshot identity mismatch")
        at = instant(s["as_of"])
        if at > now + timedelta(seconds=30) or now - at > timedelta(minutes=15):
            raise ValueError("Stale or future Core snapshot")
        version = s["source_version"]
        if type(version) is not int or version < 0 or type(s["dpd"]) is not int or s["dpd"] < 0:
            raise ValueError("Invalid source_version or DPD")
        values = [vnd(s[k]) for k in ("overdue_amount", "outstanding_principal", "outstanding_interest")]
        fingerprint = digest([s["loan_id"], s["debtor_cif"], version, at.isoformat(), values, s["dpd"]])
        if version < e["source_version"]:
            return  # Late evidence never overwrites a newer balance.
        if version == e["source_version"]:
            if fingerprint != e["snapshot_hash"]:
                raise CaseConflict("Conflicting snapshot at the same source version")
            return
        if e["source_as_of"] and at < instant(e["source_as_of"]):
            raise CaseConflict("Source timestamp moved backwards")
        latest_payment = conn.execute("SELECT MAX(occurred_at) FROM payment_ledger WHERE case_id=? AND loan_id=?", (c["case_id"], s["loan_id"])).fetchone()[0]
        if latest_payment and at < instant(latest_payment):
            raise CaseConflict("Snapshot predates a posted payment/reversal")
        conn.execute("""UPDATE case_exposures SET overdue_vnd=?,principal_vnd=?,interest_vnd=?,dpd=?,
            balance_verified=1,source_version=?,source_as_of=?,snapshot_hash=? WHERE case_id=? AND loan_id=?""",
            (*values, s["dpd"], version, at.isoformat(), fingerprint, c["case_id"], s["loan_id"]))

    def _wrapup(self, conn, c, p, now):
        if c["lifecycle"] != "OPEN" or c["contact_hold_reason"]:
            raise CaseConflict("Case closed or held; late wrapup cannot reopen it")
        if p["outcome"] not in {"PTP_AGREED", "REFUSED", "BUSY_NO_ANSWER"}:
            raise ValueError("Unsupported wrapup outcome")
        amount, due = None, None
        if p["outcome"] == "PTP_AGREED":
            amount = vnd(p.get("ptp_amount"))
            if not amount:
                raise ValueError("PTP amount must be positive")
            date = p.get("ptp_date") or ""
            due = instant(datetime.fromisoformat(date).replace(hour=23, minute=59, second=59, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))) if len(date) == 10 else instant(date)
            if due <= now:
                raise ValueError("PTP due date must be in the future")
            loan = p.get("loan_id") or c["loan_id"]
            if not any(e["loan_id"] == loan for e in self._exposures(conn, c)):
                raise ValueError("PTP loan is not linked to case")
            if conn.execute("SELECT 1 FROM ptps WHERE case_id=? AND loan_id=? AND status IN ('SCHEDULED','PARTIALLY_KEPT')", (c["case_id"], loan)).fetchone():
                raise CaseConflict("An active promise already exists for this exposure")
            conn.execute("INSERT INTO ptps(ptp_id,case_id,loan_id,amount_vnd,created_at,due_at,status,data_origin) VALUES(?,?,?,?,?,?,'SCHEDULED',?)", (str(uuid4()), c["case_id"], loan, amount, now.isoformat(), due.isoformat(), c["data_origin"]))
        conn.execute("""INSERT INTO case_interactions(interaction_id,case_id,channel,collector_name,timestamp,outcome,outcome_label,
            ptp_amount,ptp_date,notes,sentiment,guardrail_token,created_at,data_origin) VALUES(?,?,'VOICE','Demo collector',?,?,?,?,?,?,'UNASSESSED',?,?,?)""",
            (str(uuid4()), c["case_id"], now.isoformat(), p["outcome"], p["outcome"], amount, due.isoformat() if due else None, p.get("notes"), p.get("guardrail_token"), now.isoformat(), c["data_origin"]))

    def _payment(self, conn, c, p, now):
        if not isinstance(p["event_id"], str) or not p["event_id"].strip() or len(p["event_id"]) > 128:
            raise ValueError("Valid event_id required")
        if p["debtor_cif"] != c["debtor_cif"] or not any(e["loan_id"] == p["loan_id"] for e in self._exposures(conn, c)):
            raise ValueError("Payment identity mismatch")
        amount, at = vnd(p["amount_vnd"]), instant(p["occurred_at"])
        if not amount or at > now:
            raise ValueError("Positive posted payment and non-future timestamp required")
        kind = p.get("kind", "POSTED")
        reversal = p.get("reverses_event_id")
        ptp_id = p.get("ptp_id")
        existing = conn.execute("SELECT * FROM payment_ledger WHERE event_id=?", (p["event_id"],)).fetchone()
        identity = (c["case_id"], p["loan_id"], p["debtor_cif"], kind, amount, at.isoformat(), reversal, ptp_id)
        if existing:
            if tuple(existing[k] for k in ("case_id", "loan_id", "debtor_cif", "kind", "amount_vnd", "occurred_at", "reverses_event_id", "ptp_id")) != identity:
                raise CaseConflict("Conflicting payment event_id")
            return False
        allocated = 0
        if kind == "REVERSED":
            original = conn.execute("SELECT * FROM payment_ledger WHERE event_id=?", (reversal,)).fetchone()
            if not original or original["kind"] != "POSTED" or (original["case_id"], original["loan_id"], original["amount_vnd"]) != (c["case_id"], p["loan_id"], amount) or at < instant(original["occurred_at"]) or ptp_id:
                raise CaseConflict("Full reversal must reference a matching posted event; replay after original arrives")
            if conn.execute("SELECT 1 FROM payment_ledger WHERE reverses_event_id=?", (reversal,)).fetchone():
                raise CaseConflict("Payment already reversed")
            if c["resolution"] == "CURED":
                c["lifecycle"], c["resolution"] = "PROBATION", None
            # Existing snapshots predate reconciliation even if timestamps coincide.
            conn.execute("UPDATE case_exposures SET balance_verified=0 WHERE case_id=? AND loan_id=?", (c["case_id"], p["loan_id"]))
        elif kind == "POSTED" and not reversal:
            if ptp_id:
                promise = self._ptp(conn, c, ptp_id)
                if promise["loan_id"] != p["loan_id"] or at < instant(promise["created_at"]):
                    raise ValueError("Payment does not match PTP exposure/time window")
                allocated = amount
        else:
            raise ValueError("Invalid payment kind/reversal")
        conn.execute("INSERT INTO payment_ledger VALUES(?,?,?,?,?,?,?,?,?,?,?)", (p["event_id"], *identity, allocated, c["data_origin"]))
        return True

    def _recompute_ptps(self, conn, c):
        for p in conn.execute("SELECT * FROM ptps WHERE case_id=? AND status NOT IN ('UNVERIFIED','CANCELLED')", (c["case_id"],)).fetchall():
            payments = conn.execute("SELECT p.* FROM payment_ledger p WHERE p.ptp_id=? AND p.kind='POSTED' AND NOT EXISTS(SELECT 1 FROM payment_ledger r WHERE r.reverses_event_id=p.event_id)", (p["ptp_id"],)).fetchall()
            total = sum(r["allocated_vnd"] for r in payments)
            on_time = sum(r["allocated_vnd"] for r in payments if instant(r["occurred_at"]) <= instant(p["due_at"]))
            complete = p["observed_through"] and instant(p["observed_through"]) >= instant(p["due_at"])
            status = "KEPT" if on_time >= p["amount_vnd"] else "BROKEN" if complete else "PARTIALLY_KEPT" if total else "SCHEDULED"
            conn.execute("UPDATE ptps SET paid_vnd=?,on_time_vnd=?,status=? WHERE ptp_id=?", (total, on_time, status, p["ptp_id"]))
