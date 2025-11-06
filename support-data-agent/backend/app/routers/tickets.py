import asyncio

from fastapi import APIRouter, HTTPException, Query

from ..schemas.tickets import PaginatedTickets, SupportTicket
from ..services import snowflake as snowflake_service
from ..services.configuration import get_active_configuration

router = APIRouter()


def _fetch_tickets(page: int, page_size: int, sort_by: str | None, sort_order: str, product: str | None = None) -> tuple[list[SupportTicket], int]:
    """
    Fetch paginated tickets from the active configuration's base table.

    Args:
        page: Page number (1-indexed)
        page_size: Number of tickets per page
        sort_by: Column to sort by (default: CREATED_AT)
        sort_order: Sort direction ('asc' or 'desc')
        product: Optional product name to filter by

    Returns:
        Tuple of (list of tickets, total count)
    """
    session = snowflake_service._get_session()
    tables = get_active_configuration()
    base_table = tables["base"]

    valid_sort_columns = {
        "created_at",
        "status",
        "severity",
        "case_number",
        "subject",
        "account_name",
        "generated_product",
    }
    sort_column = "CREATED_AT"
    if sort_by and sort_by.lower() in valid_sort_columns:
        # Map severity to the actual column name
        if sort_by.lower() == "severity":
            sort_column = "CURRENT_SEVERITY"
        else:
            sort_column = sort_by.upper()

    # Calculate offset
    offset = (page - 1) * page_size

    where_clause = ""
    if product:
        safe_product = product.replace("'", "''")
        where_clause = f" WHERE GENERATED_PRODUCT = '{safe_product}'"

    count_query = f"SELECT COUNT(*) FROM {base_table}{where_clause}"
    total = int(session.sql(count_query).collect()[0][0])
    data_query = f"""
    SELECT
        CASE_ID,
        CASE_NUMBER,
        CREATED_AT,
        CLOSED_AT,
        STATUS,
        CURRENT_SEVERITY,
        PEAK_SEVERITY,
        SUBJECT,
        DESCRIPTION,
        SFDC_ACCOUNT_ID,
        ACCOUNT_NAME,
        IS_PRIORITY_SUPPORT_ENTITLEMENT,
        TOTAL_COMMENTS,
        GENERATED_TOPIC,
        GENERATED_PRODUCT_CATEGORY,
        GENERATED_PRODUCT,
        ENRICHED_AT
    FROM {base_table}{where_clause}
    ORDER BY {sort_column} {sort_order.upper()}
    LIMIT {page_size}
    OFFSET {offset}
    """

    results = session.sql(data_query).collect()

    tickets = []
    for row in results:
        # Calculate resolution time if case is closed
        resolution_hours = None
        if row[3]:  # CLOSED_AT
            from datetime import datetime

            created = row[2] if row[2] else datetime.now()  # CREATED_AT
            closed = row[3]  # CLOSED_AT
            resolution_hours = (closed - created).total_seconds() / 3600

        ticket = SupportTicket(
            id=row[0],  # CASE_ID
            case_number=row[1],  # CASE_NUMBER
            created_at=row[2].isoformat() if row[2] else "",  # CREATED_AT
            updated_at=row[16].isoformat() if row[16] else (row[2].isoformat() if row[2] else ""),  # ENRICHED_AT or CREATED_AT
            closed_at=row[3].isoformat() if row[3] else None,  # CLOSED_AT
            last_modified_at=row[16].isoformat() if row[16] else (row[2].isoformat() if row[2] else ""),  # ENRICHED_AT or CREATED_AT
            status=row[4] or "",  # STATUS
            severity=row[5] or "",  # CURRENT_SEVERITY
            initial_severity=None,
            peak_severity=row[6] or None,  # PEAK_SEVERITY
            subject=str(row[7]) if row[7] else "",  # SUBJECT (VARIANT)
            description=str(row[8]) if row[8] else "",  # DESCRIPTION (VARIANT)
            account_id=row[9],  # SFDC_ACCOUNT_ID
            account_name=row[10],  # ACCOUNT_NAME
            is_priority_support=row[11],  # IS_PRIORITY_SUPPORT_ENTITLEMENT
            total_comments=int(row[12]) if row[12] is not None else None,  # TOTAL_COMMENTS
            has_jira_issues=None,
            has_escalations=None,
            has_collaborations=None,
            generated_topic=row[13],  # GENERATED_TOPIC
            generated_product_category=row[14],  # GENERATED_PRODUCT_CATEGORY
            generated_product=row[15],  # GENERATED_PRODUCT
            generated_feature=None,
            sentiment=None,
            resolution_time_hours=resolution_hours,
            sla_violated=None,
        )
        tickets.append(ticket)

    return tickets, total


@router.get("/tickets", response_model=PaginatedTickets)
async def get_tickets(
    page: int = Query(1, ge=1),
    pageSize: int = Query(50, ge=1, le=100),
    sortBy: str | None = None,
    sortOrder: str = Query("desc", pattern="^(asc|desc)$"),
    product: str | None = Query(None, description="Filter by product name"),
):
    """
    Get paginated list of support tickets from the active configuration's base table.

    Args:
        page: Page number (1-indexed)
        pageSize: Number of tickets per page (1-100)
        sortBy: Column to sort by (created_at, status, severity, case_number, subject, account_name, generated_product)
        sortOrder: Sort direction (asc or desc)
        product: Optional product name to filter by

    Returns:
        Paginated tickets response with total count
    """
    try:
        # Run blocking Snowpark operation in thread pool
        tickets, total = await asyncio.to_thread(_fetch_tickets, page, pageSize, sortBy, sortOrder, product)

        return PaginatedTickets(
            tickets=tickets,
            total=total,
            page=page,
            pageSize=pageSize,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
