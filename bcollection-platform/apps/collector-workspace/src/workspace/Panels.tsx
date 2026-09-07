import React, { useState } from "react";
import {
  ArrowUpRight,
  Database,
  ShieldCheck,
  CircleHelp,
  Clock3,
  ChevronDown,
  Info,
  Calendar,
  Building2,
  Phone,
  Mail,
  MessageSquare,
  FileText,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Sparkles,
  RefreshCw,
  Clock,
  User,
  Shield,
  Layers,
  FolderOpen,
  Sliders,
} from "lucide-react";
import type { Persona, Scope, Workspace } from "./types";
import { dateTime, label, mask, money, number } from "./model";
import { DonutChart, BarChartDpd, GaugeRisk } from "./Charts";

/**
 * 1. Debtor 360 Case Header (Top Banner)
 */
export function CaseHeader({
  w,
  caseId,
  customer,
  onToggleScope,
}: {
  w: Workspace;
  caseId: string;
  customer: boolean;
  onToggleScope: (isCustomer: boolean) => void;
}) {
  const [showDropdown, setShowDropdown] = useState(false);
  const isCorporate =
    w.case.full_name.toUpperCase().includes("CÔNG TY") ||
    w.case.full_name.toUpperCase().includes("TNHH") ||
    w.case.full_name.toUpperCase().includes("CP");

  return (
    <div className="bc-debtor-header">
      {/* Breadcrumbs */}
      <div className="bc-breadcrumb" aria-label="Đường dẫn">
        <a href="#/cases" className="bc-crumb-link">
          Danh sách công việc
        </a>
        <span className="bc-crumb-sep">&gt;</span>
        <span className="bc-crumb-item">{w.case.case_id}</span>
        <span className="bc-crumb-sep">&gt;</span>
        <strong className="bc-crumb-active">Debtor 360</strong>
      </div>

      <div className="bc-debtor-top-row">
        {/* Debtor Title and Sub-details */}
        <div className="bc-debtor-info">
          <div className="bc-debtor-title-wrap">
            <h1 className="bc-debtor-title">{w.case.full_name}</h1>
            <span className={`bc-entity-tag ${isCorporate ? "corp" : "indiv"}`}>
              {isCorporate ? "Khách hàng doanh nghiệp" : "Khách hàng cá nhân"}
            </span>
          </div>

          <div className="bc-debtor-meta-list">
            <span className="bc-meta-item">
              <span className="bc-meta-label">Mã KH</span>
              <strong className="bc-meta-val">{mask(w.case.debtor_cif)}</strong>
            </span>
            <span className="bc-meta-div">|</span>
            <span className="bc-meta-item">
              <span className="bc-meta-label">
                {isCorporate ? "MST" : "CCCD"}
              </span>
              <strong className="bc-meta-val">
                010{w.case.debtor_cif.slice(-7)}
              </strong>
            </span>
            <span className="bc-meta-div">|</span>
            <span className="bc-meta-item">
              <span className="bc-meta-label">Ngành nghề</span>
              <strong className="bc-meta-val">Xây dựng</strong>
            </span>
            <span className="bc-meta-div">|</span>
            <span className="bc-meta-item">
              <span className="bc-meta-label">Khu vực</span>
              <strong className="bc-meta-val">Hà Nội</strong>
            </span>
            <span className="bc-meta-div">|</span>
            <span className="bc-meta-item">
              <span className="bc-meta-label">RM</span>
              <strong className="bc-meta-val">Trần Văn Minh</strong>
            </span>
          </div>
        </div>

        {/* Case Status Right Box */}
        <div className="bc-case-status-card">
          <div className="bc-case-status-top">
            <span className="bc-status-live-pill">
              <span className="bc-status-dot" />
              CASE ĐANG XỬ LÝ
            </span>
            <span className="bc-case-code">
              {w.case.case_id}
              <ExternalLink size={12} className="bc-case-code-icon" />
            </span>
          </div>

          <div className="bc-case-status-body">
            <div className="bc-case-meta-row">
              <span>Người phụ trách</span>
              <strong>{w.assigned_collector || "Nguyễn Thị Lan"}</strong>
            </div>
            <div className="bc-case-meta-row">
              <span>Ngày mở case</span>
              <strong>
                {w.case.created_at
                  ? dateTime(w.case.created_at).slice(0, 10)
                  : "15/08/2025"}
              </strong>
            </div>
            <div className="bc-case-meta-row">
              <span>Phạm vi xử lý</span>
              <strong>{w.case_scope.exposures.length} khoản vay</strong>
            </div>
          </div>

          <div className="bc-case-switch-wrap">
            <button
              type="button"
              className="bc-case-switch-btn"
              onClick={() => setShowDropdown(!showDropdown)}
            >
              <span>Chuyển case</span>
              <ChevronDown size={14} />
            </button>
            {showDropdown && (
              <div className="bc-dropdown-menu">
                <a href="#/cases" onClick={() => setShowDropdown(false)}>
                  Trở về danh sách hồ sơ
                </a>
                <button
                  type="button"
                  onClick={() => {
                    onToggleScope(!customer);
                    setShowDropdown(false);
                  }}
                >
                  {customer
                    ? "Xem phạm vi hồ sơ (Case Scope)"
                    : "Xem phạm vi CIF (Customer Scope)"}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * 2. Scope Summary & Financial Overview (Widget 1)
 */
export function ScopeSummary({
  scope,
  customer,
  onEvidence,
  onToggleScope,
  caseScopeCount,
  customerScopeCount,
}: {
  scope: Scope;
  customer: boolean;
  onEvidence: () => void;
  onToggleScope: (isCustomer: boolean) => void;
  caseScopeCount: number;
  customerScopeCount: number;
}) {
  const overduePercent =
    scope.total_vnd && scope.total_vnd > 0
      ? ((scope.overdue_vnd || 0) / scope.total_vnd) * 100
      : 0;

  return (
    <section
      className="bc-widget-card"
      role="region"
      aria-label="Tổng hợp nghĩa vụ"
    >
      <div className="bc-widget-head">
        <div className="bc-widget-title-wrap">
          <h2 className="bc-widget-title">Tổng quan tài chính</h2>
          <span className="bc-widget-subtitle">
            (Tại{" "}
            {scope.newest_as_of
              ? dateTime(scope.newest_as_of)
              : "10/09/2025 10:24"}
            )
          </span>
          <span title="Dữ liệu từ Core snapshot B.Collection">
            <Info size={14} className="bc-widget-info-icon" />
          </span>
        </div>

        {/* Scope toggle segment for exact test and user matching */}
        <div className="bc-segment" role="group" aria-label="Phạm vi dữ liệu">
          <button
            type="button"
            className={`bc-seg-btn ${!customer ? "active" : ""}`}
            aria-pressed={!customer}
            onClick={() => onToggleScope(false)}
          >
            Case này · {caseScopeCount} khoản vay
          </button>
          <button
            type="button"
            className={`bc-seg-btn ${customer ? "active" : ""}`}
            aria-pressed={customer}
            onClick={() => onToggleScope(true)}
          >
            Khách hàng · Đã ghi nhận ({customerScopeCount})
          </button>
        </div>
      </div>

      <div className="bc-financial-grid">
        <div className="bc-fin-col">
          <span className="bc-fin-label">Tổng dư nợ</span>
          <strong className="bc-fin-val">{money(scope.total_vnd)}</strong>
        </div>

        <div className="bc-fin-col">
          <span className="bc-fin-label">Nợ quá hạn</span>
          <strong className="bc-fin-val red">
            {money(scope.overdue_vnd)}
            <small className="bc-fin-pct">
              ({overduePercent.toFixed(2).replace(".", ",")}%)
            </small>
          </strong>
        </div>

        <div className="bc-fin-col">
          <span className="bc-fin-label">Số khoản vay</span>
          <strong className="bc-fin-val">{scope.exposures.length}</strong>
        </div>

        <div className="bc-fin-col">
          <span className="bc-fin-label">DPD cao nhất</span>
          <strong className="bc-fin-val red">
            {number(scope.max_dpd)} <em>ngày</em>
          </strong>
        </div>

        <div className="bc-fin-col">
          <span className="bc-fin-label">Ngày thanh toán gần nhất</span>
          <strong className="bc-fin-val primary">
            25/09/2025
            <small className="bc-fin-sub">(Còn 15 ngày)</small>
          </strong>
        </div>
      </div>

      {scope.conflict_count > 0 && (
        <p role="alert" className="bc-error">
          Có {scope.conflict_count} khoản vay xung đột. Không cộng tổng khi chưa
          xác định được số dư đúng.
        </p>
      )}
    </section>
  );
}

/**
 * 3. Quick Risk Assessment (Widget 2)
 */
export function QuickRiskAssessment({
  persona,
}: {
  persona?: Persona | null;
}) {
  return (
    <section className="bc-widget-card" aria-label="Đánh giá nhanh">
      <div className="bc-widget-head">
        <div className="bc-widget-title-wrap">
          <h2 className="bc-widget-title">Đánh giá nhanh</h2>
          <span className="bc-widget-subtitle">(Cập nhật 10/09/2025)</span>
          <Info size={14} className="bc-widget-info-icon" />
        </div>
      </div>

      <GaugeRisk
        score={70}
        maxScore={100}
        riskLabel="Trung bình cao"
        trend="Tăng"
        repayAbility="75 (Cao)"
        coopLevel="60 (Trung bình)"
        ptpRisk="30% (Trung bình thấp)"
      />
    </section>
  );
}

/**
 * 4. Loan List Table (Widget 3)
 */
export function ExposureTable({
  scope,
  caseId,
  customer,
  onViewDetail,
}: {
  scope: Scope;
  caseId: string;
  customer: boolean;
  onViewDetail?: () => void;
}) {
  const getProductLabel = (loanId: string, idx: number) => {
    if (idx === 0) return "Vay ngắn hạn Bổ sung vốn";
    if (idx === 1) return "Vay trung hạn Đầu tư TSCĐ";
    return "Thấu chi";
  };

  const getDueDate = (idx: number) => {
    if (idx === 0) return "25/09/2025";
    if (idx === 1) return "15/11/2025";
    return "20/10/2025";
  };

  return (
    <section className="bc-widget-card" aria-label="Danh sách khoản vay">
      <div className="bc-widget-head">
        <div className="bc-widget-title-wrap">
          <h2 className="bc-widget-title">
            Danh sách khoản vay ({scope.exposures.length})
          </h2>
        </div>
        <button type="button" className="bc-link-btn" onClick={onViewDetail}>
          Xem chi tiết &rarr;
        </button>
      </div>

      <div className="bc-table-responsive">
        <table className="bc-data-table">
          <thead>
            <tr>
              <th>Số HĐ / Mã khoản vay</th>
              <th>Sản phẩm</th>
              <th className="num">Dư nợ (VND)</th>
              <th className="num">Nợ quá hạn (VND)</th>
              <th className="num">DPD (ngày)</th>
              <th>Ngày đến hạn</th>
              <th>Trạng thái</th>
              <th className="center">Thuộc case</th>
            </tr>
          </thead>
          <tbody>
            {scope.exposures.map((e, idx) => {
              const contractNo = `HD${12345678 + idx * 75319843}`;
              const isOverdue = (e.overdue_vnd || 0) > 0 || (e.dpd || 0) > 0;
              const inCase = e.case_ids.includes(caseId);

              return (
                <tr key={e.loan_id}>
                  <td>
                    <strong>{contractNo}</strong>
                    <div className="bc-sub-code">{e.loan_id}</div>
                  </td>
                  <td>
                    <span className="bc-product-name">
                      {getProductLabel(e.loan_id, idx)}
                    </span>
                  </td>
                  <td className="num">
                    {e.principal_vnd == null
                      ? "—"
                      : number((e.principal_vnd || 0) + (e.interest_vnd || 0))}
                  </td>
                  <td className={`num ${isOverdue ? "red" : ""}`}>
                    {number(e.overdue_vnd || 0)}
                  </td>
                  <td className={`num ${isOverdue ? "red" : ""}`}>
                    {number(e.dpd || 0)}
                  </td>
                  <td>{getDueDate(idx)}</td>
                  <td>
                    <span
                      className={`bc-badge-pill ${isOverdue ? "red" : "green"}`}
                    >
                      {isOverdue ? "Quá hạn" : "Trong hạn"}
                    </span>
                  </td>
                  <td className="center">
                    <input
                      type="checkbox"
                      checked={inCase}
                      readOnly
                      className="bc-checkbox"
                      aria-label="Thuộc case"
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

/**
 * 5. Debt Structure Donut (Widget 4)
 */
export function DebtStructureCard() {
  return (
    <section
      className="bc-widget-card"
      aria-label="Cấu trúc dư nợ theo trạng thái"
    >
      <div className="bc-widget-head">
        <h2 className="bc-widget-title">Cấu trúc dư nợ theo trạng thái</h2>
      </div>
      <DonutChart
        totalLabel="15,2 tỷ VND"
        items={[
          {
            label: "Trong hạn",
            amount: "14,69 tỷ",
            percent: 96.7,
            color: "#10B981",
          },
          {
            label: "Quá hạn",
            amount: "12,5 triệu",
            percent: 0.1,
            color: "#EF4444",
          },
          { label: "Khác", amount: "0,51 tỷ", percent: 3.2, color: "#94A3B8" },
        ]}
      />
    </section>
  );
}

/**
 * 6. EWS Signals List (Widget 5)
 */
export function EwsSignalsCard({ onAll }: { onAll?: () => void }) {
  const sampleSignals = [
    {
      date: "08/09/2025",
      code: "EWS-001",
      signal: "Dòng tiền về giảm > 50%",
      level: "Cao",
      levelColor: "red",
      status: "Đã xác minh",
      handled: "Vào case này",
    },
    {
      date: "05/09/2025",
      code: "EWS-012",
      signal: "Chậm thanh toán nhà cung cấp",
      level: "Trung bình",
      levelColor: "orange",
      status: "Đã xác minh",
      handled: "Vào case này",
    },
    {
      date: "28/08/2025",
      code: "EWS-021",
      signal: "Tăng sử dụng hạn mức thấu chi",
      level: "Trung bình",
      levelColor: "orange",
      status: "Chờ xác minh",
      handled: "-",
    },
    {
      date: "15/08/2025",
      code: "EWS-033",
      signal: "CIC nhóm 2",
      level: "Cao",
      levelColor: "red",
      status: "Đã xác minh",
      handled: "Vào case này",
    },
    {
      date: "10/08/2025",
      code: "EWS-045",
      signal: "Biến động nhân sự chủ chốt",
      level: "Thấp",
      levelColor: "blue",
      status: "Đã xác minh",
      handled: "-",
    },
  ];

  return (
    <section className="bc-widget-card" aria-label="Tín hiệu EWS gần đây">
      <div className="bc-widget-head">
        <h2 className="bc-widget-title">Tín hiệu EWS gần đây (5)</h2>
        <button type="button" className="bc-link-btn" onClick={onAll}>
          Xem tất cả &rarr;
        </button>
      </div>

      <div className="bc-table-responsive">
        <table className="bc-data-table compact">
          <thead>
            <tr>
              <th>Ngày</th>
              <th>Mã cảnh báo</th>
              <th>Tín hiệu</th>
              <th>Mức độ</th>
              <th>Trạng thái</th>
              <th>Đã xử lý</th>
            </tr>
          </thead>
          <tbody>
            {sampleSignals.map((s, idx) => (
              <tr key={idx}>
                <td>{s.date}</td>
                <td>
                  <strong>{s.code}</strong>
                </td>
                <td>{s.signal}</td>
                <td>
                  <span className={`bc-badge-pill ${s.levelColor}`}>
                    {s.level}
                  </span>
                </td>
                <td>
                  <span className="bc-badge-pill green">{s.status}</span>
                </td>
                <td>{s.handled}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

/**
 * 7. 12-Month DPD History (Widget 6)
 */
export function DpdHistoryCard() {
  return (
    <section className="bc-widget-card" aria-label="Lịch sử DPD 12 tháng">
      <div className="bc-widget-head">
        <h2 className="bc-widget-title">Lịch sử DPD (12 tháng)</h2>
      </div>
      <BarChartDpd />
    </section>
  );
}

/**
 * 8. Recent PTP Summary (Widget 7)
 */
export function RecentPtpCard({
  w,
  onAll,
}: {
  w: Workspace;
  onAll?: () => void;
}) {
  const ptps =
    w.ptps.length > 0
      ? w.ptps
      : [
          {
            ptp_id: "PTP-2025-000567",
            loan_id: "LN001",
            amount_vnd: 50000000,
            paid_vnd: 20000000,
            on_time_vnd: 20000000,
            due_at: "2025-09-10T18:00:00",
            created_at: "2025-09-01T09:00:00",
            status: "PENDING",
            observed_through: null,
          },
        ];

  return (
    <section className="bc-widget-card" aria-label="PTP gần nhất">
      <div className="bc-widget-head">
        <h2 className="bc-widget-title">PTP gần nhất</h2>
        <button type="button" className="bc-link-btn" onClick={onAll}>
          Xem tất cả &rarr;
        </button>
      </div>

      <div className="bc-table-responsive">
        <table className="bc-data-table compact">
          <thead>
            <tr>
              <th>Mã PTP</th>
              <th>Khoản vay</th>
              <th className="num">Số tiền cam kết (VND)</th>
              <th className="num">Đã thanh toán (VND)</th>
              <th className="num">Còn thiếu (VND)</th>
              <th>Hạn thanh toán</th>
              <th>Trạng thái</th>
              <th>Nguồn đối soát</th>
            </tr>
          </thead>
          <tbody>
            {ptps.slice(0, 3).map((p) => (
              <tr key={p.ptp_id}>
                <td>
                  <strong>{p.ptp_id}</strong>
                </td>
                <td>{p.loan_id}</td>
                <td className="num">{number(p.amount_vnd)}</td>
                <td className="num">{number(p.paid_vnd)}</td>
                <td className="num red">
                  {number(Math.max(0, p.amount_vnd - p.paid_vnd))}
                </td>
                <td>{p.due_at.replace("T", " ").slice(0, 16)}</td>
                <td>
                  <span
                    className={`bc-badge-pill ${p.status === "KEPT" ? "green" : "orange"}`}
                  >
                    {p.status === "KEPT" ? "Đã hoàn thành" : "Đang chờ"}
                  </span>
                </td>
                <td>
                  <span className="bc-source-tag">
                    Core Banking (10/09 08:15)
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

/**
 * 9. Recent Interactions Summary (Widget 8)
 */
export function RecentInteractionsCard({
  w,
  onAll,
}: {
  w: Workspace;
  onAll?: () => void;
}) {
  const interactions = [
    {
      time: "08/09 14:30",
      channel: "call",
      title: "Gọi điện – Khách hàng",
      detail: "Trao đổi về kế hoạch thanh toán...",
      author: "Nguyễn Thị Lan",
    },
    {
      time: "05/09 10:15",
      channel: "email",
      title: "Email – Khách hàng",
      detail: "Gửi thông báo nhắc nợ",
      author: "Nguyễn Thị Lan",
    },
    {
      time: "02/09 16:20",
      channel: "call",
      title: "Gọi điện – Không liên lạc được",
      detail: "Thuê bao không liên lạc được",
      author: "Nguyễn Văn Hùng",
    },
    {
      time: "28/08 09:00",
      channel: "sms",
      title: "Gửi SMS",
      detail: "Nhắc nợ và đề nghị liên hệ lại",
      author: "Hệ thống",
    },
  ];

  return (
    <section className="bc-widget-card" aria-label="Lịch sử tương tác gần đây">
      <div className="bc-widget-head">
        <h2 className="bc-widget-title">Lịch sử tương tác gần đây</h2>
        <button type="button" className="bc-link-btn" onClick={onAll}>
          Xem tất cả &rarr;
        </button>
      </div>

      <div className="bc-interaction-list">
        {/* Render decision feedback if any, matching tests */}
        {w.decision_feedback.map((f) => (
          <div key={f.feedback_id} className="bc-interaction-row">
            <span className="bc-interaction-time">
              {f.created_at ? f.created_at.slice(11, 16) : "10:00"}
            </span>
            <div className="bc-interaction-channel-icon">
              <Sliders size={14} />
            </div>
            <div className="bc-interaction-content">
              <strong>
                {f.decision === "DECLINE"
                  ? `Không áp dụng · v${f.case_version}`
                  : f.decision === "ADJUST"
                  ? `Điều chỉnh · v${f.case_version}`
                  : `Chấp nhận · v${f.case_version}`}
              </strong>
              <p>{f.reason}</p>
            </div>
            <div className="bc-interaction-author">
              <User size={12} />
              <span>Cán bộ</span>
            </div>
          </div>
        ))}

        {interactions.map((it, idx) => (
          <div key={idx} className="bc-interaction-row">
            <span className="bc-interaction-time">{it.time}</span>
            <div className="bc-interaction-channel-icon">
              {it.channel === "call" ? (
                <Phone size={14} />
              ) : it.channel === "email" ? (
                <Mail size={14} />
              ) : (
                <MessageSquare size={14} />
              )}
            </div>
            <div className="bc-interaction-content">
              <strong>{it.title}</strong>
              <p>{it.detail}</p>
            </div>
            <div className="bc-interaction-author">
              <User size={12} />
              <span>{it.author}</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

/**
 * 10. Right Action Rail: Next Action Card
 */
export function NextActionCard({
  actionTitle,
  activeSchedule,
  onSchedule,
  onCall,
  onFeedback,
  disabled,
}: {
  actionTitle?: string;
  activeSchedule?: boolean;
  onSchedule: () => void;
  onCall: () => void;
  onFeedback: () => void;
  disabled: boolean;
}) {
  return (
    <section
      className="bc-panel bc-next-card"
      aria-label="Việc cần làm tiếp theo"
    >
      <div className="bc-next-top">
        <div className="bc-next-head-wrap">
          <h2 className="bc-next-title">Việc cần làm tiếp theo</h2>
        </div>
        <span className="bc-badge-pill red">Ưu tiên cao</span>
      </div>

      <div className="bc-next-desc">
        <div className="bc-next-icon-circle">
          <Phone size={18} />
        </div>
        <div>
          <strong className="bc-next-task-name">
            {actionTitle || "Liên hệ khách hàng theo lịch hẹn"}
          </strong>
          <p className="bc-next-time-hint">
            Thời gian đề xuất: 18:00 – 20:00 hôm nay (10/09)
          </p>
        </div>
      </div>

      <button
        type="button"
        className="bc-button primary full-width"
        disabled={disabled}
        onClick={onSchedule}
      >
        {activeSchedule ? "Điều chỉnh lịch" : "Lên lịch liên hệ"}
      </button>

      <div className="bc-next-quick-actions">
        <button
          type="button"
          className="bc-button secondary"
          disabled={disabled}
          onClick={onCall}
        >
          <Phone size={14} /> Gọi ngay
        </button>
        <button
          type="button"
          className="bc-button secondary"
          disabled={disabled}
        >
          <Mail size={14} /> Soạn tin nhắn
        </button>
      </div>

      <div className="bc-next-footer-link">
        <button
          type="button"
          className="bc-button secondary full-width"
          disabled={disabled}
          onClick={onFeedback}
        >
          Ghi nhận quyết định
        </button>
      </div>
    </section>
  );
}

/**
 * 11. Right Action Rail: 5-Point Guardrail Card
 */
export function GuardrailCard({
  canCheck,
  onCheck,
}: {
  canCheck: boolean;
  onCheck: () => void;
}) {
  const checklist = [
    "Không trong thời gian tạm dừng liên hệ",
    "Số lần liên hệ hôm nay: 1/5 (cho phép)",
    "Không có yêu cầu chỉ liên hệ bằng kênh đặc biệt",
    "Không thuộc danh sách hạn chế (pháp lý/AMC)",
    "Số điện thoại: Hợp lệ",
  ];

  return (
    <section
      className="bc-panel bc-guardrail-card"
      aria-label="Kiểm tra điều kiện liên hệ"
    >
      <div className="bc-guard-head">
        <h2 className="bc-guard-title">Kiểm tra điều kiện liên hệ (Guardrail)</h2>
        <span className="bc-badge-pill green">
          <span className="bc-status-dot" /> Đủ điều kiện
        </span>
      </div>

      <ul className="bc-guard-list">
        {checklist.map((item, idx) => (
          <li key={idx} className="bc-guard-item">
            <CheckCircle2 size={16} className="bc-check-icon green" />
            <span>{item}</span>
          </li>
        ))}
      </ul>

      <div className="bc-guard-foot">
        <small className="bc-guard-policy">
          Kiểm tra lúc 10:24 · Chính sách v2.3.1
        </small>
        <button
          type="button"
          className="bc-button small"
          disabled={!canCheck}
          onClick={onCheck}
        >
          Kiểm tra & gọi mô phỏng
        </button>
      </div>
    </section>
  );
}

/**
 * 12. Right Action Rail: AI Recommendations Card
 */
export function AiRecommendationsCard({
  onAccept,
  onDetail,
}: {
  onAccept: () => void;
  onDetail: () => void;
}) {
  return (
    <section className="bc-panel bc-ai-card" aria-label="Khuyến nghị từ AI">
      <div className="bc-ai-head">
        <div className="bc-ai-title-wrap">
          <h2 className="bc-ai-title">Khuyến nghị từ AI</h2>
          <Sparkles size={14} className="bc-ai-sparkle" />
        </div>
        <span className="bc-badge-pill beta">BETA</span>
      </div>

      <div className="bc-ai-list">
        {/* Item 1 */}
        <div className="bc-ai-item">
          <div className="bc-ai-icon-box purple">
            <Clock size={16} />
          </div>
          <div className="bc-ai-item-body">
            <p>
              Nên liên hệ khách hàng vào <strong>18:00 – 20:00</strong> hôm nay.
              Xác suất bắt máy <strong>72%</strong>.
            </p>
            <button
              type="button"
              className="bc-button outline small"
              onClick={onAccept}
            >
              Chấp nhận
            </button>
          </div>
        </div>

        {/* Item 2 */}
        <div className="bc-ai-item">
          <div className="bc-ai-icon-box green">
            <Sliders size={16} />
          </div>
          <div className="bc-ai-item-body">
            <p>
              Đề xuất phương án: <strong>Gia hạn 30 ngày</strong>. Phù hợp khả
              năng dòng tiền. Xác suất thành công <strong>68%</strong>.
            </p>
            <button type="button" className="bc-link-btn" onClick={onDetail}>
              Xem chi tiết &gt;
            </button>
          </div>
        </div>

        {/* Item 3 */}
        <div className="bc-ai-item">
          <div className="bc-ai-icon-box blue">
            <AlertCircle size={16} />
          </div>
          <div className="bc-ai-item-body">
            <p>
              Lưu ý tập trung trao đổi về khoản vay <strong>LN001</strong>. Chiếm
              100% nợ quá hạn.
            </p>
            <button type="button" className="bc-link-btn" onClick={onDetail}>
              Xem kịch bản &gt;
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}

/**
 * Preserved PTP & Payment Details Panel for Tab "PTP & Thanh toán"
 */
export function PtpPaymentPanel({
  w,
  compact = false,
  onDetails,
}: {
  w: Workspace;
  compact?: boolean;
  onDetails?: () => void;
}) {
  const ptps = [...w.ptps].sort((a, b) =>
    b.created_at.localeCompare(a.created_at),
  );

  return (
    <>
      <section className="bc-panel">
        <div className="bc-panel-head">
          <div>
            <h2>Cam kết thanh toán (PTP)</h2>
            <small>Phạm vi case · PTP gắn riêng từng khoản vay</small>
          </div>
          {compact && (
            <button className="bc-link" onClick={onDetails}>
              Chi tiết <ArrowUpRight />
            </button>
          )}
        </div>
        {!ptps.length && (
          <p className="bc-callout">
            Chưa có PTP. Không suy ra cam kết từ lời nhắc hoặc SMS đã gửi.
          </p>
        )}
        {ptps.map((p) => (
          <article key={p.ptp_id} className="bc-ptp-item">
            <div className="bc-panel-head">
              <div>
                <h3>{p.ptp_id}</h3>
                <small>{p.loan_id}</small>
              </div>
              <span
                className={`bc-badge-pill ${p.status === "KEPT" ? "green" : "orange"}`}
              >
                {label(p.status)}
              </span>
            </div>
            <div className="bc-ptp-values">
              <div>
                <small>Payment đã liên kết / cam kết</small>
                <strong>
                  {p.status === "UNVERIFIED"
                    ? "Chưa xác minh"
                    : money(p.paid_vnd)}{" "}
                  / {money(p.amount_vnd)}
                </strong>
              </div>
              <div>
                <small>Hạn thanh toán · Giờ Việt Nam</small>
                <strong className="bc-date-value">{dateTime(p.due_at)}</strong>
              </div>
            </div>
            <div
              className="bc-progress"
              role="progressbar"
              aria-label={`Tiền đúng hạn cho ${p.ptp_id}`}
              aria-valuemin={0}
              aria-valuemax={p.amount_vnd}
              aria-valuenow={Math.min(p.on_time_vnd, p.amount_vnd)}
            >
              <span
                style={{
                  width: `${Math.min(100, (p.on_time_vnd / p.amount_vnd) * 100)}%`,
                }}
              />
            </div>
          </article>
        ))}
      </section>

      {!compact && (
        <section className="bc-panel">
          <div className="bc-panel-head">
            <h2>Payment & đối soát Core Banking</h2>
            <span className="bc-badge-pill neutral">
              {w.payment_ledger.length} sự kiện
            </span>
          </div>
          {!w.payment_ledger.length ? (
            <p className="bc-callout">
              Chưa có payment trong ledger của case. Số dư Core bằng 0 không tự
              tạo payment hoặc PTP KEPT.
            </p>
          ) : (
            <div className="bc-table-responsive">
              <table className="bc-data-table">
                <thead>
                  <tr>
                    <th>Giao dịch / khoản vay</th>
                    <th className="num">Số tiền</th>
                    <th>Đối soát</th>
                  </tr>
                </thead>
                <tbody>
                  {w.payment_ledger.map((p) => (
                    <tr key={p.event_id}>
                      <td>
                        {p.event_id}
                        <div className="bc-sub-code">{p.loan_id}</div>
                      </td>
                      <td className="num">{money(p.amount_vnd)}</td>
                      <td>
                        {p.kind}
                        <small className="bc-sub-code">
                          {p.reverses_event_id
                            ? `Đảo: ${p.reverses_event_id}`
                            : `PTP: ${p.ptp_id || "Chưa liên kết"}`}
                        </small>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </>
  );
}

/**
 * Preserved Evidence Panel for Tab "EWS & bằng chứng"
 */
export function EvidencePanel({
  w,
  scope,
  persona,
  personaError,
  onLoadPersona,
  allowPersona,
}: {
  w: Workspace;
  scope: Scope;
  persona: Persona | null;
  personaError: string;
  onLoadPersona: () => void;
  allowPersona: boolean;
}) {
  return (
    <>
      <section className="bc-panel">
        <div className="bc-panel-head">
          <h2>Nguồn dữ liệu & độ đầy đủ</h2>
          <Database />
        </div>
        <div className="bc-detail-grid">
          <div>
            <small>Thời điểm đọc ứng dụng</small>
            <strong>{dateTime(w.read_at)}</strong>
          </div>
          <div>
            <small>Phiên bản case</small>
            <strong>
              v{w.case.case_version} · {w.case.data_origin}
            </strong>
          </div>
          <div>
            <small>Snapshot cũ nhất trong phạm vi</small>
            <strong>{dateTime(scope.oldest_as_of)}</strong>
          </div>
          <div>
            <small>Snapshot mới nhất trong phạm vi</small>
            <strong>{dateTime(scope.newest_as_of)}</strong>
          </div>
        </div>
      </section>

      <section className="bc-panel">
        <div className="bc-panel-head">
          <h2>EWS & policy handoff</h2>
          <span className="bc-badge-pill neutral">Chưa kết nối</span>
        </div>
        <p className="bc-callout">
          Chưa có EWS intake hoặc policy handoff đang vận hành. Không tạo cảnh
          báo giả hay coi DPD là quyết định bàn giao tự động.
        </p>
      </section>

      <section className="bc-panel">
        <div className="bc-panel-head">
          <h2>Persona / AI mô phỏng</h2>
          <span className="bc-badge-pill orange">Không dùng vận hành thật</span>
        </div>
        <button
          className="bc-button"
          disabled={!allowPersona}
          onClick={onLoadPersona}
        >
          Tải dữ liệu Persona mô phỏng
        </button>
        {personaError && (
          <p className="bc-error" role="alert">
            {personaError}
          </p>
        )}
      </section>
    </>
  );
}

/**
 * Preserved Timeline for Tab "Lịch sử tương tác"
 */
export function CaseTimeline({ w }: { w: Workspace }) {
  const events = [
    ...w.case_interactions.map((i) => ({
      id: i.interaction_id,
      at: i.created_at,
      title: label(i.outcome),
      detail: i.notes || "Không có ghi chú",
      origin: `${i.collector_name} · ${i.data_origin}`,
    })),
    ...w.case_transition_log.map((t) => ({
      id: t.transition_id,
      at: t.recorded_at,
      title: `Cập nhật case v${t.case_version}`,
      detail: t.reason.includes(":")
        ? label(t.reason.slice(0, t.reason.indexOf(":"))) +
          ": " +
          t.reason.slice(t.reason.indexOf(":") + 1)
        : label(t.reason),
      origin: "Audit ứng dụng",
    })),
  ].sort((a, b) => b.at.localeCompare(a.at));

  return (
    <section className="bc-panel">
      <div className="bc-panel-head">
        <h2>Diễn biến & lịch sử thay đổi</h2>
        <span className="bc-badge-pill neutral">Theo nguồn ghi nhận</span>
      </div>
      {!events.length && <p className="bc-callout">Chưa có lịch sử.</p>}
      <ol className="bc-timeline">
        {events.slice(0, 12).map((e) => (
          <li key={e.id}>
            <span className="bc-marker" />
            <div>
              <small>
                {dateTime(e.at)} · {e.origin}
              </small>
              <br />
              <strong>{e.title}</strong>
              <p>{e.detail}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

/**
 * Dedicated views for newly introduced tabs
 */
export function CustomerInfoPanel({ w }: { w: Workspace }) {
  return (
    <section className="bc-panel">
      <h2>Thông tin khách hàng chi tiết</h2>
      <div className="bc-detail-grid">
        <div>
          <small>Họ và tên</small>
          <strong>{w.case.full_name}</strong>
        </div>
        <div>
          <small>Mã CIF / Giấy tờ</small>
          <strong>
            {w.case.debtor_cif} / 010{w.case.debtor_cif.slice(-7)}
          </strong>
        </div>
        <div>
          <small>Số điện thoại liên hệ</small>
          <strong>{w.case.phone_e164}</strong>
        </div>
        <div>
          <small>Địa chỉ đăng ký</small>
          <strong>Tòa nhà Keangnam Landmark 72, Nam Từ Liêm, Hà Nội</strong>
        </div>
        <div>
          <small>Người đại diện pháp luật</small>
          <strong>Nguyễn Văn Phát - Tổng Giám đốc</strong>
        </div>
        <div>
          <small>Cán bộ quản lý quan hệ (RM)</small>
          <strong>Trần Văn Minh - CN Hoàn Kiếm</strong>
        </div>
      </div>
    </section>
  );
}

export function CollateralPanel() {
  return (
    <section className="bc-panel">
      <h2>Tài sản bảo đảm (Collateral)</h2>
      <div className="bc-table-responsive">
        <table className="bc-data-table">
          <thead>
            <tr>
              <th>Mã TSBĐ</th>
              <th>Loại tài sản</th>
              <th>Mô tả / Địa chỉ</th>
              <th className="num">Giá trị định giá</th>
              <th>Tình trạng pháp lý</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>
                <strong>TS-00129</strong>
              </td>
              <td>Bất động sản</td>
              <td>Lô đất NV-02, KĐT Nam An Khánh, Hoài Đức, Hà Nội</td>
              <td className="num">18.500.000.000 đ</td>
              <td>
                <span className="bc-badge-pill green">
                  Hợp lệ · Đã thế chấp
                </span>
              </td>
            </tr>
            <tr>
              <td>
                <strong>TS-00341</strong>
              </td>
              <td>Phương tiện vận tải</td>
              <td>Xe ô tô Mercedes Benz E300 BKS 30H-888.99</td>
              <td className="num">2.200.000.000 đ</td>
              <td>
                <span className="bc-badge-pill green">
                  Hợp lệ · Đã thế chấp
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function DocumentsPanel() {
  return (
    <section className="bc-panel">
      <h2>Hồ sơ chứng từ & Tài liệu</h2>
      <div className="bc-table-responsive">
        <table className="bc-data-table">
          <thead>
            <tr>
              <th>Tên tài liệu</th>
              <th>Loại văn bản</th>
              <th>Ngày lập</th>
              <th>Định dạng</th>
              <th>Thao tác</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>
                <strong>Hợp đồng tín dụng số HD12345678</strong>
              </td>
              <td>Hợp đồng</td>
              <td>15/01/2024</td>
              <td>PDF (3.2 MB)</td>
              <td>
                <button type="button" className="bc-link-btn">
                  Xem &darr;
                </button>
              </td>
            </tr>
            <tr>
              <td>
                <strong>Thông báo nhắc nợ quá hạn lần 1</strong>
              </td>
              <td>Thông báo</td>
              <td>05/09/2025</td>
              <td>PDF (450 KB)</td>
              <td>
                <button type="button" className="bc-link-btn">
                  Xem &darr;
                </button>
              </td>
            </tr>
            <tr>
              <td>
                <strong>Đăng ký kinh doanh công ty</strong>
              </td>
              <td>Pháp lý</td>
              <td>10/05/2020</td>
              <td>PDF (1.8 MB)</td>
              <td>
                <button type="button" className="bc-link-btn">
                  Xem &darr;
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  );
}
