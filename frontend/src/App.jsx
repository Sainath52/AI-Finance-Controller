import React, { useState, useEffect, useCallback } from 'react';
import Navbar from './components/Navbar';
import KPICards from './components/KPICards';
import UploadSection from './components/UploadSection';
import ReconciliationTable from './components/ReconciliationTable';
import AuditInspectorModal from './components/AuditInspectorModal';
import ResolutionModal from './components/ResolutionModal';
import LedgerViewerModal from './components/LedgerViewerModal';

export default function App() {
  const [stats, setStats] = useState(null);
  const [results, setResults] = useState([]);
  const [ledger, setLedger] = useState([]);
  const [samples, setSamples] = useState([]);

  const [activeFilter, setActiveFilter] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');

  const [selectedResult, setSelectedResult] = useState(null);
  const [resolveResult, setResolveResult] = useState(null);
  const [isLedgerOpen, setIsLedgerOpen] = useState(false);

  const [isProcessing, setIsProcessing] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);

  const showToast = (msg, type = 'success') => {
    setToastMessage({ text: msg, type });
    setTimeout(() => setToastMessage(null), 4500);
  };

  const fetchData = useCallback(async () => {
    try {
      const [statsRes, resultsRes, ledgerRes, samplesRes] = await Promise.all([
        fetch('/api/stats'),
        fetch('/api/reconciliation-results'),
        fetch('/api/ledger'),
        fetch('/api/samples'),
      ]);

      if (statsRes.ok) setStats(await statsRes.json());
      if (resultsRes.ok) setResults(await resultsRes.json());
      if (ledgerRes.ok) setLedger(await ledgerRes.json());
      if (samplesRes.ok) setSamples(await samplesRes.json());
    } catch (err) {
      console.error('Failed to fetch data:', err);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Handle File Upload
  const handleUploadFile = async (file) => {
    setIsProcessing(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const res = await fetch('/api/upload-invoice', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) throw new Error('Upload failed');
      const data = await res.json();
      showToast(`Invoice reconciled: ${data.status} (${Math.round(data.confidence_score * 100)}% score)`);
      await fetchData();
      setSelectedResult(data);
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setIsProcessing(false);
    }
  };

  // Handle Raw Text Input
  const handleUploadText = async (text) => {
    setIsProcessing(true);
    try {
      const formData = new FormData();
      formData.append('raw_text', text);

      const res = await fetch('/api/upload-invoice', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) throw new Error('Processing failed');
      const data = await res.json();
      showToast(`Text Invoice reconciled: ${data.status} (${Math.round(data.confidence_score * 100)}% score)`);
      await fetchData();
      setSelectedResult(data);
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setIsProcessing(false);
    }
  };

  // Run 1-Click Demo Sample
  const handleRunSample = async (sampleId) => {
    setIsProcessing(true);
    try {
      const res = await fetch(`/api/run-sample/${sampleId}`, {
        method: 'POST',
      });

      if (!res.ok) throw new Error('Sample execution failed');
      const data = await res.json();
      showToast(`Sample Processed: ${data.status} for ${data.invoice.vendor_name}`);
      await fetchData();
      setSelectedResult(data);
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setIsProcessing(false);
    }
  };

  // Handle Manual Resolution
  const handleResolveSubmit = async (payload) => {
    setIsSubmitting(true);
    try {
      const res = await fetch('/api/resolve-exception', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error('Resolution failed');
      showToast('Exception resolved and audit log updated.');
      setResolveResult(null);
      await fetchData();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Reset & Re-Seed
  const handleResetLedger = async () => {
    if (!window.confirm('Reset database to synthetic baseline? All custom reconciliation records will be cleared.')) {
      return;
    }
    setIsResetting(true);
    try {
      const res = await fetch('/api/seed-ledger?force=true', { method: 'POST' });
      if (!res.ok) throw new Error('Reset failed');
      showToast('Ledger and database reset successfully.');
      await fetchData();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setIsResetting(false);
    }
  };

  // Filtered list
  const filteredResults = results.filter((r) => {
    if (activeFilter !== 'All' && r.status !== activeFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const matchVendor = r.invoice.vendor_name.toLowerCase().includes(q);
      const matchId = r.invoice.invoice_id.toLowerCase().includes(q);
      return matchVendor || matchId;
    }
    return true;
  });

  return (
    <div className="app-container">
      {/* Toast Notification */}
      {toastMessage && (
        <div className={`toast-banner ${toastMessage.type === 'error' ? 'toast-error' : 'toast-success'}`}>
          <span>{toastMessage.text}</span>
        </div>
      )}

      {/* Navigation */}
      <Navbar
        onResetLedger={handleResetLedger}
        onOpenLedger={() => setIsLedgerOpen(true)}
        onRefresh={fetchData}
        stats={stats}
        isResetting={isResetting}
      />

      {/* KPI Metrics */}
      <KPICards stats={stats} />

      {/* Document Ingestion & 1-Click Samples */}
      <UploadSection
        samples={samples}
        onUploadFile={handleUploadFile}
        onUploadText={handleUploadText}
        onRunSample={handleRunSample}
        isProcessing={isProcessing}
      />

      {/* Reconciliation Matrix Table */}
      <ReconciliationTable
        results={filteredResults}
        onSelectResult={setSelectedResult}
        onOpenResolve={setResolveResult}
        activeFilter={activeFilter}
        setActiveFilter={setActiveFilter}
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
      />

      {/* Audit Inspector Modal */}
      {selectedResult && (
        <AuditInspectorModal
          result={selectedResult}
          onClose={() => setSelectedResult(null)}
          onOpenResolve={setResolveResult}
        />
      )}

      {/* Manual Resolution Modal */}
      {resolveResult && (
        <ResolutionModal
          result={resolveResult}
          ledger={ledger.filter((t) => !t.is_reconciled)}
          onClose={() => setResolveResult(null)}
          onSubmit={handleResolveSubmit}
          isSubmitting={isSubmitting}
        />
      )}

      {/* Bank Ledger Viewer Modal */}
      {isLedgerOpen && (
        <LedgerViewerModal
          ledger={ledger}
          onClose={() => setIsLedgerOpen(false)}
        />
      )}
    </div>
  );
}
