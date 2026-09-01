import React from 'react';
import { ShieldAlert, Sparkles, UserCheck, PhoneCall, PlusCircle, AlertTriangle, FileText } from 'lucide-react';

interface PersonaCardViewProps {
  persona: any;
  onOpenEnrichment: () => void;
}

export const PersonaCardView: React.FC<PersonaCardViewProps> = ({
  persona,
  onOpenEnrichment,
}) => {
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
        <p style={{ fontSize: '13px', marginTop: '4px' }}>Chọn một khách hàng từ danh sách bên trái để xem Chân dung 360 trong 15 giây.</p>
      </div>
    );
  }

  const getScoreColor = (val: number) => {
    if (val >= 70) return 'var(--success)';
    if (val >= 50) return 'var(--warning)';
    return 'var(--danger)';
  };

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
            <h2 style={{ fontSize: '18px', fontWeight: 700 }}>{persona.full_name}</h2>
            <span className="badge" style={{ backgroundColor: 'rgba(0,90,84,0.4)', color: '#34d399' }}>
              [{persona.segment_cell}] {persona.segment_cell === 'S3' ? 'Khó khăn tạm thời' : 'Quên lịch / Tự khỏi'}
            </span>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-sub)', marginTop: '2px' }}>
            CIF: {persona.debtor_cif} • HĐ: {persona.loan_id} • DPD: {persona.dpd} ngày
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
        <ul style={{ paddingLeft: '20px', fontSize: '12px', color: '#fca5a5' }}>
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
        <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '4px' }}>
          Nguyên nhân chậm trả chính (Root Cause)
        </div>
        <div style={{ fontSize: '13px', fontWeight: 600 }}>
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
            {persona.recommended_playbook.success_rate_estimate}
          </span>
        </div>

        <p style={{ fontSize: '13px', lineHeight: 1.6, marginBottom: '10px' }}>
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
    </div>
  );
};
