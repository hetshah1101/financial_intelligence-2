# app/services/category_engine.py - Category-level aggregations

import logging
from typing import List, Dict, Any

from app.db.database import get_connection

logger = logging.getLogger(__name__)


def compute_category_aggregates(months: List[str]) -> List[Dict[str, Any]]:
    """Compute and persist category-level aggregates for given months."""
    results = []

    with get_connection() as conn:
        for month in months:
            total_row = conn.execute(
                """
                SELECT COALESCE(SUM(amount), 0) as total
                FROM transactions
                WHERE strftime('%Y-%m', date) = ? AND type = 'expense'
                """,
                (month,),
            ).fetchone()
            total_expense = total_row["total"] or 0.0

            rows = conn.execute(
                """
                SELECT category, SUM(amount) as total_amount
                FROM transactions
                WHERE strftime('%Y-%m', date) = ? AND type = 'expense'
                GROUP BY category
                ORDER BY total_amount DESC
                """,
                (month,),
            ).fetchall()

            for row in rows:
                cat_total = row["total_amount"]
                pct = (cat_total / total_expense * 100) if total_expense > 0 else 0.0

                conn.execute(
                    """
                    INSERT INTO category_aggregates
                        (month, category, total_amount, percentage_of_total)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(month, category) DO UPDATE SET
                        total_amount        = excluded.total_amount,
                        percentage_of_total = excluded.percentage_of_total,
                        updated_at          = datetime('now')
                    """,
                    (month, row["category"], cat_total, round(pct, 2)),
                )

                results.append({
                    "month":               month,
                    "category":            row["category"],
                    "total_amount":        cat_total,
                    "percentage_of_total": round(pct, 2),
                })

    logger.info(f"Category aggregates computed for {len(months)} month(s)")
    return results


def get_category_aggregates(month: str) -> List[Dict[str, Any]]:
    """Retrieve category aggregates for a specific month."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM category_aggregates
            WHERE month = ?
            ORDER BY total_amount DESC
            """,
            (month,),
        ).fetchall()
        return [dict(r) for r in rows]
