# app/services/efficiency_engine.py - Spend efficiency vs historical median

import logging
from typing import List, Dict, Any

from app.db.database import get_connection

logger = logging.getLogger(__name__)


def compute_efficiency_flags(month: str, deviation_threshold: float = 20.0) -> List[Dict[str, Any]]:
    """
    Flag categories where current spend deviates significantly from historical median.

    Args:
        month:                YYYY-MM to evaluate
        deviation_threshold:  % deviation considered significant (default 20%)
    """
    flags: List[Dict[str, Any]] = []

    with get_connection() as conn:
        current_rows = conn.execute(
            """
            SELECT category, SUM(amount) as current_total
            FROM transactions
            WHERE strftime('%Y-%m', date) = ? AND type = 'expense'
            GROUP BY category
            """,
            (month,),
        ).fetchall()

        for row in current_rows:
            cat           = row["category"]
            current_total = row["current_total"]

            hist_rows = conn.execute(
                """
                SELECT strftime('%Y-%m', date) as month, SUM(amount) as total
                FROM transactions
                WHERE strftime('%Y-%m', date) < ?
                  AND type = 'expense'
                  AND category = ?
                GROUP BY strftime('%Y-%m', date)
                ORDER BY month DESC
                """,
                (month, cat),
            ).fetchall()

            if len(hist_rows) < 2:
                continue

            hist_totals = sorted([r["total"] for r in hist_rows])
            n = len(hist_totals)
            median = (
                (hist_totals[n // 2 - 1] + hist_totals[n // 2]) / 2
                if n % 2 == 0
                else hist_totals[n // 2]
            )

            if median == 0:
                continue

            deviation_pct = ((current_total - median) / median) * 100

            if abs(deviation_pct) >= deviation_threshold:
                flags.append({
                    "category":          cat,
                    "current":           round(current_total, 2),
                    "historical_median": round(median, 2),
                    "deviation_pct":     round(deviation_pct, 2),
                })
                logger.info(
                    f"Efficiency flag: {cat} — current ₹{current_total:.0f}, "
                    f"median ₹{median:.0f}, deviation {deviation_pct:.1f}%"
                )

    return sorted(flags, key=lambda x: abs(x["deviation_pct"]), reverse=True)
