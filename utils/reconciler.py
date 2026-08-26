"""
Reconciliation and matching engine for AI Finance Controller.
Implements hybrid exact amount, date window (±3 days), RapidFuzz vendor matching,
and multi-factor candidate scoring.
"""

import re
from datetime import datetime, date
from typing import List, Optional, Tuple
from rapidfuzz import fuzz, utils as fuzz_utils

from models.schemas import (
    InvoiceData,
    LedgerTransaction,
    MatchCandidate,
    MatchScoreBreakdown,
    MatchType,
    ReconciliationStatus,
    DiscrepancyDetail,
)

# Known enterprise vendor aliases for robust mapping
VENDOR_ALIASES = {
    "aws": ["amazon web services", "amzn web services", "aws cloud svcs", "amzn aws", "amazon aws"],
    "amazon": ["amzn mktp", "amazon.com", "amazon pay", "amzn digital", "amazon web services"],
    "google": ["google cloud", "google workspace", "google gsuite", "google llc", "goog gsuite", "google ads"],
    "microsoft": ["msft azure", "microsoft 365", "msft office", "microsoft corporation", "msft cloud"],
    "uber": ["uber bv", "uber *trip", "uber eats", "uber technologies", "uber ride"],
    "github": ["github inc", "github.com", "github enterprise", "github_sub"],
    "slack": ["slack technologies", "slack inc", "slack enterprise", "slack sub"],
    "adobe": ["adobe systems", "adobe creative cloud", "adobe inc", "adobestore"],
    "zoom": ["zoom video communications", "zoom.us", "zoom communications"],
    "stripe": ["stripe payments", "stripe transfer", "stripe payout"],
    "salesforce": ["salesforce.com", "salesforce crm", "salesforce enterprise"],
    "atlassian": ["atlassian jira", "atlassian confluence", "atlassian sydney"],
    "apple": ["apple.com/bill", "apple inc", "apple store", "apple cloud"],
}

LEGAL_SUFFIX_REGEX = re.compile(
    r"\b(inc|corp|corporation|llc|ltd|limited|gmbh|bv|co|pvt|pty|sa|plc)\b",
    re.IGNORECASE,
)
CLEAN_PUNCT_REGEX = re.compile(r"[\*#\-_/,\.:;]")


def clean_vendor_name(name: str) -> str:
    """Normalize vendor string by stripping common noise and legal suffixes."""
    if not name:
        return ""
    text = name.lower().strip()
    text = CLEAN_PUNCT_REGEX.sub(" ", text)
    text = LEGAL_SUFFIX_REGEX.sub("", text)
    text = " ".join(text.split())
    return text


def check_alias_match(vendor_a: str, vendor_b: str) -> float:
    """Check if two vendor names map to the same known alias cluster."""
    norm_a = clean_vendor_name(vendor_a)
    norm_b = clean_vendor_name(vendor_b)

    if norm_a == norm_b and norm_a:
        return 1.0

    for canonical, aliases in VENDOR_ALIASES.items():
        all_names = [canonical] + aliases
        match_a = any(alias in norm_a or norm_a in alias for alias in all_names)
        match_b = any(alias in norm_b or norm_b in alias for alias in all_names)
        if match_a and match_b:
            return 0.95

    return 0.0


def calculate_vendor_similarity(invoice_vendor: str, ledger_description: str) -> float:
    """
    Calculate fuzzy vendor similarity using RapidFuzz token sort and partial ratio,
    supplemented by known alias clusters.
    """
    alias_score = check_alias_match(invoice_vendor, ledger_description)
    if alias_score > 0.85:
        return alias_score

    norm_inv = clean_vendor_name(invoice_vendor)
    norm_led = clean_vendor_name(ledger_description)

    if not norm_inv or not norm_led:
        return 0.0

    # Token sort ratio handles rearranged words
    token_sort = fuzz.token_sort_ratio(norm_inv, norm_led, processor=fuzz_utils.default_process) / 100.0
    # Partial ratio handles substring mentions (e.g. "AWS CLOUD" in "DEBIT - AWS CLOUD SVCS - 9801")
    partial_ratio = fuzz.partial_ratio(norm_inv, norm_led, processor=fuzz_utils.default_process) / 100.0
    # Token set ratio handles subsets
    token_set = fuzz.token_set_ratio(norm_inv, norm_led, processor=fuzz_utils.default_process) / 100.0

    # Combine metrics: favor high token_set/partial when substrings exist
    best_score = max(token_sort, partial_ratio * 0.92, token_set)
    return round(best_score, 4)


def parse_date(date_str: str) -> Optional[date]:
    """Parse common date formats to date object."""
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            pass
    return None


def calculate_date_proximity_score(invoice_date_str: str, ledger_date_str: str, max_window_days: int = 3) -> Tuple[float, int]:
    """
    Score date closeness.
    0 days = 1.0
    1 day = 0.9
    2 days = 0.75
    3 days = 0.6
    > 3 days = decays toward 0.0
    """
    inv_d = parse_date(invoice_date_str)
    led_d = parse_date(ledger_date_str)

    if not inv_d or not led_d:
        return 0.5, 999  # Neutral fallback if date parsing failed

    diff_days = abs((led_d - inv_d).days)

    if diff_days == 0:
        score = 1.0
    elif diff_days == 1:
        score = 0.90
    elif diff_days == 2:
        score = 0.75
    elif diff_days <= max_window_days:
        score = 0.60
    elif diff_days <= max_window_days + 4:
        score = 0.30
    else:
        score = 0.05

    return round(score, 4), diff_days


def calculate_amount_score(invoice_amount: float, ledger_amount: float) -> Tuple[float, float]:
    """
    Evaluate amount match.
    Exact to cent = 1.0
    Within $0.50 or < 0.5% variance = 0.85
    Within $2.00 = 0.50
    Otherwise decays.
    """
    inv_amt = abs(float(invoice_amount))
    led_amt = abs(float(ledger_amount))
    diff = abs(inv_amt - led_amt)

    if diff < 0.01:
        return 1.0, diff
    elif diff <= 0.50 or (inv_amt > 0 and (diff / inv_amt) < 0.005):
        return 0.85, diff
    elif diff <= 2.00 or (inv_amt > 0 and (diff / inv_amt) < 0.02):
        return 0.50, diff
    else:
        # Large variance
        return 0.0, diff


def calculate_reference_score(invoice_id: str, ledger_desc: str, ledger_ref: Optional[str]) -> float:
    """Check if invoice ID appears anywhere in bank ledger memo or reference number."""
    if not invoice_id:
        return 0.0
    clean_id = re.sub(r"[^a-zA-Z0-9]", "", invoice_id).lower()
    if len(clean_id) < 3:
        return 0.0

    target = f"{ledger_desc or ''} {ledger_ref or ''}".lower()
    target_clean = re.sub(r"[^a-zA-Z0-9]", "", target)

    if clean_id in target_clean:
        return 1.0
    return 0.0


class HybridReconciliationEngine:
    """
    Core matching engine combining:
    1. Exact amount + date window (±3 days)
    2. RapidFuzz vendor similarity
    3. Invoice ID/Reference matching
    4. Composite confidence scoring and discrepancy analysis
    """

    def __init__(self, date_window_days: int = 3, min_auto_reconcile_score: float = 0.85):
        self.date_window_days = date_window_days
        self.min_auto_reconcile_score = min_auto_reconcile_score

    def score_candidate(self, invoice: InvoiceData, ledger_tx: LedgerTransaction) -> MatchCandidate:
        amt_score, amt_diff = calculate_amount_score(invoice.total_amount, ledger_tx.amount)
        date_score, date_diff = calculate_date_proximity_score(
            invoice.invoice_date, ledger_tx.transaction_date, self.date_window_days
        )
        vendor_score = calculate_vendor_similarity(invoice.vendor_name, ledger_tx.description)
        ref_score = calculate_reference_score(invoice.invoice_id, ledger_tx.description, ledger_tx.reference_no)

        # Weighted composite score formula:
        # 45% Amount + 35% Vendor + 10% Date proximity + 10% Reference Match
        total_score = (
            (amt_score * 0.45)
            + (vendor_score * 0.35)
            + (date_score * 0.10)
            + (ref_score * 0.10)
        )
        # Bonus for perfect amount + high vendor
        if amt_score == 1.0 and vendor_score >= 0.85 and date_diff <= self.date_window_days:
            total_score = max(total_score, 0.95)

        reasons: List[str] = []
        discrepancies: List[DiscrepancyDetail] = []

        if amt_score == 1.0:
            reasons.append(f"Exact amount match (${invoice.total_amount:,.2f})")
        else:
            discrepancies.append(
                DiscrepancyDetail(
                    field="total_amount",
                    invoice_val=invoice.total_amount,
                    ledger_val=ledger_tx.amount,
                    message=f"Amount variance of ${amt_diff:,.2f} (Invoice: ${invoice.total_amount:,.2f}, Ledger: ${ledger_tx.amount:,.2f})",
                )
            )

        if vendor_score >= 0.85:
            reasons.append(f"High vendor similarity ({int(vendor_score * 100)}%) with '{ledger_tx.description}'")
        elif vendor_score >= 0.60:
            reasons.append(f"Moderate vendor similarity ({int(vendor_score * 100)}%) with '{ledger_tx.description}'")
            discrepancies.append(
                DiscrepancyDetail(
                    field="vendor_name",
                    invoice_val=invoice.vendor_name,
                    ledger_val=ledger_tx.description,
                    message=f"Vendor string variation: '{invoice.vendor_name}' vs '{ledger_tx.description}'",
                )
            )
        else:
            discrepancies.append(
                DiscrepancyDetail(
                    field="vendor_name",
                    invoice_val=invoice.vendor_name,
                    ledger_val=ledger_tx.description,
                    message=f"Low vendor match score ({int(vendor_score * 100)}%)",
                )
            )

        if date_diff <= self.date_window_days:
            reasons.append(f"Transaction date within window (diff: {date_diff} day{'s' if date_diff != 1 else ''})")
        else:
            discrepancies.append(
                DiscrepancyDetail(
                    field="date",
                    invoice_val=invoice.invoice_date,
                    ledger_val=ledger_tx.transaction_date,
                    message=f"Date posted {date_diff} days apart (Window is ±{self.date_window_days} days)",
                )
            )

        if ref_score > 0.5:
            reasons.append(f"Invoice reference '{invoice.invoice_id}' found in bank memo")

        # Determine match type
        if amt_score == 1.0 and vendor_score >= 0.90 and date_diff <= 1:
            match_type = MatchType.EXACT
        elif total_score >= 0.65:
            match_type = MatchType.FUZZY
        else:
            match_type = MatchType.NO_MATCH

        breakdown = MatchScoreBreakdown(
            amount_score=round(amt_score, 4),
            vendor_fuzzy_score=round(vendor_score, 4),
            date_proximity_score=round(date_score, 4),
            reference_score=round(ref_score, 4),
            total_score=round(total_score, 4),
        )

        return MatchCandidate(
            ledger_transaction=ledger_tx,
            match_score=breakdown,
            match_type=match_type,
            date_diff_days=date_diff,
            amount_diff=round(amt_diff, 2),
            reasons=reasons,
            discrepancies=discrepancies,
        )

    def find_matches(
        self,
        invoice: InvoiceData,
        ledger_transactions: List[LedgerTransaction],
        top_k: int = 3,
    ) -> Tuple[Optional[MatchCandidate], List[MatchCandidate], ReconciliationStatus]:
        """
        Rank all ledger transactions and return best candidate, alternative candidates,
        and reconciliation classification.
        """
        if not ledger_transactions:
            return None, [], ReconciliationStatus.FAILED

        scored_candidates: List[MatchCandidate] = []
        for tx in ledger_transactions:
            candidate = self.score_candidate(invoice, tx)
            scored_candidates.append(candidate)

        # Sort descending by composite score, then by lowest date diff
        scored_candidates.sort(
            key=lambda c: (c.match_score.total_score, -c.date_diff_days, -c.amount_diff),
            reverse=True,
        )

        best_candidate = scored_candidates[0] if scored_candidates else None
        alternatives = scored_candidates[1:top_k] if len(scored_candidates) > 1 else []

        if not best_candidate or best_candidate.match_score.total_score < 0.50:
            return None, alternatives, ReconciliationStatus.FAILED

        # Check for ambiguity: Is there a second candidate with an almost identical top score?
        if alternatives and abs(best_candidate.match_score.total_score - alternatives[0].match_score.total_score) < 0.05:
            # Ambiguous match: multiple identical candidates
            return best_candidate, alternatives, ReconciliationStatus.NEEDS_REVIEW

        # Decision threshold for Auto-Reconciled
        # Needs: total_score >= 0.85, exact amount (or <=0.01), vendor score >= 0.80, date_diff <= window
        if (
            best_candidate.match_score.total_score >= self.min_auto_reconcile_score
            and best_candidate.match_score.amount_score == 1.0
            and best_candidate.match_score.vendor_fuzzy_score >= 0.80
            and best_candidate.date_diff_days <= self.date_window_days
        ):
            return best_candidate, alternatives, ReconciliationStatus.AUTO_RECONCILED
        elif best_candidate.match_score.total_score >= 0.55:
            return best_candidate, alternatives, ReconciliationStatus.NEEDS_REVIEW
        else:
            return best_candidate, alternatives, ReconciliationStatus.FAILED
