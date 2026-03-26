# app/services/anomaly_engine.py - Spending anomaly detection

import logging
from typing import List, Dict, Any

from app.db.database import get_connection

logger = logging.getLogger(__name__)


def detect_anomalies(month: str, threshold: float = 1.4, window: int = 3) -> List[Dict[str, Any]]:
    """
    Detect categories where current month spend > threshold × avg(last `window` months).

    Args:
        month:     YYYY-MM of the month to evaluate
        threshold: multiplier above which spend is anomalous (default 1.4)
        window:    number of prior months to average (default 3)
    """
    anomalies: List[Dict[str, Any]] = []

    with get_connection() as conn:
        current_rows = conn.execute(
            """
            SELECT category, SUM(amount) as total
            FROM transactions
            WHERE strftime('%Y-%m', date) = ? AND type = 'expense'
            GROUP BY category
            """,
            (month,),
        ).fetchall()

        prior_rows = conn.execute(
            """
            SELECT category, strftime('%Y-%m', date) as month, SUM(amount) as total
            FROM transactions
            WHERE strftime('%Y-%m', date) < ?
              AND type = 'expense'
            GROUP BY category, strftime('%Y-%m', date)
            ORDER BY month DESC
            """,
            (month,),
        ).fetchall()

    # Build category -> list of recent monthly totals (capped at `window`)
    prior_by_cat: Dict[str, List[float]] = {}
    seen_months_by_cat: Dict[str, set] = {}

    for row in prior_rows:
        cat = row["category"]
        m   = row["month"]
        if cat not in prior_by_cat:
            prior_by_cat[cat] = []
            seen_months_by_cat[cat] = set()
        if len(prior_by_cat[cat]) < window and m not in seen_months_by_cat[cat]:
            prior_by_cat[cat].append(row["total"])
            seen_months_by_cat[cat].add(m)

    for row in current_rows:
        cat     = row["category"]
        current = row["total"]
        prior   = prior_by_cat.get(cat, [])

        if not prior:
            continue

        avg_prior = sum(prior) / len(prior)
        ratio     = current / avg_prior if avg_prior > 0 else 0.0

        if ratio > threshold:
            anomalies.append({
                "category":             cat,
                "current_month_amount": round(current, 2),
                "three_month_avg":      round(avg_prior, 2),
                "ratio":                round(ratio, 2),
                "month":                month,
            })
            logger.info(f"Anomaly: {cat} — ₹{current:.0f} vs avg ₹{avg_prior:.0f} (ratio {ratio:.2f})")

    return sorted(anomalies, key=lambda x: x["ratio"], reverse=True)
