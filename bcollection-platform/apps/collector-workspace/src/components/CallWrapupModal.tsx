import React, { useState } from 'react';
import { X, CheckCircle2, Calendar, DollarSign } from 'lucide-react';

interface CallWrapupModalProps {
  isOpen: boolean;
  activeCase: any;
  onClose: () => void;
  onSubmit: (outcome: string, ptpAmount?: number, ptpDate?: string, notes?: string) => void;
}

export const CallWrapupModal: React.FC<CallWrapupModalProps> = ({
  isOpen,
  activeCase,
  onClose,
  onSubmit,
}) => {
  const [outcome, setOutcome] = useState('PTP_AGREED');
  const [ptpAmount, setPtpAmount] = useState(activeCase?.overdue_amount || 0);
  const [ptpDate, setPtpDate] = useState(
    new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
  );
  const [notes, setNotes] = useState('');

  if (!isOpen || !activeCase) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(outcome, outcome === 'PTP_AGREED' ? Number(ptpAmount) : undefined, outcome === 'PTP_AGREED' ? ptpDate : undefined, notes);
  };

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.7)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      backdropFilter: 'blur(4px)'
    }}>
      <div style={{
        backgroundColor: 'var(--bg-card)',
        borderRadius: '16px',
        border: '1px solid var(--border)',
        width: '480px',
        padding: '24px',
        boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: 700 }}>Ghi nhận Kết quả Cuộc gọi</h3>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text-sub)', cursor: 'pointer' }}>
            <X size={18} />
          </button>
        </div>

        <p style={{ fontSize: '13px', color: 'var(--text-sub)', marginBottom: '16px' }}>
          Khách hàng: <strong style={{ color: 'var(--text-main)' }}>{activeCase.full_name}</strong> • HĐ: {activeCase.loan_id}
        </p>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {/* Outcome Select */}
          <div>
            <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-sub)', display: 'block', marginBottom: '4px' }}>
              Kết quả tương tác:
            </label>
            <select
              value={outcome}
              onChange={(e) => setOutcome(e.target.value)}
              style={{
                width: '100%',
                padding: '10px',
                backgroundColor: 'var(--bg-main)',
                border: '1px solid var(--border)',
                borderRadius: '8px',
                color: 'var(--text-main)',
                fontSize: '13px'
              }}
            >
              <option value="PTP_AGREED">✅ Hẹn ngày thanh toán (PTP Agreed)</option>
              <option value="REFUSED">❌ Khách hàng từ chối / Bất hợp tác</option>
              <option value="BUSY_NO_ANSWER">📵 Không nghe máy / Máy bận</option>
            </select>
          </div>

          {/* PTP Inputs if Agreed */}
          {outcome === 'PTP_AGREED' && (
            <>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-sub)', display: 'block', marginBottom: '4px' }}>
                  Số tiền cam kết trả (VNĐ):
                </label>
                <input
                  type="number"
                  value={ptpAmount}
                  onChange={(e) => setPtpAmount(Number(e.target.value))}
                  style={{
                    width: '100%',
                    padding: '10px',
                    backgroundColor: 'var(--bg-main)',
                    border: '1px solid var(--border)',
                    borderRadius: '8px',
                    color: 'var(--accent)',
                    fontWeight: 700,
                    fontSize: '14px'
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-sub)', display: 'block', marginBottom: '4px' }}>
                  Ngày hẹn thanh toán (PTP Date):
                </label>
                <input
                  type="date"
                  value={ptpDate}
                  onChange={(e) => setPtpDate(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '10px',
                    backgroundColor: 'var(--bg-main)',
                    border: '1px solid var(--border)',
                    borderRadius: '8px',
                    color: 'var(--text-main)',
                    fontSize: '13px'
                  }}
                />
              </div>
            </>
          )}

          {/* Notes */}
          <div>
            <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-sub)', display: 'block', marginBottom: '4px' }}>
              Ghi chú tóm tắt (Tối đa 200 ký tự):
            </label>
            <input
              type="text"
              placeholder="Ví dụ: Khách hẹn chuyển khoản qua VietQR ngày 10..."
              value={notes}
              maxLength={200}
              onChange={(e) => setNotes(e.target.value)}
              style={{
                width: '100%',
                padding: '10px',
                backgroundColor: 'var(--bg-main)',
                border: '1px solid var(--border)',
                borderRadius: '8px',
                color: 'var(--text-main)',
                fontSize: '13px'
              }}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '12px' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Hủy
            </button>
            <button type="submit" className="btn btn-primary">
              <CheckCircle2 size={16} />
              <span>Lưu & Commit Guardrail</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
