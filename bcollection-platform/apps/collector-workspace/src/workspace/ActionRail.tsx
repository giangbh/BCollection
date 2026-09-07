import { ArrowUpRight, CalendarClock } from "lucide-react";
import { GuardrailPanel } from "./Panels";
import { actionCopy, dateTime, label } from "./model";
import type { ActionKind, GuardrailResult, Section, Workspace } from "./types";

interface Props {
  w: Workspace;
  action: ActionKind;
  writable: boolean;
  primaryDisabled: boolean;
  editDisabled: boolean;
  planDisabled: boolean;
  canCheck: boolean;
  busy: boolean;
  connected: boolean;
  guard: GuardrailResult | null;
  guardMessage: string;
  note: string;
  setNote: (note: string) => void;
  setSection: (section: Section) => void;
  onPrimary: () => void;
  onCheck: () => void;
  onSaveNote: () => void;
  onOpen: (
    mode: "schedule_contact" | "cancel_schedule" | "decision_feedback",
  ) => void;
}

export function ActionRail(p: Props) {
  const { w, action, note } = p;
  const copy = actionCopy[action];
  const schedule = w.contact_schedules.find((s) => s.status === "PLANNED");
  const reason =
    w.case.lifecycle !== "OPEN"
      ? label(w.case.lifecycle) + " · Không liên hệ"
      : w.case.contact_hold_reason
        ? label(w.case.contact_hold_reason)
        : p.connected
          ? "Đang gọi mô phỏng"
          : action === "WAIT_SCHEDULE"
            ? "Chưa đến lịch liên hệ"
            : action === "BALANCE_CHECK"
              ? "Chưa đủ bằng chứng số dư"
              : "Chưa cấp quyền cho lần gọi mới";
  return (
    <aside className="bc-stack bc-rail" aria-label="Hỗ trợ quyết định">
      <section
        className={`bc-next ${action === "RECONCILE" ? "hold" : ""}`}
        aria-label="Việc cần làm tiếp theo"
      >
        <div className="bc-panel-head">
          <h2>Việc cần làm tiếp theo</h2>
          <CalendarClock />
        </div>
        <strong>{copy.title}</strong>
        <small>{copy.note}</small>
        {schedule && (
          <small>Lịch đã lưu: {dateTime(schedule.scheduled_at)}</small>
        )}
        <button
          className="bc-button primary"
          disabled={p.primaryDisabled}
          onClick={p.onPrimary}
        >
          {copy.button}
        </button>
        <button
          className="bc-button"
          disabled={p.planDisabled}
          onClick={() => p.onOpen("schedule_contact")}
        >
          {schedule ? "Điều chỉnh lịch" : "Lên lịch liên hệ"}
        </button>
        {schedule && (
          <button
            className="bc-link"
            disabled={p.editDisabled}
            onClick={() => p.onOpen("cancel_schedule")}
          >
            Hủy lịch đã lưu
          </button>
        )}
        <small>
          {!p.writable
            ? "Chế độ chỉ đọc / chưa đủ dữ liệu"
            : "Kế hoạch cán bộ · Không tự động liên hệ"}
        </small>
        {!!w.contact_schedules.length && (
          <details>
            <summary>Lịch sử lịch hẹn ({w.contact_schedules.length})</summary>
            {w.contact_schedules.map((s) => (
              <p key={s.schedule_id}>
                {dateTime(s.scheduled_at)} · {label(s.status)} · {s.reason}
              </p>
            ))}
          </details>
        )}
      </section>
      <GuardrailPanel
        reason={reason}
        details={[
          p.guardMessage,
          p.guard?.evaluated_at && dateTime(p.guard.evaluated_at),
          p.guard?.policy_version,
        ]
          .filter(Boolean)
          .join(" · ")}
        canCheck={p.canCheck}
        onCheck={p.onCheck}
      />
      <section className="bc-panel">
        <div className="bc-panel-head">
          <h2>Khuyến nghị xử lý</h2>
          <span className="bc-chip neutral">Theo quy tắc</span>
        </div>
        <p className="bc-aimain">{copy.title}</p>
        <button className="bc-link" onClick={() => p.setSection("evidence")}>
          Nguồn & dữ liệu thiếu <ArrowUpRight />
        </button>
        <button
          className="bc-button"
          disabled={p.editDisabled}
          onClick={() => p.onOpen("decision_feedback")}
        >
          Ghi nhận quyết định
        </button>
        <p className="bc-safety">
          Lưu kèm phiên bản case · Không phải kết quả thanh toán hay điểm AI.
        </p>
        {w.decision_feedback.length > 0 && (
          <div className="bc-decisions">
            <h3>Quyết định đã lưu</h3>
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
          </div>
        )}
      </section>
      <section className="bc-panel">
        <div className="bc-panel-head">
          <h2>Ghi chú nhanh</h2>
          <span className="bc-chip neutral">Case này</span>
        </div>
        <form
          className="bc-quick-note"
          onSubmit={(e) => {
            e.preventDefault();
            if (note.trim() && !p.editDisabled) p.onSaveNote();
          }}
        >
          <label className="bc-sr" htmlFor="quick-note">
            Nội dung ghi chú nhanh
          </label>
          <textarea
            id="quick-note"
            value={note}
            maxLength={2000}
            disabled={p.busy || !p.writable}
            onChange={(e) => p.setNote(e.target.value)}
            placeholder="Ghi lại thông tin cần theo dõi…"
          />
          <small>{note.length}/2000 · Chưa hỗ trợ @mention</small>
          <button
            type="submit"
            className="bc-button primary"
            disabled={p.editDisabled || !note.trim()}
          >
            Lưu ghi chú
          </button>
          {!!note && (
            <button
              type="button"
              className="bc-link"
              disabled={p.busy}
              onClick={() => {
                if (window.confirm("Bỏ nội dung ghi chú chưa lưu?"))
                  p.setNote("");
              }}
            >
              Bỏ bản nháp
            </button>
          )}
        </form>
        {w.case_notes?.slice(0, 2).map((n) => (
          <article className="bc-note" key={n.note_id}>
            <small>
              {dateTime(n.created_at)} · {n.author}
            </small>
            <p>{n.body}</p>
          </article>
        ))}
        <button
          className="bc-link"
          onClick={() => p.setSection("interactions")}
        >
          Xem ghi chú & nhật ký <ArrowUpRight />
        </button>
        <p className="bc-safety">
          Tác giả POC là tài khoản mô phỏng, chưa có SSO.
        </p>
      </section>
    </aside>
  );
}
