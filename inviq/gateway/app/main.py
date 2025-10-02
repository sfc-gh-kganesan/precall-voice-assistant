import os
import logging
import grpc
from fastapi import FastAPI, HTTPException, UploadFile, File, Response, Request
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
                    detail=f"No files found for lift ticket: {lift_ticket}"
                )
            
            logger.info(f"Gateway: Found {len(response.file_ids)} file(s) for lift ticket {lift_ticket}")
            
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
                        if file_size > 1024 * 1024:  # Stop after 1MB to avoid loading huge files
                            break
                    
                    files_metadata.append({
                        "file_id": file_id,
                        "filename": filename,
                        "size_bytes": file_size,
                        "type": "pdf" if filename.lower().endswith('.pdf') else "unknown"
                    })
                    
                except Exception as e:
                    logger.warning(f"Could not get metadata for file {file_id}: {str(e)}")
                    files_metadata.append({
                        "file_id": file_id,
                        "filename": f"file_{file_id}",
                        "size_bytes": 0,
                        "type": "unknown",
                        "error": str(e)
                    })
        
        logger.info(f"Gateway: Returning metadata for {len(files_metadata)} files")
        return {
            "lift_ticket": lift_ticket,
            "file_count": len(files_metadata),
            "files": files_metadata
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
                
            logger.info(f"Gateway: Downloaded {len(file_content)} bytes for file {filename}")
        
        if not file_content:
            raise HTTPException(
                status_code=404,
                detail=f"File with ID {file_id} not found or is empty"
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
                    invoice_number=None,  # Not available in extractor response
                    total_amount=response.total_amount,
                    purchase_order_number=response.purchase_order_number,
                    payment_terms=response.payment_terms,
                    due_date=None,  # Not available in extractor response
                    file_url=response.furl,  # Note: proto field is 'furl', not 'file_url'
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
        logger.error(f"Unexpected error during extraction for file ID {file_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
