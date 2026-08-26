import React from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Eye,
  Search,
} from 'lucide-react';

export default function ReconciliationTable({
  results,
  onSelectResult,
  onOpenResolve,
  activeFilter,
  setActiveFilter,
  searchQuery,
  setSearchQuery,
}) {
  return (
    <div className="glass-panel table-panel">
      {/* Table Header & Controls */}
      <div className="section-header">
        <div>
          <h2 className="section-heading">Reconciliation Ledger Matrix</h2>
          <p className="section-subheading">Processed invoices, confidence ratings, and ledger pairings</p>
        </div>

        <div className="table-controls">
          {/* Search Box */}
          <div className="search-input-wrap">
            <Search size={14} className="search-icon" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search vendor / invoice #..."
              className="search-field"
            />
          </div>

          {/* Filter Pills */}
          <div className="pill-tabs">
            {['All', 'Auto-Reconciled', 'Needs Review', 'Failed'].map((filter) => (
              <button
                key={filter}
                onClick={() => setActiveFilter(filter)}
                className={`tab-btn ${activeFilter === filter ? 'active' : ''}`}
              >
                {filter}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Table Body */}
      {results.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '48px 20px', border: '1px dashed var(--border-subtle)', borderRadius: 'var(--radius-lg)' }}>
          <p className="text-sm text-secondary font-medium">No reconciliation records found matching criteria.</p>
          <p className="text-xs text-muted" style={{ marginTop: '4px' }}>Upload an invoice or click one of the 1-Click Demo Scenarios above.</p>
        </div>
      ) : (
        <div className="table-wrapper">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Invoice Details</th>
                <th>Invoice Date</th>
                <th>Amount</th>
                <th>Reconciliation Status</th>
                <th>Confidence</th>
                <th>Matched Bank Tx</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {results.map((rec) => {
                const inv = rec.invoice;
                const tx = rec.matched_ledger_transaction;
                const isAuto = rec.status === 'Auto-Reconciled';
                const isReview = rec.status === 'Needs Review';
                const isFailed = rec.status === 'Failed';
                const scorePercent = Math.round(rec.confidence_score * 100);

                return (
                  <tr key={rec.id}>
                    {/* 1. Vendor & ID */}
                    <td>
                      <div className="font-bold text-white" style={{ fontSize: '0.8125rem' }}>{inv.vendor_name}</div>
                      <div className="text-muted font-mono" style={{ fontSize: '0.6875rem', marginTop: '2px' }}>
                        <span>{inv.invoice_id}</span>
                        {inv.currency && <span style={{ marginLeft: '4px', opacity: 0.8 }}>({inv.currency})</span>}
                      </div>
                    </td>

                    {/* 2. Date */}
                    <td>
                      <div className="font-mono text-light">{inv.invoice_date}</div>
                      {tx && tx.transaction_date !== inv.invoice_date && (
                        <div className="font-mono text-amber" style={{ fontSize: '0.6875rem' }}>
                          Bank: {tx.transaction_date}
                        </div>
                      )}
                    </td>

                    {/* 3. Amount */}
                    <td>
                      <div className="font-mono font-bold text-white" style={{ fontSize: '0.875rem' }}>
                        ${inv.total_amount.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                      </div>
                      {tx && Math.abs(tx.amount - inv.total_amount) > 0.01 && (
                        <div className="font-mono text-amber" style={{ fontSize: '0.6875rem' }}>
                          Bank: ${tx.amount.toFixed(2)}
                        </div>
                      )}
                    </td>

                    {/* 4. Status Badge */}
                    <td>
                      <span
                        className={`badge ${
                          isAuto ? 'badge-auto' : isReview ? 'badge-review' : 'badge-failed'
                        }`}
                      >
                        {isAuto && <CheckCircle2 size={13} />}
                        {isReview && <AlertTriangle size={13} />}
                        {isFailed && <XCircle size={13} />}
                        <span>{rec.status}</span>
                      </span>
                      {rec.resolved_by && (
                        <div className="text-muted" style={{ fontSize: '0.6875rem', marginTop: '3px' }}>
                          Resolved by {rec.resolved_by}
                        </div>
                      )}
                    </td>

                    {/* 5. Confidence Score Meter */}
                    <td>
                      <div className="conf-meter">
                        <div className="conf-track">
                          <div
                            className="conf-fill"
                            style={{
                              width: `${scorePercent}%`,
                              background: scorePercent >= 85 ? 'var(--emerald)' : scorePercent >= 60 ? 'var(--amber)' : 'var(--rose)'
                            }}
                          />
                        </div>
                        <span className="font-mono text-light font-medium">{scorePercent}%</span>
                      </div>
                    </td>

                    {/* 6. Matched Bank Tx */}
                    <td style={{ maxWidth: '240px' }}>
                      {tx ? (
                        <div>
                          <div className="font-mono font-semibold text-cyan truncate" style={{ fontSize: '0.75rem' }}>
                            {tx.transaction_id}
                          </div>
                          <div className="text-muted truncate" style={{ fontSize: '0.6875rem' }} title={tx.description}>
                            {tx.description}
                          </div>
                        </div>
                      ) : (
                        <span className="text-muted" style={{ fontStyle: 'italic', fontSize: '0.75rem' }}>No paired bank entry</span>
                      )}
                    </td>

                    {/* 7. Actions */}
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '6px' }}>
                        <button
                          onClick={() => onSelectResult(rec)}
                          className="btn-icon"
                          title="Inspect LangGraph Audit Trail"
                        >
                          <Eye size={15} color="var(--primary)" />
                        </button>

                        {isReview && (
                          <button
                            onClick={() => onOpenResolve(rec)}
                            className="btn btn-warning"
                            style={{ padding: '4px 10px', fontSize: '0.6875rem' }}
                            title="Resolve flagged exception"
                          >
                            Resolve
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
