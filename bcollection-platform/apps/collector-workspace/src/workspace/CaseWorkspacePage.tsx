import { useCallback, useEffect, useRef, useState } from "react";
import { RefreshCw, PhoneOff } from "lucide-react";
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
import { sections } from "./types";
import { ActionRail } from "./ActionRail";
import { SourceStatus, SourceLoans, CollateralSource, EventIntegrationStatus } from './SourcePanels';
import {
  CustomerHeader,
  CustomerInformation,
  QuickAssessment,
  DebtComposition,
  DpdChart,
  EwsPanel,
  HandoffOutcomes,
  UnconnectedPanel,
} from "./CustomerPanels";
import {
  CaseTimeline,
  EvidencePanel,
  ExposureTable,
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
  onSelectCase: (id: string) => void;
}

export function CaseWorkspacePage({
  caseId,
  section,
  setSection,
  runtime,
  onLocked,
  onSelectCase,
}: Props) {
  const [w, setW] = useState<Workspace | null>(null);
  const [loading, setLoading] = useState(true),
    [loadError, setLoadError] = useState("");
  const [customer, setCustomer] = useState(false);
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
  const [note, setNote] = useState("");
  const [linkedFeedback, setLinkedFeedback] = useState("");
  const editor = useRef<HTMLElement>(null);
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
  const httpBalanceEnabled = runtime?.mode === "demo-http" && !loadError;

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
    onLocked(busy || call !== "IDLE" || mode !== null || !!note.trim());
    return () => onLocked(false);
  }, [busy, call, mode, note, onLocked]);
  useEffect(() => {
    if (mode) {
      editor.current?.scrollIntoView({ block: "start" });
      editor.current
        ?.querySelector<HTMLElement>("input, select, textarea")
        ?.focus({ preventScroll: true });
    }
  }, [mode]);

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
    if (!w || (!writable && !(httpBalanceEnabled && ['balance_check', 'sync_customer', 'sync_payments', 'sync_ews', 'publish_outcomes'].includes(kind))) || busy || conflict) return false;
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
            : ['sync_customer', 'sync_payments', 'sync_ews', 'publish_outcomes'].includes(kind) ? `${base}/${kind.replace(/_/g, '-')}`
            : `${base}/commands/${kind}`,
        kind === "wrapup"
          ? { ...envelope, ...payload }
          : kind === "balance_check"
            ? envelope
            : { ...envelope, payload },
      );
      command.current = null;
      if (!alive.current) return true;
      if (kind === "add_note") setNote("");
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
            ? ['sync_customer', 'sync_payments', 'sync_ews', 'publish_outcomes'].includes(kind)
              ? 'Đã chạy tác vụ tích hợp. Xem trạng thái nguồn và nhật ký Payment / EWS / Outcome để kiểm tra lỗi, pending và receipt. Không thực hiện liên hệ thật.'
              : "Đã lưu vào hệ thống và tải lại trạng thái. Không có cuộc gọi hay tin nhắn thật được gửi."
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
        decision_feedback_id: linkedFeedback || null,
      });
  };

  return (
    <main className="bc-content">
      <CustomerHeader
        w={w}
        onSelectCase={onSelectCase}
        locked={busy || call !== "IDLE" || !!mode || !!note.trim()}
      />
      {runtime?.mode === "demo-http" && (
        <div className="bc-callout">
          REST demo · Customer 360, payment và EWS qua HTTP mock. CIC và tác nghiệp liên hệ thật chưa kết nối.
          <button className="bc-link" disabled={!httpBalanceEnabled || busy || conflict || loading}
            onClick={() => void perform('sync_customer', {})}>Đồng bộ Customer 360</button>
          {([['sync_payments', 'Đồng bộ thanh toán'], ['sync_ews', 'Đồng bộ EWS'], ['publish_outcomes', 'Gửi outcome']] as const).map(([kind, title]) =>
            <button key={kind} className="bc-link" disabled={!httpBalanceEnabled || busy || conflict || loading}
              onClick={() => void perform(kind, {})}>{title}</button>)}
          <button
            className="bc-link"
            disabled={!httpBalanceEnabled || busy || conflict || loading}
            onClick={() => void perform("balance_check", {})}
          >
            Kiểm tra số dư qua REST Core
          </button>
        </div>
      )}
      <SourceStatus w={w} />
      <EventIntegrationStatus w={w} />
      <nav className="bc-tabs" role="tablist" aria-label="Chi tiết hồ sơ">
        {(Object.keys(sections) as Section[]).map((s, i, all) => (
          <button
            key={s}
            role="tab"
            id={`tab-${s}`}
            aria-controls={`panel-${s}`}
            aria-selected={section === s}
            tabIndex={section === s ? 0 : -1}
            onClick={() => setSection(s)}
            onKeyDown={(e) => {
              let next: Section | undefined;
              if (e.key === "ArrowRight") next = all[(i + 1) % all.length];
              if (e.key === "ArrowLeft")
                next = all[(i - 1 + all.length) % all.length];
              if (e.key === "Home") next = all[0];
              if (e.key === "End") next = all[all.length - 1];
              if (next) {
                e.preventDefault();
                setSection(next);
                document.getElementById(`tab-${next}`)?.focus();
              }
            }}
          >
            {sections[s]}
          </button>
        ))}
      </nav>
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
      {section !== "work" && (
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
      )}
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
        <section
          ref={editor}
          className="bc-editor"
          aria-label="Biểu mẫu tác nghiệp"
        >
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
                <label htmlFor="linked-feedback">
                  Quyết định được áp dụng (không bắt buộc)
                </label>
                <select
                  id="linked-feedback"
                  value={linkedFeedback}
                  onChange={(e) => setLinkedFeedback(e.target.value)}
                >
                  <option value="">Không liên kết / chưa xác định</option>
                  {w.decision_feedback
                    .filter((f) => ["ACCEPT", "ADJUST"].includes(f.decision))
                    .map((f) => (
                      <option key={f.feedback_id} value={f.feedback_id}>
                        {label(f.decision)} · v{f.case_version} · {f.reason}
                      </option>
                    ))}
                </select>
                <small>
                  Chỉ chọn khi thực sự áp dụng. Liên kết để theo dõi kết quả,
                  không khẳng định AI gây ra thanh toán.
                </small>
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
      <div className="bc-grid">
        <div
          className="bc-stack"
          role="tabpanel"
          id={`panel-${section}`}
          aria-labelledby={`tab-${section}`}
        >
          {section === "work" && (
            <div className="bc-overview">
              <div className="bc-overview-summary">
                <ScopeSummary
                  scope={scope}
                  loanSource={w.source_data?.loans}
                  customer={customer}
                  onEvidence={() => setSection("evidence")}
                />
              </div>
              <QuickAssessment scope={scope} />
              <div className="bc-overview-loans">
                <ExposureTable
                  scope={scope}
                  caseId={caseId}
                  customer={customer}
                />
              </div>
              <DebtComposition scope={scope} />
              <div className="bc-overview-ews">
                <EwsPanel
                  w={w}
                  compact
                  onDetails={() => setSection("evidence")}
                />
              </div>
              <DpdChart
                history={w.dpd_history?.[customer ? "customer" : "case"]}
              />
              <div className="bc-overview-ptp">
                <PtpPaymentPanel
                  w={w}
                  compact
                  onDetails={() => setSection("ptp")}
                />
              </div>
              <CaseTimeline
                w={w}
                compact
                onDetails={() => setSection("interactions")}
              />
            </div>
          )}
          {section === "customer" && <CustomerInformation w={w} />}
          {section === "loans" && (
            <>
              <SourceLoans w={w} />
              <ScopeSummary
                scope={scope}
                loanSource={w.source_data?.loans}
                customer={customer}
                onEvidence={() => setSection("evidence")}
              />
              <ExposureTable
                scope={scope}
                caseId={caseId}
                customer={customer}
              />
              <DebtComposition scope={scope} />
            </>
          )}
          {section === "treatment" && (
            <>
              <HandoffOutcomes w={w} />
              <CaseTimeline w={w} />
            </>
          )}
          {section === "interactions" && (
            <>
              <CaseTimeline w={w} />
              <section className="bc-panel">
                <h2>Ghi chú đã lưu · Case này</h2>
                {!w.case_notes?.length && (
                  <p className="bc-callout">Chưa có ghi chú.</p>
                )}
                {w.case_notes?.map((n) => (
                  <article className="bc-note" key={n.note_id}>
                    <small>
                      {dateTime(n.created_at)} · {n.author} · {n.data_origin}
                    </small>
                    <p>{n.body}</p>
                  </article>
                ))}
              </section>
            </>
          )}
          {(section === "collateral" || section === "documents") && (
            section === 'collateral' && w.source_data?.collateral.snapshot
              ? <CollateralSource w={w} /> : <UnconnectedPanel section={section} />
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
            <>
              <EwsPanel w={w} />
              <HandoffOutcomes w={w} />
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
                    if (alive.current && generation === sequence.current)
                      setPersona(p);
                  } catch (e) {
                    if (alive.current && generation === sequence.current)
                      setPersonaError(errorText(e));
                  }
                }}
              />
            </>
          )}
        </div>
        <ActionRail
          w={w}
          action={action}
          writable={writable}
          primaryDisabled={
            busy ||
            loading ||
            conflict ||
            call !== "IDLE" ||
            mode !== null ||
            (!writable && !["VIEW_RESOLUTION", "RECONCILE"].includes(action))
          }
          editDisabled={
            !writable ||
            busy ||
            loading ||
            conflict ||
            !!mode ||
            call !== "IDLE"
          }
          planDisabled={!canPlan || busy || conflict || !!mode || loading}
          canCheck={canCheck}
          busy={busy}
          connected={call === "CONNECTED"}
          guard={guard}
          guardMessage={guardMessage}
          note={note}
          setNote={setNote}
          setSection={setSection}
          onPrimary={primary}
          onCheck={startCall}
          onSaveNote={() => {
            void perform("add_note", { reason: note });
          }}
          onOpen={(m) => {
            if (m === "schedule_contact") setWhen("");
            open(m);
          }}
        />
      </div>
      <footer className="bc-footer">
        <span>
          Case v{w.case.case_version} · {w.case.data_origin} · Asia/Ho_Chi_Minh
        </span>
        <span>{w.capabilities?.ews_ingress === 'RECEIVED' ? 'Đã nhận EWS demo' : 'EWS chưa đồng bộ hoặc cần kiểm tra'} · Không thực hiện cuộc gọi thật</span>
      </footer>
    </main>
  );
}
