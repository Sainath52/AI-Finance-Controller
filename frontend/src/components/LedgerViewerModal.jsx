import React, { useState } from 'react';
import { X, Database, CheckCircle2, Circle } from 'lucide-react';

export default function LedgerViewerModal({ ledger, onClose }) {
  const [filter, setFilter] = useState('all'); // 'all' | 'unreconciled' | 'reconciled'
  const [search, setSearch] = useState('');

  const filteredLedger = ledger.filter((tx) => {
    if (filter === 'unreconciled' && tx.is_reconciled) return false;
    if (filter === 'reconciled' && !tx.is_reconciled) return false;
    if (search) {
      const q = search.toLowerCase();
      return (
        tx.description.toLowerCase().includes(q) ||
        tx.transaction_id.toLowerCase().includes(q) ||
        (tx.reference_no && tx.reference_no.toLowerCase().includes(q))
      );
    }
    return true;
  });

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ padding: '6px', borderRadius: 'var(--radius-sm)', background: 'rgba(6, 182, 212, 0.15)', border: '1px solid rgba(6, 182, 212, 0.3)' }}>
              <Database size={18} color="var(--cyan)" />
            </div>
            <div>
              <h3 style={{ fontSize: '0.875rem', fontWeight: '700', color: '#ffffff' }}>General / Bank Statement Ledger</h3>
              <p className="text-muted font-mono" style={{ fontSize: '0.6875rem' }}>Total: {ledger.length} transactions</p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div className="pill-tabs">
              {['all', 'unreconciled', 'reconciled'].map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`tab-btn ${filter === f ? 'active' : ''}`}
                  style={{ textTransform: 'capitalize', padding: '4px 10px' }}
                >
                  {f}
                </button>
              ))}
            </div>

            <button onClick={onClose} className="btn-icon">
              <X size={15} />
            </button>
          </div>
        </div>

        {/* Content Table */}
        <div className="modal-body" style={{ padding: '0' }}>
          <div className="table-wrapper" style={{ margin: '0' }}>
            <table className="custom-table">
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Transaction ID</th>
                  <th>Date</th>
                  <th>Amount</th>
                  <th>Description / Memo</th>
                  <th>Ref Code</th>
                  <th>Account</th>
                </tr>
              </thead>
              <tbody>
                {filteredLedger.map((tx) => (
                  <tr key={tx.transaction_id}>
                    <td>
                      {tx.is_reconciled ? (
                        <span className="badge badge-auto">
                          <CheckCircle2 size={12} /> Reconciled
                        </span>
                      ) : (
                        <span className="badge badge-review">
                          <Circle size={8} fill="currentColor" /> Open
                        </span>
                      )}
                    </td>
                    <td className="font-mono font-semibold text-light">{tx.transaction_id}</td>
                    <td className="font-mono text-muted">{tx.transaction_date}</td>
                    <td className="font-mono font-bold text-white">${tx.amount.toFixed(2)}</td>
                    <td className="text-light truncate" style={{ maxWidth: '200px' }} title={tx.description}>
                      {tx.description}
                    </td>
                    <td className="font-mono text-muted">{tx.reference_no || '-'}</td>
                    <td className="text-muted" style={{ fontSize: '0.6875rem' }}>{tx.account}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Footer */}
        <div className="modal-footer">
          <span className="text-xs text-muted">Showing {filteredLedger.length} entries</span>
          <button onClick={onClose} className="btn btn-secondary">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
