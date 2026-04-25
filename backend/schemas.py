from pydantic import BaseModel
from typing import Optional


# ── Aggregate Schemas ──────────────────────────────────────────────────────────

class MonthlyAggregateSchema(BaseModel):
    month: str
    total_income: float
    total_expense: float
    total_investment: float
    net_savings: float
    savings_rate: float

    model_config = {"from_attributes": True}


class CategoryAggregateSchema(BaseModel):
    month: str
    category: str
    total_amount: float
    percentage_of_total_expense: float
    tag: str

    model_config = {"from_attributes": True}


class YearlyAggregateSchema(BaseModel):
    year: int
    total_income: float
    total_expense: float
    total_investment: float
    avg_monthly_expense: float
    savings_rate: float

    model_config = {"from_attributes": True}


# ── Trend Schemas ──────────────────────────────────────────────────────────────

class MonthlyTrendPoint(BaseModel):
    month: str
    income: float
    expense: float
    investment: float
    mom_income_change: Optional[float] = None
    mom_expense_change: Optional[float] = None
    rolling_3m_expense: Optional[float] = None


class YearlyTrendPoint(BaseModel):
    year: int
    total_income: float
    total_expense: float
    yoy_income_change: Optional[float] = None
    yoy_expense_change: Optional[float] = None


class CategoryTrendPoint(BaseModel):
    category: str
    month: str
    amount: float
    last_3m_avg: Optional[float] = None
    pct_deviation: Optional[float] = None


# ── Anomaly Schemas ────────────────────────────────────────────────────────────

class AnomalyRecord(BaseModel):
    month: str
    category: Optional[str] = None
    reason: str
    amount: Optional[float] = None
    threshold: Optional[float] = None


# ── Behavior Schemas ───────────────────────────────────────────────────────────

class TopCategory(BaseModel):
    category: str
    total_amount: float
    percentage: float


class SpendingBehavior(BaseModel):
    top_5_categories: list[TopCategory]
    top3_concentration_pct: float
    essential_pct: float
    discretionary_pct: float
    uncategorized_pct: float


# ── Budget & Savings Schemas ───────────────────────────────────────────────────

class BudgetBaseline(BaseModel):
    category: str
    median_3m: float
    tag: str


class SavingsOpportunity(BaseModel):
    category: str
    current_month_amount: float
    median_3m: float
    potential_savings: float
    tag: str


# ── Dashboard Response ─────────────────────────────────────────────────────────

class DashboardResponse(BaseModel):
    monthly_aggregates: list[MonthlyAggregateSchema]
    yearly_aggregates: list[YearlyAggregateSchema]
    category_aggregates: list[CategoryAggregateSchema]
    monthly_trends: list[MonthlyTrendPoint]
    yearly_trends: list[YearlyTrendPoint]
    category_trends: list[CategoryTrendPoint]
    anomalies_total_spend: list[AnomalyRecord]
    anomalies_category: list[AnomalyRecord]
    anomalies_erratic: list[AnomalyRecord]
    spending_behavior: SpendingBehavior
    budget_baseline: list[BudgetBaseline]
    savings_opportunities: list[SavingsOpportunity]


# ── Upload Response ────────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    status: str
    rows_inserted: int
    rows_skipped: int
    message: str
