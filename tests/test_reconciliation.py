"""
Unit and Integration Tests for AI Finance Controller.
Tests:
- Hybrid matching engine (Exact amount, RapidFuzz token/partial ratio, Date tolerance)
- Alias normalization (AWS, Slack, GitHub, Uber)
- LangGraph orchestration pipeline
- FastAPI endpoints with TestClient
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from models.schemas import (
    InvoiceData,
    LineItem,
    LedgerTransaction,
    ReconciliationStatus,
    MatchType,
)
from utils.reconciler import (
    HybridReconciliationEngine,
    calculate_vendor_similarity,
    calculate_amount_score,
    calculate_date_proximity_score,
    clean_vendor_name,
)
from agents.graph import run_reconciliation_pipeline
from backend.main import app
from backend.database import init_db, SessionLocal
from backend.seed_data import seed_database


@pytest.fixture(scope="module")
def setup_db():
    init_db()
    with SessionLocal() as db:
        seed_database(db, force_reset=True)
    yield


def test_clean_vendor_name():
    assert clean_vendor_name("Amazon Web Services, Inc.") == "amazon web services"
    assert clean_vendor_name("Slack Technologies LLC") == "slack technologies"
    assert clean_vendor_name("UBER *TRIP 08/18") == "uber trip 08 18"


def test_vendor_similarity_and_aliases():
    # Direct alias resolution
    score_aws = calculate_vendor_similarity("AWS", "DEBIT - AWS CLOUD SVCS - REF: INV-98213")
    assert score_aws >= 0.85

    # Rapidfuzz partial and token sort
    score_slack = calculate_vendor_similarity("Slack Technologies Inc.", "ACH WITHDRAWAL - SLACK TECHNOLOGIES INC")
    assert score_slack >= 0.85

    score_adobe = calculate_vendor_similarity("Adobe Systems Incorporated", "ADOBE *CREATIVE CLOUD WWW.ADOBE.COM")
    assert score_adobe >= 0.80

    # Unrelated vendor
    score_diff = calculate_vendor_similarity("Quantum AI Labs", "DEBIT - AWS CLOUD SVCS")
    assert score_diff < 0.40


def test_amount_scoring():
    exact_score, diff = calculate_amount_score(142.50, 142.50)
    assert exact_score == 1.0
    assert diff == 0.0

    near_score, near_diff = calculate_amount_score(142.50, 142.60)
    assert near_score == 0.85
    assert round(near_diff, 2) == 0.10

    mismatch_score, mis_diff = calculate_amount_score(142.50, 999.00)
    assert mismatch_score == 0.0
    assert mis_diff == 856.50


def test_date_proximity_scoring():
    score_0d, diff_0 = calculate_date_proximity_score("2026-08-15", "2026-08-15", max_window_days=3)
    assert score_0d == 1.0
    assert diff_0 == 0

    score_1d, diff_1 = calculate_date_proximity_score("2026-08-15", "2026-08-16", max_window_days=3)
    assert score_1d == 0.90
    assert diff_1 == 1

    score_out, diff_out = calculate_date_proximity_score("2026-08-01", "2026-08-15", max_window_days=3)
    assert score_out <= 0.30
    assert diff_out == 14


def test_hybrid_engine_high_confidence():
    engine = HybridReconciliationEngine(date_window_days=3, min_auto_reconcile_score=0.85)

    invoice = InvoiceData(
        vendor_name="Amazon Web Services, Inc.",
        invoice_id="INV-98213",
        invoice_date="2026-08-15",
        total_amount=142.50,
        currency="USD",
    )

    ledger_tx = LedgerTransaction(
        transaction_id="TXN-001",
        transaction_date="2026-08-15",
        amount=142.50,
        description="DEBIT - AWS CLOUD SVCS - REF: INV-98213",
        reference_no="INV-98213",
    )

    best, alts, status = engine.find_matches(invoice, [ledger_tx])
    assert best is not None
    assert status == ReconciliationStatus.AUTO_RECONCILED
    assert best.match_score.total_score >= 0.85
    assert len(best.discrepancies) == 0


def test_hybrid_engine_needs_review_ambiguity():
    engine = HybridReconciliationEngine(date_window_days=3, min_auto_reconcile_score=0.85)

    invoice = InvoiceData(
        vendor_name="GitHub Inc.",
        invoice_id="GH-8491",
        invoice_date="2026-08-22",
        total_amount=420.00,
        currency="USD",
    )

    # 2 competing transactions with same amount
    tx1 = LedgerTransaction(
        transaction_id="TXN-GH-1",
        transaction_date="2026-08-23",
        amount=420.00,
        description="DEBIT - GITHUB_COM_SUB_8491 SAN FRANCISCO CA",
        reference_no="GH-8491",
    )
    tx2 = LedgerTransaction(
        transaction_id="TXN-GL-2",
        transaction_date="2026-08-22",
        amount=420.00,
        description="DEBIT - GITLAB ENTERPRISE SERVICES",
        reference_no="GL-3321",
    )

    best, alts, status = engine.find_matches(invoice, [tx1, tx2])
    assert best is not None
    assert best.ledger_transaction.transaction_id == "TXN-GH-1"


def test_langgraph_pipeline_execution():
    raw_invoice_text = """
    ===========================================================
    INVOICE: INV-98213
    ===========================================================
    Vendor: Amazon Web Services, Inc.
    Invoice Date: 2026-08-15
    Due Date: 2026-09-15
    Currency: USD
    -----------------------------------------------------------
    LINE ITEMS:
    Amazon EC2 Elastic Compute Cloud   1 x $  110.00 = $  110.00
    Amazon S3 Standard Storage         1 x $   20.00 = $   20.00
    AWS Data Transfer Out              1 x $   12.50 = $   12.50
    -----------------------------------------------------------
    Subtotal: $142.50
    Tax: $0.00
    Total Amount Due: $142.50
    """

    ledger_tx = LedgerTransaction(
        transaction_id="TXN-2026-0801",
        transaction_date="2026-08-15",
        amount=142.50,
        description="DEBIT - AWS CLOUD SVCS - REF: INV-98213",
        reference_no="INV-98213",
    )

    result = run_reconciliation_pipeline(
        filename="aws_test.txt",
        raw_text=raw_invoice_text,
        ledger_transactions=[ledger_tx],
    )

    assert result.status == ReconciliationStatus.AUTO_RECONCILED
    assert result.invoice.total_amount == 142.50
    assert result.matched_ledger_transaction is not None
    assert result.matched_ledger_transaction.transaction_id == "TXN-2026-0801"
    assert len(result.audit_trail) >= 3


def test_fastapi_endpoints(setup_db):
    client = TestClient(app)

    # 1. Health check
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

    # 2. Get ledger
    res = client.get("/api/ledger")
    assert res.status_code == 200
    ledger_items = res.json()
    assert len(ledger_items) >= 5

    # 3. Stats
    res = client.get("/api/stats")
    assert res.status_code == 200
    stats = res.json()
    assert "auto_reconcile_rate" in stats

    # 4. Run sample invoice
    res = client.post("/api/run-sample/01_aws_cloud_invoice")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == ReconciliationStatus.AUTO_RECONCILED.value
    assert data["matched_ledger_transaction"]["transaction_id"] == "TXN-2026-0801"

    # 5. List results
    res = client.get("/api/reconciliation-results")
    assert res.status_code == 200
    results = res.json()
    assert len(results) >= 1

    # 6. CSV Export
    res = client.get("/api/export/csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
