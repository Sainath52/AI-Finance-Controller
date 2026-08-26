import React, { useState, useRef } from 'react';
import { UploadCloud, FileText, Play, Sparkles, Loader2, ArrowUpRight } from 'lucide-react';

export default function UploadSection({ samples, onUploadFile, onUploadText, onRunSample, isProcessing }) {
  const [activeTab, setActiveTab] = useState('samples'); // default to 'samples' for instant user gratification
  const [rawText, setRawText] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const fileInputRef = useRef(null);

  const handleFileDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const submitFile = () => {
    if (!selectedFile) return;
    onUploadFile(selectedFile);
    setSelectedFile(null);
  };

  const submitText = () => {
    if (!rawText.trim()) return;
    onUploadText(rawText);
    setRawText('');
  };

  return (
    <div className="glass-panel ingestion-panel">
      {/* Section Header */}
      <div className="section-header">
        <div className="section-title-wrap">
          <div className="section-icon-box">
            <UploadCloud size={20} />
          </div>
          <div>
            <h2 className="section-heading">Document Ingestion & Pipeline Run</h2>
            <p className="section-subheading">Feed invoice documents to trigger the LangGraph multi-step audit agent</p>
          </div>
        </div>

        <div className="pill-tabs">
          <button
            onClick={() => setActiveTab('samples')}
            className={`tab-btn ${activeTab === 'samples' ? 'active' : ''}`}
          >
            <Sparkles size={14} color="#fde047" />
            <span>1-Click Demo Scenarios</span>
          </button>
          <button
            onClick={() => setActiveTab('upload')}
            className={`tab-btn ${activeTab === 'upload' ? 'active' : ''}`}
          >
            <UploadCloud size={14} />
            <span>File Upload (PDF/TXT)</span>
          </button>
          <button
            onClick={() => setActiveTab('text')}
            className={`tab-btn ${activeTab === 'text' ? 'active' : ''}`}
          >
            <FileText size={14} />
            <span>Paste Text</span>
          </button>
        </div>
      </div>

      {/* Tab 1: 1-Click Demo Scenarios */}
      {activeTab === 'samples' && (
        <div className="samples-grid">
          {samples.map((sample) => {
            const isFailed = sample.id.includes('unmatched');
            const isReview = sample.id.includes('github');

            return (
              <div key={sample.id} className="sample-card">
                <div>
                  <div className="sample-head">
                    <span className="sample-vendor truncate">{sample.vendor}</span>
                    <span className="sample-amount font-mono">${sample.total.toFixed(2)}</span>
                  </div>
                  <div className="sample-meta font-mono">
                    <span>ID: {sample.invoice_id}</span>
                    <span>•</span>
                    <span>Date: {sample.date}</span>
                  </div>
                  <div className="sample-note-box">
                    {sample.notes}
                  </div>
                </div>

                <div className="sample-foot">
                  <span
                    className={`badge ${
                      isFailed ? 'badge-failed' : isReview ? 'badge-review' : 'badge-auto'
                    }`}
                  >
                    {isFailed ? 'Fail Scenario' : isReview ? 'Needs Review' : 'Auto-Match'}
                  </span>

                  <button
                    onClick={() => onRunSample(sample.id)}
                    disabled={isProcessing}
                    className="btn btn-primary"
                    style={{ padding: '6px 12px', fontSize: '0.75rem' }}
                  >
                    <span>Test Match</span>
                    <ArrowUpRight size={13} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Tab 2: File Upload Dropzone */}
      {activeTab === 'upload' && (
        <div>
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleFileDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`dropzone ${dragOver ? 'active' : ''}`}
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept=".pdf,.txt,.png,.jpg,.jpeg"
              style={{ display: 'none' }}
            />
            <div className="dropzone-icon">
              <UploadCloud size={24} />
            </div>
            <p className="dropzone-title">
              {selectedFile ? selectedFile.name : 'Click to browse or drag & drop invoice document'}
            </p>
            <p className="dropzone-desc">
              Supports Tax Invoices, Receipts in PDF, TXT or Scanned formats
            </p>
          </div>

          {selectedFile && (
            <div className="file-selected-card">
              <div className="file-info">
                <FileText size={18} color="var(--primary)" />
                <span className="font-semibold text-white">{selectedFile.name}</span>
                <span className="text-muted font-mono">({(selectedFile.size / 1024).toFixed(1)} KB)</span>
              </div>
              <button
                onClick={submitFile}
                disabled={isProcessing}
                className="btn btn-primary"
              >
                {isProcessing ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
                <span>{isProcessing ? 'Reconciling...' : 'Run Reconciliation Agent'}</span>
              </button>
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Paste Text */}
      {activeTab === 'text' && (
        <div>
          <textarea
            value={rawText}
            onChange={(e) => setRawText(e.target.value)}
            placeholder="Paste invoice text here (e.g. Vendor: Amazon Web Services, Invoice Date: 2026-08-15, Total: $142.50)..."
            className="raw-textarea"
          />
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '12px' }}>
            <button
              onClick={submitText}
              disabled={isProcessing || !rawText.trim()}
              className="btn btn-primary"
            >
              {isProcessing ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
              <span>{isProcessing ? 'Processing...' : 'Extract & Reconcile'}</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
