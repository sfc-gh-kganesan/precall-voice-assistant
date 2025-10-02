import tempfile
from concurrent import futures
from pathlib import Path

import grpc
import pytest
import pytest_asyncio
from py_protos import invoicestore_pb2, invoicestore_pb2_grpc

from app.main import InvoiceStoreServicer


@pytest_asyncio.fixture
async def grpc_server():
    """Start a gRPC server for testing."""
    # Create temporary database for testing
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
        db_path = temp_db.name

    # Create servicer with test database
    servicer = InvoiceStoreServicer()
    servicer.db.db_path = db_path
    servicer.db._init_db()

    # Create and start server
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    invoicestore_pb2_grpc.add_InvoiceStoreServicer_to_server(servicer, server)

    port = server.add_insecure_port("[::]:0")  # Use port 0 to get a random available port
    await server.start()

    yield f"localhost:{port}"

    # Cleanup
    await server.stop(0)
    Path(db_path).unlink(missing_ok=True)


@pytest_asyncio.fixture
async def grpc_stub(grpc_server):
    """Create a gRPC client stub."""
    async with grpc.aio.insecure_channel(grpc_server) as channel:
        stub = invoicestore_pb2_grpc.InvoiceStoreStub(channel)
        yield stub


@pytest.mark.asyncio
async def test_submit_success(grpc_stub):
    """Test successful submission via gRPC."""
    request = invoicestore_pb2.SubmissionRequest(
        lift_ticket="LT-TEST-001",
        file_ids=["file1.pdf", "file2.pdf"],
    )

    response = await grpc_stub.Submit(request)

    assert response.success is True
    assert response.status == invoicestore_pb2.SUBMISSION_STATUS_PENDING
    assert "Successfully processed 2 file(s)" in response.message
    assert "LT-TEST-001" in response.message


@pytest.mark.asyncio
async def test_submit_missing_lift_ticket(grpc_stub):
    """Test submission with missing lift ticket."""
    request = invoicestore_pb2.SubmissionRequest(
        lift_ticket="",
        file_ids=["file1.pdf"],
    )

    response = await grpc_stub.Submit(request)

    assert response.success is False
    assert response.status == invoicestore_pb2.SUBMISSION_STATUS_REJECTED
    assert "Lift ticket is required" in response.message


@pytest.mark.asyncio
async def test_submit_missing_file_ids(grpc_stub):
    """Test submission with missing file IDs."""
    request = invoicestore_pb2.SubmissionRequest(
        lift_ticket="LT-TEST-002",
        file_ids=[],
    )

    response = await grpc_stub.Submit(request)

    assert response.success is False
    assert response.status == invoicestore_pb2.SUBMISSION_STATUS_REJECTED
    assert "At least one file ID is required" in response.message


@pytest.mark.asyncio
async def test_submit_multiple_files(grpc_stub):
    """Test submission with multiple files."""
    file_ids = [f"file{i}.pdf" for i in range(5)]

    request = invoicestore_pb2.SubmissionRequest(
        lift_ticket="LT-TEST-003",
        file_ids=file_ids,
    )

    response = await grpc_stub.Submit(request)

    assert response.success is True
    assert response.status == invoicestore_pb2.SUBMISSION_STATUS_PENDING
    assert "5 file(s)" in response.message


@pytest.mark.asyncio
async def test_multiple_submissions(grpc_stub):
    """Test multiple sequential submissions."""
    for i in range(3):
        request = invoicestore_pb2.SubmissionRequest(
            lift_ticket=f"LT-TEST-{i:03d}",
            file_ids=[f"file{i}.pdf"],
        )

        response = await grpc_stub.Submit(request)

        assert response.success is True
        assert response.status == invoicestore_pb2.SUBMISSION_STATUS_PENDING


@pytest.mark.asyncio
async def test_get_submission_success(grpc_stub):
    """Test retrieving a submission by lift ticket."""
    # First create a submission
    submit_request = invoicestore_pb2.SubmissionRequest(
        lift_ticket="LT-GET-001", file_ids=["file1.pdf", "file2.pdf", "file3.pdf"]
    )

    submit_response = await grpc_stub.Submit(submit_request)
    assert submit_response.success is True

    # Now retrieve the submission
    get_request = invoicestore_pb2.GetSubmissionRequest(lift_ticket="LT-GET-001")

    get_response = await grpc_stub.GetSubmission(get_request)

    assert get_response.success is True
    assert get_response.status == invoicestore_pb2.SUBMISSION_STATUS_PENDING
    assert len(get_response.file_ids) == 3
    assert "file1.pdf" in get_response.file_ids
    assert "file2.pdf" in get_response.file_ids
    assert "file3.pdf" in get_response.file_ids
    assert "LT-GET-001" in get_response.message


@pytest.mark.asyncio
async def test_get_submission_not_found(grpc_stub):
    """Test retrieving a non-existent submission."""
    get_request = invoicestore_pb2.GetSubmissionRequest(lift_ticket="LT-NONEXISTENT")

    get_response = await grpc_stub.GetSubmission(get_request)

    assert get_response.success is False
    assert get_response.status == invoicestore_pb2.SUBMISSION_STATUS_UNKNOWN
    assert len(get_response.file_ids) == 0
    assert "No submission found" in get_response.message


@pytest.mark.asyncio
async def test_get_submission_missing_lift_ticket(grpc_stub):
    """Test retrieving submission without providing lift ticket."""
    get_request = invoicestore_pb2.GetSubmissionRequest(lift_ticket="")

    get_response = await grpc_stub.GetSubmission(get_request)

    assert get_response.success is False
    assert get_response.status == invoicestore_pb2.SUBMISSION_STATUS_UNKNOWN
    assert len(get_response.file_ids) == 0
    assert "Lift ticket is required" in get_response.message


@pytest.mark.asyncio
async def test_create_invoice_minimal_fields(grpc_stub):
    """Test creating an invoice with minimal required fields."""
    request = invoicestore_pb2.CreateInvoiceRequest(
        lift_ticket="LT-INV-001",
        file_id="invoice1.pdf",
    )

    response = await grpc_stub.CreateInvoice(request)

    assert response.success is True
    assert response.invoice_id > 0
    assert "Successfully created invoice" in response.message
    assert "LT-INV-001" in response.message


@pytest.mark.asyncio
async def test_create_invoice_all_fields(grpc_stub):
    """Test creating an invoice with all fields populated."""
    request = invoicestore_pb2.CreateInvoiceRequest(
        lift_ticket="LT-INV-002",
        file_id="invoice2.pdf",
        vendor_name="Acme Corporation",
        invoice_number="INV-2024-001",
        invoice_date="2024-01-15",
        total_amount="5000.00",
        purchase_order_number="PO-2024-100",
        banking_details="Bank: First National, Account: 123456789",
        payment_terms="Net 30",
        memo_description="Office supplies and equipment",
        shipped_to_address="123 Main St, San Francisco, CA 94105",
        service_start_date="2024-01-01",
        service_end_date="2024-01-31",
        quantity="25",
        unit_price="200.00",
        payment_type="Wire Transfer",
        due_date="2024-02-15",
        vendor_tax_id="12-3456789",
        snowflake_tax_id="SF-98-7654321",
        prepaid_flag="N",
    )

    response = await grpc_stub.CreateInvoice(request)

    assert response.success is True
    assert response.invoice_id > 0
    assert "Successfully created invoice" in response.message


@pytest.mark.asyncio
async def test_create_invoice_missing_lift_ticket(grpc_stub):
    """Test creating invoice with missing lift ticket."""
    request = invoicestore_pb2.CreateInvoiceRequest(
        lift_ticket="",
        file_id="invoice3.pdf",
    )

    response = await grpc_stub.CreateInvoice(request)

    assert response.success is False
    assert response.invoice_id == 0
    assert "Lift ticket is required" in response.message


@pytest.mark.asyncio
async def test_create_invoice_missing_file_id(grpc_stub):
    """Test creating invoice with missing file ID."""
    request = invoicestore_pb2.CreateInvoiceRequest(
        lift_ticket="LT-INV-004",
        file_id="",
    )

    response = await grpc_stub.CreateInvoice(request)

    assert response.success is False
    assert response.invoice_id == 0
    assert "File ID is required" in response.message


@pytest.mark.asyncio
async def test_create_multiple_invoices(grpc_stub):
    """Test creating multiple invoices."""
    invoices_created = []

    for i in range(3):
        request = invoicestore_pb2.CreateInvoiceRequest(
            lift_ticket=f"LT-INV-{i:03d}",
            file_id=f"invoice{i}.pdf",
            vendor_name=f"Vendor {i}",
            invoice_number=f"INV-{i}",
            total_amount=f"{(i + 1) * 1000}.00",
        )

        response = await grpc_stub.CreateInvoice(request)

        assert response.success is True
        assert response.invoice_id > 0
        invoices_created.append(response.invoice_id)

    # Verify all invoice IDs are unique
    assert len(invoices_created) == len(set(invoices_created))


@pytest.mark.asyncio
async def test_create_invoice_with_optional_fields(grpc_stub):
    """Test creating invoice with some optional fields."""
    request = invoicestore_pb2.CreateInvoiceRequest(
        lift_ticket="LT-INV-005",
        file_id="invoice5.pdf",
        vendor_name="Tech Supplies Inc",
        invoice_number="INV-2024-005",
        total_amount="2500.00",
        payment_terms="Net 45",
        due_date="2024-03-01",
    )

    response = await grpc_stub.CreateInvoice(request)

    assert response.success is True
    assert response.invoice_id > 0
    assert "LT-INV-005" in response.message


@pytest.mark.asyncio
async def test_approve_invoice_success(grpc_stub):
    """Test successfully approving an invoice."""
    # First create an invoice
    create_request = invoicestore_pb2.CreateInvoiceRequest(
        lift_ticket="LT-APPROVE-001",
        file_id="invoice_approve_1.pdf",
        vendor_name="Test Vendor",
        invoice_number="INV-APPROVE-001",
        total_amount="1000.00",
    )

    create_response = await grpc_stub.CreateInvoice(create_request)
    assert create_response.success is True
    invoice_id = create_response.invoice_id

    # Now approve the invoice
    approve_request = invoicestore_pb2.ApproveInvoiceRequest(invoice_id=invoice_id)

    approve_response = await grpc_stub.ApproveInvoice(approve_request)

    assert approve_response.succes is True
    assert f"Successfully approved invoice {invoice_id}" in approve_response.message


@pytest.mark.asyncio
async def test_approve_invoice_invalid_id(grpc_stub):
    """Test approving invoice with invalid ID."""
    approve_request = invoicestore_pb2.ApproveInvoiceRequest(invoice_id=0)

    approve_response = await grpc_stub.ApproveInvoice(approve_request)

    assert approve_response.succes is False
    assert "Valid invoice ID is required" in approve_response.message


@pytest.mark.asyncio
async def test_approve_invoice_negative_id(grpc_stub):
    """Test approving invoice with negative ID."""
    approve_request = invoicestore_pb2.ApproveInvoiceRequest(invoice_id=-1)

    approve_response = await grpc_stub.ApproveInvoice(approve_request)

    assert approve_response.succes is False
    assert "Valid invoice ID is required" in approve_response.message


@pytest.mark.asyncio
async def test_reject_invoice_success(grpc_stub):
    """Test successfully rejecting an invoice."""
    # First create an invoice
    create_request = invoicestore_pb2.CreateInvoiceRequest(
        lift_ticket="LT-REJECT-001",
        file_id="invoice_reject_1.pdf",
        vendor_name="Test Vendor",
        invoice_number="INV-REJECT-001",
        total_amount="1500.00",
    )

    create_response = await grpc_stub.CreateInvoice(create_request)
    assert create_response.success is True
    invoice_id = create_response.invoice_id

    # Now reject the invoice
    reject_request = invoicestore_pb2.RejectInvoiceRequest(invoice_id=invoice_id, reason="Invalid vendor information")

    reject_response = await grpc_stub.RejectInvoice(reject_request)

    assert reject_response.succes is True
    assert f"Successfully rejected invoice {invoice_id}" in reject_response.message


@pytest.mark.asyncio
async def test_reject_invoice_invalid_id(grpc_stub):
    """Test rejecting invoice with invalid ID."""
    reject_request = invoicestore_pb2.RejectInvoiceRequest(invoice_id=0, reason="Some reason")

    reject_response = await grpc_stub.RejectInvoice(reject_request)

    assert reject_response.succes is False
    assert "Valid invoice ID is required" in reject_response.message


@pytest.mark.asyncio
async def test_reject_invoice_negative_id(grpc_stub):
    """Test rejecting invoice with negative ID."""
    reject_request = invoicestore_pb2.RejectInvoiceRequest(invoice_id=-1, reason="Some reason")

    reject_response = await grpc_stub.RejectInvoice(reject_request)

    assert reject_response.succes is False
    assert "Valid invoice ID is required" in reject_response.message


@pytest.mark.asyncio
async def test_reject_invoice_missing_reason(grpc_stub):
    """Test rejecting invoice without providing a reason."""
    # First create an invoice
    create_request = invoicestore_pb2.CreateInvoiceRequest(
        lift_ticket="LT-REJECT-002",
        file_id="invoice_reject_2.pdf",
        vendor_name="Test Vendor",
        invoice_number="INV-REJECT-002",
        total_amount="2000.00",
    )

    create_response = await grpc_stub.CreateInvoice(create_request)
    assert create_response.success is True
    invoice_id = create_response.invoice_id

    # Try to reject without a reason
    reject_request = invoicestore_pb2.RejectInvoiceRequest(invoice_id=invoice_id, reason="")

    reject_response = await grpc_stub.RejectInvoice(reject_request)

    assert reject_response.succes is False
    assert "Rejection reason is required" in reject_response.message
