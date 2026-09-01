import React, { useState, useEffect } from 'react';
import { HeaderSoftphone } from './components/HeaderSoftphone';
import { CaseQueueTable } from './components/CaseQueueTable';
import { PersonaCardView } from './components/PersonaCardView';
import { CallWrapupModal } from './components/CallWrapupModal';
import { ManualEnrichmentModal } from './components/ManualEnrichmentModal';

export const App: React.FC = () => {
  const [cases, setCases] = useState<any[]>([]);
  const [selectedCase, setSelectedCase] = useState<any>(null);
  const [personaData, setPersonaData] = useState<any>(null);
  const [loadingPersona, setLoadingPersona] = useState(false);

  // Softphone state
  const [callState, setCallState] = useState<'IDLE' | 'CALLING' | 'CONNECTED' | 'ENDED'>('IDLE');
  const [callDuration, setCallDuration] = useState(0);
  const [guardrailToken, setGuardrailToken] = useState<string | null>(null);

  // Modals
  const [isWrapupOpen, setIsWrapupOpen] = useState(false);
  const [isEnrichmentOpen, setIsEnrichmentOpen] = useState(false);

  // Fetch initial case queue
  useEffect(() => {
    fetch('/api/cases')
      .then((res) => res.json())
      .then((data) => {
        setCases(data);
        if (data.length > 0) {
          handleSelectCase(data[0]);
        }
      })
      .catch((err) => console.error('Error fetching cases:', err));
  }, []);

  // Call duration timer
  useEffect(() => {
    let interval: any = null;
    if (callState === 'CONNECTED') {
      interval = setInterval(() => setCallDuration((prev) => prev + 1), 1000);
    } else if (callState === 'IDLE') {
      setCallDuration(0);
    }
    return () => clearInterval(interval);
  }, [callState]);

  const handleSelectCase = (caseItem: any) => {
    setSelectedCase(caseItem);
    setLoadingPersona(true);
    fetch(`/api/cases/${caseItem.case_id}/persona`)
      .then((res) => res.json())
      .then((data) => {
        setPersonaData(data);
        setLoadingPersona(false);
      })
      .catch((err) => {
        console.error('Error fetching persona:', err);
        setLoadingPersona(false);
      });
  };

  const handleStartCall = () => {
    if (!selectedCase) return;
    setCallState('CALLING');

    // Gọi API evaluate intent qua L6 Guardrail
    fetch(`/api/cases/${selectedCase.case_id}/call-intent`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target_party_id: selectedCase.debtor_cif, channel: 'VOICE' })
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.is_allowed) {
          setGuardrailToken(data.guardrail_token);
          setTimeout(() => setCallState('CONNECTED'), 1200); // Giả lập nối máy
        } else {
          alert(`🚫 GUARDRAIL CHẶN CUỘC GỌI:\n${data.blocking_reason}`);
          setCallState('IDLE');
        }
      })
      .catch((err) => {
        alert('Lỗi kết nối Guardrail Service: ' + err);
        setCallState('IDLE');
      });
  };

  const handleEndCall = () => {
    setCallState('ENDED');
    setIsWrapupOpen(true);
  };

  const handleSubmitWrapup = (outcome: string, ptpAmount?: number, ptpDate?: string, notes?: string) => {
    if (!selectedCase) return;

    fetch(`/api/cases/${selectedCase.case_id}/call-wrapup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        guardrail_token: guardrailToken || '',
        outcome,
        ptp_amount: ptpAmount,
        ptp_date: ptpDate,
        notes
      })
    })
      .then((res) => res.json())
      .then(() => {
        setIsWrapupOpen(false);
        setCallState('IDLE');
        // Refresh cases
        fetch('/api/cases')
          .then((res) => res.json())
          .then((data) => setCases(data));
      });
  };

  const handleSubmitFact = (factType: string, payload: any) => {
    alert(`Đã ghi nhận Event Fact [${factType}]:\n${JSON.stringify(payload)}`);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
      {/* Top Header & Softphone */}
      <HeaderSoftphone
        activeCase={selectedCase}
        callState={callState}
        callDuration={callDuration}
        onStartCall={handleStartCall}
        onEndCall={handleEndCall}
      />

      {/* Main Workspace Body */}
      <main style={{
        flex: 1,
        display: 'grid',
        gridTemplateColumns: '48% 52%',
        gap: '16px',
        padding: '16px',
        overflow: 'hidden'
      }}>
        {/* Left Column: Case Queue */}
        <CaseQueueTable
          cases={cases}
          selectedCaseId={selectedCase?.case_id || null}
          onSelectCase={handleSelectCase}
        />

        {/* Right Column: Debtor 360 Persona Card */}
        <PersonaCardView
          persona={personaData}
          onOpenEnrichment={() => setIsEnrichmentOpen(true)}
        />
      </main>

      {/* Modals */}
      <CallWrapupModal
        isOpen={isWrapupOpen}
        activeCase={selectedCase}
        onClose={() => { setIsWrapupOpen(false); setCallState('IDLE'); }}
        onSubmit={handleSubmitWrapup}
      />

      <ManualEnrichmentModal
        isOpen={isEnrichmentOpen}
        activeCase={selectedCase}
        onClose={() => setIsEnrichmentOpen(false)}
        onSubmitFact={handleSubmitFact}
      />
    </div>
  );
};
