# app/services/behavior_engine.py - Behavioral spend pattern detection

import logging
from datetime import datetime
from typing import List, Dict, Any

from app.db.database import get_connection

logger = logging.getLogger(__name__)


def analyze_behavior(month: str, high_freq_threshold: int = 5) -> List[Dict[str, Any]]:
    """
    Detect behavioral patterns:
      - High-frequency small spends per category
      - Weekend vs weekday spend ratio

    Args:
        month:               YYYY-MM to analyze
        high_freq_threshold: min transactions/month to flag as high-frequency
    """
    patterns: List[Dict[str, Any]] = []

    with get_connection() as conn:
        freq_rows = conn.execute(
            """
            SELECT category,
                   COUNT(*)    as txn_count,
                   AVG(amount) as avg_amount,
                   SUM(amount) as total
            FROM transactions
            WHERE strftime('%Y-%m', date) = ? AND type = 'expense'
            GROUP BY category
            HAVING COUNT(*) >= ?
            ORDER BY txn_count DESC
            """,
            (month, high_freq_threshold),
        ).fetchall()

        for row in freq_rows:
            patterns.append({
                "pattern_type": "high_frequency_spend",
                "description":  (
                    f"{row['category']}: {row['txn_count']} transactions "
                    f"averaging ₹{row['avg_amount']:.0f} each"
                ),
                "value": round(row["total"], 2),
            })

        all_rows = conn.execute(
            """
            SELECT date, amount
            FROM transactions
            WHERE strftime('%Y-%m', date) = ? AND type = 'expense'
            """,
            (month,),
        ).fetchall()

    weekend_total = 0.0
    weekday_total = 0.0

    for row in all_rows:
        d = datetime.strptime(row["date"], "%Y-%m-%d")
        if d.weekday() >= 5:  # Saturday=5, Sunday=6
            weekend_total += row["amount"]
        else:
            weekday_total += row["amount"]

    if weekday_total > 0:
        ratio = weekend_total / weekday_total
        patterns.append({
            "pattern_type": "weekend_vs_weekday",
            "description":  (
                f"Weekend spend ₹{weekend_total:.0f} vs weekday ₹{weekday_total:.0f} "
                f"(ratio {ratio:.2f})"
            ),
            "value": round(ratio, 2),
        })

    logger.info(f"Behavior analysis for {month}: {len(patterns)} patterns found")
    return patterns
