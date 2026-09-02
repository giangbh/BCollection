import React, { useState, useEffect } from 'react';
import { 
  X, CheckCircle2, Calendar, DollarSign, Sparkles, 
  ShieldCheck, Volume2, Bot, ArrowRight, RefreshCw, Edit3
} from 'lucide-react';

interface CallWrapupModalProps {
  isOpen: boolean;
  activeCase: any;
  callDuration?: number;
  onClose: () => void;
  onSubmit: (outcome: string, ptpAmount?: number, ptpDate?: string, notes?: string) => void;
}

export const CallWrapupModal: React.FC<CallWrapupModalProps> = ({
  isOpen,
  activeCase,
  callDuration = 45,
  onClose,
  onSubmit,
}) => {
  const [isTranscribing, setIsTranscribing] = useState(true);
  const [transcribeData, setTranscribeData] = useState<any>(null);

  const [outcome, setOutcome] = useState('PTP_AGREED');
  const [ptpAmount, setPtpAmount] = useState(activeCase?.overdue_amount || 0);
  const [ptpDate, setPtpDate] = useState(
    new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
  );
  const [notes, setNotes] = useState('');
  const [isManualEdit, setIsManualEdit] = useState(false);

  // Kích hoạt bóc tách cuộc gọi ngay khi mở Modal
  useEffect(() => {
    if (!isOpen || !activeCase) return;

    setIsTranscribing(true);
    setIsManualEdit(false);

    const startTime = Date.now();
    fetch(`/api/cases/${activeCase.case_id}/call-transcribe`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ call_duration_seconds: callDuration, channel: 'VOICE' })
    })
      .then((res) => res.json())
      .then((data) => {
        const elapsed = Date.now() - startTime;
        const delay = Math.max(0, 1200 - elapsed); // Hiển thị hiệu ứng phân tích tối thiểu 1.2s

        setTimeout(() => {
          setTranscribeData(data);
          setOutcome(data.extracted_outcome || 'PTP_AGREED');
          if (data.extracted_ptp_amount) {
            setPtpAmount(data.extracted_ptp_amount);
          } else {
            setPtpAmount(activeCase.overdue_amount || 0);
          }
          if (data.extracted_ptp_date) {
            setPtpDate(data.extracted_ptp_date);
          }
          setNotes(data.auto_notes || '');
          setIsTranscribing(false);
        }, delay);
      })
      .catch((err) => {
        console.error('Lỗi phân tích cuộc gọi:', err);
        setIsTranscribing(false);
      });
  }, [isOpen, activeCase]);

  if (!isOpen || !activeCase) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(
      outcome, 
      outcome === 'PTP_AGREED' ? Number(ptpAmount) : undefined, 
      outcome === 'PTP_AGREED' ? ptpDate : undefined, 
      notes
    );
  };

  const formatVND = (amount: number) => {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amount);
  };

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      backgroundColor: 'rgba(2, 6, 23, 0.85)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      backdropFilter: 'blur(8px)'
    }}>
      <div style={{
        backgroundColor: 'var(--bg-card)',
        borderRadius: '16px',
        border: '1px solid var(--border)',
        width: '640px',
        maxHeight: '90vh',
        overflowY: 'auto',
        padding: '24px',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7)',
        position: 'relative'
      }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{
              padding: '6px',
              borderRadius: '8px',
              backgroundColor: 'rgba(52, 211, 153, 0.15)',
              color: '#34d399',
              display: 'flex',
              alignItems: 'center'
            }}>
              <Sparkles size={18} />
            </div>
            <div>
              <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-main)', margin: 0 }}>
                Ghi nhận Cuộc gọi & Bóc tách AI
              </h3>
              <p style={{ fontSize: '11px', color: 'var(--text-sub)', margin: 0 }}>
                Khách hàng: <strong>{activeCase.full_name}</strong> • HĐ: {activeCase.loan_id}
              </p>
            </div>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text-sub)', cursor: 'pointer' }}>
            <X size={18} />
          </button>
        </div>

        {/* TRẠNG THÁI ĐANG BÓC TÁCH GIỌNG NÓI */}
        {isTranscribing ? (
          <div style={{
            padding: '36px 20px',
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '16px',
            backgroundColor: 'rgba(15, 23, 42, 0.6)',
            borderRadius: '12px',
            border: '1px dashed var(--border)'
          }}>
            {/* Audio waveform simulation */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px', height: '40px' }}>
              {[18, 32, 24, 40, 20, 36, 28, 16, 38, 22, 34, 18].map((h, i) => (
                <div
                  key={i}
                  style={{
                    width: '4px',
                    height: `${h}px`,
                    backgroundColor: '#34d399',
                    borderRadius: '2px',
                    animation: `pulse 1s infinite alternate ${i * 0.08}s`
                  }}
                />
              ))}
            </div>

            <div>
              <p style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)', marginBottom: '4px' }}>
                Đang bóc tách hội thoại cuộc gọi qua Speech AI...
              </p>
              <p style={{ fontSize: '12px', color: 'var(--text-sub)', margin: 0 }}>
                Nhận diện Whisper ASR • Trích xuất cam kết PTP • Kiểm tra tuân thủ L6 Guardrail
              </p>
            </div>
          </div>
        ) : (
          /* TRẠNG THÁI ĐÃ BÓC TÁCH HOÀN TẤT & AUTO-FILL */
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            
            {/* BẰNG CHỨNG HỘI THOẠI AI BÓC TÁCH */}
            <div style={{
              backgroundColor: 'rgba(15, 23, 42, 0.7)',
              borderRadius: '12px',
              border: '1px solid rgba(52, 211, 153, 0.2)',
              padding: '14px',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '11px', fontWeight: 700, color: '#34d399', letterSpacing: '0.5px', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <Volume2 size={13} /> Trích dẫn hội thoại vừa ghi nhận (Dual-Channel)
                </span>
                <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '10px', backgroundColor: 'rgba(52, 211, 153, 0.15)', color: '#34d399', fontWeight: 600 }}>
                  Độ tin cậy: {Math.round((transcribeData?.confidence || 0.95) * 100)}%
                </span>
              </div>

              {/* Dialogue Transcript */}
              <div style={{ fontSize: '12px', display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '130px', overflowY: 'auto' }}>
                {transcribeData?.transcript?.map((item: any, idx: number) => (
                  <div key={idx} style={{ display: 'flex', gap: '8px', lineHeight: 1.4 }}>
                    <span style={{
                      fontWeight: 700,
                      color: item.speaker === 'RM' ? '#60a5fa' : '#f59e0b',
                      minWidth: '55px',
                      fontSize: '11px'
                    }}>
                      {item.speaker === 'RM' ? 'Chuyên viên:' : 'Khách hàng:'}
                    </span>
                    <span style={{ color: 'var(--text-main)' }}>
                      {item.text}
                    </span>
                  </div>
                ))}
              </div>

              {/* Badges: Sentiment & Compliance */}
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', paddingTop: '6px', borderTop: '1px solid var(--border)' }}>
                <span style={{
                  fontSize: '11px',
                  padding: '3px 8px',
                  borderRadius: '6px',
                  backgroundColor: transcribeData?.sentiment?.score >= 0 ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                  color: transcribeData?.sentiment?.score >= 0 ? '#34d399' : '#f87171',
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px'
                }}>
                  🎭 Cảm xúc: {transcribeData?.sentiment?.label} ({transcribeData?.sentiment?.tone})
                </span>

                <span style={{
                  fontSize: '11px',
                  padding: '3px 8px',
                  borderRadius: '6px',
                  backgroundColor: 'rgba(59, 130, 246, 0.15)',
                  color: '#60a5fa',
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px'
                }}>
                  <ShieldCheck size={12} /> Tuân thủ L6: {transcribeData?.compliance_audit?.status} (Chuẩn mực)
                </span>
              </div>
            </div>

            {/* FORM INPUTS - TỰ ĐỘNG ĐIỀN */}
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
              backgroundColor: 'var(--bg-main)',
              padding: '16px',
              borderRadius: '12px',
              border: '1px solid var(--border)'
            }}>
              {/* Outcome Select */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-sub)' }}>
                    Kết quả cuộc gọi:
                  </label>
                  <span style={{ fontSize: '11px', color: '#34d399', display: 'flex', alignItems: 'center', gap: '3px' }}>
                    <Sparkles size={11} /> AI tự động phát hiện
                  </span>
                </div>
                <select
                  value={outcome}
                  onChange={(e) => { setOutcome(e.target.value); setIsManualEdit(true); }}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    backgroundColor: 'var(--bg-card)',
                    border: '1px solid var(--border)',
                    borderRadius: '8px',
                    color: 'var(--text-main)',
                    fontSize: '13px',
                    outline: 'none'
                  }}
                >
                  <option value="PTP_AGREED">✅ Hẹn ngày thanh toán (PTP Agreed)</option>
                  <option value="REFUSED">❌ Khách hàng từ chối / Bất hợp tác</option>
                  <option value="BUSY_NO_ANSWER">📵 Không nghe máy / Máy bận</option>
                </select>
              </div>

              {/* PTP Fields */}
              {outcome === 'PTP_AGREED' && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                      <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-sub)' }}>
                        Số tiền cam kết trả (VNĐ):
                      </label>
                      <span style={{ fontSize: '10px', color: '#34d399' }}>✨ Trích xuất</span>
                    </div>
                    <input
                      type="number"
                      value={ptpAmount}
                      onChange={(e) => { setPtpAmount(Number(e.target.value)); setIsManualEdit(true); }}
                      style={{
                        width: '100%',
                        padding: '8px 12px',
                        backgroundColor: 'var(--bg-card)',
                        border: '1px solid rgba(52, 211, 153, 0.4)',
                        borderRadius: '8px',
                        color: 'var(--accent)',
                        fontWeight: 700,
                        fontSize: '13px',
                        outline: 'none'
                      }}
                    />
                  </div>

                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                      <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-sub)' }}>
                        Ngày hẹn thanh toán (PTP):
                      </label>
                      <span style={{ fontSize: '10px', color: '#34d399' }}>✨ Trích xuất</span>
                    </div>
                    <input
                      type="date"
                      value={ptpDate}
                      onChange={(e) => { setPtpDate(e.target.value); setIsManualEdit(true); }}
                      style={{
                        width: '100%',
                        padding: '8px 12px',
                        backgroundColor: 'var(--bg-card)',
                        border: '1px solid rgba(52, 211, 153, 0.4)',
                        borderRadius: '8px',
                        color: 'var(--text-main)',
                        fontSize: '13px',
                        outline: 'none'
                      }}
                    />
                  </div>
                </div>
              )}

              {/* Auto Notes */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-sub)' }}>
                    Tóm tắt nội dung cuộc gọi:
                  </label>
                  <span style={{ fontSize: '10px', color: '#34d399' }}>✨ Tóm tắt tự động</span>
                </div>
                <textarea
                  rows={2}
                  value={notes}
                  onChange={(e) => { setNotes(e.target.value); setIsManualEdit(true); }}
                  placeholder="Ghi chú cuộc gọi..."
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    backgroundColor: 'var(--bg-card)',
                    border: '1px solid var(--border)',
                    borderRadius: '8px',
                    color: 'var(--text-main)',
                    fontSize: '12px',
                    outline: 'none',
                    resize: 'none',
                    lineHeight: 1.4
                  }}
                />
              </div>
            </div>

            {/* ACTION BUTTONS: 1-CLICK CONFIRMATION */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '4px' }}>
              <button
                type="button"
                onClick={() => setIsManualEdit(!isManualEdit)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: isManualEdit ? 'var(--accent)' : 'var(--text-sub)',
                  fontSize: '12px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px'
                }}
              >
                <Edit3 size={13} />
                <span>{isManualEdit ? 'Đang chỉnh sửa thủ công' : 'Chỉnh sửa nếu cần'}</span>
              </button>

              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  type="button"
                  onClick={onClose}
                  className="btn btn-secondary"
                  style={{ padding: '8px 16px', fontSize: '13px' }}
                >
                  Bỏ qua
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  style={{
                    padding: '8px 20px',
                    fontSize: '13px',
                    fontWeight: 700,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    backgroundColor: '#059669',
                    border: 'none'
                  }}
                >
                  <CheckCircle2 size={16} />
                  <span>XÁC NHẬN & LƯU HỒ SƠ (1-CLICK)</span>
                </button>
              </div>
            </div>

          </form>
        )}
      </div>
    </div>
  );
};
