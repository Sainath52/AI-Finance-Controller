import React from 'react';
import {
  X,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Sparkles,
  FileText,
  Building2,
} from 'lucide-react';

export default function AuditInspectorModal({ result, onClose, onOpenResolve }) {
  if (!result) return null;

  const inv = result.invoice;
  const tx = result.matched_ledger_transaction;
  const isAuto = result.status === 'Auto-Reconciled';
  const isReview = result.status === 'Needs Review';
  const isFailed = result.status === 'Failed';

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div className="brand-icon-wrapper" style={{ width: '36px', height: '36px' }}>
              <ShieldCheck size={20} color="#ffffff" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h3 style={{ fontSize: '0.9375rem', fontWeight: '700', color: '#ffffff' }}>
                  Audit Inspector: {inv.vendor_name}
                </h3>
                <span
                  className={`badge ${
                    isAuto ? 'badge-auto' : isReview ? 'badge-review' : 'badge-failed'
                  }`}
                >
                  {result.status}
                </span>
              </div>
              <p className="text-muted font-mono" style={{ fontSize: '0.6875rem' }}>
                ID: {result.id} • Invoice #{inv.invoice_id}
              </p>
            </div>
          </div>

          <button onClick={onClose} className="btn-icon">
            <X size={16} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="modal-body">
          {/* 1. Side-by-Side Comparison */}
          <div className="grid-2col">
            {/* Invoice Card */}
            <div className="sub-panel">
              <div className="sub-panel-title text-primary">
                <FileText size={15} />
                <span>Extracted Invoice Data</span>
              </div>
              <div className="kv-row">
                <span className="kv-key">Vendor:</span>
                <span className="kv-val text-white">{inv.vendor_name}</span>
              </div>
              <div className="kv-row">
                <span className="kv-key">Invoice ID:</span>
                <span className="kv-val font-mono">{inv.invoice_id}</span>
              </div>
              <div className="kv-row">
                <span className="kv-key">Invoice Date:</span>
                <span className="kv-val font-mono">{inv.invoice_date}</span>
              </div>
              {inv.subtotal !== null && (
                <div className="kv-row">
                  <span className="kv-key">Subtotal:</span>
                  <span className="kv-val font-mono">${inv.subtotal?.toFixed(2)}</span>
                </div>
              )}
              {inv.tax !== null && (
                <div className="kv-row">
                  <span className="kv-key">Tax:</span>
                  <span className="kv-val font-mono">${inv.tax?.toFixed(2)}</span>
                </div>
              )}
              <div className="kv-row" style={{ paddingTop: '8px', borderTop: '1px solid var(--border-subtle)', marginTop: '4px' }}>
                <span className="kv-key" style={{ fontWeight: '700', color: 'var(--text-light)' }}>Total Amount:</span>
                <span className="kv-val font-mono text-primary" style={{ fontSize: '0.9375rem' }}>${inv.total_amount.toFixed(2)}</span>
              </div>

              {/* Line Items */}
              {inv.line_items && inv.line_items.length > 0 && (
                <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px solid var(--border-subtle)' }}>
                  <span className="text-muted" style={{ fontSize: '0.6875rem', fontWeight: '700', textTransform: 'uppercase', display: 'block', marginBottom: '6px' }}>
                    Line Items Breakdown:
                  </span>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {inv.line_items.map((item, idx) => (
                      <div
                        key={idx}
                        style={{
                          background: 'rgba(15, 23, 42, 0.6)',
                          padding: '6px 8px',
                          borderRadius: 'var(--radius-sm)',
                          fontSize: '0.6875rem',
                          display: 'flex',
                          justifyContent: 'space-between'
                        }}
                      >
                        <span className="text-light truncate" style={{ maxWidth: '200px' }}>{item.description}</span>
                        <span className="font-mono text-white font-semibold">${item.total_price.toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Matched Bank Ledger Card */}
            <div className="sub-panel">
              <div className="sub-panel-title text-cyan">
                <Building2 size={15} />
                <span>Matched Bank / Ledger</span>
              </div>
              {tx ? (
                <>
                  <div className="kv-row">
                    <span className="kv-key">Transaction ID:</span>
                    <span className="kv-val font-mono text-cyan">{tx.transaction_id}</span>
                  </div>
                  <div className="kv-row">
                    <span className="kv-key">Bank Memo:</span>
                    <span className="kv-val truncate" style={{ maxWidth: '180px' }} title={tx.description}>{tx.description}</span>
                  </div>
                  <div className="kv-row">
                    <span className="kv-key">Posting Date:</span>
                    <span className="kv-val font-mono">{tx.transaction_date}</span>
                  </div>
                  <div className="kv-row">
                    <span className="kv-key">Account:</span>
                    <span className="kv-val">{tx.account}</span>
                  </div>
                  <div className="kv-row">
                    <span className="kv-key">Reference Code:</span>
                    <span className="kv-val font-mono">{tx.reference_no || 'N/A'}</span>
                  </div>
                  <div className="kv-row" style={{ paddingTop: '8px', borderTop: '1px solid var(--border-subtle)', marginTop: '4px' }}>
                    <span className="kv-key" style={{ fontWeight: '700', color: 'var(--text-light)' }}>Bank Debit Amount:</span>
                    <span className="kv-val font-mono text-cyan" style={{ fontSize: '0.9375rem' }}>${tx.amount.toFixed(2)}</span>
                  </div>
                </>
              ) : (
                <div style={{ textAlign: 'center', padding: '36px 12px', color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                  <p>No corresponding transaction found in bank statement ledger.</p>
                </div>
              )}
            </div>
          </div>

          {/* 2. Match Factor Analysis */}
          <div className="sub-panel">
            <div className="sub-panel-title text-amber">
              <Sparkles size={15} />
              <span>Engine Match Analysis & Factor Evaluation</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {result.reasons?.map((reason, idx) => (
                <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: 'var(--emerald)' }}>
                  <CheckCircle2 size={14} />
                  <span>{reason}</span>
                </div>
              ))}
              {result.discrepancies?.map((disc, idx) => (
                <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: 'var(--amber)' }}>
                  <AlertTriangle size={14} />
                  <span>{disc.message}</span>
                </div>
              ))}
            </div>
          </div>

          {/* 3. LangGraph Chronological Audit Trail */}
          <div className="sub-panel">
            <div className="sub-panel-title text-primary">
              <Clock size={15} />
              <span>LangGraph Agent Audit Trail (Step-by-Step Rationale)</span>
            </div>

            <div className="timeline-box">
              {result.audit_trail?.map((entry, idx) => (
                <div key={idx} className="timeline-step">
                  <div className="step-meta font-mono">
                    <strong className="text-light">{entry.stage}</strong>
                    <span>{entry.timestamp?.slice(11, 19)}</span>
                  </div>
                  <div className="step-decision">{entry.decision}</div>
                  <div className="step-reasoning">{entry.reasoning}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="modal-footer">
          <div className="text-xs text-muted">
            Confidence Score: <strong className="text-white font-mono">{Math.round(result.confidence_score * 100)}%</strong>
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            {isReview && (
              <button
                onClick={() => {
                  onClose();
                  onOpenResolve(result);
                }}
                className="btn btn-warning"
              >
                Resolve Exception
              </button>
            )}
            <button onClick={onClose} className="btn btn-secondary">
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
