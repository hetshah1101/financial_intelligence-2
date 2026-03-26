# app/services/trend_engine.py - MoM and rolling average trends

import logging
from typing import List, Dict, Any

from app.db.database import get_connection

logger = logging.getLogger(__name__)


def compute_mom_change(month: str) -> Dict[str, Any]:
    """Compute Month-over-Month % change for key metrics."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT month, total_income, total_expense, total_investment, net_savings, savings_rate
            FROM monthly_aggregates
            ORDER BY month DESC
            LIMIT 2
            """
        ).fetchall()

    if len(rows) < 2:
        return {"available": False, "reason": "Need at least 2 months of data"}

    current  = dict(rows[0])
    previous = dict(rows[1])

    def pct_change(cur: float, prev: float) -> float:
        if prev == 0:
            return 0.0
        return round((cur - prev) / prev * 100, 2)

    return {
        "available":              True,
        "current_month":          current["month"],
        "previous_month":         previous["month"],
        "income_change_pct":      pct_change(current["total_income"],     previous["total_income"]),
        "expense_change_pct":     pct_change(current["total_expense"],    previous["total_expense"]),
        "investment_change_pct":  pct_change(current["total_investment"], previous["total_investment"]),
        "savings_change_pct":     pct_change(current["net_savings"],      previous["net_savings"]),
        "current":                current,
        "previous":               previous,
    }


def compute_rolling_averages(window: int = 3) -> Dict[str, Any]:
    """Compute rolling averages over last `window` months for key metrics."""
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT month, total_income, total_expense, total_investment, net_savings
            FROM monthly_aggregates
            ORDER BY month DESC
            LIMIT {window}
            """
        ).fetchall()

    if not rows:
        return {}

    data    = [dict(r) for r in rows]
    metrics = ["total_income", "total_expense", "total_investment", "net_savings"]

    averages: Dict[str, float] = {}
    for metric in metrics:
        vals = [r[metric] for r in data]
        averages[f"avg_{metric}"] = round(sum(vals) / len(vals), 2)

    return {
        "window_months": window,
        "months_used":   [r["month"] for r in data],
        **averages,
    }


def get_trend_series() -> List[Dict[str, Any]]:
    """Return all monthly aggregates ordered for charting."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM monthly_aggregates ORDER BY month ASC"
        ).fetchall()
        return [dict(r) for r in rows]
