from typing import Annotated

from fastapi import FastAPI, File, Form, UploadFile
from pydantic import BaseModel


class UploadResponse(BaseModel):
    message: str
    ticket_number: str
    files_received: int
    filenames: list[str]


app = FastAPI(title="Collector API", version="0.1.0")


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/upload", response_model=UploadResponse)
async def upload_invoice(
    ticket_number: Annotated[str, Form()],
    files: Annotated[list[UploadFile], File()],
) -> UploadResponse:
    """
    Upload invoice files for processing.

    Args:
        ticket_number: Service Now ticket number
        files: List of files attached to the original email

    Returns:
        Upload confirmation with ticket number and file details
    """
    filenames = [file.filename for file in files if file.filename]

    return UploadResponse(
        message="Files uploaded successfully",
        ticket_number=ticket_number,
        files_received=len(files),
        filenames=filenames,
    )
