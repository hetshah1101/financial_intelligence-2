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


class AccountMonthlySchema(BaseModel):
    month: str
    account_type: str  # "Bank" or "Card"
    expense: float
    income: float
    investment: float


class AccountCategorySchema(BaseModel):
    month: str
    account_type: str
    category: str
    total_amount: float


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
    account_monthly_aggregates: list[AccountMonthlySchema] = []
    account_category_aggregates: list[AccountCategorySchema] = []
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


# ── Investment / Portfolio Schemas ─────────────────────────────────────────────

class InvestmentSchema(BaseModel):
    id: int
    date: str
    month: str
    instrument_type: str
    name: str
    symbol: Optional[str] = None
    isin: Optional[str] = None
    folio_number: Optional[str] = None
    units: Optional[float] = None
    price_per_unit: Optional[float] = None
    amount: float
    transaction_type: Optional[str] = None
    account: Optional[str] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class HoldingSchema(BaseModel):
    id: int
    snapshot_date: str
    instrument_type: str
    name: str
    symbol: Optional[str] = None
    isin: Optional[str] = None
    folio_number: Optional[str] = None
    units: Optional[float] = None
    avg_cost_per_unit: Optional[float] = None
    current_price: Optional[float] = None
    current_value: Optional[float] = None
    invested_value: Optional[float] = None
    unrealised_pnl: Optional[float] = None
    unrealised_pnl_pct: Optional[float] = None
    account: Optional[str] = None

    model_config = {"from_attributes": True}


class LiabilitySchema(BaseModel):
    id: int
    name: str
    liability_type: Optional[str] = None
    principal: Optional[float] = None
    outstanding: float
    interest_rate: Optional[float] = None
    emi_amount: Optional[float] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    account: Optional[str] = None
    as_of_date: Optional[str] = None

    model_config = {"from_attributes": True}


class LiabilityCreate(BaseModel):
    name: str
    liability_type: Optional[str] = None
    principal: Optional[float] = None
    outstanding: float
    interest_rate: Optional[float] = None
    emi_amount: Optional[float] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    account: Optional[str] = None
    as_of_date: Optional[str] = None


class GoalSchema(BaseModel):
    id: int
    name: str
    target_amount: float
    target_date: Optional[str] = None
    current_amount: float
    monthly_sip: float
    linked_isin: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


class GoalCreate(BaseModel):
    name: str
    target_amount: float
    target_date: Optional[str] = None
    current_amount: float = 0
    monthly_sip: float = 0
    linked_isin: Optional[str] = None
    notes: Optional[str] = None


class GoalUpdate(BaseModel):
    target_amount: Optional[float] = None
    target_date: Optional[str] = None
    current_amount: Optional[float] = None
    monthly_sip: Optional[float] = None
    linked_isin: Optional[str] = None
    notes: Optional[str] = None


class PortfolioSummary(BaseModel):
    snapshot_date: str
    total_current_value: float
    total_invested_value: float
    total_unrealised_pnl: float
    total_unrealised_pnl_pct: float
    by_instrument_type: dict


class NetWorthSummary(BaseModel):
    as_of_date: str
    total_assets: float
    total_liabilities: float
    net_worth: float
    asset_breakdown: dict
    liability_breakdown: dict


class CategoryTagOverrideSchema(BaseModel):
    category: str
    tag: str

    model_config = {"from_attributes": True}


class GoalSimulation(BaseModel):
    goal_name: str
    target_amount: float
    current_amount: float
    monthly_sip: float
    months_to_goal: Optional[int] = None
    projected_date: Optional[str] = None
    shortfall: float
    on_track: bool
