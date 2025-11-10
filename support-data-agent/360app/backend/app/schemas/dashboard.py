from pydantic import BaseModel

from .common import KPIMetric


class Issue(BaseModel):
    issue: str
    count: int


class TrendPoint(BaseModel):
    date: str
    value: int


class ProductMetrics(BaseModel):
    productId: str
    productName: str
    productCategory: str
    parentProduct: str | None = None
    metrics: dict
    topIssues: list[Issue]
    trend: list[TrendPoint]


class TopicSentiment(BaseModel):
    positive: int
    neutral: int
    negative: int


class TopicTopProduct(BaseModel):
    product: str
    count: int


class TopicMetrics(BaseModel):
    topicId: str
    topicName: str
    totalCases: int
    change: int
    changePercentage: float
    changeType: str
    avgResolutionTime: float
    resolutionRate: float
    sentiment: TopicSentiment
    topProducts: list[TopicTopProduct]


class KPIsResponse(BaseModel):
    avgCases: KPIMetric
    avgCaseLife: KPIMetric
    resolutionRate: KPIMetric
    firstResponseTime: KPIMetric
