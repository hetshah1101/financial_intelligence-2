import pandas as pd
from collections import defaultdict
from sqlalchemy import func
from sqlalchemy.orm import Session

from models import MonthlyAggregate, CategoryAggregate, YearlyAggregate, Transaction
from analytics.monthly import compute_monthly_aggregates
from analytics.yearly import compute_yearly_aggregates
from analytics.category import compute_category_aggregates
from analytics.trends import compute_monthly_trends, compute_yearly_trends, compute_category_trends
from analytics.anomalies import detect_total_spend_anomalies, detect_category_anomalies, detect_erratic_spend
from analytics.behavior import compute_spending_behavior
from analytics.budget import compute_budget_baseline
from analytics.savings import compute_savings_opportunities
from schemas import DashboardResponse

# Card credit/charge account name fragments (case-insensitive substring match)
_CARD_KEYWORDS = ("card", "credit", "amex", "onecard", "slice")
_DEBIT_KEYWORDS = ("debit",)


def _acct_type(name: str) -> str:
    n = name.strip().lower()
    if any(kw in n for kw in _DEBIT_KEYWORDS):
        return "Bank"
    if any(kw in n for kw in _CARD_KEYWORDS):
        return "Card"
    return "Bank"


def recompute_aggregates(db: Session, months: list[str] | None = None) -> None:
    years = None
    if months:
        years = list({int(m[:4]) for m in months})

    compute_monthly_aggregates(db, months=months)
    compute_yearly_aggregates(db, years=years)
    compute_category_aggregates(db, months=months)


def build_dashboard(db: Session) -> DashboardResponse:
    # Load all aggregates as DataFrames
    monthly_rows = db.query(MonthlyAggregate).order_by(MonthlyAggregate.month).all()
    yearly_rows = db.query(YearlyAggregate).order_by(YearlyAggregate.year).all()
    category_rows = db.query(CategoryAggregate).order_by(
        CategoryAggregate.month, CategoryAggregate.category
    ).all()

    monthly_df = pd.DataFrame([{
        "month": r.month,
        "total_income": r.total_income,
        "total_expense": r.total_expense,
        "total_investment": r.total_investment,
        "net_savings": r.net_savings,
        "savings_rate": r.savings_rate,
    } for r in monthly_rows])

    yearly_df = pd.DataFrame([{
        "year": r.year,
        "total_income": r.total_income,
        "total_expense": r.total_expense,
        "total_investment": r.total_investment,
        "avg_monthly_expense": r.avg_monthly_expense,
        "savings_rate": r.savings_rate,
    } for r in yearly_rows])

    category_df = pd.DataFrame([{
        "month": r.month,
        "category": r.category,
        "total_amount": r.total_amount,
        "percentage_of_total_expense": r.percentage_of_total_expense,
        "tag": r.tag,
    } for r in category_rows])

    # Compute analytics layers
    monthly_trends = compute_monthly_trends(monthly_df) if not monthly_df.empty else []
    yearly_trends = compute_yearly_trends(yearly_df) if not yearly_df.empty else []
    category_trends = compute_category_trends(category_df) if not category_df.empty else []

    anomalies_total = detect_total_spend_anomalies(monthly_df) if not monthly_df.empty else []
    anomalies_cat = detect_category_anomalies(category_df) if not category_df.empty else []
    anomalies_erratic = detect_erratic_spend(category_df) if not category_df.empty else []

    behavior = compute_spending_behavior(category_df)
    budget = compute_budget_baseline(category_df)
    savings = compute_savings_opportunities(category_df, budget)

    # ── Account-level monthly breakdown (Bank vs Card) ───────────────────────
    acct_type_rows = (
        db.query(
            Transaction.month,
            Transaction.account,
            Transaction.type,
            func.sum(Transaction.amount).label("total"),
        )
        .filter(Transaction.type.in_(["expense", "income", "investment"]))
        .group_by(Transaction.month, Transaction.account, Transaction.type)
        .all()
    )
    acct_monthly_map: dict = defaultdict(lambda: {"expense": 0.0, "income": 0.0, "investment": 0.0})
    for row in acct_type_rows:
        k = (row.month, _acct_type(row.account))
        acct_monthly_map[k][row.type] += float(row.total or 0)

    acct_monthly_list = [
        {
            "month": k[0],
            "account_type": k[1],
            "expense": v["expense"],
            "income": v["income"],
            "investment": v["investment"],
        }
        for k, v in sorted(acct_monthly_map.items())
    ]

    # ── Account-level category breakdown (expenses only) ─────────────────────
    acct_cat_rows = (
        db.query(
            Transaction.month,
            Transaction.account,
            Transaction.category,
            func.sum(Transaction.amount).label("total"),
        )
        .filter(Transaction.type == "expense")
        .group_by(Transaction.month, Transaction.account, Transaction.category)
        .all()
    )
    acct_cat_map: dict = defaultdict(float)
    for row in acct_cat_rows:
        acct_cat_map[(row.month, _acct_type(row.account), row.category)] += float(row.total or 0)

    acct_cat_list = [
        {"month": k[0], "account_type": k[1], "category": k[2], "total_amount": v}
        for k, v in sorted(acct_cat_map.items())
    ]

    return DashboardResponse(
        monthly_aggregates=[{
            "month": r.month,
            "total_income": r.total_income,
            "total_expense": r.total_expense,
            "total_investment": r.total_investment,
            "net_savings": r.net_savings,
            "savings_rate": r.savings_rate,
        } for r in monthly_rows],
        yearly_aggregates=[{
            "year": r.year,
            "total_income": r.total_income,
            "total_expense": r.total_expense,
            "total_investment": r.total_investment,
            "avg_monthly_expense": r.avg_monthly_expense,
            "savings_rate": r.savings_rate,
        } for r in yearly_rows],
        category_aggregates=[{
            "month": r.month,
            "category": r.category,
            "total_amount": r.total_amount,
            "percentage_of_total_expense": r.percentage_of_total_expense,
            "tag": r.tag,
        } for r in category_rows],
        account_monthly_aggregates=acct_monthly_list,
        account_category_aggregates=acct_cat_list,
        monthly_trends=monthly_trends,
        yearly_trends=yearly_trends,
        category_trends=category_trends,
        anomalies_total_spend=anomalies_total,
        anomalies_category=anomalies_cat,
        anomalies_erratic=anomalies_erratic,
        spending_behavior=behavior,
        budget_baseline=budget,
        savings_opportunities=savings,
    )
