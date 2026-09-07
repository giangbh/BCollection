import type { ActionKind, Scope, Workspace } from "./types";
export const money = (v: number | null | undefined) =>
  v == null
    ? "Chưa có dữ liệu"
    : new Intl.NumberFormat("vi-VN").format(v) + " đ";
export const number = (v: number | null) =>
  v == null ? "—" : new Intl.NumberFormat("vi-VN").format(v);
export const mask = (s: string) =>
  s.length > 4 ? "••••" + s.slice(-4) : "••••";
export function dateTime(value: string | null | undefined): string {
  if (!value) return "Chưa có thông tin";
  if (!/(Z|[+-]\d{2}:\d{2})$/.test(value))
    return value + " (giờ nguồn chưa xác minh)";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Thời gian không hợp lệ"
    : new Intl.DateTimeFormat("vi-VN", {
        dateStyle: "short",
        timeStyle: "short",
        timeZone: "Asia/Ho_Chi_Minh",
      }).format(date);
}
const names: Record<string, string> = {
  CREDIT_CARD: "Thẻ tín dụng",
  PERSONAL_LOAN: "Vay cá nhân",
  AUTO_LOAN: "Vay mua ô tô",
  MORTGAGE: "Vay thế chấp",
  BUSY_NO_ANSWER: "Không nghe máy",
  SMS_SENT: "Đã gửi SMS",
  PTP_AGREED: "Ghi nhận lời hứa thanh toán",
  REFUSED: "Chưa thống nhất thanh toán",
  balance_check: "Đối soát số dư",
  schedule_contact: "Lưu lịch liên hệ",
  cancel_schedule: "Hủy lịch liên hệ",
  decision_feedback: "Phản hồi đề xuất",
  reconcile: "Xác nhận rà soát",
  wrapup: "Ghi nhận kết quả tương tác",
  OPEN: "Đang xử lý",
  CLOSED: "Đã đóng",
  SUSPENDED: "Tạm dừng",
  PROBATION: "Chờ rà soát",
  CURED: "Hết quá hạn",
  PRE_COLLECTION: "Trước thu hồi",
  EARLY_COLLECTION: "Thu hồi sớm",
  RECOVERY: "Xử lý thu hồi",
  SCHEDULED: "Chờ thực hiện",
  PARTIALLY_KEPT: "Đã trả một phần",
  KEPT: "Đã giữ đúng hạn",
  BROKEN: "Không giữ đúng hạn",
  UNVERIFIED: "Chưa xác minh",
  CANCELLED: "Đã hủy",
  OVERDUE: "Còn quá hạn",
  CURRENT: "Trong hạn",
  SETTLED: "Đã tất toán",
  CONFLICT: "Dữ liệu xung đột",
  PLANNED: "Đã lên lịch",
  SUPERSEDED: "Đã thay thế",
  ACCEPT: "Chấp nhận",
  ADJUST: "Điều chỉnh",
  DECLINE: "Không áp dụng",
  PAYMENT_RECONCILIATION: "Đối soát payment",
  RECONCILIATION_REQUIRED: "Cần rà soát",
  UNVERIFIED_EXPOSURE: "Khoản vay chưa xác minh",
};
export const label = (s: string | null) =>
  s ? names[s] || s : "Chưa có thông tin";
export const stale = (s: Scope, now = Date.now()) =>
  !s.exposures.length ||
  s.exposures.some(
    (e) =>
      !e.balance_verified ||
      e.conflict ||
      !e.source_as_of ||
      !Number.isFinite(Date.parse(e.source_as_of)) ||
      now - Date.parse(e.source_as_of) > 900000 ||
      Date.parse(e.source_as_of) - now > 30000,
  );
export function nextAction(w: Workspace, now = Date.now()): ActionKind {
  if (w.case.lifecycle === "CLOSED") return "VIEW_RESOLUTION";
  if (w.case.contact_hold_reason || w.case.lifecycle !== "OPEN")
    return "RECONCILE";
  if (stale(w.case_scope, now)) return "BALANCE_CHECK";
  if (
    w.contact_schedules.some(
      (s) => s.status === "PLANNED" && Date.parse(s.scheduled_at) > now,
    )
  )
    return "WAIT_SCHEDULE";
  return "CHECK_CONTACT";
}
export const actionCopy: Record<
  ActionKind,
  { title: string; button: string; note: string }
> = {
  VIEW_RESOLUTION: {
    title: "Case đã đóng. Không tiếp tục nhắc nợ.",
    button: "Xem kết quả đối soát",
    note: "Hết quá hạn khác tất toán; kết quả PTP có bằng chứng riêng.",
  },
  RECONCILE: {
    title: "Ưu tiên đối soát trước khi liên hệ",
    button: "Xem hồ sơ đối soát",
    note: "Không tự mở lại liên hệ chỉ vì phát hiện giao dịch thanh toán.",
  },
  BALANCE_CHECK: {
    title: "Xác minh số dư trước bước xử lý tiếp theo",
    button: "Đối soát số dư",
    note: "Dữ liệu thiếu, chưa xác minh hoặc quá thời hạn làm mới. Không suy ra đã hết nợ.",
  },
  WAIT_SCHEDULE: {
    title: "Chờ lịch liên hệ đã ghi nhận",
    button: "Xem / điều chỉnh lịch",
    note: "Lịch là kế hoạch của cán bộ, không phải bằng chứng về ưu tiên của khách hàng hoặc quyền gọi.",
  },
  CHECK_CONTACT: {
    title: "Kiểm tra điều kiện trước khi liên hệ",
    button: "Kiểm tra & gọi mô phỏng",
    note: "Kiểm tra Core và guardrail ngay lúc thực hiện; không tái sử dụng quyền gọi cũ.",
  },
};
