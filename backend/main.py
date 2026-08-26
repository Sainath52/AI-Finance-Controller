"""
FastAPI Backend Application for AI Finance Controller.
Provides REST endpoints for invoice ingestion, LangGraph agent execution,
ledger matching queries, exception resolution, and audit reporting.
"""

import os
import json
import csv
import io
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from sqlalchemy.orm import Session

from backend.database import (
    init_db,
    get_db,
    DBInvoice,
    DBLineItem,
    DBLedgerTransaction,
    DBReconciliation,
    SessionLocal,
)
from backend.seed_data import seed_database
from models.schemas import (
    InvoiceData,
    LedgerTransaction,
    ReconciliationResult,
    ReconciliationStatus,
    MatchType,
    ManualResolutionRequest,
    DashboardStats,
    AuditLogEntry,
    DiscrepancyDetail,
    MatchCandidate,
)
from agents.graph import run_reconciliation_pipeline
from utils.generate_samples import SAMPLE_INVOICES_DATA, generate_all_samples, SAMPLE_DIR

# Initialize database tables
init_db()

# Create initial seed if empty
with SessionLocal() as db_session:
    seed_database(db_session, force_reset=False)

app = FastAPI(
    title="AI Finance Controller API",
    description="Automated financial reconciliation & invoice-to-ledger audit engine powered by LangGraph, Instructor & RapidFuzz",
    version="1.0.0",
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_active_ledger_transactions(db: Session, include_reconciled: bool = False) -> List[LedgerTransaction]:
    """Fetch active bank ledger transactions from DB."""
    query = db.query(DBLedgerTransaction)
    if not include_reconciled:
        query = query.filter(DBLedgerTransaction.is_reconciled == False)
    db_txs = query.all()
    return [
        LedgerTransaction(
            transaction_id=tx.transaction_id,
            transaction_date=tx.transaction_date,
            amount=tx.amount,
            description=tx.description,
            vendor_normalized=tx.vendor_normalized,
            account=tx.account,
            reference_no=tx.reference_no,
            is_reconciled=tx.is_reconciled,
            matched_invoice_id=tx.matched_invoice_id,
        )
        for tx in db_txs
    ]


def save_reconciliation_to_db(db: Session, result: ReconciliationResult) -> None:
    """Commit invoice, line items, and reconciliation result to the database."""
    # 1. Save or merge Invoice using unique reconciliation result ID
    db_inv = DBInvoice(
        id=result.id,
        vendor_name=result.invoice.vendor_name,
        invoice_id=result.invoice.invoice_id,
        invoice_date=result.invoice.invoice_date,
        due_date=result.invoice.due_date,
        subtotal=result.invoice.subtotal,
        tax=result.invoice.tax,
        total_amount=result.invoice.total_amount,
        currency=result.invoice.currency,
        raw_text=result.invoice.raw_text,
        confidence_score=result.invoice.confidence_score,
    )
    db.merge(db_inv)

    # 2. Save Line Items (clear existing if re-saving same id)
    db.query(DBLineItem).filter(DBLineItem.invoice_id == result.id).delete()
    for item in result.invoice.line_items:
        db_item = DBLineItem(
            invoice_id=result.id,
            description=item.description,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.total_price,
        )
        db.add(db_item)

    # 3. Save Reconciliation Record
    matched_id = result.matched_ledger_transaction.transaction_id if result.matched_ledger_transaction else None
    db_rec = DBReconciliation(
        id=result.id,
        invoice_id=result.id,
        matched_ledger_id=matched_id,
        status=result.status.value,
        confidence_score=result.confidence_score,
        match_type=result.match_type.value,
        reasons_json=json.dumps(result.reasons),
        discrepancies_json=json.dumps([d.model_dump() for d in result.discrepancies]),
        audit_trail_json=json.dumps([a.model_dump() for a in result.audit_trail]),
        alternative_candidates_json=json.dumps([c.model_dump() for c in result.alternative_candidates]),
        created_at=datetime.utcnow(),
    )
    db.merge(db_rec)

    # 4. If Auto-Reconciled, mark ledger entry as reconciled
    if result.status == ReconciliationStatus.AUTO_RECONCILED and matched_id:
        db_tx = db.query(DBLedgerTransaction).filter(DBLedgerTransaction.transaction_id == matched_id).first()
        if db_tx:
            db_tx.is_reconciled = True
            db_tx.matched_invoice_id = result.id

    db.commit()


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "AI Finance Controller",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/api/seed-ledger")
def reset_and_seed_ledger(force: bool = Query(default=True), db: Session = Depends(get_db)):
    """Reset or initialize the database with realistic synthetic bank ledger entries."""
    seed_database(db, force_reset=force)
    generate_all_samples()
    return {"message": "Ledger reset and re-seeded successfully with 10 synthetic transactions."}


@app.get("/api/ledger")
def get_ledger_entries(status: str = Query(default="all"), db: Session = Depends(get_db)):
    """List ledger transactions."""
    query = db.query(DBLedgerTransaction)
    if status == "unreconciled":
        query = query.filter(DBLedgerTransaction.is_reconciled == False)
    elif status == "reconciled":
        query = query.filter(DBLedgerTransaction.is_reconciled == True)

    entries = query.order_by(DBLedgerTransaction.transaction_date.desc()).all()
    return [
        {
            "transaction_id": tx.transaction_id,
            "transaction_date": tx.transaction_date,
            "amount": tx.amount,
            "description": tx.description,
            "vendor_normalized": tx.vendor_normalized,
            "account": tx.account,
            "reference_no": tx.reference_no,
            "is_reconciled": tx.is_reconciled,
            "matched_invoice_id": tx.matched_invoice_id,
        }
        for tx in entries
    ]


@app.post("/api/upload-invoice", response_model=ReconciliationResult)
async def upload_invoice(
    file: Optional[UploadFile] = File(None),
    raw_text: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Ingest an invoice document (PDF, TXT, Image, or Raw Text), execute the LangGraph
    orchestration agent, run hybrid matching against the bank ledger, and log audit trails.
    """
    filename = file.filename if file else "manual_text_input.txt"
    file_bytes = await file.read() if file else None

    if not file_bytes and not raw_text:
        raise HTTPException(status_code=400, detail="Either a file upload or raw_text must be provided.")

    # Get active ledger entries
    ledger_txs = get_active_ledger_transactions(db, include_reconciled=False)

    # Run LangGraph pipeline
    result = run_reconciliation_pipeline(
        filename=filename,
        raw_content=file_bytes,
        raw_text=raw_text,
        ledger_transactions=ledger_txs,
    )

    # Persist to database
    save_reconciliation_to_db(db, result)

    return result


@app.post("/api/reconcile-invoice", response_model=ReconciliationResult)
def reconcile_invoice_json(invoice: InvoiceData, db: Session = Depends(get_db)):
    """Directly reconcile a structured InvoiceData payload."""
    ledger_txs = get_active_ledger_transactions(db, include_reconciled=False)
    result = run_reconciliation_pipeline(invoice=invoice, ledger_transactions=ledger_txs)
    save_reconciliation_to_db(db, result)
    return result


@app.get("/api/reconciliation-results", response_model=List[ReconciliationResult])
def list_reconciliation_results(
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Retrieve all processed reconciliation results with audit logs."""
    query = db.query(DBReconciliation)
    if status and isinstance(status, str) and status != "All":
        query = query.filter(DBReconciliation.status == status)

    records = query.order_by(DBReconciliation.created_at.desc()).all()
    results: List[ReconciliationResult] = []

    for rec in records:
        inv = rec.invoice
        if not inv:
            continue

        # Optional search filter
        if search:
            s = search.lower()
            if s not in inv.vendor_name.lower() and s not in inv.invoice_id.lower():
                continue

        line_items = [
            {"description": item.description, "quantity": item.quantity, "unit_price": item.unit_price, "total_price": item.total_price}
            for item in inv.line_items
        ]

        invoice_data = InvoiceData(
            vendor_name=inv.vendor_name,
            invoice_id=inv.invoice_id,
            invoice_date=inv.invoice_date,
            due_date=inv.due_date,
            subtotal=inv.subtotal,
            tax=inv.tax,
            total_amount=inv.total_amount,
            currency=inv.currency,
            raw_text=inv.raw_text,
            confidence_score=inv.confidence_score,
            line_items=line_items,
        )

        matched_tx = None
        if rec.matched_ledger:
            matched_tx = LedgerTransaction(
                transaction_id=rec.matched_ledger.transaction_id,
                transaction_date=rec.matched_ledger.transaction_date,
                amount=rec.matched_ledger.amount,
                description=rec.matched_ledger.description,
                vendor_normalized=rec.matched_ledger.vendor_normalized,
                account=rec.matched_ledger.account,
                reference_no=rec.matched_ledger.reference_no,
                is_reconciled=rec.matched_ledger.is_reconciled,
                matched_invoice_id=rec.matched_ledger.matched_invoice_id,
            )

        reasons = json.loads(rec.reasons_json or "[]")
        discrepancies = [DiscrepancyDetail(**d) for d in json.loads(rec.discrepancies_json or "[]")]
        audit_trail = [AuditLogEntry(**a) for a in json.loads(rec.audit_trail_json or "[]")]
        alternatives = [MatchCandidate(**c) for c in json.loads(rec.alternative_candidates_json or "[]")]

        results.append(
            ReconciliationResult(
                id=rec.id,
                invoice=invoice_data,
                matched_ledger_transaction=matched_tx,
                status=ReconciliationStatus(rec.status),
                confidence_score=rec.confidence_score,
                match_type=MatchType(rec.match_type),
                reasons=reasons,
                discrepancies=discrepancies,
                alternative_candidates=alternatives,
                audit_trail=audit_trail,
                created_at=rec.created_at.isoformat() if rec.created_at else datetime.utcnow().isoformat(),
                resolved_by=rec.resolved_by,
                resolution_notes=rec.resolution_notes,
            )
        )

    return results


@app.post("/api/resolve-exception")
def resolve_exception(req: ManualResolutionRequest, db: Session = Depends(get_db)):
    """Handle finance controller manual override: approve match, link different ledger tx, or reject."""
    rec = db.query(DBReconciliation).filter(DBReconciliation.id == req.reconciliation_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Reconciliation record not found.")

    audit_trail = json.loads(rec.audit_trail_json or "[]")

    if req.action == "approve_match":
        rec.status = ReconciliationStatus.AUTO_RECONCILED.value
        rec.resolved_by = req.resolved_by
        rec.resolution_notes = req.notes or "Controller manually approved suggested match."
        if rec.matched_ledger_id:
            tx = db.query(DBLedgerTransaction).filter(DBLedgerTransaction.transaction_id == rec.matched_ledger_id).first()
            if tx:
                tx.is_reconciled = True
                tx.matched_invoice_id = rec.invoice_id

        audit_trail.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "stage": "Manual Controller Review",
                "status": "Auto-Reconciled",
                "decision": "Manual Approval by Finance Controller",
                "reasoning": req.notes or "Controller confirmed match after reviewing discrepancy notes.",
                "confidence": 1.0,
            }
        )

    elif req.action == "link_ledger":
        if not req.ledger_transaction_id:
            raise HTTPException(status_code=400, detail="ledger_transaction_id is required for link action.")
        tx = db.query(DBLedgerTransaction).filter(DBLedgerTransaction.transaction_id == req.ledger_transaction_id).first()
        if not tx:
            raise HTTPException(status_code=404, detail="Selected ledger transaction not found.")

        # Unlink previous if any
        if rec.matched_ledger_id and rec.matched_ledger_id != req.ledger_transaction_id:
            old_tx = db.query(DBLedgerTransaction).filter(DBLedgerTransaction.transaction_id == rec.matched_ledger_id).first()
            if old_tx:
                old_tx.is_reconciled = False
                old_tx.matched_invoice_id = None

        rec.matched_ledger_id = tx.transaction_id
        rec.status = ReconciliationStatus.AUTO_RECONCILED.value
        rec.match_type = MatchType.MANUAL_OVERRIDE.value
        rec.resolved_by = req.resolved_by
        rec.resolution_notes = req.notes or f"Manually linked to ledger entry {tx.transaction_id}."
        tx.is_reconciled = True
        tx.matched_invoice_id = rec.invoice_id

        audit_trail.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "stage": "Manual Controller Review",
                "status": "Auto-Reconciled",
                "decision": f"Manual Override Link to {tx.transaction_id}",
                "reasoning": req.notes or f"Controller explicitly mapped invoice to ledger transaction {tx.transaction_id}.",
                "confidence": 1.0,
            }
        )

    elif req.action == "reject":
        if rec.matched_ledger_id:
            tx = db.query(DBLedgerTransaction).filter(DBLedgerTransaction.transaction_id == rec.matched_ledger_id).first()
            if tx:
                tx.is_reconciled = False
                tx.matched_invoice_id = None
        rec.matched_ledger_id = None
        rec.status = ReconciliationStatus.FAILED.value
        rec.resolved_by = req.resolved_by
        rec.resolution_notes = req.notes or "Controller rejected match."

        audit_trail.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "stage": "Manual Controller Review",
                "status": "Failed",
                "decision": "Match Rejected by Controller",
                "reasoning": req.notes or "Controller flagged transaction as illegitimate or missing bank debit.",
                "confidence": 0.0,
            }
        )

    rec.audit_trail_json = json.dumps(audit_trail)
    db.commit()

    return {"message": "Exception resolved successfully", "status": rec.status}


@app.get("/api/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Calculate key financial reconciliation KPIs."""
    total_invoices = db.query(DBReconciliation).count()
    auto_reconciled = db.query(DBReconciliation).filter(DBReconciliation.status == ReconciliationStatus.AUTO_RECONCILED.value).count()
    needs_review = db.query(DBReconciliation).filter(DBReconciliation.status == ReconciliationStatus.NEEDS_REVIEW.value).count()
    failed = db.query(DBReconciliation).filter(DBReconciliation.status == ReconciliationStatus.FAILED.value).count()

    auto_rate = round((auto_reconciled / total_invoices * 100.0), 1) if total_invoices > 0 else 0.0

    invoices = db.query(DBInvoice).all()
    total_amount = sum(inv.total_amount for inv in invoices)

    reconciled_recs = db.query(DBReconciliation).filter(DBReconciliation.status == ReconciliationStatus.AUTO_RECONCILED.value).all()
    reconciled_inv_ids = [r.invoice_id for r in reconciled_recs]
    total_reconciled_amt = sum(inv.total_amount for inv in invoices if inv.id in reconciled_inv_ids)

    unreconciled_tx_count = db.query(DBLedgerTransaction).filter(DBLedgerTransaction.is_reconciled == False).count()

    return DashboardStats(
        total_invoices=total_invoices,
        auto_reconciled_count=auto_reconciled,
        needs_review_count=needs_review,
        failed_count=failed,
        auto_reconcile_rate=auto_rate,
        total_amount_processed=round(total_amount, 2),
        total_amount_reconciled=round(total_reconciled_amt, 2),
        unreconciled_ledger_count=unreconciled_tx_count,
    )


@app.get("/api/samples")
def list_sample_invoices():
    """List available sample invoices for quick testing."""
    return [
        {
            "id": item["filename_base"],
            "vendor": item["vendor"],
            "invoice_id": item["invoice_id"],
            "date": item["date"],
            "total": item["total"],
            "notes": item["notes"],
        }
        for item in SAMPLE_INVOICES_DATA
    ]


@app.post("/api/run-sample/{sample_id}")
async def run_sample_invoice(sample_id: str, db: Session = Depends(get_db)):
    """Execute reconciliation pipeline directly on a preloaded sample invoice."""
    matched_sample = next((s for s in SAMPLE_INVOICES_DATA if s["filename_base"] == sample_id), None)
    if not matched_sample:
        raise HTTPException(status_code=404, detail="Sample invoice not found.")

    txt_path = os.path.join(SAMPLE_DIR, f"{sample_id}.txt")
    if not os.path.exists(txt_path):
        generate_all_samples()

    with open(txt_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    ledger_txs = get_active_ledger_transactions(db, include_reconciled=False)
    result = run_reconciliation_pipeline(
        filename=f"{sample_id}.txt",
        raw_text=raw_text,
        ledger_transactions=ledger_txs,
    )
    save_reconciliation_to_db(db, result)
    return result


@app.get("/api/export/csv")
def export_reconciliation_csv(db: Session = Depends(get_db)):
    """Export reconciliation ledger to CSV."""
    records = db.query(DBReconciliation).order_by(DBReconciliation.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Reconciliation ID",
        "Invoice ID",
        "Vendor Name",
        "Invoice Date",
        "Invoice Amount",
        "Status",
        "Confidence Score",
        "Match Type",
        "Matched Ledger Transaction ID",
        "Matched Ledger Desc",
        "Matched Ledger Amount",
        "Matched Ledger Date",
        "Resolved By",
        "Resolution Notes",
        "Created At",
    ])

    for r in records:
        inv = r.invoice
        tx = r.matched_ledger
        writer.writerow([
            r.id,
            inv.invoice_id if inv else "",
            inv.vendor_name if inv else "",
            inv.invoice_date if inv else "",
            f"{inv.total_amount:.2f}" if inv else "",
            r.status,
            f"{r.confidence_score * 100:.1f}%",
            r.match_type,
            tx.transaction_id if tx else "",
            tx.description if tx else "",
            f"{tx.amount:.2f}" if tx else "",
            tx.transaction_date if tx else "",
            r.resolved_by or "",
            r.resolution_notes or "",
            r.created_at.isoformat() if r.created_at else "",
        ])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=reconciliation_report.csv"},
    )


@app.get("/api/export/json")
def export_reconciliation_json(db: Session = Depends(get_db)):
    """Export complete audit ledger to JSON."""
    results = list_reconciliation_results(status=None, search=None, db=db)
    content = json.dumps([r.model_dump() for r in results], indent=2)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=reconciliation_audit_log.json"},
    )


# Serve Static Frontend if built
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(FRONTEND_DIST):
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = os.path.join(FRONTEND_DIST, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))

