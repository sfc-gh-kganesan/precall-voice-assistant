import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from loguru import logger
from pydantic import BaseModel

from . import snowflake

FILE_UPLOAD_DIR = Path(os.getenv("FILE_UPLOAD_DIR", tempfile.TemporaryDirectory().name))
logger.info(f"File uploads will be stored in {FILE_UPLOAD_DIR.absolute()}")
FILE_UPLOAD_DIR.mkdir(exist_ok=True)

DEFAULT_SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
DEFAULT_SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
DEFAULT_SNOWFLAKE_PASSWORD = os.getenv("SNOWFLAKE_PAT")
DEFAULT_SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE") or "compute_wh"
DEFAULT_SNOWFLAKE_ROLE = os.getenv("SNOWFLAKE_ROLE") or "invoiceiq_admin"
DEFAULT_SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE") or "invoiceiq"
DEFAULT_SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA") or "service"
DEFAULT_SNOWFLAKE_STAGE = os.getenv("SNOWFLAKE_STAGE") or "ticket_attachments"
DEFAULT_SNOWFLAKE_TICKET_METADATA_TABLE = (
    os.getenv("SNOWFLAKE_TICKET_METADATA_TABLE") or "invoiceiq.service.ticket_metadata"
)
DEFAULT_SNOWFLAKE_FILE_METADATA_TABLE = os.getenv("SNOWFLAKE_FILE_METADATA_TABLE") or "invoiceiq.service.file_metadata"


def _resolve(value: str | None, default: str | None, label: str, *, required: bool = True) -> str:
    candidates = (value, default)
    for candidate in candidates:
        if candidate is None:
            continue
        trimmed = candidate.strip()
        if trimmed:
            return trimmed
    if required:
        raise ValueError(f"{label} must be provided")
    return ""


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
    snowflake_database: Annotated[str | None, Form()] = DEFAULT_SNOWFLAKE_DATABASE,
    snowflake_schema: Annotated[str | None, Form()] = DEFAULT_SNOWFLAKE_SCHEMA,
    snowflake_stage: Annotated[str | None, Form()] = DEFAULT_SNOWFLAKE_STAGE,
    snowflake_account: Annotated[str | None, Form()] = DEFAULT_SNOWFLAKE_ACCOUNT,
    snowflake_user: Annotated[str | None, Form()] = DEFAULT_SNOWFLAKE_USER,
    snowflake_password: Annotated[str | None, Form()] = DEFAULT_SNOWFLAKE_PASSWORD,
    snowflake_warehouse: Annotated[str | None, Form()] = DEFAULT_SNOWFLAKE_WAREHOUSE,
    snowflake_role: Annotated[str | None, Form()] = DEFAULT_SNOWFLAKE_ROLE,
    snowflake_ticket_metadata: Annotated[str | None, Form()] = DEFAULT_SNOWFLAKE_TICKET_METADATA_TABLE,
    snowflake_file_metadata: Annotated[str | None, Form()] = DEFAULT_SNOWFLAKE_FILE_METADATA_TABLE,
) -> SubmitTicketResponse:
    """
    Submit ticket

    Args:
        ticket_number: Service Now ticket number
        files: List of files attached to the original email
        email: Sender of the original email
        snowflake_database: Snowflake database to target
        snowflake_schema: Snowflake schema to target
        snowflake_stage: Snowflake stage for file uploads
        snowflake_account: Snowflake account identifier
        snowflake_user: Snowflake username
        snowflake_password: Snowflake password or PAT
        snowflake_warehouse: Snowflake warehouse to use
        snowflake_role: Snowflake role to assume
        snowflake_ticket_metadata: Fully-qualified ticket metadata table name
        snowflake_file_metadata: Fully-qualified file metadata table name

    Returns:
        Confirmation with submission id
    """
    try:
        account = _resolve(snowflake_account, DEFAULT_SNOWFLAKE_ACCOUNT, "Snowflake account")
        user = _resolve(snowflake_user, DEFAULT_SNOWFLAKE_USER, "Snowflake user")
        password = _resolve(snowflake_password, DEFAULT_SNOWFLAKE_PASSWORD, "Snowflake password")
        warehouse = _resolve(snowflake_warehouse, DEFAULT_SNOWFLAKE_WAREHOUSE, "Snowflake warehouse")
        role = _resolve(snowflake_role, DEFAULT_SNOWFLAKE_ROLE, "Snowflake role")
        database = _resolve(snowflake_database, DEFAULT_SNOWFLAKE_DATABASE, "Snowflake database")
        schema = _resolve(snowflake_schema, DEFAULT_SNOWFLAKE_SCHEMA, "Snowflake schema")
        stage = _resolve(snowflake_stage, DEFAULT_SNOWFLAKE_STAGE, "Snowflake stage")
        ticket_metadata_table = _resolve(
            snowflake_ticket_metadata,
            DEFAULT_SNOWFLAKE_TICKET_METADATA_TABLE,
            "Snowflake ticket metadata table",
        )
        file_metadata_table = _resolve(
            snowflake_file_metadata,
            DEFAULT_SNOWFLAKE_FILE_METADATA_TABLE,
            "Snowflake file metadata table",
        )

        connection_kwargs = {
            "account": account,
            "user": user,
            "password": password,
            "warehouse": warehouse,
            "role": role,
        }

        snowflake.whoami(database=database, schema=schema, **connection_kwargs)
        submission_id = uuid.uuid4().hex
        snowflake.insert_ticket_metadata(
            submission_id,
            ticket_number,
            email,
            database=database,
            schema=schema,
            table=ticket_metadata_table,
            **connection_kwargs,
        )

        if len(files) > 0:
            # save all uploaded files in a temp directory
            uploaded_files = []
            for file in files:
                filename = file.filename or "noname.bin"
                abs = FILE_UPLOAD_DIR.joinpath(filename)
                try:
                    with abs.open("wb") as out_file:
                        shutil.copyfileobj(file.file, out_file)
                finally:
                    await file.close()
                uploaded_files.append(filename)

            # run snowflake PUT command to store all of these files
            # in the stage
            snowflake.stage_put_files(
                FILE_UPLOAD_DIR,
                "*",
                database=database,
                schema=schema,
                stage=stage,
                **connection_kwargs,
            )
            for filename in uploaded_files:
                snowflake.insert_file_metadata(
                    filename,
                    filename,
                    ticket_number,
                    database=database,
                    schema=schema,
                    table=file_metadata_table,
                    **connection_kwargs,
                )

        return SubmitTicketResponse(
            submission_id=submission_id,
            success=True,
            ticket_number=ticket_number,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
