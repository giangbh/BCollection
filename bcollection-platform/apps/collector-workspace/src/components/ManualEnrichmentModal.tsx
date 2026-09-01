import React, { useState } from 'react';
import { X, PlusCircle, Sparkles } from 'lucide-react';

interface ManualEnrichmentModalProps {
  isOpen: boolean;
  activeCase: any;
  onClose: () => void;
  onSubmitFact: (factType: string, payload: any) => void;
}

export const ManualEnrichmentModal: React.FC<ManualEnrichmentModalProps> = ({
  isOpen,
  activeCase,
  onClose,
  onSubmitFact,
}) => {
  const [factType, setFactType] = useState('CONTACT_WINDOW');
  const [windowVal, setWindowVal] = useState('18:00-21:00');
  const [salaryDay, setSalaryDay] = useState(10);
  const [altPhone, setAltPhone] = useState('');
  const [rootCause, setRootCause] = useState('CASHFLOW_TIMING');

  if (!isOpen || !activeCase) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    let payload = {};
    if (factType === 'CONTACT_WINDOW') payload = { window: windowVal };
    else if (factType === 'SALARY_CYCLE') payload = { day_of_month: salaryDay };
    else if (factType === 'ALT_PHONE') payload = { phone: altPhone };
    else if (factType === 'ROOT_CAUSE') payload = { primary: rootCause };

    onSubmitFact(factType, payload);
    onClose();
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
        width: '460px',
        padding: '24px'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: 700 }}>Làm giàu Thông tin (Event Sourcing)</h3>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text-sub)', cursor: 'pointer' }}>
            <X size={18} />
          </button>
        </div>

        <p style={{ fontSize: '12px', color: 'var(--text-sub)', marginBottom: '14px' }}>
          Mọi dữ liệu bổ sung sẽ được lưu vết có nguồn gốc (*Provenance*) và có thời hạn (*TTL Decay*).
        </p>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {/* Fact Type Selector */}
          <div>
            <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-sub)', display: 'block', marginBottom: '4px' }}>
              Loại thông tin bổ sung (Fact Type):
            </label>
            <select
              value={factType}
              onChange={(e) => setFactType(e.target.value)}
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
              <option value="CONTACT_WINDOW">🕒 Khung giờ khách dễ nghe máy</option>
              <option value="SALARY_CYCLE">💰 Ngày nhận lương hàng tháng</option>
              <option value="ALT_PHONE">📱 Số điện thoại phụ (Đã xác minh)</option>
              <option value="ROOT_CAUSE">🔍 Nguyên nhân chậm trả thực tế</option>
            </select>
          </div>

          {/* Dynamic Payload Form */}
          {factType === 'CONTACT_WINDOW' && (
            <div>
              <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-sub)', display: 'block', marginBottom: '4px' }}>
                Khung giờ tối ưu (07:00 - 21:00):
              </label>
              <select
                value={windowVal}
                onChange={(e) => setWindowVal(e.target.value)}
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
                <option value="08:30-11:30">Buổi sáng (08:30 - 11:30)</option>
                <option value="14:00-17:00">Buổi chiều (14:00 - 17:00)</option>
                <option value="18:00-21:00">Buổi tối sau giờ làm (18:00 - 21:00)</option>
              </select>
            </div>
          )}

          {factType === 'SALARY_CYCLE' && (
            <div>
              <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-sub)', display: 'block', marginBottom: '4px' }}>
                Ngày nhận lương trong tháng (1 - 31):
              </label>
              <input
                type="number"
                min={1}
                max={31}
                value={salaryDay}
                onChange={(e) => setSalaryDay(Number(e.target.value))}
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
          )}

          {factType === 'ALT_PHONE' && (
            <div>
              <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-sub)', display: 'block', marginBottom: '4px' }}>
                Số điện thoại phụ (Chuẩn +84):
              </label>
              <input
                type="text"
                placeholder="+84912345678"
                value={altPhone}
                onChange={(e) => setAltPhone(e.target.value)}
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
          )}

          {factType === 'ROOT_CAUSE' && (
            <div>
              <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-sub)', display: 'block', marginBottom: '4px' }}>
                Phân loại nguyên nhân:
              </label>
              <select
                value={rootCause}
                onChange={(e) => setRootCause(e.target.value)}
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
                <option value="CASHFLOW_TIMING">Lệch chu kỳ dòng tiền / Chờ lương</option>
                <option value="INCOME_LOSS">Mất việc / Giảm thu nhập</option>
                <option value="FORGOT_OR_ADMIN">Quên hạn / Lỗi chuyển khoản</option>
                <option value="BUSINESS_DOWNTURN">Kinh doanh chậm / Hàng tồn</option>
              </select>
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '12px' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Hủy
            </button>
            <button type="submit" className="btn btn-primary">
              <PlusCircle size={16} />
              <span>Ghi nhận Fact</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
