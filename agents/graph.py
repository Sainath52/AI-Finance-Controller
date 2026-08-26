"""
LangGraph StateGraph orchestrator for the AI Finance Controller.
Coordinates document ingestion, schema extraction, hybrid reconciliation engine,
LLM reasoning fallback, and structured audit trail generation.
"""

import uuid
import json
import os
from datetime import datetime
from typing import List, Optional, Dict, Any, TypedDict

from langgraph.graph import StateGraph, END

from models.schemas import (
    InvoiceData,
    LedgerTransaction,
    MatchCandidate,
    MatchType,
    ReconciliationStatus,
    ReconciliationResult,
    AuditLogEntry,
    DiscrepancyDetail,
)
from utils.reconciler import HybridReconciliationEngine
from utils.ocr_extractor import SchemaExtractor
from agents.prompts import AMBIGUOUS_REASONING_PROMPT


class ControllerAgentState(TypedDict):
    reconciliation_id: str
    filename: Optional[str]
    raw_content: Optional[bytes]
    raw_text: Optional[str]
    invoice: Optional[InvoiceData]
    ledger_transactions: List[LedgerTransaction]
    best_candidate: Optional[MatchCandidate]
    alternative_candidates: List[MatchCandidate]
    status: ReconciliationStatus
    match_type: MatchType
    confidence_score: float
    reasons: List[str]
    discrepancies: List[DiscrepancyDetail]
    audit_trail: List[AuditLogEntry]
    error: Optional[str]


# Helper instances
extractor = SchemaExtractor()
reconciliation_engine = HybridReconciliationEngine(date_window_days=3, min_auto_reconcile_score=0.85)


def ingest_and_extract_node(state: ControllerAgentState) -> Dict[str, Any]:
    """Node 1: Ingest document, perform OCR/text extraction, and parse into Pydantic InvoiceData."""
    audit_trail = list(state.get("audit_trail", []))
    filename = state.get("filename") or "invoice_document"
    raw_content = state.get("raw_content")
    raw_text = state.get("raw_text")

    try:
        if raw_content:
            invoice = extractor.extract_from_file_bytes(filename, raw_content)
        elif raw_text:
            invoice = extractor.extract_from_text(raw_text)
        elif state.get("invoice"):
            invoice = state["invoice"]
        else:
            raise ValueError("No invoice file, text, or structured data provided.")

        audit_trail.append(
            AuditLogEntry(
                stage="Document Ingestion & OCR",
                status="Success",
                decision="Extracted structured invoice schema",
                reasoning=(
                    f"Successfully parsed invoice from '{filename}'. Identified vendor: '{invoice.vendor_name}', "
                    f"Invoice ID: '{invoice.invoice_id}', Date: {invoice.invoice_date}, "
                    f"Total Amount: {invoice.currency} {invoice.total_amount:,.2f} with {len(invoice.line_items)} line items."
                ),
                confidence=invoice.confidence_score,
                metadata={"vendor": invoice.vendor_name, "invoice_id": invoice.invoice_id, "amount": invoice.total_amount},
            )
        )

        return {
            "invoice": invoice,
            "raw_text": invoice.raw_text,
            "audit_trail": audit_trail,
        }
    except Exception as e:
        audit_trail.append(
            AuditLogEntry(
                stage="Document Ingestion & OCR",
                status="Error",
                decision="Extraction failed",
                reasoning=f"Failed to extract structured data: {str(e)}",
                confidence=0.0,
            )
        )
        return {
            "error": str(e),
            "status": ReconciliationStatus.FAILED,
            "audit_trail": audit_trail,
        }


def matching_rules_node(state: ControllerAgentState) -> Dict[str, Any]:
    """Node 2: Run deterministic + RapidFuzz hybrid matching against ledger transactions."""
    invoice = state.get("invoice")
    ledger_txs = state.get("ledger_transactions", [])
    audit_trail = list(state.get("audit_trail", []))

    if not invoice:
        return {"status": ReconciliationStatus.FAILED}

    best_candidate, alternatives, status = reconciliation_engine.find_matches(
        invoice=invoice, ledger_transactions=ledger_txs, top_k=3
    )

    reasons = best_candidate.reasons if best_candidate else ["No suitable matching bank transaction found."]
    discrepancies = best_candidate.discrepancies if best_candidate else []
    confidence = best_candidate.match_score.total_score if best_candidate else 0.0
    match_type = best_candidate.match_type if best_candidate else MatchType.NO_MATCH

    # Append audit trail
    if best_candidate:
        audit_trail.append(
            AuditLogEntry(
                stage="Rule & Fuzzy Matching Engine",
                status="Evaluated",
                decision=f"Identified candidate {best_candidate.ledger_transaction.transaction_id} (Score: {int(confidence * 100)}%)",
                reasoning=(
                    f"Evaluated {len(ledger_txs)} ledger entries. Top candidate: '{best_candidate.ledger_transaction.description}' "
                    f"on {best_candidate.ledger_transaction.transaction_date} for ${best_candidate.ledger_transaction.amount:,.2f}. "
                    f"Match Factors: Amount match: {int(best_candidate.match_score.amount_score * 100)}%, "
                    f"Vendor fuzzy similarity: {int(best_candidate.match_score.vendor_fuzzy_score * 100)}%, "
                    f"Date proximity: {best_candidate.date_diff_days} day(s) difference."
                ),
                confidence=confidence,
                metadata={
                    "ledger_id": best_candidate.ledger_transaction.transaction_id,
                    "scores": best_candidate.match_score.model_dump(),
                },
            )
        )
    else:
        audit_trail.append(
            AuditLogEntry(
                stage="Rule & Fuzzy Matching Engine",
                status="No Match",
                decision="No matching transaction found in ledger",
                reasoning=f"Searched {len(ledger_txs)} active ledger entries. No transaction matched amount ${invoice.total_amount:,.2f} within allowable date/vendor thresholds.",
                confidence=0.0,
            )
        )

    return {
        "best_candidate": best_candidate,
        "alternative_candidates": alternatives,
        "status": status,
        "match_type": match_type,
        "confidence_score": confidence,
        "reasons": reasons,
        "discrepancies": discrepancies,
        "audit_trail": audit_trail,
    }


def llm_reasoning_node(state: ControllerAgentState) -> Dict[str, Any]:
    """Node 3: LLM reasoning fallback for ambiguous matches, vendor aliases, or minor variance."""
    invoice = state.get("invoice")
    best_candidate = state.get("best_candidate")
    alternatives = state.get("alternative_candidates", [])
    audit_trail = list(state.get("audit_trail", []))

    if not invoice or not best_candidate:
        return {}

    # Format summaries for reasoning
    items_summary = ", ".join([f"{item.description} (${item.total_price})" for item in invoice.line_items[:4]])
    candidates_list = [best_candidate] + alternatives
    candidates_desc = "\n".join(
        [
            f"- Candidate {idx + 1}: ID={c.ledger_transaction.transaction_id}, Desc='{c.ledger_transaction.description}', "
            f"Date={c.ledger_transaction.transaction_date}, Amount=${c.ledger_transaction.amount}, "
            f"Score={c.match_score.total_score:.2f}, Discrepancies={[d.message for d in c.discrepancies]}"
            for idx, c in enumerate(candidates_list)
        ]
    )

    groq_key = os.environ.get("GROQ_API_KEY", "")
    openai_key = os.environ.get("OPENAI_API_KEY")
    reasoning_text = ""

    prompt = AMBIGUOUS_REASONING_PROMPT.format(
        vendor_name=invoice.vendor_name,
        invoice_id=invoice.invoice_id,
        invoice_date=invoice.invoice_date,
        currency=invoice.currency,
        total_amount=invoice.total_amount,
        line_items_summary=items_summary or "General invoice line items",
        candidates_summary=candidates_desc,
    )

    if groq_key:
        try:
            import groq
            client = groq.Groq(api_key=groq_key)
            response = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {"role": "system", "content": "You are a Senior Financial Controller providing brief, auditable reconciliation explanations."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=300,
            )
            reasoning_text = response.choices[0].message.content or ""
        except Exception as e:
            print(f"[Groq LLM reasoning fallback note: {e}]")

    if not reasoning_text and openai_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            reasoning_text = response.choices[0].message.content or ""
        except Exception as e:
            print(f"[OpenAI reasoning fallback note: {e}]")

    if not reasoning_text:
        # High quality heuristic reasoning synthesis
        disc_text = "; ".join([d.message for d in best_candidate.discrepancies]) or "Slight naming/timing ambiguity"
        reasoning_text = (
            f"Evaluated vendor relation: Invoice vendor '{invoice.vendor_name}' compared against bank memo "
            f"'{best_candidate.ledger_transaction.description}'. Amount is within tolerance (${best_candidate.amount_diff:,.2f} diff) "
            f"and posted with a {best_candidate.date_diff_days}-day offset. Flagged for review due to: {disc_text}."
        )

    audit_trail.append(
        AuditLogEntry(
            stage="AI Discrepancy & Reasoning Analysis",
            status="Reviewed",
            decision=f"Classified as {state.get('status', ReconciliationStatus.NEEDS_REVIEW)}",
            reasoning=reasoning_text,
            confidence=state.get("confidence_score", 0.75),
            metadata={"llm_assisted": bool(groq_key or openai_key)},
        )
    )

    return {
        "audit_trail": audit_trail,
    }


def audit_and_classify_node(state: ControllerAgentState) -> Dict[str, Any]:
    """Node 4: Finalize audit classification and attach comprehensive controller sign-off trail."""
    audit_trail = list(state.get("audit_trail", []))
    status = state.get("status", ReconciliationStatus.FAILED)
    best_candidate = state.get("best_candidate")
    confidence = state.get("confidence_score", 0.0)

    if status == ReconciliationStatus.AUTO_RECONCILED:
        decision_msg = "Auto-Reconciliation Approved"
        justification = (
            f"All financial controls satisfied: Exact amount match (${best_candidate.ledger_transaction.amount:,.2f}), "
            f"high vendor confidence ({int(best_candidate.match_score.vendor_fuzzy_score * 100)}%), and date within window "
            f"({best_candidate.date_diff_days} day diff). Ledger entry {best_candidate.ledger_transaction.transaction_id} linked."
        )
    elif status == ReconciliationStatus.NEEDS_REVIEW:
        decision_msg = "Flagged for Finance Controller Review"
        justification = (
            f"Matched candidate {best_candidate.ledger_transaction.transaction_id} with moderate confidence ({int(confidence * 100)}%). "
            f"Requires one-click manual confirmation due to minor vendor variance or date clearance timing."
        )
    else:
        decision_msg = "Reconciliation Failed / Unmatched"
        justification = "No corresponding bank ledger transaction met the minimum reconciliation criteria."

    audit_trail.append(
        AuditLogEntry(
            stage="Final Controller Audit Classification",
            status=status.value,
            decision=decision_msg,
            reasoning=justification,
            confidence=confidence,
        )
    )

    return {
        "status": status,
        "audit_trail": audit_trail,
    }


def route_matching_decision(state: ControllerAgentState) -> str:
    """Routing logic based on matching engine outcome."""
    if state.get("error") or state.get("status") == ReconciliationStatus.FAILED:
        return "audit_and_classify"
    if state.get("status") == ReconciliationStatus.AUTO_RECONCILED:
        return "audit_and_classify"
    return "llm_reasoning"


def create_reconciliation_graph() -> StateGraph:
    """Build the LangGraph workflow graph."""
    workflow = StateGraph(ControllerAgentState)

    # Register Nodes
    workflow.add_node("ingest_and_extract", ingest_and_extract_node)
    workflow.add_node("matching_rules", matching_rules_node)
    workflow.add_node("llm_reasoning", llm_reasoning_node)
    workflow.add_node("audit_and_classify", audit_and_classify_node)

    # Define Edges
    workflow.set_entry_point("ingest_and_extract")
    workflow.add_edge("ingest_and_extract", "matching_rules")

    workflow.add_conditional_edges(
        "matching_rules",
        route_matching_decision,
        {
            "audit_and_classify": "audit_and_classify",
            "llm_reasoning": "llm_reasoning",
        },
    )

    workflow.add_edge("llm_reasoning", "audit_and_classify")
    workflow.add_edge("audit_and_classify", END)

    return workflow.compile()


# Global compiled graph
reconciliation_pipeline = create_reconciliation_graph()


def run_reconciliation_pipeline(
    filename: Optional[str] = None,
    raw_content: Optional[bytes] = None,
    raw_text: Optional[str] = None,
    invoice: Optional[InvoiceData] = None,
    ledger_transactions: Optional[List[LedgerTransaction]] = None,
) -> ReconciliationResult:
    """
    Synchronous execution wrapper for the LangGraph reconciliation pipeline.
    """
    rec_id = f"REC-{uuid.uuid4().hex[:10].upper()}"
    initial_state: ControllerAgentState = {
        "reconciliation_id": rec_id,
        "filename": filename,
        "raw_content": raw_content,
        "raw_text": raw_text,
        "invoice": invoice,
        "ledger_transactions": ledger_transactions or [],
        "best_candidate": None,
        "alternative_candidates": [],
        "status": ReconciliationStatus.FAILED,
        "match_type": MatchType.NO_MATCH,
        "confidence_score": 0.0,
        "reasons": [],
        "discrepancies": [],
        "audit_trail": [],
        "error": None,
    }

    final_state = reconciliation_pipeline.invoke(initial_state)

    matched_ledger = (
        final_state["best_candidate"].ledger_transaction
        if final_state.get("best_candidate")
        and final_state.get("status") in [ReconciliationStatus.AUTO_RECONCILED, ReconciliationStatus.NEEDS_REVIEW]
        else None
    )

    return ReconciliationResult(
        id=rec_id,
        invoice=final_state["invoice"]
        or InvoiceData(
            vendor_name="Unknown",
            invoice_id=f"ERR-{rec_id}",
            invoice_date=datetime.now().strftime("%Y-%m-%d"),
            total_amount=0.0,
        ),
        matched_ledger_transaction=matched_ledger,
        status=final_state["status"],
        confidence_score=round(final_state.get("confidence_score", 0.0), 4),
        match_type=final_state.get("match_type", MatchType.NO_MATCH),
        reasons=final_state.get("reasons", []),
        discrepancies=final_state.get("discrepancies", []),
        alternative_candidates=final_state.get("alternative_candidates", []),
        audit_trail=final_state.get("audit_trail", []),
        created_at=datetime.utcnow().isoformat(),
    )
