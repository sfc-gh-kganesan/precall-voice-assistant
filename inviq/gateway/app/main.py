import os
import logging
import grpc
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional

# Import gRPC stubs
from py_protos import (
    invoicestore_pb2,
    invoicestore_pb2_grpc,
    extractor_pb2,
    extractor_pb2_grpc,
)

# --- Environment Variables for Service Discovery ---
INVOICESTORE_GRPC_URL = os.getenv("INVOICESTORE_GRPC_URL", "localhost:50051")
EXTRACTOR_GRPC_URL = os.getenv("EXTRACTOR_GRPC_URL", "localhost:50051")

# --- FastAPI App Initialization ---
app = FastAPI(title="InvoiceIQ Gateway API", version="0.1.0")
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


# --- API Endpoints ---
@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/extract-invoice", response_model=ExtractResponse)
async def extract_invoice(file: UploadFile = File(...)):
    """
    Extract invoice data from an uploaded file using the Extractor service.

    This endpoint accepts a file upload and returns structured invoice data
    including vendor information, amounts, payment terms, etc.
    """
    logger.info(f"Gateway: Extracting invoice data from file: {file.filename}")

    try:
        # Read the uploaded file content
        file_content = await file.read()

        # Connect to the Extractor service
        async with grpc.aio.insecure_channel(EXTRACTOR_GRPC_URL) as channel:
            stub = extractor_pb2_grpc.ExtractorStub(channel)

            # Create chunk generator for streaming upload
            def chunk_generator():
                chunk_size = 1024 * 1024  # 1MB chunks
                filename = file.filename or "unknown"

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
                    f"Gateway: Successfully extracted data from {file.filename}"
                )
                return ExtractResponse(
                    success=response.success,
                    message=response.message,
                    file_id=response.file_id,
                    vendor_name=response.vendor_name,
                    total_amount=response.total_amount,
                    purchase_order_number=response.purchase_order_number,
                    payment_terms=response.payment_terms,
                    file_url=response.furl,
                )
            else:
                logger.error(
                    f"Gateway: Extraction failed for {file.filename}: {response.message}"
                )
                raise HTTPException(
                    status_code=422,
                    detail=f"Invoice extraction failed: {response.message}",
                )

    except grpc.aio.AioRpcError as e:
        logger.error(f"gRPC error while calling Extractor: {e.details()}")
        raise HTTPException(
            status_code=502,
            detail=f"Error communicating with Extractor service: {e.details()}",
        )
    except Exception as e:
        logger.error(f"Unexpected error during extraction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/test-invoicestore-failure")
async def test_invoicestore_failure():
    """
    A temporary test endpoint to confirm connectivity to the InvoiceStore.
    It intentionally sends an invalid request to trigger a failure response.
    """
    logger.info("Gateway: Sending intentional failure request to InvoiceStore...")
    try:
        async with grpc.aio.insecure_channel(INVOICESTORE_GRPC_URL) as channel:
            stub = invoicestore_pb2_grpc.InvoiceStoreStub(channel)
            # Send an invalid request with an empty lift_ticket and no file_ids
            request = invoicestore_pb2.SubmissionRequest(lift_ticket="", file_ids=[])
            response = await stub.Submit(request)

            # We expect this to fail, so receiving a success response is unexpected
            if response.success:
                raise HTTPException(
                    status_code=500,
                    detail=f"Unexpected success from InvoiceStore: {response.message}",
                )

            # Return the failure message from the service
            return {
                "message": "Successfully received expected failure from InvoiceStore.",
                "service_response": response.message,
                "service_success_flag": response.success,
            }
    except grpc.aio.AioRpcError as e:
        # This is the most likely outcome if the service is unreachable
        logger.error(f"gRPC error while testing InvoiceStore: {e.details()}")
        raise HTTPException(
            status_code=502,
            detail=f"Error communicating with InvoiceStore: {e.details()}",
        )
