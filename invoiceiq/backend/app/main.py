import os
import logging
import tempfile
import json
from typing import Optional, List
from contextlib import contextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import snowflake.connector
from snowflake.connector import DictCursor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(title="InvoiceIQ Backend API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Snowflake connection config
SNOWFLAKE_CONFIG = {
    "account": os.getenv("SNOWFLAKE_ACCOUNT"),
    "user": os.getenv("SNOWFLAKE_USER"),
    "authenticator": "SNOWFLAKE_JWT",
    "private_key_file": os.getenv("SNOWFLAKE_KEY"),
    "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
    "database": os.getenv("SNOWFLAKE_DATABASE", "INVOICEIQ"),
    "schema": os.getenv("SNOWFLAKE_SCHEMA", "SERVICE"),
    "role": os.getenv("SNOWFLAKE_ROLE"),
}


# Pydantic models
class Invoice(BaseModel):
    id: str  # TICKET_NUMBER
    ticket_number: str
    status: str  # approved, pending, rejected
    file_url: str
    relative_path: str
    # Extracted fields from VARIANT column
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    total_amount: Optional[str] = None
    purchase_order_number: Optional[str] = None
    due_date: Optional[str] = None
    # Metadata
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    email_from: Optional[str] = None
    email_subject: Optional[str] = None


class InvoiceListResponse(BaseModel):
    success: bool
    invoices: List[Invoice]
    total_count: int
    limit: int
    offset: int


# ============================================================================
# Helper Functions
# ============================================================================


@contextmanager
def get_snowflake_connection():
    """Context manager for Snowflake connections."""
    conn = None
    try:
        conn = snowflake.connector.connect(**SNOWFLAKE_CONFIG)
        logger.info("Successfully connected to Snowflake")
        yield conn
    except Exception as e:
        logger.error(f"Failed to connect to Snowflake: {e}")
        raise HTTPException(
            status_code=503, detail=f"Database connection failed: {str(e)}"
        )
    finally:
        if conn:
            conn.close()


def parse_extracted_fields(variant_data) -> dict:
    """Parse the EXTRACTED_FIELDS VARIANT column into a dict."""
    if isinstance(variant_data, dict):
        return variant_data
    elif isinstance(variant_data, str):
        try:
            return json.loads(variant_data)
        except (json.JSONDecodeError, ValueError):
            return {}
    else:
        return {}


def get_file_path_for_ticket(cursor, ticket_number: str) -> str:
    """Get the relative file path for a given ticket number."""
    query = """
        SELECT f.RELATIVE_PATH
        FROM TICKET_METADATA t
        JOIN FILE_METADATA f ON t.SUBMISSION_ID = f.SUBMISSION_ID
        WHERE t.TICKET_NUMBER = %s
        LIMIT 1
    """
    cursor.execute(query, (ticket_number,))
    row = cursor.fetchone()

    if not row or not row.get("RELATIVE_PATH"):
        raise HTTPException(
            status_code=404, detail=f"No file found for ticket {ticket_number}"
        )

    return row["RELATIVE_PATH"]


def download_file_from_stage(cursor, relative_path: str) -> str:
    """
    Download a file from Snowflake stage to local temp directory.
    Returns the local file path.
    """
    # Create temp directory
    temp_dir = tempfile.mkdtemp()

    # Construct stage path
    stage_path = f"@INVOICEIQ.SERVICE.TICKET_ATTACHMENTS/{relative_path}"

    # Download file using Snowflake GET command
    # Note: GET requires quotes around paths
    get_command = f"GET '{stage_path}' 'file://{temp_dir}/'"

    try:
        cursor.execute(get_command)

        # The file will be downloaded with its original name
        filename = relative_path.split("/")[-1]
        local_file_path = os.path.join(temp_dir, filename)

        if not os.path.exists(local_file_path):
            raise HTTPException(
                status_code=404, detail=f"File not found in stage: {stage_path}"
            )

        return local_file_path

    except Exception:
        # Clean up temp directory on error
        if os.path.exists(temp_dir):
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)
        raise


# ============================================================================
# API Endpoints
# ============================================================================


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "InvoiceIQ Backend"}


@app.get("/invoices", response_model=InvoiceListResponse)
async def list_invoices(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=500, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results to skip"),
):
    """
    List invoices with optional filtering and pagination.

    Query Parameters:
    - status: Filter by 'approved', 'pending', or 'rejected' (optional)
    - limit: Maximum invoices to return (default: 50, max: 500)
    - offset: Number of invoices to skip for pagination (default: 0)
    """
    logger.info(f"Listing invoices: status={status}, limit={limit}, offset={offset}")

    try:
        with get_snowflake_connection() as conn:
            cursor = conn.cursor(DictCursor)

            # Build query with optional status filter
            query = """
                SELECT 
                    t.TICKET_NUMBER,
                    t.EMAIL,
                    t.CREATED_AT,
                    f.RELATIVE_PATH,
                    f.STATUS,
                    f.EXTRACTED_FIELDS,
                    f.UPDATED_AT
                FROM TICKET_METADATA t
                LEFT JOIN FILE_METADATA f ON t.SUBMISSION_ID = f.SUBMISSION_ID
                WHERE f.RELATIVE_PATH IS NOT NULL
            """

            params = []
            if status:
                query += " AND UPPER(f.STATUS) = %s"
                params.append(status.upper())

            # Get total count
            count_query = f"SELECT COUNT(*) as total FROM ({query}) as subquery"
            cursor.execute(count_query, params)
            total_count = cursor.fetchone()["TOTAL"]

            # Add pagination and execute
            query += " ORDER BY t.CREATED_AT DESC LIMIT %s OFFSET %s"
            cursor.execute(query, params + [limit, offset])
            rows = cursor.fetchall()

            # Build invoice list
            invoices = []
            for row in rows:
                extracted = parse_extracted_fields(row.get("EXTRACTED_FIELDS"))
                relative_path = row.get("RELATIVE_PATH", "")

                invoices.append(
                    Invoice(
                        id=row["TICKET_NUMBER"],
                        ticket_number=row["TICKET_NUMBER"],
                        status=row.get("STATUS", "unknown").lower(),
                        file_url=f"@INVOICEIQ.SERVICE.TICKET_ATTACHMENTS/{relative_path}"
                        if relative_path
                        else "",
                        relative_path=relative_path,
                        vendor_name=extracted.get("vendor_name"),
                        invoice_number=extracted.get("invoice_number"),
                        invoice_date=extracted.get("invoice_date"),
                        total_amount=extracted.get("total_amount"),
                        purchase_order_number=extracted.get("purchase_order_number"),
                        due_date=extracted.get("due_date"),
                        created_at=str(row.get("CREATED_AT", "")),
                        updated_at=str(row.get("UPDATED_AT", "")),
                        email_from=row.get("EMAIL"),
                        email_subject=None,
                    )
                )

            logger.info(f"Retrieved {len(invoices)} invoices (total: {total_count})")
            return InvoiceListResponse(
                success=True,
                invoices=invoices,
                total_count=total_count,
                limit=limit,
                offset=offset,
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing invoices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/invoices/{ticket_number}/view")
async def view_invoice_pdf(ticket_number: str):
    """
    View invoice PDF in browser.
    Streams the PDF with 'inline' disposition for viewing in browser/PDF viewers.
    """
    logger.info(f"Viewing PDF for ticket: {ticket_number}")

    try:
        with get_snowflake_connection() as conn:
            cursor = conn.cursor(DictCursor)
            relative_path = get_file_path_for_ticket(cursor, ticket_number)
            local_file_path = download_file_from_stage(cursor, relative_path)

            logger.info(f"Serving PDF for viewing: {ticket_number}")

            # Serve file with inline disposition (opens in browser)
            return FileResponse(
                path=local_file_path,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"inline; filename={ticket_number}.pdf"
                },
                background=None,  # FastAPI will handle cleanup
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error viewing PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/invoices/{ticket_number}/download")
async def download_invoice_pdf(ticket_number: str):
    """
    Download invoice PDF file.
    Streams the PDF with 'attachment' disposition to trigger browser download.
    """
    logger.info(f"Downloading PDF for ticket: {ticket_number}")

    try:
        with get_snowflake_connection() as conn:
            cursor = conn.cursor(DictCursor)
            relative_path = get_file_path_for_ticket(cursor, ticket_number)
            local_file_path = download_file_from_stage(cursor, relative_path)
            filename = relative_path.split("/")[-1]

            logger.info(f"Serving PDF for download: {ticket_number}")

            # Serve file with attachment disposition (triggers download)
            return FileResponse(
                path=local_file_path,
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
                background=None,  # FastAPI will handle cleanup
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
