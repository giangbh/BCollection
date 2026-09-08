import type { Workspace } from './types';
import { dateTime, money } from './model';

const statuses: Record<string, string> = {
  RECORDED: 'Đã đồng bộ', UNCHANGED: 'Không thay đổi', EMPTY: 'Nguồn trả về rỗng',
  STALE: 'Dữ liệu cũ', NOT_CONNECTED: 'Chưa đồng bộ', NOT_CONFIGURED: 'Chưa cấu hình',
  NOT_FOUND: 'Không có bản ghi nguồn', SOURCE_UNAVAILABLE: 'Không kết nối được',
  HTTP_ERROR: 'Lỗi API nguồn', INVALID_CONTRACT: 'Dữ liệu không hợp lệ',
  OUT_OF_ORDER: 'Bản tin cũ bị từ chối', VERSION_CONFLICT: 'Xung đột phiên bản',
  SOURCE_CONFLICT: 'Nguồn thay đổi cần kiểm tra',
};

export function SourceStatus({ w }: { w: Workspace }) {
  if (!w.source_data) return null;
  return <details className="bc-panel">
    <summary>Nguồn dữ liệu Customer 360 · Trạng thái đồng bộ</summary>
    <div className="bc-table-wrap"><table>
      <thead><tr><th>Nguồn</th><th>Lần kiểm tra gần nhất</th><th>Bản dữ liệu đang hiển thị</th><th>Phạm vi</th></tr></thead>
      <tbody>{Object.entries(w.source_data).map(([name, resource]) => <tr key={name}>
        <td>{({ profile: 'CRM', loans: 'Core / Lịch trả nợ', history: 'Lịch sử DPD', collateral: 'Tài sản bảo đảm', directory: 'Danh bạ RM' } as Record<string, string>)[name]}</td>
        <td>{statuses[resource.status] || resource.status}<small>{dateTime(resource.last_attempt_at)}</small></td>
        <td>{resource.snapshot ? <>{resource.snapshot.source_system} · v{resource.snapshot.source_version}<small>{dateTime(resource.snapshot.as_of)} · {resource.snapshot.data_origin}</small></> : 'Chưa có bản dữ liệu hợp lệ'}</td>
        <td>{resource.snapshot?.coverage === 'COMPLETE' ? 'Đầy đủ theo contract nguồn' : resource.snapshot?.coverage === 'PARTIAL' ? 'Một phần' : 'Chưa xác định'}</td>
      </tr>)}</tbody>
    </table></div>
    <p className="bc-callout">Nguồn lỗi hoặc xung đột: giữ bản hợp lệ trước đó, không thay bằng 0. Dữ liệu trên 24 giờ được đánh dấu cũ. Danh bạ RM không phải đăng nhập hay phân công collector.</p>
  </details>;
}

export function SourceLoans({ w }: { w: Workspace }) {
  const source = w.source_data?.loans;
  if (!source?.snapshot) return null;
  return <section className="bc-panel">
    <h2>Danh mục khoản vay từ Core ({source.snapshot.items.length})</h2>
    <p>{statuses[source.status] || source.status} · {dateTime(source.snapshot.as_of)} · {source.snapshot.data_origin}</p>
    <div className="bc-table-wrap"><table>
      <thead><tr><th>Khoản vay / sản phẩm</th><th>Gốc + lãi</th><th>Quá hạn / DPD</th><th>Thuộc case này</th><th>Lịch trả nợ từ nguồn</th></tr></thead>
      <tbody>{source.snapshot.items.map(loan => <tr key={loan.loan_id}>
        <td>{loan.loan_id}<small>{loan.product_code}</small></td>
        <td>{money(loan.outstanding_principal + loan.outstanding_interest)}</td>
        <td>{money(loan.overdue_amount)}<small>{loan.dpd} ngày</small></td>
        <td>{w.case_scope.exposures.some(e => e.loan_id === loan.loan_id) ? 'Có' : 'Không'}</td>
        <td>{loan.repayment_schedule.length ? loan.repayment_schedule.map(p => <div key={p.due_at}>{dateTime(p.due_at)} · {money(p.amount_vnd)}</div>) : 'Nguồn không có kỳ trả nợ'}</td>
      </tr>)}</tbody>
    </table></div>
    <p className="bc-callout">Phạm vi {source.snapshot.coverage === 'COMPLETE' ? 'đầy đủ' : 'một phần'} theo nguồn tại thời điểm trên. Đồng bộ không tự thêm khoản vay vào case, không thay số dư tác nghiệp hay xác nhận PTP. Tổng case/khách hàng ở đầu trang vẫn là khoản đã ghi nhận trong B.Collection.</p>
  </section>;
}

export function CollateralSource({ w }: { w: Workspace }) {
  const source = w.source_data?.collateral;
  if (!source?.snapshot) return null;
  return <section className="bc-panel">
    <h2>Tài sản bảo đảm từ nguồn LOS</h2>
    <p>{statuses[source.status] || source.status} · {dateTime(source.snapshot.as_of)} · {source.snapshot.data_origin}</p>
    {!source.snapshot.items.length ? <p>Nguồn trả về danh sách tài sản rỗng; không phải lỗi kết nối.</p> : <div className="bc-table-wrap"><table>
      <thead><tr><th>Tài sản</th><th>Khoản vay liên quan</th><th>Giá trị định giá</th><th>Thời điểm / trạng thái</th></tr></thead>
      <tbody>{source.snapshot.items.map(item => <tr key={item.collateral_id}>
        <td>{item.collateral_id}<small>{item.description}</small></td><td>{item.loan_ids.join(', ')}</td>
        <td>{money(item.valuation_vnd)}</td><td>{dateTime(item.valued_at)}<small>{item.legal_status}</small></td>
      </tr>)}</tbody>
    </table></div>}
    <p className="bc-callout">Giá trị định giá không phải số tiền chắc chắn thu hồi. Đây là dữ liệu đọc, chưa có quyền xử lý tài sản hoặc liên hệ bên bảo lãnh.</p>
  </section>;
}

export function EventIntegrationStatus({ w }: { w: Workspace }) {
  const state = w.integration_state;
  if (!state) return null;
  return <details className="bc-panel">
    <summary>Payment / EWS / Outcome · Nhật ký tích hợp</summary>
    <h3>Cursor và mốc dữ liệu đầy đủ</h3>
    <div className="bc-table-wrap"><table>
      <thead><tr><th>Luồng</th><th>Cursor</th><th>Nguồn xác nhận đầy đủ đến</th><th>Đã xử lý đến</th><th>Lỗi nguồn</th></tr></thead>
      <tbody>{state.streams.map(s => <tr key={`${s.kind}:${s.stream_id}`}>
        <td>{s.kind} · {s.stream_id}</td><td>{s.cursor}</td><td>{dateTime(s.complete_through)}</td>
        <td>{dateTime(s.applied_through)}</td><td>{s.last_error || '—'}</td>
      </tr>)}</tbody>
    </table></div>
    <p>Payment chờ kiểm tra: {state.pending_payments.length} (hiển thị tối đa 100).</p>
    {state.pending_payments.map(p => <p key={p.event_id}>{p.event_id} · {p.state} · {p.error}</p>)}
    <p className="bc-callout">Nhận đủ sự kiện không có nghĩa mọi PTP đã được đối soát. Payment chưa phân bổ cần kiểm tra; nguồn không xác nhận đầy đủ thì không kết luận PTP bị phá. Đồng bộ không tự bỏ giữ liên hệ.</p>
    <h3>Quyết định handoff · policy demo</h3>
    {state.pending_ews?.map(e => <p key={e.event_id}>EWS chờ kiểm tra: {e.event_id} · {e.error}</p>)}
    <div className="bc-table-wrap"><table>
      <thead><tr><th>Tín hiệu / phiên bản</th><th>Policy</th><th>Quyết định</th><th>Case / lý do</th></tr></thead>
      <tbody>{state.ews_decisions.map(d => <tr key={`${d.signal_id}:${d.signal_version}:${d.policy_version}`}>
        <td>{d.signal_id} · v{d.signal_version}</td><td>{d.policy_version}</td><td>{d.decision}</td>
        <td>{d.case_id || 'Chưa tạo/gắn case'}<small>{d.reason}</small></td>
      </tr>)}</tbody>
    </table></div>
    <h3>Outcome outbox</h3>
    <p>Đã xác nhận nhận: {state.delivery.delivered} · Chờ gửi/gửi lại: {state.delivery.pending}</p>
    <div className="bc-table-wrap"><table>
      <thead><tr><th>Event / case version</th><th>Trạng thái</th><th>Số lần thử</th><th>Receipt / lỗi</th></tr></thead>
      <tbody>{state.delivery.events.map(e => <tr key={e.event_id}>
        <td>{e.event_id}<small>v{e.case_version}</small></td><td>{e.state}</td><td>{e.attempts}</td><td>{e.receipt_id || e.last_error || '—'}</td>
      </tr>)}</tbody>
    </table></div>
    <p className="bc-callout">Outbox có chống trùng và gửi lại; đảo giao dịch phát phiên bản outcome điều chỉnh. Receipt không chứng minh thu hồi thành công hay quan hệ nhân quả của AI. Chưa kết nối hệ thống thật.</p>
  </details>;
}
