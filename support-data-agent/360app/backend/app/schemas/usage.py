import json

from pydantic import BaseModel, field_validator


class UsageTrendPoint(BaseModel):
    ds: str
    credits: float
    rolling_avg_7d: float


class BiggestMover(BaseModel):
    salesforce_account_name: str
    salesforce_account_id: str
    l7_total_credits: float
    delta: float
    pct_change: float | None
    sales_engineer_email: str | None
    is_cap1: bool | None
    agreement_type: str | None


class BiggestMoversResponse(BaseModel):
    gainers: list[BiggestMover]
    decliners: list[BiggestMover]


class TopAccount(BaseModel):
    ds: str
    salesforce_account_name: str
    salesforce_account_id: str
    total_indexed_rows: int
    total_active_serving_rows: int
    num_services: int
    snowflake_account_type: str
    acct_first_svc_creation_date: str
    sales_engineer_email: str | None
    accounts: list[dict]

    @field_validator("accounts", mode="before")
    @classmethod
    def parse_accounts_json(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v if v else []


class UsageMetrics(BaseModel):
    total_credits: float
    total_credits_change: float
    total_credits_change_pct: float
    active_accounts: int
    active_accounts_change: int
    seven_day_change_pct: float


class HighValueCustomer(BaseModel):
    salesforce_account_name: str
    salesforce_account_id: str
    total_active_serving_rows: int
    credits_per_week: float
    seven_day_change_pct: float | None
    open_cases_count: int
    critical_cases_count: int
    top_issue: str | None
    priority_score: float  # Calculated score for ranking
