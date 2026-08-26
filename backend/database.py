"""
SQLAlchemy database setup and ORM models for AI Finance Controller.
Stores invoices, ledger entries, matching records, and comprehensive audit trails.
"""

import json
from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    Integer,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session

DATABASE_URL = "sqlite:///./finance_controller.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class DBInvoice(Base):
    __tablename__ = "invoices"

    id = Column(String(64), primary_key=True, index=True)
    vendor_name = Column(String(255), nullable=False, index=True)
    invoice_id = Column(String(128), nullable=False, index=True)
    invoice_date = Column(String(32), nullable=False)
    due_date = Column(String(32), nullable=True)
    subtotal = Column(Float, nullable=True)
    tax = Column(Float, nullable=True)
    total_amount = Column(Float, nullable=False, index=True)
    currency = Column(String(16), default="USD")
    raw_text = Column(Text, nullable=True)
    confidence_score = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    line_items = relationship("DBLineItem", back_populates="invoice", cascade="all, delete-orphan")
    reconciliation = relationship("DBReconciliation", back_populates="invoice", uselist=False)


class DBLineItem(Base):
    __tablename__ = "line_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(String(64), ForeignKey("invoices.id"), nullable=False)
    description = Column(String(512), nullable=False)
    quantity = Column(Float, default=1.0)
    unit_price = Column(Float, default=0.0)
    total_price = Column(Float, nullable=False)

    invoice = relationship("DBInvoice", back_populates="line_items")


class DBLedgerTransaction(Base):
    __tablename__ = "ledger_transactions"

    transaction_id = Column(String(64), primary_key=True, index=True)
    transaction_date = Column(String(32), nullable=False, index=True)
    amount = Column(Float, nullable=False, index=True)
    description = Column(String(512), nullable=False)
    vendor_normalized = Column(String(255), nullable=True)
    account = Column(String(128), default="Operating Checking - 4092")
    reference_no = Column(String(128), nullable=True)
    is_reconciled = Column(Boolean, default=False)
    matched_invoice_id = Column(String(64), nullable=True)


class DBReconciliation(Base):
    __tablename__ = "reconciliations"

    id = Column(String(64), primary_key=True, index=True)
    invoice_id = Column(String(64), ForeignKey("invoices.id"), nullable=False, index=True)
    matched_ledger_id = Column(String(64), ForeignKey("ledger_transactions.transaction_id"), nullable=True)
    status = Column(String(64), nullable=False, index=True)  # Auto-Reconciled, Needs Review, Failed
    confidence_score = Column(Float, default=0.0)
    match_type = Column(String(32), default="no_match")
    reasons_json = Column(Text, default="[]")
    discrepancies_json = Column(Text, default="[]")
    audit_trail_json = Column(Text, default="[]")
    alternative_candidates_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_by = Column(String(128), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    invoice = relationship("DBInvoice", back_populates="reconciliation")
    matched_ledger = relationship("DBLedgerTransaction", foreign_keys=[matched_ledger_id])


def init_db():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
