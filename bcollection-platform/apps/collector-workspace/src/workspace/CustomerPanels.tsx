import {
  Building2,
  UserRound,
  Database,
  ArrowUpRight,
  Radar,
  ChartColumn,
  FileLock2,
  ShieldCheck,
  CircleHelp,
} from "lucide-react";
import type { DpdHistory, Scope, Workspace } from "./types";
import { dateTime, label, mask, money, number } from "./model";
import { debtComposition } from "./customerModel";

export function CustomerHeader({
  w,
  onSelectCase,
  locked,
}: {
  w: Workspace;
  onSelectCase: (id: string) => void;
  locked: boolean;
}) {
  const p = w.customer_profile;
  return (
    <>
      <div className="bc-breadcrumb">
        Danh sách công việc <span>/</span> {w.case.case_id} <span>/</span>{" "}
        <strong>Debtor 360</strong>
      </div>
      <div className="bc-customer-header">
        <div>
          <div className="bc-title-line">
            <h1>Khách hàng 360</h1>
            <span className="bc-chip neutral">
              {p
                ? p.party_type === "ORGANIZATION"
                  ? "Khách hàng doanh nghiệp"
                  : "Khách hàng cá nhân"
                : "Chưa xác định loại khách hàng"}
            </span>
          </div>
          <h2 className="bc-legal-name">{p?.legal_name || w.case.full_name}</h2>
          <div className="bc-subtitle">
            <span>CIF {mask(w.case.debtor_cif)}</span>
            {p?.tax_id && <span>MST {mask(p.tax_id)}</span>}
            <span>{p?.industry || "Ngành nghề: chưa có nguồn"}</span>
            <span>{p?.region || "Khu vực: chưa có nguồn"}</span>
            <span>RM: {p?.rm_name || "Chưa có thông tin"}</span>
          </div>
        </div>
        <section className="bc-case-context" aria-label="Case đang chọn">
          <div className="bc-panel-head">
            <span
              className={`bc-chip ${w.case.contact_hold_reason ? "warn" : ""}`}
            >
              {label(w.case.lifecycle)}
            </span>
            <label className="bc-case-selector">
              <span className="bc-sr">Case của khách hàng</span>
              <select
                aria-label="Chọn case của khách hàng"
                title="Chỉ đổi case đang xem, không chuyển giao người xử lý"
                value={w.case.case_id}
                disabled={locked || !w.customer_cases?.length}
                onChange={(e) => onSelectCase(e.target.value)}
              >
                {(w.customer_cases?.length
                  ? w.customer_cases
                  : [{ ...w.case, created_at: "" }]
                ).map((c) => (
                  <option key={c.case_id} value={c.case_id}>
                    {c.case_id} · {label(c.lifecycle)}
                  </option>
                ))}
              </select>
            </label>
            <small>v{w.case.case_version}</small>
          </div>
          <div className="bc-case-meta">
            <div>
              <small>Người phụ trách</small>
              <strong>{w.assigned_collector || "Chưa có thông tin"}</strong>
            </div>
            <div>
              <small>Ngày mở case</small>
              <strong>{dateTime(w.case.created_at)}</strong>
            </div>
            <div>
              <small>Phạm vi xử lý</small>
              <strong>{w.case_scope.exposures.length} khoản vay</strong>
            </div>
          </div>
        </section>
      </div>
    </>
  );
}

export function CustomerInformation({ w }: { w: Workspace }) {
  const p = w.customer_profile;
  return (
    <section className="bc-panel">
      <div className="bc-panel-head">
        <h2>Thông tin khách hàng đã ghi nhận</h2>
        {p?.party_type === "ORGANIZATION" ? <Building2 /> : <UserRound />}
      </div>
      <dl className="bc-profile-fields">
        {[
          ["Tên khách hàng", p?.legal_name || w.case.full_name],
          ["CIF", mask(w.case.debtor_cif)],
          [
            "Loại khách hàng",
            p
              ? p.party_type === "ORGANIZATION"
                ? "Doanh nghiệp / tổ chức"
                : "Cá nhân"
              : "Chưa xác định",
          ],
          ["Mã số thuế", p?.tax_id ? mask(p.tax_id) : "Chưa có nguồn"],
          ["Điện thoại (đã che)", mask(w.case.phone_e164)],
          ["Ngành nghề", p?.industry || "Chưa có nguồn"],
          ["Khu vực", p?.region || "Chưa có nguồn"],
          ["RM", p?.rm_name || "Chưa có nguồn"],
          [
            "Nguồn hồ sơ",
            p
              ? `${p.source} · ${p.data_origin}`
              : `Bản ghi case · ${w.case.data_origin}`,
          ],
          ["Cập nhật hồ sơ nguồn", dateTime(p?.source_as_of)],
        ].map(([name, value]) => (
          <div key={name}>
            <dt>{name}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      <p className="bc-callout">
        Không suy loại khách hàng từ tên. Hồ sơ nguồn chưa kết nối thì không tự
        bổ sung MST, RM, nghề nghiệp hoặc quan hệ khách hàng.
      </p>
    </section>
  );
}

export function QuickAssessment({ scope }: { scope: Scope }) {
  const count = scope.exposures.length;
  const percent = count ? Math.round((scope.verified_count / count) * 100) : 0;
  return (
    <section className="bc-panel bc-assessment">
      <div className="bc-panel-head">
        <h2>Đánh giá nhanh</h2>
        <span className="bc-chip neutral">Chưa có mô hình rủi ro</span>
      </div>
      <div className="bc-assessment-body">
        <div
          className="bc-donut coverage"
          style={{
            background: `conic-gradient(var(--bc-teal) ${percent}%, var(--bc-line) 0)`,
          }}
          role="img"
          aria-label={`${scope.verified_count}/${count} khoản có snapshot xác minh`}
        >
          <div>
            <strong>
              {scope.verified_count}/{count}
            </strong>
            <small>Có snapshot</small>
          </div>
        </div>
        <dl>
          <div>
            <dt>Điểm rủi ro</dt>
            <dd>Chưa có dữ liệu</dd>
          </div>
          <div>
            <dt>Khả năng trả nợ</dt>
            <dd>Chưa đánh giá</dd>
          </div>
          <div>
            <dt>Mức độ hợp tác</dt>
            <dd>Chưa đánh giá</dd>
          </div>
          <div>
            <dt>Rủi ro phá PTP</dt>
            <dd>Chưa đánh giá</dd>
          </div>
        </dl>
      </div>
      <small>
        Vòng tròn là độ bao phủ snapshot, không phải điểm rủi ro hay độ mới dữ
        liệu.
      </small>
    </section>
  );
}

export function DebtComposition({ scope }: { scope: Scope }) {
  const d = debtComposition(scope);
  return (
    <section className="bc-panel">
      <div className="bc-panel-head">
        <h2>Cơ cấu dư nợ đã ghi nhận</h2>
        <Database />
      </div>
      {!d ? (
        <Empty
          icon="chart"
          title="Chưa đủ số dư để phân bổ"
          detail="Cần số dư đã xác minh, không xung đột và cùng định nghĩa tổng dư nợ."
        />
      ) : d.total === 0 ? (
        <Empty
          icon="chart"
          title="Tổng dư nợ ghi nhận bằng 0"
          detail="Không tự kết luận PTP đã giữ hoặc case đã tất toán."
        />
      ) : (
        <>
          <div className="bc-composition">
            <div
              className="bc-donut"
              style={{
                background: `conic-gradient(var(--bc-red) ${d.overduePercent}%, var(--bc-teal) 0)`,
              }}
              role="img"
              aria-label={`Quá hạn ${money(d.overdue)}; phần dư nợ còn lại ${money(d.remainder)}`}
            >
              <div>
                <strong>
                  {new Intl.NumberFormat("vi", {
                    maximumFractionDigits: 2,
                  }).format(
                    d.total / (d.total >= 1e9 ? 1e9 : d.total >= 1e6 ? 1e6 : 1),
                  )}
                </strong>
                <small>
                  {d.total >= 1e9
                    ? "tỷ VND"
                    : d.total >= 1e6
                      ? "triệu VND"
                      : "VND"}
                </small>
              </div>
            </div>
            <dl className="bc-chart-legend">
              <div>
                <dt>
                  <i className="teal" />
                  Dư nợ còn lại
                </dt>
                <dd>{money(d.remainder)}</dd>
              </div>
              <div>
                <dt>
                  <i className="red" />
                  Phần quá hạn
                </dt>
                <dd>{money(d.overdue)}</dd>
              </div>
            </dl>
          </div>
          <p className="bc-table-note">
            Tổng = gốc + lãi. Phần còn lại = tổng − quá hạn; không đồng nghĩa
            toàn bộ là khoản vay trong hạn.
          </p>
        </>
      )}
    </section>
  );
}

export function DpdChart({ history }: { history?: DpdHistory }) {
  const points = history?.points || [];
  const any = points.some((p) => p.max_dpd != null);
  const max = Math.max(1, ...points.map((p) => p.max_dpd || 0));
  return (
    <section className="bc-panel">
      <div className="bc-panel-head">
        <h2>Lịch sử DPD · 12 tháng</h2>
        <ChartColumn />
      </div>
      {!any ? (
        <Empty
          icon="chart"
          title="Chưa đủ lịch sử DPD"
          detail="Bắt đầu tích lũy từ snapshot Core hợp lệ. Không nội suy tháng thiếu thành 0 ngày."
        />
      ) : (
        <>
          <div className="bc-chart-key">
            <span>Thang đo: 0–{number(max)} ngày</span>
            <span>
              <i className="red" />
              DPD cao nhất
            </span>
            <span>
              <i className="blue" />
              Trung bình không trọng số
            </span>
          </div>
          <div
            className="bc-dpd-chart"
            role="img"
            aria-label="DPD theo tháng; giá trị chi tiết trong bảng dữ liệu bên dưới"
          >
            {points.map((p) => (
              <div
                className="bc-chart-month"
                key={p.month}
                title={`${p.month}: tối đa ${number(p.max_dpd)}, trung bình ${number(p.average_dpd)} ngày; ${p.observed_loans}/${p.scope_loans} khoản`}
              >
                <div className="bc-bars">
                  {p.max_dpd == null ? (
                    <span className="bc-missing">—</span>
                  ) : (
                    <>
                      <i
                        className="max"
                        style={{
                          height: `${(p.max_dpd / max) * 100}%`,
                        }}
                      />
                      <i
                        className="avg"
                        style={{
                          height: `${((p.average_dpd || 0) / max) * 100}%`,
                        }}
                      />
                    </>
                  )}
                </div>
                <small>
                  {p.month.slice(5)}/{p.month.slice(2, 4)}
                </small>
              </div>
            ))}
          </div>
        </>
      )}
      {!!points.length && (
        <details>
          <summary>Dữ liệu & cách tính</summary>
          <p>
            Lấy quan sát mới nhất của từng khoản trong tháng, theo giờ Việt Nam.
            Trung bình cộng trên các khoản thuộc phạm vi hiện tại; chỉ tính khi
            đủ tất cả khoản. Đây không phải số chốt cuối tháng.
          </p>
          <div className="bc-table-wrap">
            <table>
              <caption className="bc-sr">Dữ liệu lịch sử DPD</caption>
              <thead>
                <tr>
                  <th>Tháng</th>
                  <th>Cao nhất</th>
                  <th>Trung bình</th>
                  <th>Bao phủ</th>
                </tr>
              </thead>
              <tbody>
                {points.map((p) => (
                  <tr key={p.month}>
                    <td>
                      {p.month}
                      <small>
                        {dateTime(p.oldest_as_of)} → {dateTime(p.newest_as_of)}
                      </small>
                    </td>
                    <td>{number(p.max_dpd)}</td>
                    <td>{number(p.average_dpd)}</td>
                    <td>
                      {p.observed_loans}/{p.scope_loans}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
    </section>
  );
}

export function EwsPanel({
  w,
  compact = false,
  onDetails,
}: {
  w: Workspace;
  compact?: boolean;
  onDetails?: () => void;
}) {
  const signals = w.ews.signals;
  return (
    <section className="bc-panel">
      <div className="bc-panel-head">
        <div>
          <h2>Tín hiệu EWS gần đây ({signals.length})</h2>
          <small>
            Phạm vi khách hàng · Nguồn và xác minh riêng từng tín hiệu
          </small>
        </div>
        {compact ? (
          <button className="bc-link" onClick={onDetails}>
            Xem tất cả <ArrowUpRight />
          </button>
        ) : (
          <Radar />
        )}
      </div>
      {!signals.length ? (
        <Empty
          icon="ews"
          title="Chưa kết nối nguồn EWS"
          detail="Chưa có EWS intake hoặc policy handoff đang vận hành. DPD không tự trở thành cảnh báo EWS."
        />
      ) : (
        <div className="bc-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Ngày / nguồn</th>
                <th>Tín hiệu</th>
                <th>Mức độ</th>
                <th>Xác minh</th>
                <th>Case này</th>
              </tr>
            </thead>
            <tbody>
              {(compact ? signals.slice(0, 5) : signals).map((s) => (
                <tr key={s.signal_id}>
                  <td>
                    {dateTime(s.occurred_at)}
                    <small>
                      {s.source} · {s.data_origin}
                    </small>
                  </td>
                  <td>
                    {s.title}
                    <small>{s.signal_id}</small>
                  </td>
                  <td>
                    <span
                      className={`bc-chip ${s.severity === "HIGH" ? "danger" : s.severity === "MEDIUM" ? "warn" : "neutral"}`}
                    >
                      {
                        { HIGH: "Cao", MEDIUM: "Trung bình", LOW: "Thấp" }[
                          s.severity
                        ]
                      }
                    </span>
                  </td>
                  <td>
                    {{
                      VERIFIED: "Đã xác minh",
                      UNVERIFIED: "Chờ xác minh",
                      DISMISSED: "Đã loại",
                    }[s.verification] || "Chưa xác định"}
                  </td>
                  <td>
                    {w.policy_handoffs?.some((h) => h.signal_id === s.signal_id)
                      ? "Có bàn giao"
                      : "Chưa liên kết"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {!!signals.length && (
        <p className="bc-table-note">
          Bằng chứng đã ghi nhận không đồng nghĩa luồng EWS đang kết nối
          realtime.
        </p>
      )}
    </section>
  );
}

export function HandoffOutcomes({ w }: { w: Workspace }) {
  return (
    <>
      <section className="bc-panel">
        <div className="bc-panel-head">
          <h2>EWS → Policy → Case</h2>
          <ShieldCheck />
        </div>
        {!w.policy_handoffs?.length ? (
          <Empty
            icon="ews"
            title="Chưa có bàn giao được ghi nhận"
            detail="Cần mã tín hiệu, phiên bản policy, quyết định, lý do và case đích. Không suy bàn giao từ DPD."
          />
        ) : (
          w.policy_handoffs.map((h) => (
            <article className="bc-trace" key={h.handoff_id}>
              <div>
                <span className="bc-chip neutral">{h.signal_id}</span>
                <span>→</span>
                <strong>{h.policy_version}</strong>
                <span>→</span>
                <span className="bc-chip">{h.case_id}</span>
              </div>
              <p>
                {h.decision} · {h.reason}
              </p>
              <small>
                {h.handoff_id} · {dateTime(h.occurred_at)} · {h.data_origin}
              </small>
            </article>
          ))
        )}
      </section>
      <section className="bc-panel">
        <div className="bc-panel-head">
          <h2>Outcome feedback · Dấu vết kết quả</h2>
          <span className="bc-chip neutral">Nội bộ POC</span>
        </div>
        {!w.outcome_feedback?.links.length ? (
          <Empty
            icon="chart"
            title="Chưa có kết quả liên kết với quyết định"
            detail="Khi ghi nhận cuộc gọi, có thể chọn quyết định đã áp dụng. PTP và payment được theo dõi qua liên kết tường minh."
          />
        ) : (
          w.outcome_feedback.links.map((l) => (
            <article key={l.interaction_id} className="bc-trace">
              <div>
                <span className="bc-chip neutral">
                  Quyết định {l.feedback_id}
                </span>
                <span>→</span>
                <strong>{label(l.outcome)}</strong>
                <span>→</span>
                <span>
                  {l.ptp_status ? label(l.ptp_status) : "Không có PTP"}
                </span>
              </div>
              <small>
                {dateTime(l.created_at)} · {l.interaction_id}
              </small>
              {l.ptp_id && (
                <p>
                  {l.ptp_id} · Đã phân bổ: {money(l.paid_vnd)} · Đúng hạn:{" "}
                  {money(l.on_time_vnd)} · Nguồn đầy đủ đến:{" "}
                  {dateTime(l.observed_through)}
                </p>
              )}
              <details>
                <summary>Payment / đảo giao dịch ({l.payments.length})</summary>
                {l.payments.map((p) => (
                  <p key={p.event_id}>
                    {p.event_id} · {p.kind} · {money(p.amount_vnd)} ·{" "}
                    {dateTime(p.occurred_at)}
                    {p.reverses_event_id && ` · Đảo ${p.reverses_event_id}`}
                  </p>
                ))}
              </details>
            </article>
          ))
        )}
        <p className="bc-callout">
          Chấp nhận đề xuất ≠ thu hồi thành công. Dấu vết không chứng minh quan
          hệ nhân quả; chưa phát outcome sang EWS hoặc huấn luyện AI.
        </p>
      </section>
    </>
  );
}

export function Empty({
  title,
  detail,
  icon = "source",
}: {
  title: string;
  detail: string;
  icon?: "source" | "chart" | "ews";
}) {
  return (
    <div className="bc-empty">
      <span>
        {icon === "chart" ? (
          <ChartColumn />
        ) : icon === "ews" ? (
          <Radar />
        ) : (
          <CircleHelp />
        )}
      </span>
      <strong>{title}</strong>
      <p>{detail}</p>
    </div>
  );
}

export function UnconnectedPanel({
  section,
}: {
  section: "collateral" | "documents";
}) {
  return (
    <section className="bc-panel">
      <div className="bc-panel-head">
        <h2>
          {section === "collateral"
            ? "Tài sản bảo đảm & bảo lãnh"
            : "Tài liệu khách hàng / case"}
        </h2>
        <FileLock2 />
      </div>
      <Empty
        title="Chưa kết nối nguồn dữ liệu"
        detail={
          section === "collateral"
            ? "Cần nguồn quản lý tài sản, quan hệ với khoản vay, thời điểm định giá và quyền truy cập. Không tự nhập giá trị bảo đảm để tính khả năng thu hồi."
            : "Cần kho tài liệu, phân quyền và kiểm soát tải xuống. Chưa hỗ trợ tải lên hoặc mở tài liệu ngoài hệ thống."
        }
      />
    </section>
  );
}
