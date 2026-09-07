import { useEffect, useRef, useState } from "react";
import { Search, X } from "lucide-react";
import { request, errorText } from "./api";
import { label, mask } from "./model";

interface Result {
  items: {
    case_id: string;
    debtor_cif: string;
    full_name: string;
    lifecycle: string;
    data_origin: string;
  }[];
  has_more: boolean;
}

export function GlobalSearch({
  onSelect,
  locked,
}: {
  onSelect: (id: string) => void;
  locked: boolean;
}) {
  const [query, setQuery] = useState(""),
    [result, setResult] = useState<Result | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [open, setOpen] = useState(false);
  const input = useRef<HTMLInputElement>(null),
    abort = useRef<AbortController>();
  useEffect(() => {
    const shortcut = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        input.current?.focus();
      }
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", shortcut);
    return () => {
      window.removeEventListener("keydown", shortcut);
      abort.current?.abort();
    };
  }, []);
  const search = async (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim().length < 2) return;
    abort.current?.abort();
    const controller = new AbortController();
    abort.current = controller;
    setBusy(true);
    setOpen(true);
    setError("");
    setResult(null);
    try {
      const data = await request<Result>(
        `/api/customer-search?q=${encodeURIComponent(query.trim())}`,
        { signal: controller.signal },
      );
      if (!controller.signal.aborted) setResult(data);
    } catch (e) {
      if (!controller.signal.aborted) setError(errorText(e));
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  };
  return (
    <div className="bc-global-search">
      <form role="search" onSubmit={search}>
        <Search />
        <label className="bc-sr" htmlFor="global-search">
          Tìm khách hàng, CIF, MST, khoản vay hoặc case
        </label>
        <input
          ref={input}
          id="global-search"
          type="search"
          maxLength={100}
          minLength={2}
          placeholder="Tìm khách hàng, CIF, MST, khoản vay, case…"
          value={query}
          onChange={(e) => {
            abort.current?.abort();
            setBusy(false);
            setQuery(e.target.value);
            setResult(null);
            setOpen(false);
          }}
        />
        <button
          className="bc-link"
          type="submit"
          disabled={busy || query.trim().length < 2}
          aria-label="Tìm kiếm"
        >
          Tìm
        </button>
        <kbd>⌘ K</kbd>
      </form>
      {open && (
        <section className="bc-search-results" aria-label="Kết quả tìm kiếm">
          <div className="bc-panel-head">
            <small>Chỉ dữ liệu đã ghi nhận trong B.Collection</small>
            <button
              className="bc-link"
              aria-label="Đóng kết quả tìm kiếm"
              onClick={() => setOpen(false)}
            >
              <X />
            </button>
          </div>
          {busy && <p role="status">Đang tìm…</p>}
          {error && <p role="alert">{error}</p>}
          {result && !result.items.length && (
            <p>Không tìm thấy kết quả phù hợp.</p>
          )}
          {result?.items.map((c) => (
            <button
              className="bc-search-result"
              key={c.case_id}
              disabled={locked}
              onClick={() => {
                onSelect(c.case_id);
                setOpen(false);
              }}
            >
              <strong>{c.full_name}</strong>
              <small>
                {c.case_id} · CIF {mask(c.debtor_cif)} · {label(c.lifecycle)} ·{" "}
                {c.data_origin}
              </small>
            </button>
          ))}
          {result?.has_more && (
            <p>Hiển thị 25 kết quả. Nhập thêm thông tin để thu hẹp.</p>
          )}
          {locked && <p>Hoàn tất hoặc bỏ bản nháp trước khi đổi case.</p>}
        </section>
      )}
    </div>
  );
}
