from typing import Literal

from pydantic import BaseModel, Field


class KPIMetric(BaseModel):
    id: str
    name: str
    value: float | int
    previousValue: float | int
    change: float | int
    changePercentage: float
    changeType: Literal["increase", "decrease", "neutral"]
    period: Literal["week", "month", "custom"]
    comparisonPeriod: str
    unit: str | None = None
    drillDownEnabled: bool


class Filters(BaseModel):
    period: Literal["week", "month", "custom"]
    startDate: str | None = Field(default=None)
    endDate: str | None = Field(default=None)
    products: list[str] | None = Field(default=None)
    topics: list[str] | None = Field(default=None)
    categories: list[str] | None = Field(default=None)
