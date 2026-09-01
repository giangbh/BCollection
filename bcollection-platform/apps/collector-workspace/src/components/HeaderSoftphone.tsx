import React, { useState, useEffect } from 'react';
import { Phone, PhoneCall, PhoneOff, Mic, MicOff, ShieldCheck, Clock } from 'lucide-react';

interface HeaderSoftphoneProps {
  activeCase: any;
  callState: 'IDLE' | 'CALLING' | 'CONNECTED' | 'ENDED';
  callDuration: number;
  onStartCall: () => void;
  onEndCall: () => void;
}

export const HeaderSoftphone: React.FC<HeaderSoftphoneProps> = ({
  activeCase,
  callState,
  callDuration,
  onStartCall,
  onEndCall,
}) => {
  const [isMuted, setIsMuted] = useState(false);

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <header style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '12px 24px',
      backgroundColor: 'var(--bg-card)',
      borderBottom: '1px solid var(--border)',
      position: 'sticky',
      top: 0,
      zIndex: 100
    }}>
      {/* Brand Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{
          width: '36px',
          height: '36px',
          borderRadius: '8px',
          background: 'linear-gradient(135deg, #005a54, #d4a017)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: 800,
          color: '#fff',
          fontSize: '18px'
        }}>
          B
        </div>
        <div>
          <h1 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-main)' }}>
            B.Collection <span style={{ color: 'var(--accent)', fontSize: '12px' }}>MVP</span>
          </h1>
          <p style={{ fontSize: '11px', color: 'var(--text-sub)' }}>Hệ thống Thu hồi nợ Bán lẻ (Bucket B1)</p>
        </div>
      </div>

      {/* Softphone Bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '16px',
        backgroundColor: 'var(--bg-main)',
        padding: '6px 16px',
        borderRadius: '12px',
        border: '1px solid var(--border)'
      }}>
        {/* Case Info */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{
            width: '10px',
            height: '10px',
            borderRadius: '50%',
            backgroundColor: callState === 'CONNECTED' ? 'var(--success)' : callState === 'CALLING' ? 'var(--warning)' : 'var(--text-sub)'
          }} />
          <span style={{ fontSize: '13px', fontWeight: 500 }}>
            {activeCase ? `${activeCase.full_name} (${activeCase.phone_e164})` : 'Chưa chọn hồ sơ'}
          </span>
        </div>

        {/* Call Timer */}
        {callState !== 'IDLE' && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--accent)', fontSize: '13px', fontWeight: 600 }}>
            <Clock size={14} />
            <span>{formatDuration(callDuration)}</span>
          </div>
        )}

        {/* Guardrail Status Badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px', color: 'var(--success)' }}>
          <ShieldCheck size={14} />
          <span>Guardrail L6 Active</span>
        </div>

        {/* Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {callState === 'IDLE' ? (
            <button
              className="btn btn-primary"
              onClick={onStartCall}
              disabled={!activeCase}
              style={{ padding: '6px 14px', fontSize: '13px' }}
            >
              <PhoneCall size={15} />
              <span>Gọi điện</span>
            </button>
          ) : (
            <>
              <button
                className="btn btn-secondary"
                onClick={() => setIsMuted(!isMuted)}
                style={{ padding: '6px 10px' }}
              >
                {isMuted ? <MicOff size={15} color="var(--danger)" /> : <Mic size={15} />}
              </button>
              <button
                className="btn btn-danger"
                onClick={onEndCall}
                style={{ padding: '6px 14px', fontSize: '13px' }}
              >
                <PhoneOff size={15} />
                <span>Kết thúc</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Collector Info */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <div style={{ textAlign: 'right' }}>
          <p style={{ fontSize: '13px', fontWeight: 600 }}>Lê Văn Chuyên (CB-8842)</p>
          <p style={{ fontSize: '11px', color: 'var(--text-sub)' }}>Chi nhánh Hoàn Kiếm</p>
        </div>
        <div style={{
          width: '32px',
          height: '32px',
          borderRadius: '50%',
          backgroundColor: '#005a54',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: 600,
          fontSize: '14px'
        }}>
          LC
        </div>
      </div>
    </header>
  );
};
