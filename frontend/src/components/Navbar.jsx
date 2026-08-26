import React from 'react';
import { ShieldCheck, RefreshCw, Database, Download, FileSpreadsheet, Sparkles } from 'lucide-react';

export default function Navbar({ onResetLedger, onOpenLedger, onRefresh, stats, isResetting }) {
  return (
    <header className="glass-panel navbar">
      <div className="navbar-brand">
        <div className="brand-icon-wrapper">
          <ShieldCheck size={24} color="#ffffff" />
        </div>
        <div>
          <div className="brand-title-row">
            <h1 className="brand-title">AI Finance Controller</h1>
            <span className="brand-tag">
              <Sparkles size={13} /> LangGraph + RapidFuzz
            </span>
          </div>
          <p className="brand-subtitle">Automated Invoice-to-Ledger Reconciliation & Audit Trail</p>
        </div>
      </div>

      <div className="navbar-actions">
        <button
          onClick={onOpenLedger}
          className="btn btn-secondary"
          title="Inspect Bank / General Ledger transactions"
        >
          <Database size={15} color="var(--cyan)" />
          <span>Ledger Book ({stats?.unreconciled_ledger_count ?? 0} open)</span>
        </button>

        <a
          href="/api/export/csv"
          download="reconciliation_report.csv"
          className="btn btn-secondary"
        >
          <FileSpreadsheet size={15} color="var(--emerald)" />
          <span>Export CSV</span>
        </a>

        <a
          href="/api/export/json"
          download="reconciliation_audit.json"
          className="btn btn-secondary"
        >
          <Download size={15} color="var(--indigo)" />
          <span>Audit JSON</span>
        </a>

        <button
          onClick={onResetLedger}
          disabled={isResetting}
          className="btn btn-danger"
          title="Reset database to synthetic bank statement baseline"
        >
          <RefreshCw size={15} className={isResetting ? 'animate-spin' : ''} />
          <span>{isResetting ? 'Resetting...' : 'Reset Ledger'}</span>
        </button>
      </div>
    </header>
  );
}
