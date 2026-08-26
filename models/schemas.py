"""
Pydantic schemas and models for the AI Finance Controller.
Defines data structures for invoice extraction, ledger transactions,
hybrid matching results, and audit logging.
"""

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ReconciliationStatus(str, Enum):
    AUTO_RECONCILED = "Auto-Reconciled"
    NEEDS_REVIEW = "Needs Review"
    FAILED = "Failed"


class MatchType(str, Enum):
    EXACT = "exact"
    FUZZY = "fuzzy"
    LLM_ASSISTED = "llm_assisted"
    MANUAL_OVERRIDE = "manual_override"
    NO_MATCH = "no_match"


class LineItem(BaseModel):
    description: str = Field(..., description="Description of the service or product")
    quantity: float = Field(default=1.0, description="Quantity of items")
    unit_price: float = Field(default=0.0, description="Unit price per item")
    total_price: float = Field(..., description="Total price for this line item")


class InvoiceData(BaseModel):
    vendor_name: str = Field(..., description="Name of the vendor/supplier on the invoice")
    invoice_id: str = Field(..., description="Invoice or reference identification number")
    invoice_date: str = Field(..., description="Date of the invoice (YYYY-MM-DD format)")
    due_date: Optional[str] = Field(None, description="Payment due date if available (YYYY-MM-DD)")
    line_items: List[LineItem] = Field(default_factory=list, description="Extracted individual line items")
    subtotal: Optional[float] = Field(None, description="Subtotal amount before taxes")
    tax: Optional[float] = Field(None, description="Tax amount")
    total_amount: float = Field(..., description="Total gross invoice amount")
    currency: str = Field(default="USD", description="Currency code (e.g. USD, EUR, INR)")
    raw_text: Optional[str] = Field(None, description="Raw OCR or extracted text")
    confidence_score: float = Field(default=1.0, description="Confidence of extraction (0.0 - 1.0)")


class LedgerTransaction(BaseModel):
    transaction_id: str = Field(..., description="Unique bank/ledger transaction ID")
    transaction_date: str = Field(..., description="Date posted on bank/ledger (YYYY-MM-DD)")
    amount: float = Field(..., description="Posted transaction amount")
    description: str = Field(..., description="Raw bank statement description")
    vendor_normalized: Optional[str] = Field(None, description="Normalized or recognized vendor name")
    account: str = Field(default="Operating Checking - 4092", description="General ledger account")
    reference_no: Optional[str] = Field(None, description="Bank transaction reference code")
    is_reconciled: bool = Field(default=False, description="Whether transaction is already reconciled")
    matched_invoice_id: Optional[str] = Field(None, description="Associated invoice ID if reconciled")


class DiscrepancyDetail(BaseModel):
    field: str
    invoice_val: Any
    ledger_val: Any
    message: str


class MatchScoreBreakdown(BaseModel):
    amount_score: float = Field(default=0.0, description="Score based on amount equality (0.0 to 1.0)")
    vendor_fuzzy_score: float = Field(default=0.0, description="RapidFuzz vendor name similarity (0.0 to 1.0)")
    date_proximity_score: float = Field(default=0.0, description="Date closeness score within ±3 days window")
    reference_score: float = Field(default=0.0, description="Invoice ID / Reference match score")
    total_score: float = Field(default=0.0, description="Weighted composite confidence score")


class MatchCandidate(BaseModel):
    ledger_transaction: LedgerTransaction
    match_score: MatchScoreBreakdown
    match_type: MatchType
    date_diff_days: int
    amount_diff: float
    reasons: List[str] = Field(default_factory=list)
    discrepancies: List[DiscrepancyDetail] = Field(default_factory=list)


class AuditLogEntry(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    stage: str = Field(..., description="Pipeline stage (e.g. Ingestion, Matching, LLM Reasoning, Review)")
    status: str = Field(..., description="Status at this step")
    decision: str = Field(..., description="High-level decision or action taken")
    reasoning: str = Field(..., description="Detailed explanation / chain-of-thought rationale")
    confidence: Optional[float] = Field(None, description="Confidence rating at this stage")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ReconciliationResult(BaseModel):
    id: str
    invoice: InvoiceData
    matched_ledger_transaction: Optional[LedgerTransaction] = None
    status: ReconciliationStatus
    confidence_score: float
    match_type: MatchType
    reasons: List[str] = Field(default_factory=list)
    discrepancies: List[DiscrepancyDetail] = Field(default_factory=list)
    alternative_candidates: List[MatchCandidate] = Field(default_factory=list)
    audit_trail: List[AuditLogEntry] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    resolved_by: Optional[str] = None
    resolution_notes: Optional[str] = None


class ManualResolutionRequest(BaseModel):
    reconciliation_id: str
    action: str = Field(..., description="'approve_match', 'link_ledger', 'reject', 'mark_manual'")
    ledger_transaction_id: Optional[str] = None
    notes: Optional[str] = None
    resolved_by: str = Field(default="Finance Controller")


class DashboardStats(BaseModel):
    total_invoices: int
    auto_reconciled_count: int
    needs_review_count: int
    failed_count: int
    auto_reconcile_rate: float
    total_amount_processed: float
    total_amount_reconciled: float
    unreconciled_ledger_count: int
