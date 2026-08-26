"""
Generates realistic sample invoices in both text and PDF format for instant demonstration.
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors

SAMPLE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_invoices")
os.makedirs(SAMPLE_DIR, exist_ok=True)

SAMPLE_INVOICES_DATA = [
    {
        "filename_base": "01_aws_cloud_invoice",
        "vendor": "Amazon Web Services, Inc.",
        "invoice_id": "INV-98213",
        "date": "2026-08-15",
        "due_date": "2026-09-15",
        "items": [
            ("Amazon EC2 Elastic Compute Cloud", 1, 110.00, 110.00),
            ("Amazon S3 Standard Storage", 1, 20.00, 20.00),
            ("AWS Data Transfer Out", 1, 12.50, 12.50),
        ],
        "subtotal": 142.50,
        "tax": 0.00,
        "total": 142.50,
        "currency": "USD",
        "notes": "Expected Outcome: Auto-Reconciled (Exact amount $142.50, 0-day diff, reference match)",
    },
    {
        "filename_base": "02_slack_technologies_invoice",
        "vendor": "Slack Technologies Inc.",
        "invoice_id": "SUB-2026-88",
        "date": "2026-08-16",
        "due_date": "2026-08-30",
        "items": [
            ("Slack Enterprise Grid (100 Active Users)", 100, 12.50, 1250.00),
        ],
        "subtotal": 1250.00,
        "tax": 0.00,
        "total": 1250.00,
        "currency": "USD",
        "notes": "Expected Outcome: Auto-Reconciled (Exact amount $1,250.00, reference SUB-2026-88)",
    },
    {
        "filename_base": "03_github_enterprise_invoice",
        "vendor": "GitHub Inc.",
        "invoice_id": "GH-8491",
        "date": "2026-08-22",  # 1-day offset from bank 2026-08-23
        "due_date": "2026-09-22",
        "items": [
            ("GitHub Team Subscription - 20 seats", 20, 21.00, 420.00),
        ],
        "subtotal": 420.00,
        "tax": 0.00,
        "total": 420.00,
        "currency": "USD",
        "notes": "Expected Outcome: Needs Review / Discrepancy Analysis (Vendor alias GITHUB_COM_SUB_8491, 1-day clearance offset)",
    },
    {
        "filename_base": "04_adobe_creative_cloud_invoice",
        "vendor": "Adobe Systems Incorporated",
        "invoice_id": "ADB-77123",
        "date": "2026-08-21",
        "due_date": "2026-09-01",
        "items": [
            ("Creative Cloud All Apps Single App License", 1, 89.99, 89.99),
        ],
        "subtotal": 89.99,
        "tax": 0.00,
        "total": 89.99,
        "currency": "USD",
        "notes": "Expected Outcome: Auto-Reconciled (Fuzzy vendor match > 85%, amount $89.99)",
    },
    {
        "filename_base": "05_unmatched_vendor_invoice",
        "vendor": "Quantum AI Hardware Labs Ltd",
        "invoice_id": "QAI-99014",
        "date": "2026-08-26",
        "due_date": "2026-09-10",
        "items": [
            ("Quantum Tensor Processor Unit rental (48 hrs)", 2, 4500.00, 9000.00),
            ("High Speed Quantum Interconnect Setup", 1, 1500.00, 1500.00),
        ],
        "subtotal": 10500.00,
        "tax": 0.00,
        "total": 10500.00,
        "currency": "USD",
        "notes": "Expected Outcome: Failed (No bank transaction found for $10,500.00)",
    },
]


def generate_text_invoice(data: dict) -> str:
    """Generate a clean ASCII formatted invoice string."""
    lines = [
        f"===========================================================",
        f"INVOICE: {data['invoice_id']}",
        f"===========================================================",
        f"Vendor: {data['vendor']}",
        f"Invoice Date: {data['date']}",
        f"Due Date: {data['due_date']}",
        f"Currency: {data['currency']}",
        f"-----------------------------------------------------------",
        f"LINE ITEMS:",
    ]
    for desc, qty, unit, total in data["items"]:
        lines.append(f"{desc:<35} {qty:>3} x ${unit:>8.2f} = ${total:>8.2f}")

    lines.extend([
        f"-----------------------------------------------------------",
        f"Subtotal: ${data['subtotal']:.2f}",
        f"Tax: ${data['tax']:.2f}",
        f"Total Amount Due: ${data['total']:.2f}",
        f"===========================================================",
        f"Notes: {data['notes']}",
    ])
    return "\n".join(lines)


def generate_pdf_invoice(data: dict, filepath: str):
    """Generate a clean styled PDF invoice using ReportLab."""
    c = canvas.Canvas(filepath, pagesize=letter)
    width, height = letter

    # Header
    c.setFont("Helvetica-Bold", 20)
    c.setFillColor(colors.HexColor("#1e293b"))
    c.drawString(50, height - 60, data["vendor"])

    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(colors.HexColor("#2563eb"))
    c.drawRightString(width - 50, height - 60, "TAX INVOICE")

    # Metadata
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#475569"))
    c.drawString(50, height - 90, f"Invoice Number: {data['invoice_id']}")
    c.drawString(50, height - 105, f"Invoice Date: {data['date']}")
    c.drawString(50, height - 120, f"Payment Due: {data['due_date']}")

    c.drawRightString(width - 50, height - 90, f"Currency: {data['currency']}")
    c.drawRightString(width - 50, height - 105, "Status: UNPAID / POSTED")

    # Table Header
    c.setStrokeColor(colors.HexColor("#cbd5e1"))
    c.setFillColor(colors.HexColor("#f1f5f9"))
    c.rect(50, height - 165, width - 100, 24, fill=1, stroke=1)

    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.HexColor("#1e293b"))
    c.drawString(60, height - 155, "Description")
    c.drawRightString(350, height - 155, "Qty")
    c.drawRightString(440, height - 155, "Unit Price")
    c.drawRightString(width - 60, height - 155, "Total Amount")

    # Table Rows
    y = height - 190
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#334155"))
    for desc, qty, unit, total in data["items"]:
        c.drawString(60, y, desc[:40])
        c.drawRightString(350, y, str(qty))
        c.drawRightString(440, y, f"${unit:,.2f}")
        c.drawRightString(width - 60, y, f"${total:,.2f}")
        y -= 22

    # Divider & Totals
    c.setStrokeColor(colors.HexColor("#e2e8f0"))
    c.line(50, y - 5, width - 50, y - 5)
    y -= 25

    c.setFont("Helvetica", 10)
    c.drawString(350, y, "Subtotal:")
    c.drawRightString(width - 60, y, f"${data['subtotal']:,.2f}")
    y -= 18

    c.drawString(350, y, "Tax (0%):")
    c.drawRightString(width - 60, y, f"${data['tax']:,.2f}")
    y -= 22

    # Grand Total Box
    c.setFillColor(colors.HexColor("#eff6ff"))
    c.rect(340, y - 8, width - 390, 26, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.HexColor("#1e40af"))
    c.drawString(350, y, "Total Amount Due:")
    c.drawRightString(width - 60, y, f"${data['total']:,.2f}")

    # Footer Notes
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(colors.HexColor("#64748b"))
    c.drawString(50, 60, f"Reconciliation Test Note: {data['notes']}")

    c.save()


def generate_all_samples():
    """Generate both txt and pdf files for each sample invoice."""
    for item in SAMPLE_INVOICES_DATA:
        txt_path = os.path.join(SAMPLE_DIR, f"{item['filename_base']}.txt")
        pdf_path = os.path.join(SAMPLE_DIR, f"{item['filename_base']}.pdf")

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(generate_text_invoice(item))

        try:
            generate_pdf_invoice(item, pdf_path)
        except Exception as e:
            print(f"Could not generate PDF for {item['filename_base']}: {e}")

    print(f"Generated sample invoices in {SAMPLE_DIR}")


if __name__ == "__main__":
    generate_all_samples()
