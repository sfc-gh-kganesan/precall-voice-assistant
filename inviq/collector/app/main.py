import logging
import os
from typing import Annotated

import grpc
import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile

# Import gRPC stubs for both filestore and invoicestore
from py_protos import (
    filestore_pb2,
    filestore_pb2_grpc,
    invoicestore_pb2,
    invoicestore_pb2_grpc,
)
from pydantic import BaseModel

from .logging import initialize_logging


# --- Pydantic Models for HTTP API ---
class FileUploadResponse(BaseModel):
    success: bool
    message: str
    file_id: str


class SubmissionResponse(BaseModel):
    success: bool
    message: str


class UploadResponse(BaseModel):
    lift_ticket: str
    success: bool
    message: str
    file_ids: list[str]


N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")

# --- FastAPI Application Setup ---
app = FastAPI(title="Collector API", version="0.1.0")
initialize_logging()
logger = logging.getLogger(__name__)


@app.get("/")
async def root():
    return {"message": "Hello World..."}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


async def upload_file_to_filestore(file: UploadFile) -> FileUploadResponse:
    """
    Upload a file to the filestore service via gRPC.

    Args:
        file: The file to upload

    Returns:
        FileUploadResponse indicating success or failure
    """
    try:
        channel = grpc.insecure_channel("filestore:50051")
        stub = filestore_pb2_grpc.FileStoreStub(channel)

        # Read file content
        content = await file.read()

        # Create file chunks for streaming
        def chunk_generator():
            chunk_size = 1024 * 1024  # 1MB chunks
            filename = file.filename or "unknown"

            for i in range(0, len(content), chunk_size):
                chunk_data = content[i : i + chunk_size]
                is_last = (i + chunk_size) >= len(content)

                yield filestore_pb2.FileChunk(filename=filename, content=chunk_data, is_last=is_last)

        # Upload file
        response = stub.UploadFile(chunk_generator())

        # Close channel
        channel.close()

        return FileUploadResponse(success=response.success, message=response.message, file_id=response.file_id)

    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        return FileUploadResponse(success=False, message=f"Failed to upload file: {str(e)}", file_id="")


async def write_to_invoicestore(lift_ticket: str, file_ids: list[str]) -> SubmissionResponse:
    """
    Write a submission to the invoicestore service via gRPC.

    Args:
        lift_ticket: Service Now ticket number
        file_ids: List of file IDs to associate with the submission

    Returns:
        SubmissionResponse indicating success or failure
    """
    try:
        # Create gRPC channel
        channel = grpc.insecure_channel("invoicestore:50051")
        stub = invoicestore_pb2_grpc.InvoiceStoreStub(channel)

        # Upload submission
        response = stub.Submit(invoicestore_pb2.SubmissionRequest(lift_ticket=lift_ticket, file_ids=file_ids))

        # Close channel
        channel.close()

        return SubmissionResponse(success=response.success, message=response.message)

    except Exception as e:
        logger.error(f"Error with submission: {str(e)}")
        return SubmissionResponse(success=False, message=f"Failed to submit submission: {str(e)}")


async def trigger_n8n_workflow(lift_ticket: str):
    """Triggers the n8n workflow by sending the submission ID to a webhook."""
    if not N8N_WEBHOOK_URL:
        logger.warning("N8N_WEBHOOK_URL not set. Skipping workflow trigger.")
        return

    async with httpx.AsyncClient() as client:
        try:
            await client.post(N8N_WEBHOOK_URL, json={"lift_ticket_id": lift_ticket})
            logger.info(f"Successfully triggered n8n workflow for ticket {lift_ticket}")
        except httpx.HTTPError as e:
            logger.error(f"Failed to trigger n8n workflow for ticket {lift_ticket}: {e}")


@app.post("/upload", response_model=UploadResponse)
async def upload(
    lift_ticket: Annotated[str, Form()],
    files: Annotated[list[UploadFile], File()],
) -> UploadResponse:
    """
    Upload invoice files for processing.

    Args:
        lift_ticket: Service Now ticket number
        files: List of files attached to the original email

    Returns:
        Upload confirmation with ticket number and file details
    """
    if len(files) > 0:
        file = files[0]
        if not file.filename:
            logger.debug("No filename provided in the uploaded file.")
            raise HTTPException(status_code=400, detail="No filename provided")

        results: list[FileUploadResponse] = []
        for file in files:
            result = await upload_file_to_filestore(file)
            if not result.success:
                logger.error(f"File upload failed for ticket {lift_ticket}: {result.message}")
                raise HTTPException(status_code=500, detail=result.message)
            logger.info(
                f"File uploaded successfully for ticket {lift_ticket}:"
                + f"{file.filename} with ID {result.file_id} ({result.message})"
            )
            results.append(result)

        # Step 2: Create the submission record in InvoiceStore via gRPC
        submission_result = await write_to_invoicestore(lift_ticket, [r.file_id for r in results])

        # Step 3: Trigger the n8n workflow (fire and forget)
        await trigger_n8n_workflow(lift_ticket)

        return UploadResponse(
            lift_ticket=lift_ticket,
            success=submission_result.success,
            message=submission_result.message,
            file_ids=[result.file_id for result in results],
        )
    else:
        raise HTTPException(status_code=400, detail="No file provided")
