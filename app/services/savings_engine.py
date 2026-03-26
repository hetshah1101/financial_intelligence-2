# app/services/savings_engine.py - Savings opportunity identification

import logging
from typing import List, Dict, Any

from app.db.database import get_connection

logger = logging.getLogger(__name__)

# Optimal spend ranges as fraction of monthly income (lower_pct, upper_pct)
OPTIMAL_RANGES: Dict[str, tuple] = {
    "Food":          (0.10, 0.18),
    "Transport":     (0.04, 0.08),
    "Entertainment": (0.02, 0.05),
    "Shopping":      (0.03, 0.07),
    "Utilities":     (0.03, 0.06),
    "Travel":        (0.03, 0.08),
    "Health":        (0.02, 0.05),
}


def identify_savings_opportunities(month: str) -> List[Dict[str, Any]]:
    """
    Identify categories where spend exceeds the optimal upper bound.

    Returns:
        List of {category, current, optimal_range, potential_savings}
    """
    opportunities: List[Dict[str, Any]] = []

    with get_connection() as conn:
        agg_row = conn.execute(
            "SELECT total_income FROM monthly_aggregates WHERE month = ?", (month,)
        ).fetchone()

        if not agg_row or agg_row["total_income"] == 0:
            return []

        income = agg_row["total_income"]

        cat_rows = conn.execute(
            """
            SELECT category, SUM(amount) as total
            FROM transactions
            WHERE strftime('%Y-%m', date) = ? AND type = 'expense'
            GROUP BY category
            """,
            (month,),
        ).fetchall()

    for row in cat_rows:
        cat     = row["category"]
        current = row["total"]

        if cat not in OPTIMAL_RANGES:
            continue

        low_pct, high_pct = OPTIMAL_RANGES[cat]
        low_abs  = income * low_pct
        high_abs = income * high_pct

        if current > high_abs:
            savings = round(current - high_abs, 2)
            opportunities.append({
                "category":          cat,
                "current":           round(current, 2),
                "optimal_range":     f"₹{low_abs:.0f} – ₹{high_abs:.0f}",
                "potential_savings": savings,
            })
            logger.info(f"Savings opportunity: {cat} — save ₹{savings:.0f}")

    return sorted(opportunities, key=lambda x: x["potential_savings"], reverse=True)
