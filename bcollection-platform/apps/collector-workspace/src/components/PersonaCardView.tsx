import React, { useState } from 'react';
import { 
  ShieldAlert, Sparkles, UserCheck, PhoneCall, PlusCircle, 
  Clock, History, MessageSquare, ShieldCheck, CheckCircle2, 
  XCircle, PhoneMissed, ArrowRight, User
} from 'lucide-react';

interface PersonaCardViewProps {
  persona: any;
  history?: any[];
  onOpenEnrichment: () => void;
}

export const PersonaCardView: React.FC<PersonaCardViewProps> = ({
  persona,
  history = [],
  onOpenEnrichment,
}) => {
  const [activeTab, setActiveTab] = useState<'PERSONA' | 'HISTORY'>('PERSONA');
  const [historyFilter, setHistoryFilter] = useState<'ALL' | 'VOICE' | 'SMS'>('ALL');

  if (!persona) {
    return (
      <div style={{
        backgroundColor: 'var(--bg-card)',
        borderRadius: '12px',
        border: '1px solid var(--border)',
        padding: '32px',
        textAlign: 'center',
        color: 'var(--text-sub)',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        <UserCheck size={48} style={{ opacity: 0.3, marginBottom: '16px' }} />
        <h3 style={{ fontSize: '16px', fontWeight: 600 }}>Chưa chọn Hồ sơ</h3>
        <p style={{ fontSize: '13px', marginTop: '4px' }}>Chọn một khách hàng từ danh sách bên trái để xem Chân dung 360 và Lịch sử tương tác.</p>
      </div>
    );
  }

  const getScoreColor = (val: number) => {
    if (val >= 70) return 'var(--success)';
    if (val >= 50) return 'var(--warning)';
    return 'var(--danger)';
  };

  const formatVND = (amount: number) => {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amount);
  };

  const filteredHistory = history.filter((item) => {
    if (historyFilter === 'ALL') return true;
    return item.channel === historyFilter;
  });

  return (
    <div style={{
      backgroundColor: 'var(--bg-card)',
      borderRadius: '12px',
      border: '1px solid var(--border)',
      padding: '20px',
      height: '100%',
      overflowY: 'auto',
      display: 'flex',
      flexDirection: 'column',
      gap: '16px'
    }}>
      {/* Header Info */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h2 style={{ fontSize: '18px', fontWeight: 700, margin: 0 }}>{persona.full_name}</h2>
            <span className="badge" style={{ backgroundColor: 'rgba(0,90,84,0.4)', color: '#34d399' }}>
              [{persona.segment_cell}] {persona.segment_name}
            </span>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-sub)', marginTop: '4px', marginBottom: 0 }}>
            CIF: {persona.debtor_cif} • HĐ: {persona.loan_id} • DPD: {persona.dpd} ngày • Dư nợ: <strong style={{ color: 'var(--accent)' }}>{formatVND(persona.overdue_amount)}</strong>
          </p>
        </div>

        <button
          className="btn btn-secondary"
          onClick={onOpenEnrichment}
          style={{ fontSize: '12px', padding: '6px 12px' }}
        >
          <PlusCircle size={14} />
          <span>Làm giàu thông tin</span>
        </button>
      </div>

      {/* Tabs Navigation: Persona vs Case History */}
      <div style={{
        display: 'flex',
        borderBottom: '1px solid var(--border)',
        gap: '8px'
      }}>
        <button
          onClick={() => setActiveTab('PERSONA')}
          style={{
            padding: '8px 16px',
            background: 'none',
            border: 'none',
            borderBottom: activeTab === 'PERSONA' ? '2px solid var(--accent)' : '2px solid transparent',
            color: activeTab === 'PERSONA' ? 'var(--text-main)' : 'var(--text-sub)',
            fontWeight: activeTab === 'PERSONA' ? 700 : 500,
            fontSize: '13px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}
        >
          <User size={15} />
          <span>Chân dung Debtor 360</span>
        </button>

        <button
          onClick={() => setActiveTab('HISTORY')}
          style={{
            padding: '8px 16px',
            background: 'none',
            border: 'none',
            borderBottom: activeTab === 'HISTORY' ? '2px solid var(--accent)' : '2px solid transparent',
            color: activeTab === 'HISTORY' ? 'var(--text-main)' : 'var(--text-sub)',
            fontWeight: activeTab === 'HISTORY' ? 700 : 500,
            fontSize: '13px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}
        >
          <History size={15} />
          <span>Lịch sử Tương tác (Case History)</span>
          <span style={{
            fontSize: '11px',
            padding: '1px 7px',
            borderRadius: '10px',
            backgroundColor: history.length > 0 ? 'rgba(52, 211, 153, 0.2)' : 'var(--bg-main)',
            color: history.length > 0 ? '#34d399' : 'var(--text-sub)',
            fontWeight: 700
          }}>
            {history.length}
          </span>
        </button>
      </div>

      {/* TAB 1: CHÂN DUNG PERSONA 360 */}
      {activeTab === 'PERSONA' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* 3 Core Scores */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: '12px',
            backgroundColor: 'var(--bg-main)',
            padding: '14px',
            borderRadius: '10px',
            border: '1px solid var(--border)'
          }}>
            {/* Ability Score */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                <span style={{ color: 'var(--text-sub)' }}>Khả năng trả (D1)</span>
                <span style={{ fontWeight: 700, color: getScoreColor(persona.scores.ability.value) }}>
                  {persona.scores.ability.value}/100
                </span>
              </div>
              <div className="score-bar">
                <div
                  className="score-fill"
                  style={{
                    width: `${persona.scores.ability.value}%`,
                    backgroundColor: getScoreColor(persona.scores.ability.value)
                  }}
                />
              </div>
              <div style={{ fontSize: '10px', color: 'var(--text-sub)', marginTop: '4px' }}>
                {persona.scores.ability.top_drivers?.[0] || 'Dòng tiền ổn định'}
              </div>
            </div>

            {/* Willingness Score */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                <span style={{ color: 'var(--text-sub)' }}>Thiện chí (D2)</span>
                <span style={{ fontWeight: 700, color: getScoreColor(persona.scores.willingness.value) }}>
                  {persona.scores.willingness.value}/100
                </span>
              </div>
              <div className="score-bar">
                <div
                  className="score-fill"
                  style={{
                    width: `${persona.scores.willingness.value}%`,
                    backgroundColor: getScoreColor(persona.scores.willingness.value)
                  }}
                />
              </div>
              <div style={{ fontSize: '10px', color: 'var(--text-sub)', marginTop: '4px' }}>
                {persona.scores.willingness.top_drivers?.[0] || 'Hợp tác khi liên hệ'}
              </div>
            </div>

            {/* Contactability Score */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                <span style={{ color: 'var(--text-sub)' }}>Khả năng liên hệ (D3)</span>
                <span style={{ fontWeight: 700, color: getScoreColor(persona.scores.contactability.value) }}>
                  {persona.scores.contactability.value}/100
                </span>
              </div>
              <div className="score-bar">
                <div
                  className="score-fill"
                  style={{
                    width: `${persona.scores.contactability.value}%`,
                    backgroundColor: getScoreColor(persona.scores.contactability.value)
                  }}
                />
              </div>
              <div style={{ fontSize: '10px', color: 'var(--text-sub)', marginTop: '4px' }}>
                {persona.scores.contactability.top_drivers?.[1] || 'Đăng nhập app đều'}
              </div>
            </div>
          </div>

          {/* Mandatory Guardrail Warnings (Luôn ở trên hành động) */}
          <div style={{
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: '10px',
            padding: '12px 16px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--danger)', fontWeight: 600, fontSize: '13px', marginBottom: '6px' }}>
              <ShieldAlert size={16} />
              <span>LƯU Ý BẮT BUỘC TỪ L6 GUARDRAIL</span>
            </div>
            <ul style={{ paddingLeft: '20px', fontSize: '12px', color: '#fca5a5', margin: 0 }}>
              {persona.mandatory_guardrail_notes.map((note: string, idx: number) => (
                <li key={idx} style={{ marginBottom: '2px' }}>{note}</li>
              ))}
            </ul>
          </div>

          {/* Root Cause Analysis */}
          <div style={{
            backgroundColor: 'var(--bg-main)',
            borderRadius: '10px',
            border: '1px solid var(--border)',
            padding: '14px'
          }}>
            <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '4px' }}>
              Nguyên nhân chậm trả chính (Root Cause)
            </div>
            <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-main)' }}>
              {persona.root_cause.primary}: {persona.root_cause.description}
            </div>
          </div>

          {/* AI Next Best Action Recommendation */}
          <div style={{
            backgroundColor: 'rgba(0, 90, 84, 0.2)',
            border: '1px solid rgba(0, 90, 84, 0.5)',
            borderRadius: '10px',
            padding: '16px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#34d399', fontWeight: 700, fontSize: '13px', marginBottom: '8px' }}>
              <Sparkles size={16} />
              <span>KHUYẾN NGHỊ HÀNH ĐỘNG (NEXT BEST ACTION)</span>
              <span style={{ fontSize: '11px', color: 'var(--text-sub)', fontWeight: 400 }}>
                • Tỷ lệ thành công: {persona.recommended_playbook.success_rate_estimate}
              </span>
            </div>

            <p style={{ fontSize: '13px', lineHeight: 1.6, marginBottom: '10px', color: 'var(--text-main)' }}>
              {persona.recommended_playbook.suggested_action}
            </p>

            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              {persona.recommended_playbook.top_levers.map((lev: string, idx: number) => (
                <span key={idx} className="badge" style={{ backgroundColor: 'rgba(212, 160, 23, 0.2)', color: '#fbbf24', fontSize: '11px' }}>
                  Đòn bẩy: {lev}
                </span>
              ))}
            </div>
          </div>

          {/* Mini preview for history */}
          {history.length > 0 && (
            <div 
              onClick={() => setActiveTab('HISTORY')}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px 14px',
                backgroundColor: 'rgba(15, 23, 42, 0.6)',
                borderRadius: '8px',
                border: '1px solid var(--border)',
                cursor: 'pointer',
                fontSize: '12px'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-sub)' }}>
                <Clock size={14} />
                <span>Tương tác gần nhất: <strong style={{ color: 'var(--text-main)' }}>{history[0].outcome_label || history[0].outcome}</strong> ({history[0].timestamp})</span>
              </div>
              <span style={{ color: '#34d399', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '2px' }}>
                Xem toàn bộ lịch sử <ArrowRight size={13} />
              </span>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: LỊCH SỬ TƯƠNG TÁC (CASE HISTORY TIMELINE) */}
      {activeTab === 'HISTORY' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {/* History Filters */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-main)' }}>
              DÒNG THỜI GIAN TƯƠNG TÁC ({filteredHistory.length})
            </div>

            <div style={{ display: 'flex', gap: '6px' }}>
              {(['ALL', 'VOICE', 'SMS'] as const).map((filter) => (
                <button
                  key={filter}
                  onClick={() => setHistoryFilter(filter)}
                  style={{
                    padding: '4px 10px',
                    borderRadius: '6px',
                    border: '1px solid var(--border)',
                    backgroundColor: historyFilter === filter ? 'var(--accent)' : 'var(--bg-main)',
                    color: historyFilter === filter ? '#fff' : 'var(--text-sub)',
                    fontSize: '11px',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                >
                  {filter === 'ALL' ? 'Tất cả' : filter === 'VOICE' ? 'Cuộc gọi' : 'Tin nhắn'}
                </button>
              ))}
            </div>
          </div>

          {/* Timeline List */}
          {filteredHistory.length === 0 ? (
            <div style={{
              padding: '32px 16px',
              textAlign: 'center',
              color: 'var(--text-sub)',
              fontSize: '13px',
              backgroundColor: 'var(--bg-main)',
              borderRadius: '8px',
              border: '1px dashed var(--border)'
            }}>
              Chưa có lịch sử tương tác nào được ghi nhận cho hồ sơ này.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {filteredHistory.map((item: any, idx: number) => {
                const isPtp = item.outcome === 'PTP_AGREED';
                const isRefused = item.outcome === 'REFUSED';
                const isBusy = item.outcome === 'BUSY_NO_ANSWER';

                return (
                  <div
                    key={item.id || idx}
                    style={{
                      backgroundColor: 'var(--bg-main)',
                      borderRadius: '10px',
                      border: '1px solid var(--border)',
                      padding: '14px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '8px',
                      position: 'relative'
                    }}
                  >
                    {/* Top Row: Channel Icon + Title + Timestamp */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div style={{
                          padding: '6px',
                          borderRadius: '8px',
                          backgroundColor: item.channel === 'VOICE' ? 'rgba(59, 130, 246, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                          color: item.channel === 'VOICE' ? '#60a5fa' : '#34d399',
                          display: 'flex',
                          alignItems: 'center'
                        }}>
                          {item.channel === 'VOICE' ? <PhoneCall size={14} /> : <MessageSquare size={14} />}
                        </div>
                        <div>
                          <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-main)' }}>
                            {item.channel === 'VOICE' ? 'Cuộc gọi đàm phán nợ' : 'SMS Brandname BIDV'}
                          </span>
                          <span style={{ fontSize: '11px', color: 'var(--text-sub)', marginLeft: '8px' }}>
                            • {item.collector_name}
                          </span>
                        </div>
                      </div>

                      <span style={{ fontSize: '11px', color: 'var(--text-sub)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <Clock size={12} />
                        {item.timestamp}
                      </span>
                    </div>

                    {/* Outcome Badge & Details */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                      <span style={{
                        fontSize: '11px',
                        padding: '3px 8px',
                        borderRadius: '6px',
                        fontWeight: 700,
                        backgroundColor: isPtp ? 'rgba(16, 185, 129, 0.2)' : isRefused ? 'rgba(239, 68, 68, 0.2)' : 'rgba(148, 163, 184, 0.15)',
                        color: isPtp ? '#34d399' : isRefused ? '#f87171' : 'var(--text-sub)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px'
                      }}>
                        {isPtp && <CheckCircle2 size={12} />}
                        {isRefused && <XCircle size={12} />}
                        {isBusy && <PhoneMissed size={12} />}
                        {item.outcome_label || item.outcome}
                      </span>

                      {item.ptp_amount && (
                        <span style={{ fontSize: '11px', color: 'var(--accent)', fontWeight: 700 }}>
                          Cam kết: {formatVND(item.ptp_amount)}
                        </span>
                      )}

                      {item.ptp_date && (
                        <span style={{ fontSize: '11px', color: 'var(--text-main)', fontWeight: 600 }}>
                          • Ngày hẹn: {item.ptp_date}
                        </span>
                      )}

                      {item.sentiment && (
                        <span style={{
                          fontSize: '10px',
                          padding: '2px 6px',
                          borderRadius: '4px',
                          backgroundColor: item.sentiment === 'TÍCH CỰC' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                          color: item.sentiment === 'TÍCH CỰC' ? '#34d399' : '#f87171',
                          fontWeight: 600
                        }}>
                          {item.sentiment}
                        </span>
                      )}
                    </div>

                    {/* Notes Content */}
                    <p style={{
                      fontSize: '12px',
                      lineHeight: 1.5,
                      color: 'var(--text-main)',
                      margin: 0,
                      backgroundColor: 'rgba(15, 23, 42, 0.4)',
                      padding: '8px 10px',
                      borderRadius: '6px',
                      border: '1px solid rgba(255, 255, 255, 0.05)'
                    }}>
                      {item.notes}
                    </p>

                    {/* Guardrail Audit Token Footnote */}
                    {item.guardrail_token && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10px', color: 'var(--text-sub)' }}>
                        <ShieldCheck size={11} color="#34d399" />
                        <span>Guardrail Audit Token: <code>{item.guardrail_token}</code></span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
