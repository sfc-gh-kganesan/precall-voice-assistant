import asyncio

from fastapi import APIRouter, HTTPException, Query

from ..schemas.tickets import PaginatedTickets, SupportTicket
from ..services import snowflake as snowflake_service
from ..services.configuration import get_active_configuration

router = APIRouter()


def _fetch_tickets(
    page: int, page_size: int, sort_by: str | None, sort_order: str, product: str | None = None
) -> tuple[list[SupportTicket], int]:
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
        ID,
        CASE_NUMBER,
        CREATED_AT,
        UPDATED_AT,
        CLOSED_AT,
        LAST_MODIFIED_AT,
        STATUS,
        SEVERITY,
        SUBJECT,
        DESCRIPTION,
        ACCOUNT_ID,
        ACCOUNT_NAME,
        GENERATED_TOPIC,
        GENERATED_PRODUCT_CATEGORY,
        GENERATED_PRODUCT,
        RESOLUTION_TIME_HOURS
    FROM {base_table}{where_clause}
    ORDER BY {sort_column} {sort_order.upper()}
    LIMIT {page_size}
    OFFSET {offset}
    """

    results = session.sql(data_query).collect()

    tickets = []
    for row in results:
        ticket = SupportTicket(
            id=row[0],
            case_number=row[1],
            created_at=row[2].isoformat() if row[2] else "",
            updated_at=row[3].isoformat() if row[3] else "",
            closed_at=row[4].isoformat() if row[4] else None,
            last_modified_at=row[5].isoformat() if row[5] else "",
            status=row[6] or "",
            severity=row[7] or "",
            initial_severity=None,
            peak_severity=None,
            subject=row[8] or "",
            description=row[9] or "",
            account_id=row[10],
            account_name=row[11],
            is_priority_support=None,
            total_comments=None,
            has_jira_issues=None,
            has_escalations=None,
            has_collaborations=None,
            generated_topic=row[12],
            generated_product_category=row[13],
            generated_product=row[14],
            generated_feature=None,
            sentiment=None,
            resolution_time_hours=float(row[15]) if row[15] is not None else None,
            sla_violated=None
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
