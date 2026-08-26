# AI Finance Controller - Automated Financial Reconciliation & Ledger Engine

An end-to-end enterprise MVP for an **AI Finance Controller** designed for automated financial reconciliation and invoice-to-ledger processing.

Powered by **FastAPI**, **LangGraph**, **Instructor + Pydantic**, **RapidFuzz**, **SQLAlchemy**, and a **React + Vite Financial Dashboard**.

---

## 🚀 Live Demo

Experience the production deployment of the AI Finance Controller live in your browser:

👉 **[Launch Live App](https://ai-finance-controller-xi.vercel.app/)**

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
