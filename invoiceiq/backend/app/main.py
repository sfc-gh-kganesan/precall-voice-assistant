import os
import logging
import tempfile
import json
from typing import Optional, List
from contextlib import contextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, Response
from pydantic import BaseModel
import snowflake.connector
from snowflake.connector import DictCursor
from dotenv import load_dotenv
import httpx

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
def get_snowflake_config():
    """Get Snowflake connection config based on environment (SPCS vs local)."""
    # When running in SPCS, use OAuth with session token
    if os.path.isfile("/snowflake/session/token"):
        logger.info("Using SPCS OAuth session token for Snowflake authentication")
        return {
            "host": os.getenv("SNOWFLAKE_HOST"),
            "port": os.getenv("SNOWFLAKE_PORT"),
            "protocol": "https",
            "account": os.getenv("SNOWFLAKE_ACCOUNT"),
            "authenticator": "oauth",
            "token": open("/snowflake/session/token").read(),
            "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
            "database": os.getenv("SNOWFLAKE_DATABASE", "INVOICEIQ"),
            "schema": os.getenv("SNOWFLAKE_SCHEMA", "SERVICE"),
            "role": os.getenv("SNOWFLAKE_ROLE"),
            "client_session_keep_alive": True,
        }
    else:
        # Local development with JWT key-pair authentication
        logger.info("Using JWT key-pair authentication for Snowflake")
        return {
            "account": os.getenv("SNOWFLAKE_ACCOUNT"),
            "user": os.getenv("SNOWFLAKE_USER"),
            "password": os.getenv("SNOWFLAKE_PAT"),
            "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
            "database": os.getenv("SNOWFLAKE_DATABASE", "INVOICEIQ"),
            "schema": os.getenv("SNOWFLAKE_SCHEMA", "SERVICE"),
            "role": os.getenv("SNOWFLAKE_ROLE"),
        }


# Helper function to trigger agent review
async def trigger_agent_review(invoice_id: str, relative_path: str):
    """
    Call the agent service to reprocess an invoice.
    Uses existing metadata (doesn't re-extract from PDF).
    """
    # AGENT_SERVICE_URL varies per environment:
    # - Local dev: http://localhost:8000
    # - SPCS: invoice-processing-service.<compute-pool>.svc.spcs.internal:8000
    #   (where <compute-pool> is the name of your SPCS compute pool, e.g., 'ivzu')
    agent_service_url = os.getenv("AGENT_SERVICE_URL", "http://localhost:8000")

    # Prepare the payload for the agent service
    payload = {
        "target_table": "INVOICES",
        "invoice_id": invoice_id,
        "relative_path": relative_path,
        "stage_name": "TICKET_ATTACHMENTS",
        "use_existing_ai_extract": True,  # Don't re-run AI_EXTRACT, use existing metadata
    }

    try:
        # Use longer timeout as agent processing can take 1-2 minutes
        # TODO: Consider making this a background task with status polling in future iteration
        async with httpx.AsyncClient(timeout=180.0) as client:
            logger.info(
                f"Calling agent service at {agent_service_url}/process for invoice {invoice_id}"
            )
            logger.info(f"Agent payload: {payload}")
            response = await client.post(f"{agent_service_url}/process", json=payload)
            response.raise_for_status()
            result = response.json()
            logger.info(f"Agent service response: {result}")
            return result
    except httpx.TimeoutException:
        logger.error(f"Timeout calling agent service for invoice {invoice_id}")
        return None
    except Exception as e:
        logger.error(
            f"Failed to trigger agent review for invoice {invoice_id}: {str(e)}"
        )
        # Don't fail the field update if agent call fails
        return None


# Pydantic models
class Invoice(BaseModel):
    id: str  # TICKET_NUMBER
    ticket_number: str
    status: str  # approved, pending, rejected (from AI_DECISION column)
    file_url: str
    relative_path: str
    # Invoice fields from INVOICES table
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    total_amount: Optional[str] = None
    purchase_order_number: Optional[str] = None
    due_date: Optional[str] = None
    banking_details: Optional[str] = None
    freight_shipping_amount: Optional[str] = None
    invoice_currency: Optional[str] = None
    memo_description: Optional[str] = None
    payment_terms: Optional[str] = None
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
    # AI fields
    ai_reasoning: Optional[str] = None
    ai_processed_at: Optional[str] = None
    # Edit tracking
    last_edited_by: Optional[str] = None
    last_edited_at: Optional[str] = None
    # Metadata
    submission_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    email_from: Optional[str] = None
    email_subject: Optional[str] = None
    # Bounding boxes for UI highlighting
    bounding_boxes: Optional[List[dict]] = None
    fields_with_bounding_boxes: Optional[dict] = None


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


class UpdateFieldsResponse(BaseModel):
    success: bool
    message: str


class InvoiceStatsResponse(BaseModel):
    success: bool
    approved: int
    pending: int
    rejected: int
    total: int


class InvoicesByStatusResponse(BaseModel):
    success: bool
    approved: List[Invoice]
    pending: List[Invoice]
    rejected: List[Invoice]
    approved_count: int
    pending_count: int
    rejected_count: int


class GenerateEmailRequest(BaseModel):
    ai_reasoning: str
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None


class GenerateEmailResponse(BaseModel):
    success: bool
    email_template: str


# ============================================================================
# Helper Functions
# ============================================================================


@contextmanager
def get_snowflake_connection():
    """Context manager for Snowflake connections."""
    conn = None
    try:
        config = get_snowflake_config()
        conn = snowflake.connector.connect(**config)
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


def build_invoice_from_row(row: dict) -> Invoice:
    """Helper function to build an Invoice object from a database row."""
    relative_path = row.get("RELATIVE_PATH", "")

    # Use AI_DECISION if available, fallback to 'pending'
    # Normalize to 'approved'/'rejected'/'pending' format (with -ed suffix)
    ai_decision = row.get("AI_DECISION")
    if not ai_decision:
        status_value = "pending"
    elif ai_decision.lower() == "approve":
        status_value = "approved"
    elif ai_decision.lower() == "reject":
        status_value = "rejected"
    else:
        status_value = ai_decision.lower()

    return Invoice(
        id=row.get("TICKET_NUMBER", ""),
        ticket_number=row.get("TICKET_NUMBER", ""),
        status=status_value,
        file_url=f"@INVOICEIQ.SERVICE.TICKET_ATTACHMENTS/{relative_path}"
        if relative_path
        else "",
        relative_path=relative_path,
        vendor_name=row.get("VENDOR_NAME"),
        invoice_number=row.get("INVOICE_NUMBER"),
        invoice_date=str(row.get("INVOICE_DATE", ""))
        if row.get("INVOICE_DATE")
        else None,
        total_amount=str(row.get("TOTAL_AMOUNT", ""))
        if row.get("TOTAL_AMOUNT")
        else None,
        purchase_order_number=row.get("PURCHASE_ORDER_NUMBER"),
        due_date=str(row.get("DUE_DATE", "")) if row.get("DUE_DATE") else None,
        banking_details=row.get("BANKING_DETAILS"),
        freight_shipping_amount=str(row.get("FREIGHT_SHIPPING_AMOUNT", ""))
        if row.get("FREIGHT_SHIPPING_AMOUNT")
        else None,
        invoice_currency=row.get("INVOICE_CURRENCY"),
        memo_description=row.get("MEMO_DESCRIPTION"),
        payment_terms=row.get("PAYMENT_TERMS"),
        payment_type=row.get("PAYMENT_TYPE"),
        prepaid_flag=row.get("PREPAID_FLAG"),
        quantity=str(row.get("QUANTITY", "")) if row.get("QUANTITY") else None,
        service_end_date=str(row.get("SERVICE_END_DATE", ""))
        if row.get("SERVICE_END_DATE")
        else None,
        service_start_date=str(row.get("SERVICE_START_DATE", ""))
        if row.get("SERVICE_START_DATE")
        else None,
        shipped_to_address=row.get("SHIPPED_TO_ADDRESS"),
        snowflake_entity=row.get("SNOWFLAKE_ENTITY"),
        snowflake_tax_id=row.get("SNOWFLAKE_TAX_ID"),
        tax_amount=str(row.get("TAX_AMOUNT", "")) if row.get("TAX_AMOUNT") else None,
        unit_price=str(row.get("UNIT_PRICE", "")) if row.get("UNIT_PRICE") else None,
        vendor_address=row.get("VENDOR_ADDRESS"),
        vendor_tax_id=row.get("VENDOR_TAX_ID"),
        ai_reasoning=row.get("AI_REASONING"),
        ai_processed_at=str(row.get("AI_PROCESSED_AT", ""))
        if row.get("AI_PROCESSED_AT")
        else None,
        last_edited_by=row.get("LAST_EDITED_BY"),
        last_edited_at=str(row.get("LAST_EDITED_AT", ""))
        if row.get("LAST_EDITED_AT")
        else None,
        submission_id=row.get("SUBMISSION_ID"),
        created_at=str(row.get("CREATED_AT", "")),
        updated_at=str(row.get("UPDATED_AT", "")),
        email_from=row.get("EMAIL"),
        email_subject=None,
        bounding_boxes=json.loads(row.get("BOUNDING_BOXES"))
        if row.get("BOUNDING_BOXES") and isinstance(row.get("BOUNDING_BOXES"), str)
        else row.get("BOUNDING_BOXES"),
        fields_with_bounding_boxes=json.loads(row.get("FIELDS_WITH_BOUNDING_BOXES"))
        if row.get("FIELDS_WITH_BOUNDING_BOXES")
        and isinstance(row.get("FIELDS_WITH_BOUNDING_BOXES"), str)
        else row.get("FIELDS_WITH_BOUNDING_BOXES"),
    )


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


@app.get("/invoices/all", response_model=InvoicesByStatusResponse)
async def get_all_invoices(
    limit: int = Query(100, ge=1, le=1000, description="Maximum results per status"),
):
    """
    Fetch all invoices grouped by status using SELECT * and Python categorization.
    This fetches all invoice data and categorizes them in Python rather than SQL.

    Query Parameters:
    - limit: Maximum invoices to return per status (default: 100, max: 1000)

    Returns:
    - approved: List of approved invoices
    - pending: List of pending invoices
    - rejected: List of rejected invoices
    - approved_count/pending_count/rejected_count: Number of invoices in each list
    """
    logger.info(f"Fetching all invoices grouped by status, limit={limit}")

    try:
        with get_snowflake_connection() as conn:
            cursor = conn.cursor(DictCursor)

            # Simple SELECT * query - categorization happens in Python
            query = """
                SELECT
                    i.INVOICE_ID,
                    i.TICKET_NUMBER,
                    i.SUBMISSION_ID,
                    i.AI_DECISION,
                    i.RELATIVE_PATH,
                    i.FILE_URL,
                    i.VENDOR_NAME,
                    i.INVOICE_NUMBER,
                    i.INVOICE_DATE,
                    i.TOTAL_AMOUNT,
                    i.PURCHASE_ORDER_NUMBER,
                    i.DUE_DATE,
                    i.BANKING_DETAILS,
                    i.FREIGHT_SHIPPING_AMOUNT,
                    i.INVOICE_CURRENCY,
                    i.MEMO_DESCRIPTION,
                    i.PAYMENT_TERMS,
                    i.PAYMENT_TYPE,
                    i.PREPAID_FLAG,
                    i.QUANTITY,
                    i.SERVICE_END_DATE,
                    i.SERVICE_START_DATE,
                    i.SHIPPED_TO_ADDRESS,
                    i.SNOWFLAKE_ENTITY,
                    i.SNOWFLAKE_TAX_ID,
                    i.TAX_AMOUNT,
                    i.UNIT_PRICE,
                    i.VENDOR_ADDRESS,
                    i.VENDOR_TAX_ID,
                    i.AI_REASONING,
                    i.AI_PROCESSED_AT,
                    i.LAST_EDITED_BY,
                    i.LAST_EDITED_AT,
                    i.CREATED_AT,
                    i.UPDATED_AT,
                    i.BOUNDING_BOXES,
                    i.FIELDS_WITH_BOUNDING_BOXES,
                    t.EMAIL
                FROM INVOICES i
                LEFT JOIN TICKET_METADATA t ON i.TICKET_NUMBER = t.TICKET_NUMBER
                WHERE i.RELATIVE_PATH IS NOT NULL
                ORDER BY i.CREATED_AT DESC
            """

            cursor.execute(query)
            rows = cursor.fetchall()

            # Categorize invoices in Python
            approved = []
            pending = []
            rejected = []

            for row in rows:
                invoice_obj = build_invoice_from_row(row)

                # Add to appropriate list (respecting limit for each)
                if invoice_obj.status == "approved" and len(approved) < limit:
                    approved.append(invoice_obj)
                elif invoice_obj.status == "pending" and len(pending) < limit:
                    pending.append(invoice_obj)
                elif invoice_obj.status == "rejected" and len(rejected) < limit:
                    rejected.append(invoice_obj)

                # Early exit if all buckets are full
                if (
                    len(approved) >= limit
                    and len(pending) >= limit
                    and len(rejected) >= limit
                ):
                    break

            logger.info(
                f"Grouped invoices - Approved: {len(approved)}, Pending: {len(pending)}, Rejected: {len(rejected)}"
            )

            return InvoicesByStatusResponse(
                success=True,
                approved=approved,
                pending=pending,
                rejected=rejected,
                approved_count=len(approved),
                pending_count=len(pending),
                rejected_count=len(rejected),
            )
    except Exception as e:
        logger.error(f"Error fetching all invoices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/invoices/search", response_model=InvoiceListResponse)
async def search_invoices(
    search_by: str = Query(
        ..., description="Field to search: 'liftTicket' or 'purchaseOrder'"
    ),
    search_term: str = Query(
        ..., description="Search term (exact match, case-insensitive)"
    ),
    limit: int = Query(1000, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results to skip"),
):
    """
    Search invoices by Lift Ticket # or Purchase Order #.
    Returns all matching invoices regardless of status.

    Query Parameters:
    - search_by: Field to search - 'liftTicket' or 'purchaseOrder'
    - search_term: Search term (exact match, case-insensitive)
    - limit: Maximum invoices to return (default: 1000, max: 1000)
    - offset: Number of invoices to skip for pagination (default: 0)
    """
    logger.info(
        f"Searching invoices: search_by={search_by}, search_term={search_term}, limit={limit}, offset={offset}"
    )

    if search_by not in ["liftTicket", "purchaseOrder"]:
        raise HTTPException(
            status_code=400, detail="search_by must be 'liftTicket' or 'purchaseOrder'"
        )

    if not search_term or search_term.strip() == "":
        raise HTTPException(status_code=400, detail="search_term cannot be empty")

    try:
        with get_snowflake_connection() as conn:
            cursor = conn.cursor(DictCursor)

            query = """
                SELECT
                    i.INVOICE_ID,
                    i.TICKET_NUMBER,
                    i.SUBMISSION_ID,
                    i.AI_DECISION,
                    i.RELATIVE_PATH,
                    i.FILE_URL,
                    i.VENDOR_NAME,
                    i.INVOICE_NUMBER,
                    i.INVOICE_DATE,
                    i.TOTAL_AMOUNT,
                    i.PURCHASE_ORDER_NUMBER,
                    i.DUE_DATE,
                    i.BANKING_DETAILS,
                    i.FREIGHT_SHIPPING_AMOUNT,
                    i.INVOICE_CURRENCY,
                    i.MEMO_DESCRIPTION,
                    i.PAYMENT_TERMS,
                    i.PAYMENT_TYPE,
                    i.PREPAID_FLAG,
                    i.QUANTITY,
                    i.SERVICE_END_DATE,
                    i.SERVICE_START_DATE,
                    i.SHIPPED_TO_ADDRESS,
                    i.SNOWFLAKE_ENTITY,
                    i.SNOWFLAKE_TAX_ID,
                    i.TAX_AMOUNT,
                    i.UNIT_PRICE,
                    i.VENDOR_ADDRESS,
                    i.VENDOR_TAX_ID,
                    i.AI_REASONING,
                    i.AI_PROCESSED_AT,
                    i.LAST_EDITED_BY,
                    i.LAST_EDITED_AT,
                    i.CREATED_AT,
                    i.UPDATED_AT,
                    i.BOUNDING_BOXES,
                    i.FIELDS_WITH_BOUNDING_BOXES,
                    t.EMAIL
                FROM INVOICES i
                LEFT JOIN TICKET_METADATA t ON i.TICKET_NUMBER = t.TICKET_NUMBER
                WHERE i.RELATIVE_PATH IS NOT NULL
            """

            params = []
            # Add search condition based on field - exact match
            if search_by == "liftTicket":
                query += " AND LOWER(i.TICKET_NUMBER) = LOWER(%s)"
                params.append(search_term)
            elif search_by == "purchaseOrder":
                query += " AND LOWER(i.PURCHASE_ORDER_NUMBER) = LOWER(%s)"
                params.append(search_term)

            # Get total count
            count_query = f"SELECT COUNT(*) as total FROM ({query}) as subquery"
            cursor.execute(count_query, params)
            total_count = cursor.fetchone()["TOTAL"]

            # Add pagination and execute
            query += " ORDER BY i.CREATED_AT DESC LIMIT %s OFFSET %s"
            cursor.execute(query, params + [limit, offset])
            rows = cursor.fetchall()

            # Build invoice list using helper function
            invoices = [build_invoice_from_row(row) for row in rows]

            logger.info(
                f"Found {len(invoices)} invoices matching search (total: {total_count})"
            )
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
        logger.error(f"Error searching invoices: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to search invoices: {str(e)}"
        )


@app.options("/invoices/{ticket_number}/view")
async def options_view_invoice_pdf(ticket_number: str):
    """Handle CORS preflight request for PDF viewing."""
    return Response(
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "Range, Content-Type",
            "Access-Control-Max-Age": "86400",
        }
    )


@app.get("/invoices/{ticket_number}/view")
async def view_invoice_pdf(ticket_number: str):
    """
    Stream invoice PDF directly to browser for inline viewing.
    Returns the PDF file with appropriate headers for browser display.
    """
    logger.info(f"Streaming PDF for ticket: {ticket_number}")

    try:
        with get_snowflake_connection() as conn:
            cursor = conn.cursor(DictCursor)
            relative_path = get_file_path_for_ticket(cursor, ticket_number)
            local_file_path = download_file_from_stage(cursor, relative_path)

            logger.info(
                f"Serving PDF for viewing: {ticket_number}, file_path: {local_file_path}"
            )

            # Read PDF file into memory
            try:
                with open(local_file_path, "rb") as f:
                    pdf_bytes = f.read()

                logger.info(f"PDF loaded into memory, size: {len(pdf_bytes)} bytes")

                # Clean up temp file
                import shutil

                temp_dir = os.path.dirname(local_file_path)
                shutil.rmtree(temp_dir, ignore_errors=True)

                # Return as streaming response with explicit content length
                return StreamingResponse(
                    iter([pdf_bytes]),
                    media_type="application/pdf",
                    headers={
                        "Content-Disposition": f"inline; filename={ticket_number}.pdf",
                        "X-Content-Type-Options": "nosniff",
                        "Cache-Control": "no-cache",
                        "Content-Length": str(len(pdf_bytes)),
                        "Accept-Ranges": "bytes",
                    },
                )
            except FileNotFoundError:
                raise HTTPException(
                    status_code=404,
                    detail=f"PDF file not found for ticket {ticket_number}",
                )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error streaming PDF: {e}")
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
    Update the AI decision status of one or more invoices.
    Updates the AI_DECISION column in the INVOICES table.

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

            # Build UPDATE query with parameterized IN clause - update AI_DECISION
            placeholders = ",".join(["%s"] * len(request.ticket_numbers))
            update_query = f"""
                UPDATE INVOICES
                SET AI_DECISION = %s,
                    UPDATED_AT = CURRENT_TIMESTAMP()
                WHERE TICKET_NUMBER IN ({placeholders})
            """

            # Execute update (store in lowercase to match AI agent's format)
            params = [request.status.lower()] + request.ticket_numbers
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


@app.patch("/invoices/{ticket_number}/fields", response_model=UpdateFieldsResponse)
async def update_invoice_fields(ticket_number: str, fields: dict):
    """
    Update specific fields of an invoice.
    Updates the specified columns in the INVOICES table.

    Path parameters:
    - ticket_number: The ticket number of the invoice to update

    Body: Dictionary of field names and values to update
    """
    logger.info(f"Updating fields for invoice {ticket_number}: {list(fields.keys())}")

    if not fields:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    # Mapping from frontend field names to database column names
    field_mapping = {
        "ticketNumber": "TICKET_NUMBER",
        "invoiceNumber": "INVOICE_NUMBER",
        "purchaseOrderNumber": "PURCHASE_ORDER_NUMBER",
        "invoiceDate": "INVOICE_DATE",
        "dueDate": "DUE_DATE",
        "invoiceCurrency": "INVOICE_CURRENCY",
        "vendorName": "VENDOR_NAME",
        "vendorTaxId": "VENDOR_TAX_ID",
        "vendorAddress": "VENDOR_ADDRESS",
        "totalAmount": "TOTAL_AMOUNT",
        "taxAmount": "TAX_AMOUNT",
        "unitPrice": "UNIT_PRICE",
        "quantity": "QUANTITY",
        "freightShippingAmount": "FREIGHT_SHIPPING_AMOUNT",
        "prepaidFlag": "PREPAID_FLAG",
        "paymentTerms": "PAYMENT_TERMS",
        "paymentType": "PAYMENT_TYPE",
        "bankingDetails": "BANKING_DETAILS",
        "serviceStartDate": "SERVICE_START_DATE",
        "serviceEndDate": "SERVICE_END_DATE",
        "shippedToAddress": "SHIPPED_TO_ADDRESS",
        "snowflakeEntity": "SNOWFLAKE_ENTITY",
        "snowflakeTaxId": "SNOWFLAKE_TAX_ID",
        "memoDescription": "MEMO_DESCRIPTION",
    }

    # Fields that are numeric and should convert empty strings to None
    numeric_fields = {
        "totalAmount",
        "taxAmount",
        "unitPrice",
        "quantity",
        "freightShippingAmount",
    }

    # Build SET clause for SQL
    set_clauses = []
    params = []

    for field_name, value in fields.items():
        # Skip fields that shouldn't be updated or don't exist in mapping
        if field_name in ["id", "pdfUrl", "createdAt", "updatedAt"]:
            continue

        db_column = field_mapping.get(field_name)
        if db_column:
            # Convert empty strings to None for numeric fields
            if field_name in numeric_fields and value == "":
                value = None
            set_clauses.append(f"{db_column} = %s")
            params.append(value)

    if not set_clauses:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    # Add UPDATED_AT timestamp
    set_clauses.append("UPDATED_AT = CURRENT_TIMESTAMP()")

    try:
        with get_snowflake_connection() as conn:
            cursor = conn.cursor()

            # Build and execute UPDATE query
            update_query = f"""
                UPDATE INVOICES
                SET {", ".join(set_clauses)}
                WHERE TICKET_NUMBER = %s
            """

            logger.info(update_query)
            params.append(ticket_number)
            cursor.execute(update_query, params)
            updated_count = cursor.rowcount

            # Commit the transaction
            conn.commit()

            if updated_count == 0:
                raise HTTPException(
                    status_code=404,
                    detail=f"Invoice with ticket number {ticket_number} not found",
                )

            logger.info(f"Successfully updated invoice {ticket_number}")

            return UpdateFieldsResponse(
                success=True, message=f"Successfully updated invoice {ticket_number}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating invoice fields: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/invoices/{ticket_number}/reprocess")
async def reprocess_invoice(ticket_number: str):
    """
    Manually trigger the agent to reprocess an invoice.
    This endpoint is called after user edits to re-run the agent workflow.

    Path parameters:
    - ticket_number: The ticket number of the invoice to reprocess
    """
    logger.info(f"Manual reprocess requested for invoice {ticket_number}")

    try:
        with get_snowflake_connection() as conn:
            cursor = conn.cursor(DictCursor)

            # Get the INVOICE_ID and RELATIVE_PATH for this ticket
            query = "SELECT INVOICE_ID, RELATIVE_PATH FROM INVOICES WHERE TICKET_NUMBER = %s"
            cursor.execute(query, [ticket_number])
            result = cursor.fetchone()

            if not result:
                raise HTTPException(
                    status_code=404,
                    detail=f"Invoice with ticket number {ticket_number} not found",
                )

            invoice_id = result["INVOICE_ID"]
            relative_path = result["RELATIVE_PATH"]
            logger.info(
                f"Found invoice_id {invoice_id} and relative_path {relative_path} for ticket {ticket_number}"
            )

            # Trigger agent review with existing metadata
            agent_result = await trigger_agent_review(invoice_id, relative_path)

            if agent_result:
                return {
                    "success": True,
                    "message": f"Agent reprocessing triggered for invoice {ticket_number}",
                    "invoice_id": invoice_id,
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to trigger agent reprocessing for invoice {ticket_number}",
                    "invoice_id": invoice_id,
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reprocessing invoice: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/invoices/generate-email", response_model=GenerateEmailResponse)
async def generate_email_template(request: GenerateEmailRequest):
    """
    Generate an email template for a rejected invoice using Snowflake's COMPLETE function.
    Uses AI reasoning to create a professional email to send to the supplier.

    Body:
    - ai_reasoning: The AI reasoning for why the invoice was rejected
    - vendor_name: Optional vendor name to personalize the email
    - invoice_number: Optional invoice number to reference in the email
    """
    logger.info(
        f"Generating email template for vendor: {request.vendor_name}, invoice: {request.invoice_number}"
    )

    if not request.ai_reasoning or request.ai_reasoning.strip() == "":
        raise HTTPException(status_code=400, detail="ai_reasoning cannot be empty")

    try:
        with get_snowflake_connection() as conn:
            cursor = conn.cursor(DictCursor)

            # Build the prompt for email generation
            vendor_info = f" to {request.vendor_name}" if request.vendor_name else ""
            invoice_ref = (
                f" regarding invoice #{request.invoice_number}"
                if request.invoice_number
                else ""
            )

            prompt = f"""Generate a professional and polite email{vendor_info}{invoice_ref} explaining why their invoice was rejected.

AI Reasoning for rejection:
{request.ai_reasoning}

The email should:
1. Be professional and courteous
2. Clearly explain the issues found
3. Request specific corrections or clarifications
4. Provide a clear path forward
5. Include a professional closing

Format the email with proper greeting, body paragraphs, and closing."""

            # Use Snowflake's COMPLETE function to generate the email
            # COMPLETE is part of Snowflake Cortex AI functions
            # Using simple string prompt (single argument version)
            query = """
                SELECT SNOWFLAKE.CORTEX.COMPLETE(
                    'claude-4-sonnet',
                    %s
                ) AS email_template
            """

            logger.info(f"Executing COMPLETE query with prompt length: {len(prompt)}")
            cursor.execute(query, (prompt,))
            result = cursor.fetchone()

            if not result or not result.get("EMAIL_TEMPLATE"):
                raise HTTPException(
                    status_code=500,
                    detail="Failed to generate email template from Snowflake COMPLETE",
                )

            email_template = result["EMAIL_TEMPLATE"]
            logger.info(
                f"Successfully generated email template (length: {len(email_template)})"
            )

            return GenerateEmailResponse(success=True, email_template=email_template)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating email template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
