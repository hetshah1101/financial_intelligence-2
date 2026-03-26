# app/services/cashflow_engine.py - Monthly cashflow aggregation

import logging
from typing import List, Dict, Any

from app.db.database import get_connection

logger = logging.getLogger(__name__)


def compute_monthly_aggregates(months: List[str]) -> List[Dict[str, Any]]:
    """Compute and persist monthly aggregate metrics for given months."""
    results = []

    with get_connection() as conn:
        for month in months:
            rows = conn.execute(
                """
                SELECT type, SUM(amount) as total
                FROM transactions
                WHERE strftime('%Y-%m', date) = ?
                GROUP BY type
                """,
                (month,),
            ).fetchall()

            totals: Dict[str, float] = {r["type"]: r["total"] for r in rows}
            income      = totals.get("income", 0.0)
            expense     = totals.get("expense", 0.0)
            investment  = totals.get("investment", 0.0)
            net_savings = income - expense - investment
            savings_rate = (net_savings / income * 100) if income > 0 else 0.0

            conn.execute(
                """
                INSERT INTO monthly_aggregates
                    (month, total_income, total_expense, total_investment, net_savings, savings_rate)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(month) DO UPDATE SET
                    total_income     = excluded.total_income,
                    total_expense    = excluded.total_expense,
                    total_investment = excluded.total_investment,
                    net_savings      = excluded.net_savings,
                    savings_rate     = excluded.savings_rate,
                    updated_at       = datetime('now')
                """,
                (month, income, expense, investment, net_savings, savings_rate),
            )

            results.append({
                "month":            month,
                "total_income":     income,
                "total_expense":    expense,
                "total_investment": investment,
                "net_savings":      net_savings,
                "savings_rate":     round(savings_rate, 2),
            })
            logger.info(f"Month {month}: income={income}, expense={expense}, savings_rate={savings_rate:.1f}%")

    return results


def get_all_monthly_aggregates() -> List[Dict[str, Any]]:
    """Retrieve all monthly aggregates ordered by month."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM monthly_aggregates ORDER BY month ASC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_monthly_aggregate(month: str) -> Dict[str, Any]:
    """Retrieve aggregate for a single month."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM monthly_aggregates WHERE month = ?", (month,)
        ).fetchone()
        return dict(row) if row else {}
