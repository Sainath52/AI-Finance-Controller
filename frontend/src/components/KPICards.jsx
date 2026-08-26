import React from 'react';
import { CheckCircle2, AlertTriangle, XCircle, DollarSign } from 'lucide-react';

export default function KPICards({ stats }) {
  const autoRate = stats?.auto_reconcile_rate ?? 0;
  const totalProcessed = stats?.total_amount_processed ?? 0;
  const totalReconciled = stats?.total_amount_reconciled ?? 0;
  const pendingReview = stats?.needs_review_count ?? 0;
  const failed = stats?.failed_count ?? 0;
  const autoCount = stats?.auto_reconciled_count ?? 0;
  const totalInvoices = stats?.total_invoices ?? 0;

  return (
    <div className="kpi-grid">
      {/* 1. Auto-Reconciliation Rate */}
      <div className="glass-panel kpi-card">
        <div>
          <div className="kpi-top">
            <span className="kpi-label">Auto-Reconciled Rate</span>
            <div className="kpi-icon-pill" style={{ background: 'var(--emerald-bg)', border: '1px solid var(--emerald-border)' }}>
              <CheckCircle2 size={16} color="var(--emerald)" />
            </div>
          </div>
          <div className="kpi-main-val">
            <span className="kpi-number">{autoRate}%</span>
            <span className="kpi-detail text-emerald">({autoCount}/{totalInvoices} Invoices)</span>
          </div>
        </div>
        <div>
          <div className="kpi-bar-track">
            <div
              className="kpi-bar-fill"
              style={{
                width: `${Math.min(autoRate, 100)}%`,
                background: 'linear-gradient(90deg, var(--emerald), var(--cyan))'
              }}
            />
          </div>
          <div className="kpi-foot-text">High-confidence automated matches</div>
        </div>
      </div>

      {/* 2. Total Reconciled Volume */}
      <div className="glass-panel kpi-card">
        <div>
          <div className="kpi-top">
            <span className="kpi-label">Reconciled Volume</span>
            <div className="kpi-icon-pill" style={{ background: 'rgba(59, 130, 246, 0.12)', border: '1px solid rgba(59, 130, 246, 0.3)' }}>
              <DollarSign size={16} color="var(--primary)" />
            </div>
          </div>
          <div className="kpi-main-val">
            <span className="kpi-number">
              ${totalReconciled.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
        </div>
        <div className="kpi-foot-text">
          Processed Total: <strong className="text-light">${totalProcessed.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong>
        </div>
      </div>

      {/* 3. Flagged For Review */}
      <div className="glass-panel kpi-card">
        <div>
          <div className="kpi-top">
            <span className="kpi-label">Needs Review</span>
            <div className="kpi-icon-pill" style={{ background: 'var(--amber-bg)', border: '1px solid var(--amber-border)' }}>
              <AlertTriangle size={16} color="var(--amber)" />
            </div>
          </div>
          <div className="kpi-main-val">
            <span className="kpi-number text-amber">{pendingReview}</span>
            <span className="kpi-detail text-secondary">Exceptions Pending</span>
          </div>
        </div>
        <div className="kpi-foot-text text-amber">
          Requires 1-click controller confirmation
        </div>
      </div>

      {/* 4. Failed / Unmatched */}
      <div className="glass-panel kpi-card">
        <div>
          <div className="kpi-top">
            <span className="kpi-label">Failed / No Match</span>
            <div className="kpi-icon-pill" style={{ background: 'var(--rose-bg)', border: '1px solid var(--rose-border)' }}>
              <XCircle size={16} color="var(--rose)" />
            </div>
          </div>
          <div className="kpi-main-val">
            <span className="kpi-number text-rose">{failed}</span>
            <span className="kpi-detail text-secondary">Unmatched Items</span>
          </div>
        </div>
        <div className="kpi-foot-text">
          No corresponding bank entry in window
        </div>
      </div>
    </div>
  );
}
