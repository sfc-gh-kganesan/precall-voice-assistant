from typing import Annotated

import grpc
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from py_protos import filestore_pb2, filestore_pb2_grpc
from pydantic import BaseModel


class UploadResponse(BaseModel):
    message: str
    ticket_number: str
    files_received: int
    filenames: list[str]


class FileUploadResponse(BaseModel):
    success: bool
    message: str
    file_id: str


class UploadInvoiceResponse(BaseModel):
    ticket_number: str
    success: bool
    message: str
    file_ids: list[str]


app = FastAPI(title="Collector API", version="0.1.0")


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


async def upload_file_to_filestore(file) -> FileUploadResponse:
    """Upload a file to the filestore service via gRPC."""
    try:
        # Create gRPC channel
        channel = grpc.insecure_channel("localhost:50051")
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

                yield filestore_pb2.FileChunk(
                    filename=filename, content=chunk_data, is_last=is_last
                )

        # Upload file
        response = stub.UploadFile(chunk_generator())

        # Close channel
        channel.close()

        return FileUploadResponse(
            success=response.success, message=response.message, file_id=response.file_id
        )

    except Exception as e:
        return FileUploadResponse(
            success=False, message=f"Failed to upload file: {str(e)}", file_id=""
        )


@app.post("/upload", response_model=UploadInvoiceResponse)
async def upload_file(
    ticket_number: Annotated[str, Form()],
    files: Annotated[list[UploadFile], File()],
) -> UploadInvoiceResponse:
    """
    Upload invoice files for processing.

    Args:
        ticket_number: Service Now ticket number
        files: List of files attached to the original email

    Returns:
        Upload confirmation with ticket number and file details
    """
    if len(files) > 0:
        file = files[0]
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        results: list[FileUploadResponse] = []
        for file in files:
            result = await upload_file_to_filestore(file)
            if not result.success:
                raise HTTPException(status_code=500, detail=result.message)
            results.append(result)
        return UploadInvoiceResponse(
            ticket_number=ticket_number,
            success=True,
            message="All files uploaded successfully",
            file_ids=[result.file_id for result in results],
        )
    else:
        raise HTTPException(status_code=400, detail="No file provided")
