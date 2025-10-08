import os
import logging
import grpc
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

# Import gRPC stubs
from py_protos import (
    invoicestore_pb2,
    invoicestore_pb2_grpc,
    extractor_pb2,
    extractor_pb2_grpc,
    filestore_pb2,
    filestore_pb2_grpc,
)

# --- Environment Variables for Service Discovery ---
INVOICESTORE_GRPC_URL = os.getenv("INVOICESTORE_GRPC_URL", "localhost:50051")
EXTRACTOR_GRPC_URL = os.getenv("EXTRACTOR_GRPC_URL", "localhost:50051")
FILESTORE_GRPC_URL = os.getenv("FILESTORE_GRPC_URL", "localhost:50051")

# --- FastAPI App Initialization ---
app = FastAPI(title="InvoiceIQ Gateway API", version="0.1.0")

# Add CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- Pydantic Models ---
class ExtractResponse(BaseModel):
    success: bool
    message: str
    file_id: str
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    total_amount: Optional[str] = None
    purchase_order_number: Optional[str] = None
    payment_terms: Optional[str] = None
    due_date: Optional[str] = None
    file_url: Optional[str] = None
    banking_details: Optional[str] = None
    freight_shipping_amount: Optional[str] = None
    invoice_currency: Optional[str] = None
    invoice_date: Optional[str] = None
    memo_description: Optional[str] = None
    payment_type: Optional[str] = None
    prepaid_flag: Optional[bool] = None
    quantity: Optional[str] = None
    service_end_date: Optional[str] = None
    service_start_date: Optional[str] = None
    shipped_to_address: Optional[str] = None
    snowflake_entity: Optional[str] = None
    snowflake_tax_id: Optional[str] = None
    tax_amount: Optional[str] = None
    unit_price: Optional[str] = None
    vendor_address: Optional[str] = None
    vendor_tax_id: Optional[str] = None


class CreateInvoiceRequest(BaseModel):
    lift_ticket: str
    file_id: str
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    total_amount: Optional[str] = None
    purchase_order_number: Optional[str] = None
    banking_details: Optional[str] = None
    payment_terms: Optional[str] = None
    memo_description: Optional[str] = None
    shipped_to_address: Optional[str] = None
    service_start_date: Optional[str] = None
    service_end_date: Optional[str] = None
    quantity: Optional[str] = None
    unit_price: Optional[str] = None
    payment_type: Optional[str] = None
    due_date: Optional[str] = None
    vendor_tax_id: Optional[str] = None
    snowflake_tax_id: Optional[str] = None
    prepaid_flag: Optional[str] = None
    # Action flag: "approve", "reject", or "pending" (default)
    action: Optional[str] = "pending"
    rejection_reason: Optional[str] = None


class CreateInvoiceResponse(BaseModel):
    success: bool
    message: str
    invoice_id: int
    status: str  # "pending", "approved", "rejected"


# --- API Endpoints ---
@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/invoices")
async def list_all_invoices(
    status: Optional[str] = None, limit: int = 100, offset: int = 0
):
    """
    List all invoices from the InvoiceStore.

    Args:
        status: Optional status filter ("PENDING", "APPROVED", "REJECTED")
        limit: Maximum number of invoices to return (default: 100)
        offset: Number of invoices to skip for pagination (default: 0)

    Returns:
        List of all invoices with their current status
    """
    logger.info(
        f"Gateway: Listing invoices with status={status}, limit={limit}, offset={offset}"
    )

    try:
        async with grpc.aio.insecure_channel(INVOICESTORE_GRPC_URL) as channel:
            stub = invoicestore_pb2_grpc.InvoiceStoreStub(channel)

            # Create request with optional filters
            request = invoicestore_pb2.ListInvoicesRequest(
                status=status or "", limit=limit, offset=offset
            )

            response = await stub.ListInvoices(request)

            if response.success:
                invoices = []
                for invoice in response.invoices:
                    # Convert status to lowercase for frontend consistency
                    status_lower = (
                        invoice.status.lower() if invoice.status else "unknown"
                    )

                    invoices.append(
                        {
                            "id": str(invoice.id),
                            "lift_ticket": invoice.lift_ticket,
                            "file_id": invoice.file_id,
                            "vendor_name": invoice.vendor_name,
                            "invoice_number": invoice.invoice_number,
                            "invoice_date": invoice.invoice_date,
                            "total_amount": invoice.total_amount,
                            "purchase_order_number": invoice.purchase_order_number,
                            "payment_terms": invoice.payment_terms,
                            "due_date": invoice.due_date,
                            "status": status_lower,
                            "created_at": invoice.created_at,
                            "rejection_reason": invoice.status_desc
                            if status_lower == "rejected"
                            else None,
                            # Additional fields for completeness
                            "banking_details": invoice.banking_details,
                            "memo_description": invoice.memo_description,
                            "shipped_to_address": invoice.shipped_to_address,
                            "service_start_date": invoice.service_start_date,
                            "service_end_date": invoice.service_end_date,
                            "quantity": invoice.quantity,
                            "unit_price": invoice.unit_price,
                            "payment_type": invoice.payment_type,
                            "vendor_tax_id": invoice.vendor_tax_id,
                            "snowflake_tax_id": invoice.snowflake_tax_id,
                            "prepaid_flag": invoice.prepaid_flag,
                        }
                    )

                logger.info(
                    f"Gateway: Successfully retrieved {len(invoices)} invoices (total: {response.total_count})"
                )
                return {
                    "success": True,
                    "invoices": invoices,
                    "total_count": response.total_count,
                    "limit": limit,
                    "offset": offset,
                }
            else:
                logger.error(f"Gateway: Failed to list invoices: {response.message}")
                raise HTTPException(status_code=500, detail=response.message)

    except grpc.aio.AioRpcError as e:
        logger.error(f"gRPC error while listing invoices: {e.details()}")
        raise HTTPException(
            status_code=502,
            detail=f"Error communicating with InvoiceStore service: {e.details()}",
        )
    except Exception as e:
        logger.error(f"Unexpected error during invoice listing: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/list-files-by-ticket")
async def list_files_by_ticket(lift_ticket: str):
    """
    List all files associated with a lift ticket for AI Agent processing.

    Returns metadata for all files including file_id, filename, and size.
    The AI Agent can then decide which files to process and in what order.
    """
    logger.info(f"Gateway: Listing files for lift ticket: {lift_ticket}")

    try:
        # Step 1: Get file_ids from InvoiceStore
        async with grpc.aio.insecure_channel(INVOICESTORE_GRPC_URL) as channel:
            stub = invoicestore_pb2_grpc.InvoiceStoreStub(channel)
            request = invoicestore_pb2.GetSubmissionRequest(lift_ticket=lift_ticket)
            response = await stub.GetSubmission(request)

            if not response.success or not response.file_ids:
                logger.error(f"Gateway: No files found for lift ticket: {lift_ticket}")
                raise HTTPException(
                    status_code=404,
                    detail=f"No files found for lift ticket: {lift_ticket}",
                )

            logger.info(
                f"Gateway: Found {len(response.file_ids)} file(s) for lift ticket {lift_ticket}"
            )

        # Step 2: Get metadata for each file from FileStore
        files_metadata = []
        async with grpc.aio.insecure_channel(FILESTORE_GRPC_URL) as channel:
            stub = filestore_pb2_grpc.FileStoreStub(channel)

            for file_id in response.file_ids:
                try:
                    # Get file info (we'll peek at the first chunk for metadata)
                    request = filestore_pb2.DownloadRequest(file_id=file_id)
                    first_chunk = None
                    file_size = 0
                    filename = "unknown"

                    async for chunk in stub.DownloadFile(request):
                        if first_chunk is None:
                            first_chunk = chunk
                            filename = chunk.filename or f"file_{file_id}"
                        file_size += len(chunk.content)
                        # Don't download the whole file, just get metadata
                        if (
                            file_size > 1024 * 1024
                        ):  # Stop after 1MB to avoid loading huge files
                            break

                    files_metadata.append(
                        {
                            "file_id": file_id,
                            "filename": filename,
                            "size_bytes": file_size,
                            "type": "pdf"
                            if filename.lower().endswith(".pdf")
                            else "unknown",
                        }
                    )

                except Exception as e:
                    logger.warning(
                        f"Could not get metadata for file {file_id}: {str(e)}"
                    )
                    files_metadata.append(
                        {
                            "file_id": file_id,
                            "filename": f"file_{file_id}",
                            "size_bytes": 0,
                            "type": "unknown",
                            "error": str(e),
                        }
                    )

        logger.info(f"Gateway: Returning metadata for {len(files_metadata)} files")
        return {
            "lift_ticket": lift_ticket,
            "file_count": len(files_metadata),
            "files": files_metadata,
        }

    except grpc.aio.AioRpcError as e:
        logger.error(f"gRPC error: {e.details()}")
        raise HTTPException(status_code=502, detail=f"Service error: {e.details()}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/extract-invoice-by-file-id", response_model=ExtractResponse)
async def extract_invoice_by_file_id(file_id: str):
    """
    Download a file by ID and extract invoice data in one call.

    This is a convenience endpoint for AI Agents that combines:
    1. Downloading the file from FileStore by file_id
    2. Extracting invoice data using the Extractor service
    3. Returning structured invoice data

    Perfect for n8n workflows where you want a single tool call.
    """
    logger.info(f"Gateway: Extracting invoice data from file ID: {file_id}")

    try:
        # Step 1: Download file from FileStore
        file_content = b""
        filename = "invoice.pdf"

        async with grpc.aio.insecure_channel(FILESTORE_GRPC_URL) as channel:
            stub = filestore_pb2_grpc.FileStoreStub(channel)
            download_request = filestore_pb2.DownloadRequest(file_id=file_id)

            async for chunk in stub.DownloadFile(download_request):
                if chunk.filename and not filename.endswith(chunk.filename):
                    filename = chunk.filename
                file_content += chunk.content

            logger.info(
                f"Gateway: Downloaded {len(file_content)} bytes for file {filename}"
            )

        if not file_content:
            raise HTTPException(
                status_code=404, detail=f"File with ID {file_id} not found or is empty"
            )

        # Step 2: Extract invoice data using Extractor service
        async with grpc.aio.insecure_channel(EXTRACTOR_GRPC_URL) as channel:
            stub = extractor_pb2_grpc.ExtractorStub(channel)

            # Create chunk generator for streaming upload to extractor
            def chunk_generator():
                chunk_size = 1024 * 1024  # 1MB chunks

                for i in range(0, len(file_content), chunk_size):
                    chunk_data = file_content[i : i + chunk_size]
                    is_last = (i + chunk_size) >= len(file_content)

                    yield extractor_pb2.FileChunk(
                        filename=filename, content=chunk_data, is_last=is_last
                    )

            # Call the extractor service
            response = await stub.Extract(chunk_generator())

            if response.success:
                logger.info(
                    f"Gateway: Successfully extracted data from file ID {file_id} ({filename})"
                )
                return ExtractResponse(
                    success=response.success,
                    message=response.message,
                    file_id=file_id,  # Use the original file_id from request
                    vendor_name=response.vendor_name,
                    invoice_number=response.invoice_number,
                    total_amount=response.total_amount,
                    purchase_order_number=response.purchase_order_number,
                    payment_terms=response.payment_terms,
                    due_date=response.due_date,
                    file_url=response.furl,  # Note: proto field is 'furl', not 'file_url'
                    banking_details=response.banking_details,
                    freight_shipping_amount=response.freight_shipping_amount,
                    invoice_currency=response.invoice_currency,
                    invoice_date=response.invoice_date,
                    memo_description=response.memo_description,
                    payment_type=response.payment_type,
                    prepaid_flag=response.prepaid_flag,
                    quantity=response.quantity,
                    service_end_date=response.service_end_date,
                    service_start_date=response.service_start_date,
                    shipped_to_address=response.shipped_to_address,
                    snowflake_entity=response.snowflake_entity,
                    snowflake_tax_id=response.snowflake_tax_id,
                    tax_amount=response.tax_amount,
                    unit_price=response.unit_price,
                    vendor_address=response.vendor_address,
                    vendor_tax_id=response.vendor_tax_id,
                )
            else:
                logger.error(
                    f"Gateway: Extraction failed for file ID {file_id}: {response.message}"
                )
                raise HTTPException(
                    status_code=422,
                    detail=f"Invoice extraction failed: {response.message}",
                )

    except grpc.aio.AioRpcError as e:
        logger.error(f"gRPC error while processing file ID {file_id}: {e.details()}")
        raise HTTPException(
            status_code=502,
            detail=f"Error communicating with services: {e.details()}",
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during extraction for file ID {file_id}: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/create-invoice", response_model=CreateInvoiceResponse)
async def create_invoice(request: CreateInvoiceRequest):
    """
    Create a new invoice in the InvoiceStore with extracted data.

    This endpoint:
    1. Creates an invoice record with all the extracted data
    2. Optionally approves or rejects the invoice based on the action flag
    3. Returns the invoice ID and final status

    Action values:
    - "pending" (default): Creates invoice in pending state
    - "approve": Creates invoice and immediately approves it
    - "reject": Creates invoice and immediately rejects it (requires rejection_reason)
    """
    logger.info(f"Gateway: Creating invoice for lift ticket: {request.lift_ticket}")

    try:
        # Step 1: Create the invoice
        async with grpc.aio.insecure_channel(INVOICESTORE_GRPC_URL) as channel:
            stub = invoicestore_pb2_grpc.InvoiceStoreStub(channel)

            # Create the invoice request
            create_request = invoicestore_pb2.CreateInvoiceRequest(
                lift_ticket=request.lift_ticket,
                file_id=request.file_id,
                vendor_name=request.vendor_name or "",
                invoice_number=request.invoice_number or "",
                invoice_date=request.invoice_date or "",
                total_amount=request.total_amount or "",
                purchase_order_number=request.purchase_order_number or "",
                banking_details=request.banking_details or "",
                payment_terms=request.payment_terms or "",
                memo_description=request.memo_description or "",
                shipped_to_address=request.shipped_to_address or "",
                service_start_date=request.service_start_date or "",
                service_end_date=request.service_end_date or "",
                quantity=request.quantity or "",
                unit_price=request.unit_price or "",
                payment_type=request.payment_type or "",
                due_date=request.due_date or "",
                vendor_tax_id=request.vendor_tax_id or "",
                snowflake_tax_id=request.snowflake_tax_id or "",
                prepaid_flag=request.prepaid_flag or "",
            )

            # Create the invoice
            create_response = await stub.CreateInvoice(create_request)

            if not create_response.success:
                logger.error(
                    f"Gateway: Failed to create invoice: {create_response.message}"
                )
                raise HTTPException(
                    status_code=422,
                    detail=f"Failed to create invoice: {create_response.message}",
                )

            invoice_id = create_response.invoice_id
            logger.info(f"Gateway: Successfully created invoice {invoice_id}")

            # Step 2: Handle approval/rejection based on action flag
            final_status = "pending"
            final_message = create_response.message

            if request.action == "approve":
                approve_request = invoicestore_pb2.ApproveInvoiceRequest(
                    invoice_id=invoice_id
                )
                approve_response = await stub.ApproveInvoice(approve_request)

                if approve_response.succes:  # Note: proto has typo "succes"
                    final_status = "approved"
                    final_message = (
                        f"Invoice {invoice_id} created and approved successfully"
                    )
                    logger.info(f"Gateway: Successfully approved invoice {invoice_id}")
                else:
                    logger.warning(
                        f"Gateway: Failed to approve invoice {invoice_id}: {approve_response.message}"
                    )
                    final_message = f"Invoice {invoice_id} created but approval failed: {approve_response.message}"

            elif request.action == "reject":
                if not request.rejection_reason:
                    raise HTTPException(
                        status_code=400,
                        detail="rejection_reason is required when action is 'reject'",
                    )

                reject_request = invoicestore_pb2.RejectInvoiceRequest(
                    invoice_id=invoice_id, reason=request.rejection_reason
                )
                reject_response = await stub.RejectInvoice(reject_request)

                if reject_response.succes:  # Note: proto has typo "succes"
                    final_status = "rejected"
                    final_message = f"Invoice {invoice_id} created and rejected: {request.rejection_reason}"
                    logger.info(f"Gateway: Successfully rejected invoice {invoice_id}")
                else:
                    logger.warning(
                        f"Gateway: Failed to reject invoice {invoice_id}: {reject_response.message}"
                    )
                    final_message = f"Invoice {invoice_id} created but rejection failed: {reject_response.message}"

            return CreateInvoiceResponse(
                success=True,
                message=final_message,
                invoice_id=invoice_id,
                status=final_status,
            )

    except grpc.aio.AioRpcError as e:
        logger.error(f"gRPC error while creating invoice: {e.details()}")
        raise HTTPException(
            status_code=502,
            detail=f"Error communicating with InvoiceStore service: {e.details()}",
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error during invoice creation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
