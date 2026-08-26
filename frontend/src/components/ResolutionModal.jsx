import React, { useState } from 'react';
import { X, Check, Link2, XCircle, AlertTriangle, Loader2 } from 'lucide-react';

export default function ResolutionModal({ result, ledger, onClose, onSubmit, isSubmitting }) {
  if (!result) return null;

  const [action, setAction] = useState('approve_match'); // 'approve_match' | 'link_ledger' | 'reject'
  const [selectedLedgerId, setSelectedLedgerId] = useState(
    result.matched_ledger_transaction?.transaction_id || (ledger[0]?.transaction_id ?? '')
  );
  const [notes, setNotes] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit({
      reconciliation_id: result.id,
      action: action,
      ledger_transaction_id: action === 'link_ledger' ? selectedLedgerId : result.matched_ledger_transaction?.transaction_id,
      notes: notes || (action === 'approve_match' ? 'Approved by Controller' : 'Manual action taken'),
      resolved_by: 'Finance Controller',
    });
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-dialog" style={{ maxWidth: '520px' }} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ padding: '6px', borderRadius: 'var(--radius-sm)', background: 'var(--amber-bg)', border: '1px solid var(--amber-border)' }}>
              <AlertTriangle size={18} color="var(--amber)" />
            </div>
            <div>
              <h3 style={{ fontSize: '0.875rem', fontWeight: '700', color: '#ffffff' }}>Manual Exception Resolution</h3>
              <p className="text-muted" style={{ fontSize: '0.6875rem' }}>
                Invoice: {result.invoice.vendor_name} (${result.invoice.total_amount.toFixed(2)})
              </p>
            </div>
          </div>
          <button onClick={onClose} className="btn-icon">
            <X size={15} />
          </button>
        </div>

        {/* Body Form */}
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <div>
              <label className="text-muted font-semibold uppercase text-xs" style={{ display: 'block', marginBottom: '8px' }}>
                Choose Resolution Action:
              </label>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px' }}>
                <button
                  type="button"
                  onClick={() => setAction('approve_match')}
                  className={`btn ${action === 'approve_match' ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ flexDirection: 'column', padding: '12px 8px', fontSize: '0.75rem', gap: '6px' }}
                >
                  <Check size={16} />
                  <span>Approve Match</span>
                </button>

                <button
                  type="button"
                  onClick={() => setAction('link_ledger')}
                  className={`btn ${action === 'link_ledger' ? 'btn-accent' : 'btn-secondary'}`}
                  style={{ flexDirection: 'column', padding: '12px 8px', fontSize: '0.75rem', gap: '6px' }}
                >
                  <Link2 size={16} />
                  <span>Link Other Tx</span>
                </button>

                <button
                  type="button"
                  onClick={() => setAction('reject')}
                  className={`btn ${action === 'reject' ? 'btn-danger' : 'btn-secondary'}`}
                  style={{ flexDirection: 'column', padding: '12px 8px', fontSize: '0.75rem', gap: '6px' }}
                >
                  <XCircle size={16} />
                  <span>Reject Match</span>
                </button>
              </div>
            </div>

            {/* Select Target Ledger if Link selected */}
            {action === 'link_ledger' && (
              <div>
                <label className="text-secondary font-semibold text-xs" style={{ display: 'block', marginBottom: '6px' }}>
                  Select Target Ledger Transaction:
                </label>
                <select
                  value={selectedLedgerId}
                  onChange={(e) => setSelectedLedgerId(e.target.value)}
                  className="search-field"
                  style={{ height: '38px' }}
                >
                  {ledger.map((tx) => (
                    <option key={tx.transaction_id} value={tx.transaction_id}>
                      {tx.transaction_id} | ${tx.amount.toFixed(2)} | {tx.transaction_date} | {tx.description.slice(0, 35)}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Sign-off Notes */}
            <div>
              <label className="text-secondary font-semibold text-xs" style={{ display: 'block', marginBottom: '6px' }}>
                Audit Sign-off Notes / Reason:
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="e.g. Verified vendor alias, timing offset is due to weekend clearance..."
                className="raw-textarea"
                rows={3}
                style={{ minHeight: '80px' }}
              />
            </div>
          </div>

          {/* Footer */}
          <div className="modal-footer">
            <button type="button" onClick={onClose} className="btn btn-secondary">
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="btn btn-primary"
            >
              {isSubmitting && <Loader2 size={14} className="animate-spin" />}
              <span>Commit Decision</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
