"""
Synthetic bank statement and general ledger generator for testing the
AI Finance Controller matching engine with realistic scenarios and edge cases.
"""

from typing import List
from sqlalchemy.orm import Session
from backend.database import DBLedgerTransaction, DBInvoice, DBLineItem, DBReconciliation, SessionLocal, init_db

SAMPLE_LEDGER_TRANSACTIONS = [
    # 1. High Confidence Matches (Exact / Standard vendor variants)
    {
        "transaction_id": "TXN-2026-0801",
        "transaction_date": "2026-08-15",
        "amount": 142.50,
        "description": "DEBIT - AWS CLOUD SVCS - REF: INV-98213",
        "vendor_normalized": "Amazon Web Services",
        "account": "Operating Checking - 4092",
        "reference_no": "INV-98213",
        "is_reconciled": False,
    },
    {
        "transaction_id": "TXN-2026-0802",
        "transaction_date": "2026-08-16",
        "amount": 1250.00,
        "description": "ACH WITHDRAWAL - SLACK TECHNOLOGIES INC - SUB-2026-88",
        "vendor_normalized": "Slack Technologies",
        "account": "Operating Checking - 4092",
        "reference_no": "SUB-2026-88",
        "is_reconciled": False,
    },
    {
        "transaction_id": "TXN-2026-0803",
        "transaction_date": "2026-08-18",
        "amount": 54.20,
        "description": "POS UBER *TRIP 08/18 SAN FRANCISCO CA",
        "vendor_normalized": "Uber Technologies",
        "account": "Corporate Credit Card - 1104",
        "reference_no": "UBR-90412",
        "is_reconciled": False,
    },
    {
        "transaction_id": "TXN-2026-0804",
        "transaction_date": "2026-08-20",
        "amount": 3400.00,
        "description": "WIRE TRF - GOOGLE LLC WORKSPACE ENTERPRISE",
        "vendor_normalized": "Google Cloud",
        "account": "Operating Checking - 4092",
        "reference_no": "GOOG-55419",
        "is_reconciled": False,
    },
    {
        "transaction_id": "TXN-2026-0805",
        "transaction_date": "2026-08-21",
        "amount": 89.99,
        "description": "ADOBE *CREATIVE CLOUD WWW.ADOBE.COM CA",
        "vendor_normalized": "Adobe Inc",
        "account": "Corporate Credit Card - 1104",
        "reference_no": "ADB-77123",
        "is_reconciled": False,
    },
    # 2. Ambiguous / Needs Review Scenarios (Date offsets ±2d, alias differences, tax discrepancy)
    {
        "transaction_id": "TXN-2026-0806",
        "transaction_date": "2026-08-23",
        "amount": 420.00,
        "description": "DEBIT - GITHUB_COM_SUB_8491 SAN FRANCISCO CA",
        "vendor_normalized": "GitHub",
        "account": "Operating Checking - 4092",
        "reference_no": "GH-8491",
        "is_reconciled": False,
    },
    {
        "transaction_id": "TXN-2026-0807",
        "transaction_date": "2026-08-22",
        "amount": 420.00,
        "description": "DEBIT - GITLAB ENTERPRISE SERVICES",
        "vendor_normalized": "GitLab",
        "account": "Operating Checking - 4092",
        "reference_no": "GL-3321",
        "is_reconciled": False,
    },
    {
        "transaction_id": "TXN-2026-0808",
        "transaction_date": "2026-08-24",
        "amount": 789.50,
        "description": "ACH DEBIT - ZOOM VIDEO COMMUNICATIONS INC",
        "vendor_normalized": "Zoom",
        "account": "Operating Checking - 4092",
        "reference_no": "ZM-99214",
        "is_reconciled": False,
    },
    {
        "transaction_id": "TXN-2026-0809",
        "transaction_date": "2026-08-25",
        "amount": 2150.00,
        "description": "DIRECT DEBIT - SALESFORCE.COM INC ENTERPRISE CRM",
        "vendor_normalized": "Salesforce",
        "account": "Operating Checking - 4092",
        "reference_no": "SF-00192",
        "is_reconciled": False,
    },
    {
        "transaction_id": "TXN-2026-0810",
        "transaction_date": "2026-08-26",
        "amount": 312.45,
        "description": "OFFICE DEPOT STORE #401 SAN JOSE CA",
        "vendor_normalized": "Office Depot",
        "account": "Corporate Credit Card - 1104",
        "reference_no": "OD-6612",
        "is_reconciled": False,
    },
]


def seed_database(db: Session, force_reset: bool = False):
    """Seed or reset bank ledger transactions."""
    if force_reset:
        db.query(DBReconciliation).delete()
        db.query(DBLineItem).delete()
        db.query(DBInvoice).delete()
        db.query(DBLedgerTransaction).delete()
        db.commit()

    existing_count = db.query(DBLedgerTransaction).count()
    if existing_count == 0 or force_reset:
        for tx in SAMPLE_LEDGER_TRANSACTIONS:
            db_tx = DBLedgerTransaction(
                transaction_id=tx["transaction_id"],
                transaction_date=tx["transaction_date"],
                amount=tx["amount"],
                description=tx["description"],
                vendor_normalized=tx["vendor_normalized"],
                account=tx["account"],
                reference_no=tx["reference_no"],
                is_reconciled=tx["is_reconciled"],
            )
            db.merge(db_tx)
        db.commit()
        print(f"Successfully seeded {len(SAMPLE_LEDGER_TRANSACTIONS)} ledger transactions.")


if __name__ == "__main__":
    init_db()
    db = SessionLocal()
    seed_database(db, force_reset=True)
    db.close()
