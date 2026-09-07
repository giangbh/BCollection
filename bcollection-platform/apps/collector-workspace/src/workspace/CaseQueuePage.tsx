import { useEffect, useMemo, useState } from "react";
import { ArrowRight, Search } from "lucide-react";
import { request, errorText } from "./api";
import { label, mask, money } from "./model";
import type { CaseRecord } from "./types";

export function CaseQueuePage({
  onSelect,
}: {
  onSelect: (id: string) => void;
}) {
  const [cases, setCases] = useState<CaseRecord[]>([]),
    [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true),
    [error, setError] = useState(""),
    [retry, setRetry] = useState(0),
    [page, setPage] = useState(0);
  useEffect(() => {
    const abort = new AbortController();
    setLoading(true);
    setError("");
    request<CaseRecord[]>("/api/cases", { signal: abort.signal })
      .then((data) => {
        if (!Array.isArray(data)) throw new Error("Danh sách không hợp lệ.");
        if (!abort.signal.aborted) setCases(data);
      })
      .catch((e) => {
        if (!abort.signal.aborted) setError(errorText(e));
      })
      .finally(() => {
        if (!abort.signal.aborted) setLoading(false);
      });
    return () => abort.abort();
  }, [retry]);
  const filtered = useMemo(
    () =>
      cases.filter((c) =>
        [c.case_id, c.full_name, c.debtor_cif, c.phone_e164].some((v) =>
          v.toLocaleLowerCase("vi").includes(query.toLocaleLowerCase("vi")),
        ),
      ),
    [cases, query],
  );
  return (
    <main className="bc-content">
      <div className="bc-eyebrow">COLLECTOR WORKSPACE</div>
      <h1>Hồ sơ xử lý</h1>
      <p className="bc-subtitle">
        Chọn hồ sơ để xem nghĩa vụ, bằng chứng và bước xử lý tiếp theo.
      </p>
      <div className="bc-queue-search">
        <Search aria-hidden="true" />
        <label className="bc-sr" htmlFor="case-search">
          Tìm hồ sơ theo tên, CIF, mã case hoặc số điện thoại
        </label>
        <input
          id="case-search"
          type="search"
          placeholder="Tìm theo tên, CIF, mã case, số điện thoại..."
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setPage(0);
          }}
        />
      </div>
      {loading && (
        <p role="status" className="bc-callout">
          Đang tải danh sách...
        </p>
      )}
      {error && (
        <p role="alert" className="bc-error">
          {error}{" "}
          <button className="bc-button" onClick={() => setRetry(retry + 1)}>
            Thử lại
          </button>
        </p>
      )}
      {!loading && !error && (
        <section className="bc-panel">
          <div className="bc-panel-head">
            <h2>{filtered.length} hồ sơ đã ghi nhận</h2>
            <span className="bc-chip neutral">
              Không phải toàn danh mục Core
            </span>
          </div>
          <div className="bc-table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Khách hàng / hồ sơ</th>
                  <th className="num">Nợ quá hạn ghi nhận</th>
                  <th className="num">DPD</th>
                  <th>Trạng thái / nguồn</th>
                  <th>
                    <span className="bc-sr">Mở hồ sơ</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {filtered.slice(page * 25, page * 25 + 25).map((c) => (
                  <tr key={c.case_id}>
                    <td>
                      <button
                        className="bc-link bc-customer-name"
                        onClick={() => onSelect(c.case_id)}
                      >
                        {c.full_name}
                      </button>
                      <small>
                        {c.case_id} · CIF {mask(c.debtor_cif)}
                      </small>
                    </td>
                    <td className="num">{money(c.overdue_amount)}</td>
                    <td className="num">{c.dpd}</td>
                    <td>
                      <span
                        className={`bc-chip ${c.contact_hold_reason ? "warn" : "neutral"}`}
                      >
                        {c.contact_hold_reason
                          ? label(c.contact_hold_reason)
                          : label(c.lifecycle)}
                      </span>
                      <small>{c.data_origin}</small>
                    </td>
                    <td>
                      <button
                        className="bc-link"
                        aria-label={`Mở hồ sơ ${c.case_id}`}
                        onClick={() => onSelect(c.case_id)}
                      >
                        <ArrowRight />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!filtered.length && (
            <p className="bc-callout">
              {cases.length
                ? "Không tìm thấy hồ sơ phù hợp."
                : "Chưa có hồ sơ. Khởi tạo schema không tự tạo dữ liệu demo."}
            </p>
          )}
          <div className="bc-actions-row">
            <button
              className="bc-button"
              disabled={page === 0}
              onClick={() => setPage(page - 1)}
            >
              Trang trước
            </button>
            <small>
              Trang {page + 1} / {Math.max(1, Math.ceil(filtered.length / 25))}
            </small>
            <button
              className="bc-button"
              disabled={(page + 1) * 25 >= filtered.length}
              onClick={() => setPage(page + 1)}
            >
              Trang sau
            </button>
          </div>
        </section>
      )}
    </main>
  );
}
