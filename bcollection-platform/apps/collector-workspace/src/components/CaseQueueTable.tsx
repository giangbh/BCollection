import React, { useState } from 'react';
import { Search, Filter, AlertCircle, ArrowUpRight } from 'lucide-react';

interface CaseQueueTableProps {
  cases: any[];
  selectedCaseId: string | null;
  onSelectCase: (caseItem: any) => void;
}

export const CaseQueueTable: React.FC<CaseQueueTableProps> = ({
  cases,
  selectedCaseId,
  onSelectCase,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterArm, setFilterArm] = useState<'ALL' | 'TREATED' | 'CONTROL'>('ALL');

  const filteredCases = cases.filter((c) => {
    const matchesSearch =
      c.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.debtor_cif.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.phone_e164.includes(searchTerm);
    const matchesArm = filterArm === 'ALL' || c.experiment_arm === filterArm;
    return matchesSearch && matchesArm;
  });

  const formatVND = (amount: number) => {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amount);
  };

  const getDpdBadgeClass = (dpd: number) => {
    if (dpd <= 10) return 'badge-dpd-low';
    if (dpd <= 20) return 'badge-dpd-mid';
    return 'badge-dpd-high';
  };

  return (
    <div style={{
      backgroundColor: 'var(--bg-card)',
      borderRadius: '12px',
      border: '1px solid var(--border)',
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      overflow: 'hidden'
    }}>
      {/* Header & Search */}
      <div style={{ padding: '16px', borderBottom: '1px solid var(--border)', display: 'flex', gap: '12px', alignItems: 'center' }}>
        <div style={{
          position: 'relative',
          flex: 1,
          display: 'flex',
          alignItems: 'center'
        }}>
          <Search size={16} style={{ position: 'absolute', left: '12px', color: 'var(--text-sub)' }} />
          <input
            type="text"
            placeholder="Tìm theo Tên, CIF hoặc Số ĐT..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              width: '100%',
              padding: '8px 12px 8px 36px',
              backgroundColor: 'var(--bg-main)',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              color: 'var(--text-main)',
              fontSize: '13px',
              outline: 'none'
            }}
          />
        </div>

        {/* Experiment Filter */}
        <select
          value={filterArm}
          onChange={(e: any) => setFilterArm(e.target.value)}
          style={{
            padding: '8px 12px',
            backgroundColor: 'var(--bg-main)',
            border: '1px solid var(--border)',
            borderRadius: '8px',
            color: 'var(--text-main)',
            fontSize: '13px',
            outline: 'none'
          }}
        >
          <option value="ALL">Tất cả ({cases.length})</option>
          <option value="TREATED">Treatment 90%</option>
          <option value="CONTROL">Holdout 10%</option>
        </select>
      </div>

      {/* Table List */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
          <thead>
            <tr style={{ backgroundColor: 'var(--bg-main)', color: 'var(--text-sub)', borderBottom: '1px solid var(--border)' }}>
              <th style={{ padding: '10px 16px' }}>Khách hàng / CIF</th>
              <th style={{ padding: '10px 12px' }}>Sản phẩm</th>
              <th style={{ padding: '10px 12px' }}>DPD</th>
              <th style={{ padding: '10px 16px', textAlign: 'right' }}>Dư nợ quá hạn</th>
              <th style={{ padding: '10px 12px', textAlign: 'center' }}>Nhóm</th>
            </tr>
          </thead>
          <tbody>
            {filteredCases.map((c) => {
              const isSelected = c.case_id === selectedCaseId;
              return (
                <tr
                  key={c.case_id}
                  onClick={() => onSelectCase(c)}
                  style={{
                    borderBottom: '1px solid var(--border)',
                    backgroundColor: isSelected ? 'rgba(0, 90, 84, 0.25)' : 'transparent',
                    cursor: 'pointer',
                    transition: 'background 0.15s ease'
                  }}
                  onMouseEnter={(e) => { if (!isSelected) e.currentTarget.style.backgroundColor = 'var(--bg-card-sub)'; }}
                  onMouseLeave={(e) => { if (!isSelected) e.currentTarget.style.backgroundColor = 'transparent'; }}
                >
                  <td style={{ padding: '12px 16px' }}>
                    <div style={{ fontWeight: 600, color: isSelected ? '#34d399' : 'var(--text-main)' }}>{c.full_name}</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-sub)' }}>{c.debtor_cif} • {c.phone_e164}</div>
                  </td>
                  <td style={{ padding: '12px 12px' }}>
                    <span style={{ fontSize: '12px' }}>{c.product_code}</span>
                  </td>
                  <td style={{ padding: '12px 12px' }}>
                    <span className={`badge ${getDpdBadgeClass(c.dpd)}`}>DPD {c.dpd}</span>
                  </td>
                  <td style={{ padding: '12px 16px', textAlign: 'right', fontWeight: 600, color: 'var(--accent)' }}>
                    {formatVND(c.overdue_amount)}
                  </td>
                  <td style={{ padding: '12px 12px', textAlign: 'center' }}>
                    <span className={`badge ${c.experiment_arm === 'CONTROL' ? 'badge-holdout' : 'badge-treated'}`}>
                      {c.experiment_arm === 'CONTROL' ? 'Holdout 10%' : 'Treated 90%'}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
