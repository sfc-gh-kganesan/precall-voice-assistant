import tempfile
from pathlib import Path

import pytest
from py_protos import invoicestore_pb2

from app.db import Db, InvoiceSchema


@pytest.fixture
def db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
        db_path = Path(temp_db.name)

    test_db = Db(db_path)
    yield test_db

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


def test_insert_and_get_submission(db):
    """Test inserting and retrieving a submission."""
    file_ids = ["file1.pdf", "file2.pdf"]
    lift_ticket = "LT-12345"
    status = invoicestore_pb2.SUBMISSION_STATUS_PENDING

    # Insert submission
    submission = db.insert_submission(file_ids, lift_ticket, status)

    assert submission is not None
    assert submission.id is not None
    assert submission.lift_ticket == lift_ticket
    assert submission.created_at is not None

    # Retrieve submission
    retrieved = db.get_submission_by_id(submission.id)

    assert retrieved is not None
    assert retrieved.id == submission.id
    assert retrieved.lift_ticket == lift_ticket


def test_get_submission_nonexistent(db):
    """Test retrieving a non-existent submission returns None."""
    result = db.get_submission_by_id(99999)
    assert result is None


def test_create_invoice(db):
    """Test creating an invoice."""
    invoice = InvoiceSchema(
        lift_ticket="LT-12345",
        file_id="file1.pdf",
        vendor_name="Acme Corp",
        invoice_number="INV-001",
        invoice_date="2024-01-01",
        total_amount="1000.00",
        purchase_order_number="PO-123",
    )

    created_invoice = db.create_invoice(invoice)

    assert created_invoice is not None
    assert created_invoice.id is not None
    assert created_invoice.lift_ticket == "LT-12345"
    assert created_invoice.file_id == "file1.pdf"
    assert created_invoice.vendor_name == "Acme Corp"
    assert created_invoice.invoice_number == "INV-001"
    assert created_invoice.status == "PENDING"
    assert created_invoice.created_at is not None


def test_approve_invoice(db):
    """Test approving an invoice."""
    invoice = InvoiceSchema(
        lift_ticket="LT-12345",
        file_id="file1.pdf",
        vendor_name="Acme Corp",
        invoice_number="INV-001",
    )

    created_invoice = db.create_invoice(invoice)
    result = db.approve_invoice(created_invoice.id)

    assert result is True


def test_reject_invoice(db):
    """Test rejecting an invoice with a reason."""
    invoice = InvoiceSchema(
        lift_ticket="LT-12345",
        file_id="file1.pdf",
        vendor_name="Acme Corp",
        invoice_number="INV-001",
    )

    created_invoice = db.create_invoice(invoice)
    reason = "Invalid invoice number"
    result = db.reject_invoice(created_invoice.id, reason)

    assert result is True


def test_create_invoice_with_all_fields(db):
    """Test creating an invoice with all fields populated."""
    invoice = InvoiceSchema(
        lift_ticket="LT-12345",
        file_id="file1.pdf",
        vendor_name="Acme Corp",
        invoice_number="INV-001",
        invoice_date="2024-01-01",
        total_amount="1000.00",
        purchase_order_number="PO-123",
        banking_details="Bank: ABC, Account: 123456",
        payment_terms="Net 30",
        memo_description="Office supplies",
        shipped_to_address="123 Main St",
        service_start_date="2024-01-01",
        service_end_date="2024-01-31",
        quantity="10",
        unit_price="100.00",
        payment_type="Credit Card",
        due_date="2024-02-01",
        vendor_tax_id="TAX-123",
        snowflake_tax_id="SF-TAX-456",
        prepaid_flag="N",
    )

    created_invoice = db.create_invoice(invoice)

    assert created_invoice is not None
    assert created_invoice.id is not None
    assert created_invoice.vendor_name == "Acme Corp"
    assert created_invoice.banking_details == "Bank: ABC, Account: 123456"
    assert created_invoice.payment_terms == "Net 30"
    assert created_invoice.memo_description == "Office supplies"
    assert created_invoice.shipped_to_address == "123 Main St"
    assert created_invoice.service_start_date == "2024-01-01"
    assert created_invoice.service_end_date == "2024-01-31"
    assert created_invoice.quantity == "10"
    assert created_invoice.unit_price == "100.00"
    assert created_invoice.payment_type == "Credit Card"
    assert created_invoice.due_date == "2024-02-01"
    assert created_invoice.vendor_tax_id == "TAX-123"
    assert created_invoice.snowflake_tax_id == "SF-TAX-456"
    assert created_invoice.prepaid_flag == "N"


def test_multiple_submissions(db):
    """Test inserting multiple submissions."""
    submissions = []
    for i in range(3):
        submission = db.insert_submission([f"file{i}.pdf"], f"LT-{i}", invoicestore_pb2.SUBMISSION_STATUS_PENDING)
        submissions.append(submission)

    assert len(submissions) == 3
    for i, submission in enumerate(submissions):
        retrieved = db.get_submission_by_id(submission.id)
        assert retrieved is not None
        assert retrieved.lift_ticket == f"LT-{i}"
