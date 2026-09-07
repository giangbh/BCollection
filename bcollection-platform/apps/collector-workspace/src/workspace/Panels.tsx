import {
  ArrowUpRight,
  Database,
  ShieldCheck,
  CircleHelp,
  Clock3,
} from "lucide-react";
import type { Persona, Scope, Workspace } from "./types";
import { dateTime, label, mask, money, number } from "./model";

export function CaseHeader({
  w,
  profile,
  toggleProfile,
}: {
  w: Workspace;
  profile: boolean;
  toggleProfile: () => void;
}) {
  return (
    <>
      <div className="bc-eyebrow">CASE WORKSPACE / {w.case.case_id}</div>
      <div className="bc-head">
        <div>
          <h1>{w.case.full_name}</h1>
          <div className="bc-subtitle">
            <span>CIF {mask(w.case.debtor_cif)}</span>
            <span>{mask(w.case.phone_e164)}</span>
          <span>{label(w.case.product_code)}</span>
          </div>
        </div>
        <div className="bc-head-meta">
          <span
            className={`bc-chip ${w.case.contact_hold_reason ? "warn" : ""}`}
          >
            {label(w.case.lifecycle)}
            {w.case.resolution ? ` · ${label(w.case.resolution)}` : ""}
          </span>
          <small>
            Phụ trách: {w.assigned_collector || "Chưa có thông tin"}
          </small>
          <button
            className="bc-link"
            onClick={toggleProfile}
            aria-expanded={profile}
          >
            Thông tin khách hàng <ArrowUpRight />
          </button>
        </div>
      </div>
      {profile && (
        <section className="bc-panel bc-profile">
          <h2>Thông tin khách hàng đã ghi nhận</h2>
          <div className="bc-detail-grid">
            <div>
              <small>CIF / số điện thoại (đã che)</small>
              <strong>
                {mask(w.case.debtor_cif)} / {mask(w.case.phone_e164)}
              </strong>
            </div>
            <div>
              <small>Nguồn dữ liệu</small>
              <strong>{w.case.data_origin}</strong>
            </div>
            <div>
              <small>Nghề nghiệp / đơn vị công tác</small>
              <strong>Chưa có nguồn dữ liệu</strong>
            </div>
            <div>
              <small>Khung giờ ưu tiên của khách hàng</small>
              <strong>Chưa xác minh · Không suy từ lịch cán bộ</strong>
            </div>
          </div>
        </section>
      )}
    </>
  );
}

export function ScopeSummary({
  scope,
  customer,
  onEvidence,
}: {
  scope: Scope;
  customer: boolean;
  onEvidence: () => void;
}) {
  return (
    <>
      <section className="bc-metrics" aria-label="Tổng hợp nghĩa vụ">
        <div className="bc-metric">
          <label>Nợ quá hạn đã ghi nhận</label>
          <div
            className={`bc-value ${scope.overdue_vnd === 0 ? "paid" : "debt"}`}
          >
            {money(scope.overdue_vnd)}
          </div>
          <small>{scope.exposures.length} khoản vay trong phạm vi</small>
        </div>
        <div className="bc-metric">
          <label>Tổng dư nợ đã ghi nhận</label>
          <div className="bc-value">{money(scope.total_vnd)}</div>
          <small>
            {customer
              ? "Không khẳng định đầy đủ danh mục Core"
              : "Chỉ các khoản vay thuộc case"}
          </small>
        </div>
        <div className="bc-metric">
          <label>DPD cao nhất</label>
          <div className="bc-value">
            {number(scope.max_dpd)} <em>ngày</em>
          </div>
          <small>
            {scope.verified_count}/{scope.exposures.length} khoản đã xác minh
          </small>
        </div>
      </section>
      <div className="bc-source">
        <Database size={14} />
        <span>
          Nguồn:{" "}
          {scope.verified_count
            ? "Core snapshot + bản ghi B.Collection"
            : "Bản ghi B.Collection · Chưa đối soát Core"}
        </span>
        <button className="bc-link" onClick={onEvidence}>
          Nguồn & đối soát <ArrowUpRight />
        </button>
      </div>
      {scope.conflict_count > 0 && (
        <p role="alert" className="bc-error">
          Có {scope.conflict_count} khoản vay xung đột. Không cộng tổng khi chưa
          xác định được số dư đúng.
        </p>
      )}
    </>
  );
}

export function ExposureTable({
  scope,
  caseId,
  customer,
}: {
  scope: Scope;
  caseId: string;
  customer: boolean;
}) {
  return (
    <section className="bc-panel">
      <div className="bc-panel-head">
        <div>
          <h2>
            {customer
              ? "Các khoản vay đã ghi nhận trong B.Collection"
              : "Nghĩa vụ trong case"}
          </h2>
          <small>Đơn vị: VND · Không suy ngày đến hạn từ DPD</small>
        </div>
        <span className="bc-chip neutral">
          {scope.exposures.length} khoản vay
        </span>
      </div>
      <div className="bc-table-wrap">
        <table>
          <caption className="bc-sr">
            Số dư từng khoản vay theo phạm vi đang chọn
          </caption>
          <thead>
            <tr>
              <th>Khoản vay / bằng chứng</th>
              <th className="num">Dư nợ</th>
              <th className="num">Quá hạn</th>
              <th className="num">DPD</th>
            </tr>
          </thead>
          <tbody>
            {scope.exposures.map((e) => (
              <tr key={e.loan_id}>
                <td>
                  <span className="bc-loan">{e.loan_id}</span>
                  <small>
                    {label(e.obligation_status)} ·{" "}
                    {e.case_ids.includes(caseId) ? "Trong case" : "Ngoài case"}
                  </small>
                  <small>
                    {e.source_as_of
                      ? dateTime(e.source_as_of)
                      : "Chưa có thời điểm xác minh"}
                  </small>
                </td>
                <td className="num">
                  {e.principal_vnd == null || e.interest_vnd == null
                    ? "—"
                    : number(e.principal_vnd + e.interest_vnd)}
                </td>
                <td className="num bc-negative">{number(e.overdue_vnd)}</td>
                <td className="num">{number(e.dpd)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td>Tổng theo phạm vi</td>
              <td className="num">{number(scope.total_vnd)}</td>
              <td className="num">{number(scope.overdue_vnd)}</td>
              <td className="num">{number(scope.max_dpd)}</td>
            </tr>
          </tfoot>
        </table>
      </div>
      {!scope.exposures.length && (
        <p className="bc-callout">Chưa có khoản vay trong phạm vi này.</p>
      )}
      <p className="bc-table-note">
        {customer
          ? "Đã loại trùng theo loan ID; chỉ bao phủ dữ liệu có trong B.Collection. Hành động vẫn gắn case đang chọn."
          : "Số tổng hợp và bảng được đọc từ cùng snapshot. Chưa xác minh không đồng nghĩa hết nợ."}
      </p>
    </section>
  );
}

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
            <h2>Cam kết thanh toán</h2>
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
        {(compact ? ptps.slice(0, 2) : ptps).map((p) => (
          <article key={p.ptp_id} className="bc-ptp-item">
            <div className="bc-panel-head">
              <div>
                <h3>{p.ptp_id}</h3>
                <small>{p.loan_id}</small>
              </div>
              <span className={`bc-chip ${p.status === "KEPT" ? "" : "warn"}`}>
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
            <small>
              {p.status === "UNVERIFIED"
                ? "Dữ liệu PTP cũ chưa đủ bằng chứng; không đưa vào tỷ lệ giữ cam kết."
                : `Đúng hạn: ${money(p.on_time_vnd)} · Thiếu để giữ đúng hạn: ${money(Math.max(0, p.amount_vnd - p.on_time_vnd))}`}
            </small>
            {!compact && (
              <p className="bc-table-note">
                Nguồn payment xác nhận đầy đủ đến:{" "}
                {dateTime(p.observed_through)}. Không tự kết luận BROKEN chỉ vì
                đồng hồ vượt hạn.
              </p>
            )}
          </article>
        ))}
        {compact && ptps.length > 2 && (
          <small>Còn {ptps.length - 2} PTP khác trong tab chi tiết.</small>
        )}
      </section>
      {!compact && (
        <section className="bc-panel">
          <div className="bc-panel-head">
            <h2>Payment & đối soát</h2>
            <span className="bc-chip neutral">
              {w.payment_ledger.length} sự kiện
            </span>
          </div>
          {!w.payment_ledger.length ? (
            <p className="bc-callout">
              Chưa có payment trong ledger của case. Số dư Core bằng 0 không tự
              tạo payment hoặc PTP KEPT.
            </p>
          ) : (
            <div className="bc-table-wrap">
              <table>
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
                        <small>{p.loan_id}</small>
                        <small>{dateTime(p.occurred_at)}</small>
                      </td>
                      <td className="num">{money(p.amount_vnd)}</td>
                      <td>
                        {p.kind}
                        <small>
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
          <p className="bc-table-note">
            Giữ giao dịch đảo và ID gốc; không sửa hoặc trừ số dư thủ công tại
            đây.
          </p>
        </section>
      )}
    </>
  );
}

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
      detail: t.reason.includes(":") ? label(t.reason.slice(0, t.reason.indexOf(":"))) + ": " + t.reason.slice(t.reason.indexOf(":") + 1) : label(t.reason),
      origin: "Audit ứng dụng",
    })),
  ].sort((a, b) => b.at.localeCompare(a.at));
  return (
    <section className="bc-panel">
      <div className="bc-panel-head">
        <h2>Diễn biến & lịch sử thay đổi</h2>
        <span className="bc-chip neutral">Theo nguồn ghi nhận</span>
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
      {events.length > 12 && (
        <details>
          <summary>{events.length - 12} sự kiện trước đó</summary>
          {events.slice(12).map((e) => (
            <p key={e.id}>
              {dateTime(e.at)} · {e.title} · {e.detail}
            </p>
          ))}
        </details>
      )}
    </section>
  );
}

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
        <p className="bc-callout">
          {scope.verified_count}/{scope.exposures.length} khoản được xác minh;
          không khẳng định dữ liệu đã bao phủ toàn danh mục Core. Số 0 khác dữ
          liệu thiếu.
        </p>
      </section>
      <section className="bc-panel">
        <div className="bc-panel-head">
          <h2>EWS & policy handoff</h2>
          <span className="bc-chip neutral">Chưa kết nối</span>
        </div>
        <p className="bc-callout">
          Chưa có EWS intake hoặc policy handoff đang vận hành. Không tạo cảnh
          báo giả hay coi DPD là quyết định bàn giao tự động.
        </p>
      </section>
      <section className="bc-panel">
        <div className="bc-panel-head">
          <h2>Persona / AI mô phỏng</h2>
          <span className="bc-chip warn">Không dùng vận hành thật</span>
        </div>
        <p className="bc-table-note">
          Ưu tiên dữ liệu thiếu và PTP đã đối soát thay vì hiển thị điểm tin cậy
          giả. Gợi ý hành động trên workspace là quy tắc trạng thái, không phải
          mô hình AI.
        </p>
        <button
          className="bc-button"
          disabled={!allowPersona}
          onClick={onLoadPersona}
        >
          Tải dữ liệu Persona mô phỏng
        </button>
        {!allowPersona && (
          <p className="bc-table-note">
            Bị vô hiệu hóa ở chế độ chỉ đọc hoặc chưa xác định runtime.
          </p>
        )}
        {personaError && (
          <p className="bc-error" role="alert">
            {personaError}
          </p>
        )}
        {persona && (
          <div className="bc-detail-grid">
            <div>
              <small>Tỷ lệ giữ PTP đã đối soát</small>
              <strong>
                {persona.behavioral_summary?.ptp_kept_rate == null
                  ? "Chưa đủ dữ liệu"
                  : `${Math.round(persona.behavioral_summary.ptp_kept_rate * 100)}% (${persona.behavioral_summary.ptp_mature_count} PTP)`}
              </strong>
            </div>
            <div>
              <small>Lịch sử trả đúng kỳ</small>
              <strong>
                {persona.behavioral_summary?.historical_on_time_ratio == null
                  ? "Chưa có dữ liệu"
                  : `${persona.behavioral_summary.historical_on_time_ratio * 100}%`}
              </strong>
            </div>
            <div>
              <small>Dữ liệu còn thiếu</small>
              <strong>
                {persona.behavioral_summary?.missing_features?.join(", ") ||
                  "Chưa có báo cáo độ đầy đủ"}
              </strong>
            </div>
          </div>
        )}
      </section>
    </>
  );
}

export function GuardrailPanel({
  reason,
  details,
  canCheck,
  onCheck,
}: {
  reason: string;
  details: string;
  canCheck: boolean;
  onCheck: () => void;
}) {
  return (
    <section className="bc-panel">
      <div className="bc-panel-head">
        <h2>Điều kiện liên hệ</h2>
        <ShieldCheck />
      </div>
      <span className="bc-chip warn">{reason}</span>
      <div className="bc-rule">
        <Clock3 />
        <div>
          <strong>Lịch liên hệ là kế hoạch</strong>
          <small>Không thay thế quyền thực hiện</small>
        </div>
      </div>
      <div className="bc-rule">
        <Database />
        <div>
          <strong>Core / payment kiểm tra lại</strong>
          <small>Không dùng dấu tích lưu từ trước</small>
        </div>
      </div>
      <div className="bc-rule">
        <CircleHelp />
        <div>
          <strong>Quyền và hạn mức liên hệ</strong>
          <small>
            {details || "Chưa có đánh giá hiệu lực cho lần gọi mới"}
          </small>
        </div>
      </div>
      <button className="bc-button" disabled={!canCheck} onClick={onCheck}>
        Kiểm tra & gọi mô phỏng
      </button>
      <p className="bc-safety">
        Mỗi lần bấm đều kiểm tra lại. Không có cuộc gọi thật; integration chỉ
        đọc.
      </p>
    </section>
  );
}
