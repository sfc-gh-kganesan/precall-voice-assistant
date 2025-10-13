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
    # Invoice fields from INVOICES table
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


class UpdateStatusRequest(BaseModel):
    ticket_numbers: List[str]
    status: str  # approved, pending, rejected


class UpdateStatusResponse(BaseModel):
    success: bool
    updated_count: int
    message: str


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
        SELECT RELATIVE_PATH
        FROM INVOICES
        WHERE TICKET_NUMBER = %s
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
    limit: int = Query(50, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results to skip"),
):
    """
    List invoices with optional filtering and pagination.

    Query Parameters:
    - status: Filter by 'approved', 'pending', or 'rejected' (optional)
    - limit: Maximum invoices to return (default: 50, max: 1000)
    - offset: Number of invoices to skip for pagination (default: 0)
    """
    logger.info(f"Listing invoices: status={status}, limit={limit}, offset={offset}")

    try:
        with get_snowflake_connection() as conn:
            cursor = conn.cursor(DictCursor)

            query = """
                SELECT 
                    i.INVOICE_ID,
                    i.TICKET_NUMBER,
                    i.STATUS,
                    i.RELATIVE_PATH,
                    i.FILE_URL,
                    i.VENDOR_NAME,
                    i.INVOICE_NUMBER,
                    i.INVOICE_DATE,
                    i.TOTAL_AMOUNT,
                    i.PURCHASE_ORDER_NUMBER,
                    i.DUE_DATE,
                    i.CREATED_AT,
                    i.UPDATED_AT,
                    t.EMAIL
                FROM INVOICES i
                LEFT JOIN TICKET_METADATA t ON i.TICKET_NUMBER = t.TICKET_NUMBER
                WHERE i.RELATIVE_PATH IS NOT NULL
            """

            params = []
            if status:
                query += " AND UPPER(i.STATUS) = %s"
                params.append(status.upper())

            # Get total count
            count_query = f"SELECT COUNT(*) as total FROM ({query}) as subquery"
            cursor.execute(count_query, params)
            total_count = cursor.fetchone()["TOTAL"]

            # Add pagination and execute
            query += " ORDER BY i.CREATED_AT DESC LIMIT %s OFFSET %s"
            cursor.execute(query, params + [limit, offset])
            rows = cursor.fetchall()

            # Build invoice list
            invoices = []
            for row in rows:
                relative_path = row.get("RELATIVE_PATH", "")

                invoices.append(
                    Invoice(
                        id=row.get("TICKET_NUMBER", ""),
                        ticket_number=row.get("TICKET_NUMBER", ""),
                        status=row.get("STATUS", "unknown").lower(),
                        file_url=f"@INVOICEIQ.SERVICE.TICKET_ATTACHMENTS/{relative_path}"
                        if relative_path
                        else "",
                        relative_path=relative_path,
                        vendor_name=row.get("VENDOR_NAME"),
                        invoice_number=row.get("INVOICE_NUMBER"),
                        invoice_date=str(row.get("INVOICE_DATE", "")) if row.get("INVOICE_DATE") else None,
                        total_amount=str(row.get("TOTAL_AMOUNT", "")) if row.get("TOTAL_AMOUNT") else None,
                        purchase_order_number=row.get("PURCHASE_ORDER_NUMBER"),
                        due_date=str(row.get("DUE_DATE", "")) if row.get("DUE_DATE") else None,
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


@app.patch("/invoices/status", response_model=UpdateStatusResponse)
async def update_invoice_status(request: UpdateStatusRequest):
    """
    Update the status of one or more invoices.
    
    Body:
    - ticket_numbers: List of ticket numbers to update
    - status: New status ('approved', 'pending', or 'rejected')
    """
    logger.info(
        f"Updating status for {len(request.ticket_numbers)} invoices to '{request.status}'"
    )

    # Validate status
    valid_statuses = ["approved", "pending", "rejected"]
    if request.status.lower() not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
        )

    if not request.ticket_numbers:
        raise HTTPException(
            status_code=400, detail="ticket_numbers list cannot be empty"
        )

    try:
        with get_snowflake_connection() as conn:
            cursor = conn.cursor(DictCursor)

            # Build UPDATE query with parameterized IN clause - now using INVOICES table
            placeholders = ",".join(["%s"] * len(request.ticket_numbers))
            update_query = f"""
                UPDATE INVOICES
                SET STATUS = %s,
                    UPDATED_AT = CURRENT_TIMESTAMP()
                WHERE TICKET_NUMBER IN ({placeholders})
            """

            # Execute update
            params = [request.status.upper()] + request.ticket_numbers
            cursor.execute(update_query, params)
            updated_count = cursor.rowcount

            # Commit the transaction
            conn.commit()

            logger.info(
                f"Successfully updated {updated_count} invoices to status '{request.status}'"
            )

            return UpdateStatusResponse(
                success=True,
                updated_count=updated_count,
                message=f"Updated {updated_count} invoice(s) to status '{request.status}'",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating invoice status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
