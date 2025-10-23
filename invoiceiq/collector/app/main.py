import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, UploadFile
from loguru import logger
from pydantic import BaseModel

from . import snowflake

FILE_UPLOAD_DIR = Path(os.getenv("FILE_UPLOAD_DIR", tempfile.TemporaryDirectory().name))
logger.info(f"File uploads will be stored in {FILE_UPLOAD_DIR.absolute()}")
FILE_UPLOAD_DIR.mkdir(exist_ok=True)


# --- Pydantic Models for HTTP API ---
class SubmitTicketResponse(BaseModel):
    ticket_number: str
    success: bool
    submission_id: str


# --- FastAPI Application Setup ---
app = FastAPI(title="Collector API", version="0.1.0")


@app.get("/")
async def root():
    return {"message": "Hello World..."}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/submit", response_model=SubmitTicketResponse)
async def submit_ticket(
    ticket_number: Annotated[str, Form()],
    files: Annotated[list[UploadFile], File()],
    email: Annotated[str, Form()],
) -> SubmitTicketResponse:
    """
    Submit ticket

    Args:
        ticket_number: Service Now ticket number
        files: List of files attached to the original email
        email_from: Sender of the original email
        email_to: To line from the original email
        email_subject: Subject line from original email

    Returns:
        Confirmation with submission id
    """
    snowflake.whoami()
    submission_id = uuid.uuid4().hex
    snowflake.insert_ticket_metadata(submission_id, ticket_number, email)

    if len(files) > 0:
        # save all uploaded files in a temp directory, with filenames
        # prefixed with submission id
        for file in files:
            filename = file.filename or "noname.bin"
            safename = f"{submission_id}_{uuid.uuid4().hex}_{filename}"
            abs = FILE_UPLOAD_DIR.joinpath(safename)
            try:
                with abs.open("wb") as out_file:
                    shutil.copyfileobj(file.file, out_file)
            finally:
                await file.close()

        # run snowflake PUT command to store all of these files
        # in the stage
        results = snowflake.stage_put_files(FILE_UPLOAD_DIR, f"{submission_id}_*")
        for r in results:
            snowflake.insert_file_metadata(submission_id, r, ticket_number)

    return SubmitTicketResponse(
        submission_id=submission_id,
        success=True,
        ticket_number=ticket_number,
    )
