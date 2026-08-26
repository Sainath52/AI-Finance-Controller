# AI Finance Controller - Automated Financial Reconciliation & Ledger Engine

An end-to-end enterprise MVP for an **AI Finance Controller** designed for automated financial reconciliation and invoice-to-ledger processing.

Powered by **FastAPI**, **LangGraph**, **Instructor + Pydantic**, **RapidFuzz**, **SQLAlchemy**, and a **React + Vite Financial Dashboard**.

---

## 🌟 Key Features

1. **Document Ingestion & Schema Extraction**:
   - Ingests PDF, TXT, Image, or plain-text invoice documents.
   - Extracts structured schema: `Vendor Name`, `Invoice ID`, `Invoice Date`, `Due Date`, `Line Items`, `Subtotal`, `Tax`, and `Total Amount`.
   - Uses **Instructor + Pydantic** with OpenAI/Gemini/Claude backends and fallback deterministic NLP parser.

2. **Hybrid Matching Engine (`utils/reconciler.py`)**:
   - **Exact Amount Match**: Precision matching down to the cent.
   - **Date Window Matching**: Tolerant $\pm 3$ days window with proximity decay scoring.
   - **RapidFuzz Vendor Matching**: Token sort ratio, partial ratio, token set ratio (>80% similarity threshold) + known enterprise alias cluster mapping (e.g. AWS vs Amazon Web Services, Uber BV vs UBER *TRIP).
   - **Reference / Memo Matching**: Substring and fuzzy pattern detection in bank transaction references.
   - **Composite Multi-Factor Scoring**: Weighted scoring model with discrepancy detection.

3. **LangGraph Agent Orchestration (`agents/graph.py`)**:
   - Multi-step workflow state machine:
     `Ingest & OCR` $\to$ `Matching Rules` $\to$ `LLM Reasoning Fallback` $\to$ `Audit & Classify` $\to$ `SQLite Persistence`.
   - Classifies every invoice into:
     - `Auto-Reconciled` (high confidence $>85\%$)
     - `Needs Review` (ambiguous or flagged with variance)
     - `Failed` (no ledger match found)

4. **Interactive Finance Controller Dashboard (`frontend/`)**:
   - Real-time KPI metrics: Auto-Reconciled Rate %, Processed Volume, Exceptions Pending Review.
   - Drag-and-drop document upload & raw text editor.
   - **1-Click Demo Scenarios** for immediate evaluation (AWS, Slack, GitHub, Adobe, Unmatched).
   - **Side-by-Side Audit Inspector**: Field-level diff comparison and chronological LangGraph execution timeline.
   - **Manual Exception Resolution**: 1-click controller sign-off or custom ledger re-linking.
   - **Export Engine**: 1-click CSV reconciliation register and JSON audit logs.

---

## 📁 Directory Structure

```
f:/RazorPay/
├── backend/
│   ├── main.py              # FastAPI application with REST endpoints & static mounting
│   ├── database.py          # SQLAlchemy ORM models (Invoices, LineItems, Ledger, Audit)
│   └── seed_data.py         # Realistic synthetic bank statement generator
├── agents/
│   ├── graph.py             # LangGraph StateGraph pipeline orchestrator
│   └── prompts.py           # Prompts for schema extraction & ambiguous reasoning
├── models/
│   └── schemas.py           # Pydantic schemas for data validation and API types
├── utils/
│   ├── reconciler.py        # Core hybrid exact + RapidFuzz matching engine
│   ├── ocr_extractor.py     # PDF & text schema extractor with Instructor
│   └── generate_samples.py  # Realistic TXT and PDF sample invoice generator
├── frontend/                # React + Vite Financial Controller UI
│   ├── src/
│   │   ├── components/      # KPICards, UploadSection, ReconciliationTable, Modals
│   │   ├── App.jsx          # Main controller state & API hooks
│   │   └── index.css        # Glassmorphic dark-mode design system
│   └── dist/                # Production build served directly by FastAPI
├── sample_invoices/         # Pre-generated PDF & TXT test invoices
└── tests/
    ├── test_reconciliation.py # Pytest test suite for engine, LangGraph & API
    └── verify_e2e.py        # End-to-end integration test runner
```

---

## 🚀 Quickstart & Running Locally

### 1. Run the Backend & UI (All-in-One)
```powershell
# From the project root
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser.

### 2. Run the Vite Frontend (Dev Server with HMR)
```powershell
cd frontend
npm run dev
```
Open **[http://localhost:5173](http://localhost:5173)**.

### 3. Run Automated Tests
```powershell
# Run Pytest suite
python -m pytest tests/test_reconciliation.py -v

# Run End-to-End Verification
python tests/verify_e2e.py
```

---

## 📡 Core REST API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/upload-invoice` | Upload PDF/TXT/Image or raw text to run LangGraph pipeline |
| `POST` | `/api/reconcile-invoice` | Direct JSON reconciliation of `InvoiceData` payload |
| `GET` | `/api/reconciliation-results` | List all processed reconciliations with full audit trails |
| `POST` | `/api/resolve-exception` | Controller manual override (`approve_match`, `link_ledger`, `reject`) |
| `GET` | `/api/ledger` | Query bank statement ledger transactions (`all`, `unreconciled`, `reconciled`) |
| `POST` | `/api/seed-ledger` | Reset / re-seed ledger with realistic baseline data |
| `GET` | `/api/stats` | Live reconciliation KPI summary statistics |
| `GET` | `/api/export/csv` | Download complete reconciliation report as CSV |
| `GET` | `/api/export/json` | Download full structured audit trail JSON |
| `GET` | `/api/samples` | List available pre-configured test scenarios |
| `POST` | `/api/run-sample/{id}` | Execute 1-click reconciliation on a sample invoice |
