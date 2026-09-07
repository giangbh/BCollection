import { useCallback, useEffect, useRef, useState } from "react";
import { CalendarClock, ArrowUpRight, RefreshCw, PhoneOff } from "lucide-react";
import type {
  CommandResult,
  GuardrailResult,
  Persona,
  Runtime,
  Section,
  Workspace,
} from "./types";
import { ApiError, errorText, post, request } from "./api";
import { actionCopy, dateTime, label, nextAction, stale } from "./model";
import {
  CaseHeader,
  CaseTimeline,
  EvidencePanel,
  ExposureTable,
  GuardrailPanel,
  PtpPaymentPanel,
  ScopeSummary,
} from "./Panels";

type FormMode =
  | "schedule_contact"
  | "decision_feedback"
  | "reconcile"
  | "cancel_schedule"
  | "wrapup";
interface Props {
  caseId: string;
  section: Section;
  setSection: (s: Section) => void;
  runtime: Runtime | null;
  onLocked: (locked: boolean) => void;
}

export function CaseWorkspacePage({
  caseId,
  section,
  setSection,
  runtime,
  onLocked,
}: Props) {
  const [w, setW] = useState<Workspace | null>(null);
  const [loading, setLoading] = useState(true),
    [loadError, setLoadError] = useState("");
  const [customer, setCustomer] = useState(false),
    [profile, setProfile] = useState(false);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const [conflict, setConflict] = useState(false),
    [mode, setMode] = useState<FormMode | null>(null);
  const [reason, setReason] = useState(""),
    [when, setWhen] = useState(""),
    [decision, setDecision] = useState("ACCEPT");
  const [outcome, setOutcome] = useState("BUSY_NO_ANSWER"),
    [ptpAmount, setPtpAmount] = useState(""),
    [ptpDate, setPtpDate] = useState(""),
    [ptpLoan, setPtpLoan] = useState("");
  const [call, setCall] = useState<"IDLE" | "CONNECTED" | "WRAPUP">("IDLE");
  const [guard, setGuard] = useState<GuardrailResult | null>(null),
    [guardMessage, setGuardMessage] = useState("");
  const [persona, setPersona] = useState<Persona | null>(null),
    [personaError, setPersonaError] = useState("");
  const [now, setNow] = useState(Date.now());
  const alive = useRef(false),
    sequence = useRef(0),
    readAbort = useRef<AbortController>();
  const token = useRef("");
  const command = useRef<{ key: string; id: string; version: number } | null>(
    null,
  );
  const base = `/api/cases/${encodeURIComponent(caseId)}`;
  const writable =
    !!runtime &&
    ["demo", "test"].includes(runtime.mode) &&
    !runtime.integration_read_only &&
    !loadError;

  const load = useCallback(async () => {
    readAbort.current?.abort();
    const abort = new AbortController();
    readAbort.current = abort;
    const seq = ++sequence.current;
    setLoading(true);
    setLoadError("");
    try {
      const data = await request<Workspace>(`${base}/workspace`, {
        signal: abort.signal,
      });
      if (
        data.case?.case_id !== caseId ||
        !Array.isArray(data.case_scope?.exposures) ||
        !Array.isArray(data.customer_scope?.exposures)
      )
        throw new Error("Dữ liệu workspace không đúng hồ sơ yêu cầu.");
      if (alive.current && seq === sequence.current) {
        setW(data);
        setPersona(null);
        setPersonaError("");
        setNow(Date.now());
      }
      return true;
    } catch (e) {
      if (!abort.signal.aborted && alive.current && seq === sequence.current)
        setLoadError(errorText(e));
      return false;
    } finally {
      if (alive.current && seq === sequence.current) setLoading(false);
    }
  }, [base, caseId]);

  useEffect(() => {
    alive.current = true;
    void load();
    const timer = window.setInterval(() => setNow(Date.now()), 15000);
    return () => {
      alive.current = false;
      readAbort.current?.abort();
      clearInterval(timer);
    };
  }, [load]);
  useEffect(() => {
    onLocked(busy || call !== "IDLE" || mode !== null);
    return () => onLocked(false);
  }, [busy, call, mode, onLocked]);

  const reload = async () => {
    const ok = await load();
    setGuard(null);
    setGuardMessage("");
    if (ok && conflict) {
      command.current = null;
      setConflict(false);
      setError("");
      setNotice(
        "Đã tải phiên bản mới. Nội dung nhập vẫn được giữ; rà soát đề xuất và dữ liệu trước khi gửi lại.",
      );
    }
  };
  const perform = async (
    kind: string,
    payload: Record<string, unknown>,
  ): Promise<boolean> => {
    if (!w || !writable || busy || conflict) return false;
    setBusy(true);
    setError("");
    setNotice("");
    const key = JSON.stringify({ kind, payload });
    if (!command.current || command.current.key !== key)
      command.current = {
        key,
        id: crypto.randomUUID(),
        version: w.case.case_version,
      };
    const envelope = {
      command_id: command.current.id,
      expected_version: command.current.version,
    };
    try {
      await post<CommandResult>(
        kind === "wrapup"
          ? `${base}/call-wrapup`
          : kind === "balance_check"
            ? `${base}/balance-check`
            : `${base}/commands/${kind}`,
        kind === "wrapup"
          ? { ...envelope, ...payload }
          : kind === "balance_check"
            ? envelope
            : { ...envelope, payload },
      );
      command.current = null;
      if (!alive.current) return true;
      setMode(null);
      setReason("");
      setGuard(null);
      if (kind === "wrapup") {
        setCall("IDLE");
        token.current = "";
      }
      const refreshed = await load();
      if (alive.current)
        setNotice(
          refreshed
            ? "Đã lưu vào hệ thống và tải lại trạng thái. Không có cuộc gọi hay tin nhắn thật được gửi."
            : "Đã lưu thành công, nhưng chưa tải lại được trạng thái. Không gửi lại lệnh; hãy tải lại dữ liệu.",
        );
      return true;
    } catch (e) {
      if (alive.current) {
        setError(errorText(e));
        if (e instanceof ApiError && e.status === 409) setConflict(true);
      }
      return false;
    } finally {
      if (alive.current) setBusy(false);
    }
  };

  const startCall = async () => {
    if (
      !w ||
      !writable ||
      busy ||
      call !== "IDLE" ||
      mode ||
      nextAction(w) !== "CHECK_CONTACT"
    )
      return;
    setBusy(true);
    setError("");
    setGuard(null);
    setGuardMessage("Đang kiểm tra Core và guardrail...");
    try {
      const result = await post<GuardrailResult>(`${base}/call-intent`, {
        target_party_id: w.case.debtor_cif,
        channel: "VOICE",
        expected_version: w.case.case_version,
      });
      if (!alive.current) return;
      setGuard(result);
      if (result.is_allowed && result.guardrail_token) {
        token.current = result.guardrail_token;
        setCall("CONNECTED");
        setGuardMessage(
          "Đã kiểm tra cho cuộc gọi mô phỏng đang mở; không dùng lại cho lần sau.",
        );
      } else {
        setGuardMessage(
          result.blocking_reason || "Chưa đủ xác nhận. Không mở cuộc gọi.",
        );
        await load();
      }
    } catch (e) {
      if (alive.current) {
        setGuardMessage("Không có quyền liên hệ hiệu lực.");
        setError(errorText(e));
        if (e instanceof ApiError && e.status === 409) setConflict(true);
      }
    } finally {
      if (alive.current) setBusy(false);
    }
  };
  const open = (m: FormMode) => {
    if (!busy) {
      setMode(m);
      setError("");
      setNotice("");
      setReason("");
    }
  };

  if (!w)
    return (
      <main className="bc-content">
        <h1>Hồ sơ xử lý</h1>
        {loading ? (
          <p role="status" className="bc-callout">
            Đang tải dữ liệu hồ sơ...
          </p>
        ) : (
          <>
            <p role="alert" className="bc-error">
              {loadError || "Không có dữ liệu."}
            </p>
            <button className="bc-button" onClick={load}>
              Thử lại
            </button>
          </>
        )}
      </main>
    );
  const action = nextAction(w, now),
    copy = actionCopy[action],
    scope = customer ? w.customer_scope : w.case_scope;
  const activeSchedule = w.contact_schedules.find(
    (s) => s.status === "PLANNED",
  );
  const canPlan =
    writable &&
    w.case.lifecycle === "OPEN" &&
    !w.case.contact_hold_reason &&
    call === "IDLE";
  const canCheck =
    writable &&
    action === "CHECK_CONTACT" &&
    !busy &&
    !conflict &&
    !mode &&
    call === "IDLE" &&
    !loading;
  const primary = () => {
    if (action === "BALANCE_CHECK") void perform("balance_check", {});
    else if (action === "CHECK_CONTACT") void startCall();
    else if (action === "WAIT_SCHEDULE") open("schedule_contact");
    else setSection("ptp");
  };
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!mode || !reason.trim()) return;
    if (mode === "schedule_contact")
      void perform(mode, {
        scheduled_at: when + ":00+07:00",
        channel: "VOICE",
        reason,
      });
    else if (mode === "decision_feedback")
      void perform(mode, {
        recommendation_id: w.next_action.recommendation_id,
        recommendation_kind: w.next_action.kind,
        decision,
        reason,
      });
    else if (mode === "cancel_schedule")
      void perform(mode, { schedule_id: activeSchedule?.schedule_id, reason });
    else if (mode === "reconcile") void perform(mode, { reason });
    else
      void perform("wrapup", {
        guardrail_token: token.current,
        outcome,
        notes: reason,
        loan_id: ptpLoan || w.case.loan_id,
        ptp_amount: outcome === "PTP_AGREED" ? Number(ptpAmount) : null,
        ptp_date: outcome === "PTP_AGREED" ? ptpDate : null,
      });
  };

  return (
    <main className="bc-content">
      <CaseHeader
        w={w}
        profile={profile}
        toggleProfile={() => setProfile(!profile)}
      />
      <div className="bc-scope-line">
        <div className="bc-segment" role="group" aria-label="Phạm vi dữ liệu">
          <button aria-pressed={!customer} onClick={() => setCustomer(false)}>
            Case này · {w.case_scope.exposures.length} khoản vay
          </button>
          <button aria-pressed={customer} onClick={() => setCustomer(true)}>
            Khách hàng · Đã ghi nhận ({w.customer_scope.exposures.length})
          </button>
        </div>
        <button
          className="bc-link"
          disabled={busy || call === "CONNECTED"}
          onClick={reload}
        >
          <RefreshCw />
          {loading ? "Đang tải..." : "Tải lại dữ liệu"}
        </button>
      </div>
      {loadError && (
        <p role="alert" className="bc-error">
          {loadError} · Dữ liệu đang hiển thị có thể cũ; tạm khóa tác nghiệp.
        </p>
      )}
      <ScopeSummary
        scope={scope}
        customer={customer}
        onEvidence={() => setSection("evidence")}
      />
      <div className="bc-states">
        <span>
          Giai đoạn<strong>{label(w.case.stage)}</strong>
        </span>
        <span>
          Nghĩa vụ
          <strong>
            {w.case_scope.exposures.every(
              (e) => e.balance_verified && !e.conflict,
            ) && w.case_scope.exposures.length
              ? w.case_scope.overdue_vnd === 0 && w.case_scope.max_dpd === 0
                ? "Hết quá hạn"
                : "Còn quá hạn"
              : "Chưa xác minh đầy đủ"}
          </strong>
        </span>
        <span>
          PTP<strong>{w.ptps.length} cam kết riêng</strong>
        </span>
      </div>
      <section
        className={`bc-next ${action === "RECONCILE" ? "hold" : ""}`}
        aria-label="Việc cần làm tiếp theo"
      >
        <div className="bc-next-icon">
          <CalendarClock />
        </div>
        <div>
          <div className="bc-eyebrow">
            VIỆC TIẾP THEO · THEO TRẠNG THÁI CASE
          </div>
          <h2>{copy.title}</h2>
          <small>{copy.note}</small>
          {activeSchedule && (
            <small>Lịch đã lưu: {dateTime(activeSchedule.scheduled_at)}</small>
          )}
        </div>
        <div className="bc-next-action">
          <button
            className="bc-button primary"
            disabled={
              busy ||
              loading ||
              conflict ||
              call !== "IDLE" ||
              mode !== null ||
              (!writable && !["VIEW_RESOLUTION", "RECONCILE"].includes(action))
            }
            onClick={primary}
          >
            {copy.button}
          </button>
          <small>
            {!writable
              ? "Chế độ chỉ đọc / chưa đủ dữ liệu"
              : "Không tự động thực hiện liên hệ"}
          </small>
        </div>
      </section>
      {notice && (
        <p className="bc-message" role="status">
          {notice}
        </p>
      )}
      {error && (
        <p className="bc-error" role="alert">
          {error}
        </p>
      )}
      {call === "CONNECTED" && (
        <section className="bc-editor">
          <h2>Cuộc gọi mô phỏng đang mở</h2>
          <p>Không kết nối tổng đài hoặc gọi số điện thoại thật.</p>
          <button
            className="bc-button"
            onClick={() => {
              setCall("WRAPUP");
              open("wrapup");
            }}
          >
            <PhoneOff />
            Kết thúc & ghi nhận kết quả
          </button>
        </section>
      )}
      {mode && (
        <section className="bc-editor" aria-label="Biểu mẫu tác nghiệp">
          <div className="bc-panel-head">
            <div>
              <h2>
                {
                  {
                    schedule_contact: "Lên lịch / điều chỉnh lịch",
                    cancel_schedule: "Hủy lịch liên hệ",
                    decision_feedback: "Ghi nhận quyết định",
                    reconcile: "Xác nhận đã rà soát",
                    wrapup: "Ghi nhận kết quả cuộc gọi mô phỏng",
                  }[mode]
                }
              </h2>
              <small>
                Case {w.case.case_id} · v{w.case.case_version} · Lưu vào backend{" "}
                {runtime?.mode}
              </small>
            </div>
            <button
              className="bc-link"
              disabled={busy}
              onClick={() => {
                setMode(null);
                if (call === "WRAPUP") setCall("IDLE");
              }}
            >
              Đóng (chưa lưu)
            </button>
          </div>
          <form onSubmit={submit}>
            {mode === "schedule_contact" && (
              <>
                <label htmlFor="schedule-at">
                  Thời gian liên hệ · Asia/Ho_Chi_Minh
                </label>
                <input
                  id="schedule-at"
                  type="datetime-local"
                  required
                  value={when}
                  onChange={(e) => setWhen(e.target.value)}
                />
                <p className="bc-table-note">
                  Đây là kế hoạch cán bộ. Không tự ghi nhận rằng khách hàng đã
                  đồng ý khung giờ này.
                </p>
              </>
            )}
            {mode === "decision_feedback" && (
              <>
                <p className="bc-callout">
                  Đề xuất đang phản hồi: {actionCopy[w.next_action.kind].title}{" "}
                  · Quy tắc {w.next_action.recommendation_id}, không phải AI.
                </p>
                <label htmlFor="decision">Quyết định</label>
                <select
                  id="decision"
                  value={decision}
                  onChange={(e) => setDecision(e.target.value)}
                >
                  <option value="ACCEPT">Chấp nhận đề xuất</option>
                  <option value="ADJUST">Điều chỉnh đề xuất</option>
                  <option value="DECLINE">Không áp dụng</option>
                </select>
              </>
            )}
            {mode === "reconcile" && (
              <p className="bc-callout">
                Chỉ xác nhận khi Core mới nhất đã bao phủ payment/reversal và
                mọi nghĩa vụ. Không tự thay đổi số tiền. Đây là thao tác mô
                phỏng, chưa có maker-checker production.
              </p>
            )}
            {mode === "wrapup" && (
              <>
                <label htmlFor="outcome">Kết quả</label>
                <select
                  id="outcome"
                  value={outcome}
                  onChange={(e) => setOutcome(e.target.value)}
                >
                  <option value="BUSY_NO_ANSWER">Không nghe máy</option>
                  <option value="REFUSED">Chưa thống nhất thanh toán</option>
                  <option value="PTP_AGREED">Đồng ý cam kết PTP</option>
                </select>
                {outcome === "PTP_AGREED" && (
                  <div className="bc-detail-grid">
                    <div>
                      <label htmlFor="ptp-loan">Khoản vay áp dụng</label>
                      <select
                        id="ptp-loan"
                        value={ptpLoan || w.case.loan_id}
                        onChange={(e) => setPtpLoan(e.target.value)}
                      >
                        {w.case_scope.exposures.map((l) => (
                          <option key={l.loan_id}>{l.loan_id}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label htmlFor="ptp-amount">
                        Số tiền cam kết (VND nguyên)
                      </label>
                      <input
                        id="ptp-amount"
                        type="number"
                        min="1"
                        step="1"
                        max="9000000000000000"
                        required
                        value={ptpAmount}
                        onChange={(e) => setPtpAmount(e.target.value)}
                      />
                    </div>
                    <div>
                      <label htmlFor="ptp-date">
                        Ngày hẹn · Hết ngày giờ Việt Nam
                      </label>
                      <input
                        id="ptp-date"
                        type="date"
                        required
                        value={ptpDate}
                        onChange={(e) => setPtpDate(e.target.value)}
                      />
                    </div>
                  </div>
                )}
              </>
            )}
            <label htmlFor="reason">Lý do / nội dung ghi nhận</label>
            <textarea
              id="reason"
              required
              maxLength={2000}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
            <div className="bc-actions-row">
              <button
                className="bc-button primary"
                type="submit"
                disabled={!writable || busy || conflict || loading}
              >
                {busy ? "Đang lưu..." : "Lưu vào hệ thống"}
              </button>
              <small>
                Không tạo outcome thu hồi thành công từ lời hứa hoặc quyết định.
              </small>
            </div>
          </form>
        </section>
      )}
      <nav className="bc-tabs" role="tablist" aria-label="Chi tiết hồ sơ">
        {(["work", "ptp", "evidence"] as Section[]).map((s) => (
          <button
            key={s}
            role="tab"
            id={`tab-${s}`}
            aria-controls={`panel-${s}`}
            aria-selected={section === s}
            onClick={() => setSection(s)}
          >
            {
              {
                work: "Tác nghiệp",
                ptp: "PTP & thanh toán",
                evidence: "EWS & bằng chứng",
              }[s]
            }
          </button>
        ))}
      </nav>
      <div className="bc-grid">
        <div
          className="bc-stack"
          role="tabpanel"
          id={`panel-${section}`}
          aria-labelledby={`tab-${section}`}
        >
          {section === "work" && (
            <>
              <ExposureTable
                scope={scope}
                caseId={caseId}
                customer={customer}
              />
              <PtpPaymentPanel
                w={w}
                compact
                onDetails={() => setSection("ptp")}
              />
              <CaseTimeline w={w} />
            </>
          )}
          {section === "ptp" && (
            <>
              <PtpPaymentPanel w={w} />
              <section className="bc-panel">
                <h2>Thao tác đối soát</h2>
                <p className="bc-table-note">
                  Không nhập payment giả hoặc sửa số dư từ giao diện.
                </p>
                <div className="bc-actions-row">
                  <button
                    className="bc-button"
                    disabled={
                      !writable ||
                      busy ||
                      loading ||
                      conflict ||
                      call !== "IDLE" ||
                      !!mode
                    }
                    onClick={() => perform("balance_check", {})}
                  >
                    Đối soát số dư từ Core
                  </button>
                  <button
                    className="bc-button"
                    disabled={
                      !writable ||
                      busy ||
                      conflict ||
                      stale(w.case_scope, now) ||
                      !w.case.contact_hold_reason ||
                      !!mode ||
                      call !== "IDLE"
                    }
                    onClick={() => open("reconcile")}
                  >
                    Xác nhận đã rà soát
                  </button>
                </div>
              </section>
              <CaseTimeline w={w} />
            </>
          )}
          {section === "evidence" && (
            <EvidencePanel
              w={w}
              scope={scope}
              persona={persona}
              personaError={personaError}
              allowPersona={writable && !busy}
              onLoadPersona={async () => {
                const generation = sequence.current;
                setPersonaError("");
                try {
                  const p = await request<Persona>(`${base}/persona`);
                  if (alive.current && generation === sequence.current) setPersona(p);
                } catch (e) {
                  if (alive.current && generation === sequence.current) setPersonaError(errorText(e));
                }
              }}
            />
          )}
        </div>
        <aside className="bc-stack bc-rail" aria-label="Hỗ trợ quyết định">
          <section className="bc-panel">
            <div className="bc-panel-head">
              <h2>Hỗ trợ quyết định</h2>
              <span className="bc-chip neutral">Theo quy tắc</span>
            </div>
            <p className="bc-aimain">{copy.title}</p>
            <p>{copy.note}</p>
            <button className="bc-link" onClick={() => setSection("evidence")}>
              Nguồn & dữ liệu thiếu <ArrowUpRight />
            </button>
            <button
              className="bc-button"
              disabled={
                !writable ||
                busy ||
                conflict ||
                !!mode ||
                call !== "IDLE" ||
                loading
              }
              onClick={() => open("decision_feedback")}
            >
              Ghi nhận quyết định
            </button>
            <p className="bc-safety">
              Phản hồi được lưu kèm đề xuất và phiên bản case, không phải kết
              quả thanh toán.
            </p>
          </section>
          <GuardrailPanel
            reason={
              w.case.lifecycle !== "OPEN"
                ? label(w.case.lifecycle) + " · Không liên hệ"
                : w.case.contact_hold_reason
                ? label(w.case.contact_hold_reason)
                : call === "CONNECTED"
                  ? "Đang gọi mô phỏng"
                  : action === "WAIT_SCHEDULE" ? "Chưa đến lịch liên hệ"
                    : action === "BALANCE_CHECK" ? "Chưa đủ bằng chứng số dư" : "Chưa cấp quyền cho lần gọi mới"
            }
            details={
              guardMessage ||
              (guard?.evaluated_at
                ? `${dateTime(guard.evaluated_at)} · ${guard.policy_version}`
                : "")
            }
            canCheck={canCheck}
            onCheck={startCall}
          />
          <section className="bc-panel">
            <div className="bc-panel-head">
              <h2>Lịch liên hệ</h2>
              <CalendarClock />
            </div>
            {activeSchedule ? (
              <>
                <p>{dateTime(activeSchedule.scheduled_at)}</p>
                <p>{activeSchedule.reason}</p>
                <span className="bc-chip neutral">
                  Kế hoạch · Chưa thực hiện
                </span>
              </>
            ) : (
              <p>Chưa có lịch đang mở.</p>
            )}
            <button
              className="bc-button"
              disabled={!canPlan || busy || conflict || !!mode || loading}
              onClick={() => {
                setWhen("");
                open("schedule_contact");
              }}
            >
              {activeSchedule ? "Điều chỉnh lịch" : "Lên lịch liên hệ"}
            </button>
            {activeSchedule && (
              <button
                className="bc-link"
                disabled={
                  !writable || busy || conflict || !!mode || call !== "IDLE"
                }
                onClick={() => open("cancel_schedule")}
              >
                Hủy lịch đã lưu
              </button>
            )}
            <details>
              <summary>Lịch sử lịch hẹn ({w.contact_schedules.length})</summary>
              {w.contact_schedules.map((s) => (
                <p key={s.schedule_id}>
                  {dateTime(s.scheduled_at)} · {label(s.status)} · {s.reason}
                </p>
              ))}
            </details>
          </section>
          <section className="bc-panel">
            <h2>Quyết định đã lưu</h2>
            {!w.decision_feedback.length && (
              <p className="bc-table-note">Chưa có phản hồi được lưu.</p>
            )}
            {[...w.decision_feedback].reverse().map((f) => (
              <details key={f.feedback_id}>
                <summary>
                  {label(f.decision)} · v{f.case_version}
                </summary>
                <p>
                  {dateTime(f.created_at)} · {f.reason}
                </p>
              </details>
            ))}
          </section>
        </aside>
      </div>
      <footer className="bc-footer">
        <span>
          Case v{w.case.case_version} · {w.case.data_origin} · Asia/Ho_Chi_Minh
        </span>
        <span>EWS chưa kết nối · Không thực hiện cuộc gọi thật</span>
      </footer>
    </main>
  );
}
