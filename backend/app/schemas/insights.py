from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field

from app.schemas.analytics import (
    SalesAnalyticsResponse,
    TopProductItem,
    WarehousePerformanceItem,
)
from app.schemas.master_data import InventorySummaryResponse


class InsightCategory(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    INFORMATIONAL = "informational"
    ATTENTION = "attention"


class InsightsQuery(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    product_code: str | None = Field(default=None, max_length=200)
    warehouse_code: str | None = Field(default=None, max_length=200)
    limit: int = Field(default=10, ge=1, le=100)


class InsightPeriod(BaseModel):
    date_from: date | None
    date_to: date | None


class InsightRecord(BaseModel):
    code: str
    category: InsightCategory
    title: str
    description: str
    metric: Decimal | None = None
    metric_label: str | None = None


class InsightsOverviewResponse(BaseModel):
    period: InsightPeriod
    summary: SalesAnalyticsResponse
    top_products: list[TopProductItem]
    warehouse_performance: list[WarehousePerformanceItem]
    inventory: InventorySummaryResponse
    insights: list[InsightRecord]


class ComparisonQuery(InsightsQuery):
    pass


class ComparisonMetric(BaseModel):
    name: str
    current_value: Decimal
    previous_value: Decimal
    change: Decimal
    change_percent: Decimal | None
    category: InsightCategory


class ComparisonResponse(BaseModel):
    current_period: InsightPeriod
    previous_period: InsightPeriod
    metrics: list[ComparisonMetric]
    insights: list[InsightRecord]
