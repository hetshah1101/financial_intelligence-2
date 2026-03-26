# app/models/schemas.py - Pydantic models for API I/O

from pydantic import BaseModel, field_validator
from typing import Optional, List, Literal


class TransactionIn(BaseModel):
    date: str
    account: Optional[str] = None
    category: str
    subcategory: Optional[str] = None
    description: Optional[str] = None
    amount: float
    type: Literal["income", "expense", "investment"]

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Amount must be non-negative")
        return v


class TransactionOut(TransactionIn):
    id: int
    created_at: Optional[str] = None


class MonthlyAggregate(BaseModel):
    month: str
    total_income: float
    total_expense: float
    total_investment: float
    net_savings: float
    savings_rate: float


class CategoryAggregate(BaseModel):
    month: str
    category: str
    total_amount: float
    percentage_of_total: float


class SavingsOpportunity(BaseModel):
    category: str
    current: float
    optimal_range: str
    potential_savings: float


class AnomalyFlag(BaseModel):
    category: str
    current_month_amount: float
    three_month_avg: float
    ratio: float
    month: str


class BehaviorPattern(BaseModel):
    pattern_type: str
    description: str
    value: float


class EfficiencyFlag(BaseModel):
    category: str
    current: float
    historical_median: float
    deviation_pct: float


class AnalyticsPayload(BaseModel):
    month: str
    summary: MonthlyAggregate
    category_breakdown: List[CategoryAggregate]
    anomalies: List[AnomalyFlag]
    behavioral_patterns: List[BehaviorPattern]
    efficiency_flags: List[EfficiencyFlag]
    savings_opportunities: List[SavingsOpportunity]


class InsightOut(BaseModel):
    month: str
    insight_type: str
    content: str
    created_at: Optional[str] = None


class UploadResponse(BaseModel):
    status: str
    rows_inserted: int
    rows_skipped: int
    months_processed: List[str]
    message: str
