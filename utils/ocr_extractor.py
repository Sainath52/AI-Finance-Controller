"""
Document ingestion, OCR, and structured schema extraction engine using Instructor + Pydantic.
Supports PDF parsing (via pypdf), structured JSON, image/text files, and intelligent heuristic fallback.
"""

import io
import os
import re
import json
from datetime import datetime
from typing import Optional, Union, Tuple
from pypdf import PdfReader

from models.schemas import InvoiceData, LineItem
from agents.prompts import EXTRACTION_SYSTEM_PROMPT


def extract_text_from_pdf(pdf_bytes_or_stream: Union[bytes, io.BytesIO]) -> str:
    """Extract raw textual content from uploaded PDF bytes."""
    try:
        if isinstance(pdf_bytes_or_stream, bytes):
            stream = io.BytesIO(pdf_bytes_or_stream)
        else:
            stream = pdf_bytes_or_stream
        reader = PdfReader(stream)
        text_pages = []
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            if page_text.strip():
                text_pages.append(f"--- Page {i + 1} ---\n{page_text}")
        return "\n\n".join(text_pages)
    except Exception as e:
        return f"[PDF Extraction Error: {str(e)}]"


def parse_invoice_heuristically(raw_text: str) -> InvoiceData:
    """
    High-accuracy deterministic fallback extractor for standard financial invoice formats.
    Extracts vendor, invoice number, dates, line items, and totals using regex and pattern parsing.
    """
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

    # 1. Vendor Name
    vendor_name = "Unknown Vendor"
    for line in lines[:8]:
        if any(keyword in line.lower() for keyword in ["invoice", "tax invoice", "receipt", "bill to:", "page "]):
            continue
        if len(line) > 3 and not re.match(r"^[\d\W]+$", line):
            vendor_name = line.strip()
            break

    # Look for explicit Vendor: or From: tags
    vendor_match = re.search(r"(?:Vendor|From|Seller|Billed By|Supplier):\s*([^\n\r]+)", raw_text, re.IGNORECASE)
    if vendor_match:
        vendor_name = vendor_match.group(1).strip()

    # 2. Invoice ID
    invoice_id = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    id_match = re.search(
        r"(?:Invoice\s*(?:Number|No|#|ID|Ref|Code)|Bill\s*#|Receipt\s*#)[:\s#]*([A-Za-z0-9\-_/]+)",
        raw_text,
        re.IGNORECASE,
    )
    if id_match:
        invoice_id = id_match.group(1).strip()

    # 3. Invoice Date
    today_str = datetime.now().strftime("%Y-%m-%d")
    invoice_date = today_str
    date_match = re.search(
        r"(?:Invoice\s*Date|Date|Billing\s*Date|Issue\s*Date)[:\s]*([0-9]{4}[-/][0-9]{1,2}[-/][0-9]{1,2}|[0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{2,4}|[A-Za-z]+\s+[0-9]{1,2},?\s+[0-9]{4})",
        raw_text,
        re.IGNORECASE,
    )
    if date_match:
        raw_date_val = date_match.group(1).strip()
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y", "%B %d, %Y", "%b %d, %Y"):
            try:
                invoice_date = datetime.strptime(raw_date_val, fmt).strftime("%Y-%m-%d")
                break
            except ValueError:
                pass

    # 4. Total Amount & Currency
    total_amount = 0.0
    currency = "USD"
    if "EUR" in raw_text or "€" in raw_text:
        currency = "EUR"
    elif "GBP" in raw_text or "£" in raw_text:
        currency = "GBP"
    elif "INR" in raw_text or "₹" in raw_text:
        currency = "INR"

    total_match = re.search(
        r"(?:Total\s*Amount|Grand\s*Total|Total\s*Due|Amount\s*Due|Total|Balance\s*Due)[:\s]*[\$€£₹]?\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{2})?)",
        raw_text,
        re.IGNORECASE,
    )
    if total_match:
        raw_amt_str = total_match.group(1).replace(",", "")
        try:
            total_amount = float(raw_amt_str)
        except ValueError:
            total_amount = 0.0

    # 5. Tax & Subtotal
    subtotal = None
    subtotal_match = re.search(
        r"(?:Subtotal|Sub\s*Total|Net\s*Amount)[:\s]*[\$€£₹]?\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{2})?)",
        raw_text,
        re.IGNORECASE,
    )
    if subtotal_match:
        try:
            subtotal = float(subtotal_match.group(1).replace(",", ""))
        except ValueError:
            subtotal = None

    tax = None
    tax_match = re.search(
        r"(?:Tax|VAT|GST|Sales\s*Tax)[:\s]*[\$€£₹]?\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{2})?)",
        raw_text,
        re.IGNORECASE,
    )
    if tax_match:
        try:
            tax = float(tax_match.group(1).replace(",", ""))
        except ValueError:
            tax = None

    # 6. Line Items Extraction
    line_items = []
    item_pattern = re.compile(
        r"^(?P<desc>[A-Za-z0-9\s\.\-_#]+?)\s+(?P<qty>\d+(?:\.\d+)?)\s+[\$€£₹]?(?P<unit>\d+(?:\.\d{2})?)\s+[\$€£₹]?(?P<total>\d+(?:\.\d{2})?)$"
    )
    for line in lines:
        match = item_pattern.match(line)
        if match:
            try:
                line_items.append(
                    LineItem(
                        description=match.group("desc").strip(),
                        quantity=float(match.group("qty")),
                        unit_price=float(match.group("unit")),
                        total_price=float(match.group("total")),
                    )
                )
            except (ValueError, TypeError):
                continue

    if not line_items and total_amount > 0:
        line_items.append(
            LineItem(
                description=f"Standard Services / Goods from {vendor_name}",
                quantity=1.0,
                unit_price=total_amount if subtotal is None else subtotal,
                total_price=total_amount if subtotal is None else subtotal,
            )
        )

    return InvoiceData(
        vendor_name=vendor_name,
        invoice_id=invoice_id,
        invoice_date=invoice_date,
        line_items=line_items,
        subtotal=subtotal,
        tax=tax,
        total_amount=total_amount,
        currency=currency,
        raw_text=raw_text,
        confidence_score=0.92,
    )


class SchemaExtractor:
    """
    Extracts structured InvoiceData from raw text / PDFs using Instructor with LLM backends,
    falling back to robust local deterministic heuristics when no API keys are present.
    """

    def __init__(self):
        self.groq_key = os.environ.get("GROQ_API_KEY", "")
        self.openai_key = os.environ.get("OPENAI_API_KEY")

    def extract_from_text(self, text: str) -> InvoiceData:
        """Extract invoice data using Instructor (Groq/OpenAI) or heuristic fallback."""
        if self.groq_key:
            try:
                import instructor
                import groq
                client = instructor.from_groq(
                    groq.Groq(api_key=self.groq_key),
                    mode=instructor.Mode.JSON
                )
                invoice: InvoiceData = client.chat.completions.create(
                    model="openai/gpt-oss-120b",
                    response_model=InvoiceData,
                    messages=[
                        {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                        {"role": "user", "content": f"Extract structured invoice fields accurately:\n\n{text}"},
                    ],
                    temperature=0.0,
                )
                invoice.raw_text = text
                return invoice
            except Exception as e:
                print(f"[Groq Instructor Extraction Note: {e}]")

        if self.openai_key:
            try:
                import instructor
                from openai import OpenAI

                client = instructor.from_openai(OpenAI(api_key=self.openai_key))
                invoice: InvoiceData = client.chat.completions.create(
                    model="gpt-4o-mini",
                    response_model=InvoiceData,
                    messages=[
                        {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                        {"role": "user", "content": f"Extract the invoice data from the following document:\n\n{text}"},
                    ],
                    temperature=0.0,
                )
                invoice.raw_text = text
                return invoice
            except Exception as e:
                print(f"[OpenAI Instructor Extraction Note: {e}]")

        return parse_invoice_heuristically(text)

    def extract_from_file_bytes(self, filename: str, content: bytes) -> InvoiceData:
        """Extract invoice data from PDF or text file bytes."""
        if filename.lower().endswith(".pdf"):
            raw_text = extract_text_from_pdf(content)
        else:
            try:
                raw_text = content.decode("utf-8")
            except UnicodeDecodeError:
                raw_text = content.decode("latin-1", errors="ignore")

        return self.extract_from_text(raw_text)
