from pydantic import BaseModel


class SupportTicket(BaseModel):
    id: str
    case_number: str
    created_at: str
    updated_at: str | None = None
    closed_at: str | None = None
    last_modified_at: str | None = None
    status: str
    severity: str
    initial_severity: str | None = None
    peak_severity: str | None = None
    subject: str
    description: str
    account_id: str | None = None
    account_name: str | None = None
    is_priority_support: bool | None = None
    total_comments: int | None = None
    has_jira_issues: bool | None = None
    has_escalations: bool | None = None
    has_collaborations: bool | None = None
    generated_topic: str | None = None
    generated_product_category: str | None = None
    generated_product_subcategory: str | None = None
    generated_product: str | None = None
    generated_feature: str | None = None
    sentiment: str | None = None
    resolution_time_hours: float | None = None
    sla_violated: bool | None = None


class PaginatedTickets(BaseModel):
    tickets: list[SupportTicket]
    total: int
    page: int
    pageSize: int
