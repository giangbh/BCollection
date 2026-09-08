import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  CalendarClock,
  ArrowUpRight,
  RefreshCw,
  PhoneOff,
  X,
  Phone,
  Check,
  Clock,
  ShieldCheck,
  Mic,
  MicOff,
} from "lucide-react";
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
import { AiSpeechWrapupModal } from "./AiSpeechWrapupModal";
import {
  CaseHeader,
  ScopeSummary,
  QuickRiskAssessment,
  ExposureTable,
  DebtStructureCard,
  EwsSignalsCard,
  DpdHistoryCard,
  RecentPtpCard,
  RecentInteractionsCard,
  NextActionCard,
  GuardrailCard,
  AiRecommendationsCard,
  PtpPaymentPanel,
  EvidencePanel,
  CaseTimeline,
  CustomerInfoPanel,
  CollateralPanel,
  DocumentsPanel,
} from "./Panels";
import { QuickNotes } from "./QuickNotes";

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
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [customer, setCustomer] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [conflict, setConflict] = useState(false);
  const [mode, setMode] = useState<FormMode | null>(null);

  // Form states
  const [reason, setReason] = useState("");
  const [when, setWhen] = useState("");
  const [decision, setDecision] = useState("ACCEPT");
  const [outcome, setOutcome] = useState("BUSY_NO_ANSWER");
  const [ptpAmount, setPtpAmount] = useState("");
  const [ptpDate, setPtpDate] = useState("");
  const [ptpLoan, setPtpLoan] = useState("");

  // Call simulation
  const [call, setCall] = useState<"IDLE" | "CONNECTED" | "WRAPUP">("IDLE");
  const [callSeconds, setCallSeconds] = useState(6);
  const [isMuted, setIsMuted] = useState(false);
  const [guard, setGuard] = useState<GuardrailResult | null>(null);
  const [guardMessage, setGuardMessage] = useState("");

  useEffect(() => {
    if (call !== "CONNECTED") return;
    const interval = setInterval(() => {
      setCallSeconds((s) => s + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [call]);

  const formatTimer = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  // Persona
  const [persona, setPersona] = useState<Persona | null>(null);
  const [personaError, setPersonaError] = useState("");
  const [now, setNow] = useState(Date.now());

  const alive = useRef(false);
  const sequence = useRef(0);
  const readAbort = useRef<AbortController>();
  const token = useRef("");
  const command = useRef<{ key: string; id: string; version: number } | null>(null);

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
      ) {
        throw new Error("Dữ liệu workspace không đúng hồ sơ yêu cầu.");
      }
      if (alive.current && seq === sequence.current) {
        setW(data);
        setPersona(null);
        setPersonaError("");
        setNow(Date.now());
      }
      return true;
    } catch (e) {
      if (!abort.signal.aborted && alive.current && seq === sequence.current) {
        setLoadError(errorText(e));
      }
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
      window.clearInterval(timer);
    };
  }, [load]);

  useEffect(() => {
    onLocked(mode !== null || call !== "IDLE");
  }, [call, mode, onLocked]);

  const reload = () => {
    setConflict(false);
    command.current = null;
    void load();
  };

  if (loading && !w) {
    return (
      <div className="bc-loading" role="status" aria-busy="true">
        Đang tải hồ sơ {caseId}...
      </div>
    );
  }

  if (loadError && !w) {
    return (
      <div className="bc-error-state" role="alert">
        <h2>Không thể tải hồ sơ</h2>
        <p>{loadError || "Hồ sơ không tồn tại."}</p>
        <button className="bc-button primary" onClick={() => void load()}>
          Thử tải lại
        </button>
      </div>
    );
  }

  if (!w) return null;

  const scope = customer ? w.customer_scope : w.case_scope;
  const action = nextAction(w, now);
  const copy = actionCopy[action];
  const activeSchedule = w.contact_schedules.find((s) => s.status === "PLANNED");

  const open = (nextMode: FormMode) => {
    setError("");
    setNotice("");
    setMode(nextMode);
    setReason("");
    if (nextMode === "schedule_contact") {
      setWhen(
        activeSchedule?.scheduled_at?.slice(0, 16) ||
          new Date(Date.now() + 3600000).toISOString().slice(0, 16),
      );
    }
    if (nextMode === "wrapup") {
      const initOutcome = (w.case.dpd ?? 29) > 20 ? "REFUSED" : "PTP_AGREED";
      setOutcome(initOutcome);
      if (initOutcome === "REFUSED") {
        setReason(
          "Khách hàng từ chối cam kết ngày trả cụ thể, phản ứng bực bội khi bị nhắc nợ. Đề xuất chuyển biện pháp cảnh báo văn bản.",
        );
      } else {
        setReason(
          "Khách xác nhận bận công tác quên lịch nộp, cam kết chuyển khoản đủ qua SmartBanking vào ngày hẹn thanh toán.",
        );
      }
      setPtpLoan(w.case_scope.exposures[0]?.loan_id || w.case.loan_id);
      setPtpAmount(String(w.case.overdue_amount || 5000000));
      const d = new Date(Date.now() + 7 * 86400000);
      setPtpDate(d.toISOString().slice(0, 10));
    }
  };

  const perform = async (endpoint: string, payload: unknown, commandKey?: string) => {
    setBusy(true);
    setError("");
    setNotice("");

    // Command deduplication & retry preservation matching test requirements
    let body = payload as Record<string, unknown>;
    if (commandKey) {
      if (
        !command.current ||
        command.current.key !== commandKey ||
        command.current.version !== w.case.case_version
      ) {
        command.current = {
          key: commandKey,
          id: `cmd-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
          version: w.case.case_version,
        };
      }
      body = {
        command_id: command.current.id,
        expected_version: command.current.version,
        payload: payload,
      };
    }

    try {
      await post<CommandResult>(`${base}/${endpoint}`, body);
      setNotice("Đã lưu vào hệ thống");
      command.current = null;
      await load();
      return true;
    } catch (e) {
      setError(errorText(e));
      if (e instanceof ApiError && e.status === 409) {
        setConflict(true);
      }
      return false;
    } finally {
      setBusy(false);
    }
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!mode || !w) return;

    if (mode === "schedule_contact") {
      const ok = await perform(
        "commands/schedule_contact",
        {
          scheduled_at: new Date(when).toISOString(),
          channel: "VOICE",
          reason: reason.trim(),
        },
        "schedule",
      );
      if (ok) setMode(null);
    } else if (mode === "cancel_schedule") {
      if (!activeSchedule) return;
      const ok = await perform(
        "commands/cancel_schedule",
        {
          schedule_id: activeSchedule.schedule_id,
          reason: reason.trim(),
        },
        "cancel",
      );
      if (ok) setMode(null);
    } else if (mode === "decision_feedback") {
      const ok = await perform(
        "commands/decision_feedback",
        {
          recommendation_id: w.next_action.recommendation_id,
          recommendation_kind: w.next_action.kind,
          decision,
          reason: reason.trim(),
        },
        "feedback",
      );
      if (ok) setMode(null);
    } else if (mode === "reconcile") {
      const ok = await perform("reconcile", {
        reason: reason.trim(),
      });
      if (ok) setMode(null);
    } else if (mode === "wrapup") {
      const ok = await perform("call-wrapup", {
        command_id: `cmd-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
        expected_version: w.case.case_version,
        guardrail_token: token.current,
        outcome,
        notes: reason.trim(),
        loan_id: ptpLoan || w.case.loan_id,
        ptp_amount: outcome === "PTP_AGREED" ? parseInt(ptpAmount, 10) : undefined,
        ptp_date: outcome === "PTP_AGREED" ? ptpDate : undefined,
        ptp:
          outcome === "PTP_AGREED"
            ? {
                loan_id: ptpLoan || w.case.loan_id,
                amount_vnd: parseInt(ptpAmount, 10),
                due_date: ptpDate,
              }
            : undefined,
      });
      if (ok) {
        setCall("IDLE");
        setMode(null);
      }
    }
  };

  const handleCallIntent = async () => {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await post<GuardrailResult>(`${base}/call-intent`, {
        expected_version: w.case.case_version,
        target_party_id: w.case.debtor_cif,
        channel: "VOICE",
      });
      setGuard(result);
      if (result.is_allowed && result.guardrail_token) {
        token.current = result.guardrail_token;
        setCallSeconds(6);
        setIsMuted(false);
        setCall("CONNECTED");
        setGuardMessage("Đã đủ điều kiện. Cuộc gọi mô phỏng đang mở.");
      } else {
        setGuardMessage(result.blocking_reason || "Chưa đủ điều kiện liên hệ.");
      }
    } catch (e) {
      setError(errorText(e));
      if (e instanceof ApiError && e.status === 409) setConflict(true);
    } finally {
      setBusy(false);
    }
  };

  const isBlocked =
    !writable ||
    w.case.lifecycle !== "OPEN" ||
    !!w.case.contact_hold_reason ||
    !!loadError;

  const canCheck =
    writable &&
    !isBlocked &&
    action === "CHECK_CONTACT" &&
    !busy &&
    !conflict &&
    !mode &&
    call === "IDLE" &&
    !loading;

  const tabs: { key: Section; title: string; ariaName: string }[] = [
    { key: "work", title: "Tổng quan", ariaName: "Tác nghiệp" },
    { key: "customer", title: "Thông tin khách hàng", ariaName: "Thông tin khách hàng" },
    { key: "credit", title: "Nghĩa vụ tín dụng", ariaName: "Nghĩa vụ tín dụng" },
    { key: "case", title: "Case & xử lý", ariaName: "Case & xử lý" },
    { key: "ptp", title: "PTP & Thanh toán", ariaName: "PTP & thanh toán" },
    { key: "interactions", title: "Lịch sử tương tác", ariaName: "Lịch sử tương tác" },
    { key: "evidence", title: "EWS & Rủi ro", ariaName: "EWS & bằng chứng" },
    { key: "collateral", title: "Tài sản bảo đảm", ariaName: "Tài sản bảo đảm" },
    { key: "documents", title: "Tài liệu", ariaName: "Tài liệu" },
    { key: "other", title: "Khác", ariaName: "Khác" },
  ];

  return (
    <div className="bc-workspace-page">
      {/* 1. Header with Breadcrumb, Customer info & Case card */}
      <CaseHeader
        w={w}
        caseId={caseId}
        customer={customer}
        onToggleScope={(c) => setCustomer(c)}
      />

      {/* Top utility reload action */}
      <div className="bc-action-bar-top">
        <button
          type="button"
          className="bc-link-btn"
          disabled={busy || call === "CONNECTED"}
          onClick={reload}
        >
          <RefreshCw size={14} />
          {loading ? "Đang tải..." : "Tải lại dữ liệu"}
        </button>
      </div>

      {/* Load Error (e.g. 503 during reload while case data is already present) */}
      {loadError && (
        <div className="bc-alert-banner error" role="alert">
          <span>{loadError} · Dữ liệu đang hiển thị có thể cũ; tạm khóa tác nghiệp.</span>
        </div>
      )}

      {/* Notices & Alerts */}
      {notice && (
        <div className="bc-alert-banner success" role="status">
          <Check size={16} />
          <span>{notice}</span>
        </div>
      )}
      {error && (
        <div className="bc-alert-banner error" role="alert">
          <span>{error}</span>
        </div>
      )}

      {/* Call simulation active bar with softphone controls and exact heading for tests */}
      {call === "CONNECTED" && (
        <section className="bc-call-active-bar" role="alert">
          <div className="bc-call-active-info">
            <div className="bc-pulse-dot" />
            <Phone size={18} className="bc-pulse-icon" />
            <div>
              <div className="bc-call-bar-title-row">
                <h2 style={{ fontSize: "14px", margin: 0, fontWeight: 700 }}>
                  Cuộc gọi mô phỏng đang mở
                </h2>
                <span className="bc-call-timer-chip">
                  <Clock size={13} />
                  <span>{formatTimer(callSeconds)}</span>
                </span>
                <span className="bc-call-guardrail-chip">
                  <ShieldCheck size={13} />
                  <span>Guardrail L6 Active</span>
                </span>
              </div>
              <small>
                {w.case.full_name} ({w.case.phone_e164 || "+84939158087"}) · Khoản vay {w.case.loan_id} · DPD {w.case.dpd} ngày
              </small>
            </div>
          </div>
          <div className="bc-call-actions">
            <button
              type="button"
              className={`bc-button secondary ${isMuted ? "muted" : ""}`}
              onClick={() => setIsMuted(!isMuted)}
              title={isMuted ? "Bật mic" : "Tắt mic"}
            >
              {isMuted ? <MicOff size={16} /> : <Mic size={16} />}
              <span>{isMuted ? "Bật Mic" : "Tắt Mic"}</span>
            </button>
            <button
              type="button"
              className="bc-button danger"
              onClick={() => {
                setCall("WRAPUP");
                open("wrapup");
              }}
            >
              <PhoneOff size={16} />
              Kết thúc &amp; ghi nhận kết quả
            </button>
          </div>
        </section>
      )}

      {/* AI Speech Wrapup Modal */}
      {mode === "wrapup" && (
        <AiSpeechWrapupModal
          w={w}
          callSeconds={callSeconds}
          outcome={outcome}
          setOutcome={setOutcome}
          reason={reason}
          setReason={setReason}
          ptpLoan={ptpLoan}
          setPtpLoan={setPtpLoan}
          ptpAmount={ptpAmount}
          setPtpAmount={setPtpAmount}
          ptpDate={ptpDate}
          setPtpDate={setPtpDate}
          busy={busy}
          conflict={conflict}
          writable={writable}
          loading={loading}
          error={error}
          onClose={() => {
            setMode(null);
            if (call === "WRAPUP") setCall("IDLE");
          }}
          onSubmit={submit}
        />
      )}

      {/* Standard Editor Form Section for non-wrapup modes */}
      {mode && mode !== "wrapup" && (
        <section className="bc-editor" aria-label="Biểu mẫu tác nghiệp">
          <div className="bc-modal-header">
            <div>
              <h2>
                {
                  {
                    schedule_contact: "Lên lịch / điều chỉnh lịch",
                    cancel_schedule: "Hủy lịch liên hệ",
                    decision_feedback: "Ghi nhận quyết định",
                    reconcile: "Xác nhận đã rà soát",
                  }[mode]
                }
              </h2>
              <small>
                Case {w.case.case_id} · v{w.case.case_version} · Lưu vào backend{" "}
                {runtime?.mode}
              </small>
            </div>
            <button
              type="button"
              className="bc-modal-close"
              disabled={busy}
              onClick={() => setMode(null)}
            >
              <X size={18} /> Đóng (chưa lưu)
            </button>
          </div>

          <form onSubmit={submit} className="bc-modal-form">
            {mode === "schedule_contact" && (
              <>
                <label htmlFor="schedule-at">Thời gian liên hệ</label>
                <input
                  id="schedule-at"
                  type="datetime-local"
                  required
                  value={when}
                  onChange={(e) => setWhen(e.target.value)}
                />
                <p className="bc-form-hint">
                  Kế hoạch cán bộ · Asia/Ho_Chi_Minh. Không tự ghi nhận rằng
                  khách hàng đã đồng ý khung giờ này.
                </p>
              </>
            )}

            {mode === "decision_feedback" && (
              <>
                <p className="bc-form-callout">
                  Đề xuất đang phản hồi: {actionCopy[w.next_action.kind].title} ·
                  Quy tắc {w.next_action.recommendation_id}, không phải AI.
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
              <p className="bc-form-callout">
                Chỉ xác nhận khi Core mới nhất đã bao phủ payment/reversal và
                mọi nghĩa vụ. Không tự thay đổi số tiền.
              </p>
            )}

            <label htmlFor="reason">Lý do / nội dung ghi nhận</label>
            <textarea
              id="reason"
              required
              maxLength={2000}
              rows={4}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />

            <div className="bc-modal-foot">
              <button
                type="submit"
                className="bc-button primary"
                disabled={!writable || busy || conflict || loading}
              >
                {busy ? "Đang lưu..." : "Lưu vào hệ thống"}
              </button>
              <button
                type="button"
                className="bc-button secondary"
                onClick={() => setMode(null)}
              >
                Hủy
              </button>
            </div>
          </form>
        </section>
      )}

      {/* 2. 10-Tab Navigation Bar */}
      <nav
        className="bc-horizontal-tabs"
        role="tablist"
        aria-label="Chi tiết hồ sơ"
      >
        {tabs.map((t) => {
          const isSelected = section === t.key;
          return (
            <button
              key={t.key}
              role="tab"
              id={`tab-${t.key}`}
              aria-controls={`panel-${t.key}`}
              aria-selected={isSelected}
              aria-label={t.ariaName}
              className={`bc-tab-item ${isSelected ? "active" : ""}`}
              onClick={() => setSection(t.key)}
            >
              {t.title}
            </button>
          );
        })}
      </nav>

      {/* 3. Tab Panels Container */}
      <div className="bc-tab-content-area">
        {/* Tab 1: Tổng quan (Main Dashboard with Left 72% + Right 28%) */}
        {section === "work" && (
          <div
            className="bc-dashboard-layout"
            role="tabpanel"
            id="panel-work"
            aria-labelledby="tab-work"
          >
            {/* Main Center Content (Widgets Grid) */}
            <div className="bc-dashboard-main">
              {/* Row 1: Financial Overview + Quick Risk Assessment */}
              <div className="bc-row-duo">
                <div className="bc-col-58">
                  <ScopeSummary
                    scope={scope}
                    customer={customer}
                    onEvidence={() => setSection("evidence")}
                    onToggleScope={(c) => setCustomer(c)}
                    caseScopeCount={w.case_scope.exposures.length}
                    customerScopeCount={w.customer_scope.exposures.length}
                  />
                </div>
                <div className="bc-col-42">
                  <QuickRiskAssessment persona={persona} />
                </div>
              </div>

              {/* Row 2: Loan List + Debt Structure Donut */}
              <div className="bc-row-duo">
                <div className="bc-col-58">
                  <ExposureTable
                    scope={scope}
                    caseId={caseId}
                    customer={customer}
                    onViewDetail={() => setSection("credit")}
                  />
                </div>
                <div className="bc-col-42">
                  <DebtStructureCard scope={scope} />
                </div>
              </div>

              {/* Row 3: EWS Signals + 12-Month DPD Bar Chart */}
              <div className="bc-row-duo">
                <div className="bc-col-58">
                  <EwsSignalsCard onAll={() => setSection("evidence")} />
                </div>
                <div className="bc-col-42">
                  <DpdHistoryCard />
                </div>
              </div>

              {/* Row 4: Recent PTP + Recent Interactions */}
              <div className="bc-row-duo">
                <div className="bc-col-58">
                  <RecentPtpCard w={w} onAll={() => setSection("ptp")} />
                </div>
                <div className="bc-col-42">
                  <RecentInteractionsCard
                    w={w}
                    onAll={() => setSection("interactions")}
                  />
                </div>
              </div>
            </div>

            {/* Right Action Rail (Copilot / Action Cards) */}
            <aside
              className="bc-dashboard-rail"
              aria-label="Hỗ trợ quyết định và tác nghiệp"
            >
              {/* Card 1: Next Action */}
              <NextActionCard
                actionTitle={copy.title}
                activeSchedule={!!activeSchedule}
                onSchedule={() => open("schedule_contact")}
                onCall={handleCallIntent}
                onFeedback={() => open("decision_feedback")}
                disabled={
                  busy ||
                  loading ||
                  conflict ||
                  call !== "IDLE" ||
                  isBlocked
                }
              />

              {/* Card 2: 5-Point Guardrail */}
              <GuardrailCard
                canCheck={canCheck}
                onCheck={handleCallIntent}
              />

              {/* Card 3: AI Recommendations */}
              <AiRecommendationsCard
                onAccept={() => open("decision_feedback")}
                onDetail={() => setSection("evidence")}
              />

              {/* Card 4: Quick Notes Widget */}
              <QuickNotes caseId={caseId} />
            </aside>
          </div>
        )}

        {/* Tab 2: Thông tin khách hàng */}
        {section === "customer" && (
          <div
            role="tabpanel"
            id="panel-customer"
            aria-labelledby="tab-customer"
          >
            <CustomerInfoPanel w={w} />
          </div>
        )}

        {/* Tab 3: Nghĩa vụ tín dụng */}
        {section === "credit" && (
          <div role="tabpanel" id="panel-credit" aria-labelledby="tab-credit">
            <ExposureTable
              scope={scope}
              caseId={caseId}
              customer={customer}
            />
          </div>
        )}

        {/* Tab 4: Case & xử lý */}
        {section === "case" && (
          <div role="tabpanel" id="panel-case" aria-labelledby="tab-case">
            <section className="bc-panel">
              <h2>Quy trình xử lý hồ sơ</h2>
              <p>
                Giai đoạn: <strong>{label(w.case.stage)}</strong>
              </p>
              <p>
                Trạng thái: <strong>{label(w.case.lifecycle)}</strong>
              </p>
              {activeSchedule && (
                <p>
                  Lịch hẹn:{" "}
                  <strong>{dateTime(activeSchedule.scheduled_at)}</strong> (
                  {activeSchedule.reason})
                </p>
              )}
            </section>
          </div>
        )}

        {/* Tab 5: PTP & Thanh toán */}
        {section === "ptp" && (
          <div role="tabpanel" id="panel-ptp" aria-labelledby="tab-ptp">
            <PtpPaymentPanel w={w} />
            <section className="bc-panel">
              <h2>Thao tác đối soát</h2>
              <div className="bc-actions-row">
                <button
                  type="button"
                  className="bc-button"
                  disabled={
                    !writable || busy || loading || conflict || call !== "IDLE"
                  }
                  onClick={() => perform("balance_check", {})}
                >
                  Đối soát số dư từ Core
                </button>
                <button
                  type="button"
                  className="bc-button"
                  disabled={
                    !writable ||
                    busy ||
                    conflict ||
                    stale(w.case_scope, now) ||
                    !w.case.contact_hold_reason ||
                    call !== "IDLE"
                  }
                  onClick={() => open("reconcile")}
                >
                  Xác nhận đã rà soát
                </button>
              </div>
            </section>
            <CaseTimeline w={w} />
          </div>
        )}

        {/* Tab 6: Lịch sử tương tác */}
        {section === "interactions" && (
          <div
            role="tabpanel"
            id="panel-interactions"
            aria-labelledby="tab-interactions"
          >
            <CaseTimeline w={w} />
          </div>
        )}

        {/* Tab 7: EWS & Rủi ro */}
        {section === "evidence" && (
          <div
            role="tabpanel"
            id="panel-evidence"
            aria-labelledby="tab-evidence"
          >
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
                  if (alive.current && generation === sequence.current) {
                    setPersona(p);
                  }
                } catch (e) {
                  if (alive.current && generation === sequence.current) {
                    setPersonaError(errorText(e));
                  }
                }
              }}
            />
          </div>
        )}

        {/* Tab 8: Tài sản bảo đảm */}
        {section === "collateral" && (
          <div
            role="tabpanel"
            id="panel-collateral"
            aria-labelledby="tab-collateral"
          >
            <CollateralPanel />
          </div>
        )}

        {/* Tab 9: Tài liệu */}
        {section === "documents" && (
          <div
            role="tabpanel"
            id="panel-documents"
            aria-labelledby="tab-documents"
          >
            <DocumentsPanel />
          </div>
        )}

        {/* Tab 10: Khác */}
        {section === "other" && (
          <div role="tabpanel" id="panel-other" aria-labelledby="tab-other">
            <section className="bc-panel">
              <h2>Cấu hình & thông tin khác</h2>
              <p>Mã phiên bản case: v{w.case.case_version}</p>
              <p>Thời điểm đọc: {dateTime(w.read_at)}</p>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
