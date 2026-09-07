import React, { useState } from "react";
import { Send, MessageSquare, Clock, Check } from "lucide-react";

export function QuickNotes({ caseId }: { caseId: string }) {
  const [activeTab, setActiveTab] = useState<"note" | "log" | "chat">("note");
  const [text, setText] = useState("");
  const [notes, setNotes] = useState<{ id: string; text: string; time: string; author: string }[]>([]);
  const [savedNotice, setSavedNotice] = useState(false);

  const handleSave = () => {
    if (!text.trim()) return;
    const newNote = {
      id: Date.now().toString(),
      text: text.trim(),
      time: new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" }),
      author: "Nguyễn Thị Lan",
    };
    setNotes([newNote, ...notes]);
    setText("");
    setSavedNotice(true);
    setTimeout(() => setSavedNotice(false), 2000);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      handleSave();
    }
  };

  return (
    <section className="bc-panel bc-quicknotes" aria-label="Ghi chú nhanh">
      <div className="bc-quicknotes-tabs">
        <button
          type="button"
          className={`bc-qntab ${activeTab === "note" ? "active" : ""}`}
          onClick={() => setActiveTab("note")}
        >
          Ghi chú
        </button>
        <button
          type="button"
          className={`bc-qntab ${activeTab === "log" ? "active" : ""}`}
          onClick={() => setActiveTab("log")}
        >
          Nhật ký xử lý
        </button>
        <button
          type="button"
          className={`bc-qntab ${activeTab === "chat" ? "active" : ""}`}
          onClick={() => setActiveTab("chat")}
        >
          @Trao đổi
        </button>
      </div>

      <div className="bc-quicknotes-body">
        <textarea
          className="bc-quicknotes-input"
          placeholder={
            activeTab === "note"
              ? "Nhập ghi chú... (⌘ + Enter để lưu)"
              : activeTab === "log"
              ? "Nhập nhật ký xử lý công việc..."
              : "Nhập tin nhắn trao đổi nội bộ (@ để tag cán bộ)..."
          }
          maxLength={500}
          rows={3}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <div className="bc-quicknotes-foot">
          <span className="bc-quicknotes-count">{text.length}/500</span>
          <div className="bc-quicknotes-actions">
            {savedNotice && (
              <span className="bc-quicknotes-saved">
                <Check size={14} /> Đã lưu
              </span>
            )}
            <button
              type="button"
              className="bc-button primary small"
              disabled={!text.trim()}
              onClick={handleSave}
            >
              Lưu
            </button>
          </div>
        </div>

        {notes.length > 0 && (
          <div className="bc-quicknotes-list">
            {notes.slice(0, 3).map((n) => (
              <div key={n.id} className="bc-quicknote-item">
                <div className="bc-quicknote-meta">
                  <strong>{n.author}</strong> · <span>{n.time}</span>
                </div>
                <p>{n.text}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
