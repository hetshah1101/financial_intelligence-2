# app/services/analytics_orchestrator.py - Coordinate all analytics engines

import logging
from typing import List, Dict, Any

from app.config import config
from app.db.database import get_connection
from app.services.cashflow_engine import compute_monthly_aggregates
from app.services.category_engine import compute_category_aggregates
from app.services.trend_engine import compute_rolling_averages
from app.services.anomaly_engine import detect_anomalies
from app.services.behavior_engine import analyze_behavior
from app.services.efficiency_engine import compute_efficiency_flags
from app.services.savings_engine import identify_savings_opportunities
from app.services.ai_service import generate_and_cache_insights

logger = logging.getLogger(__name__)


def run_full_pipeline(months: List[str]) -> Dict[str, Any]:
    """
    Run complete analytics pipeline for given months.
    Used after initial load or incremental update.
    """
    logger.info(f"Running full pipeline for months: {months}")

    # Step 1: Recompute aggregates
    monthly_aggs  = compute_monthly_aggregates(months)
    category_aggs = compute_category_aggregates(months)

    # Step 2: For each month, compute advanced analytics and generate insights
    all_results: Dict[str, Any] = {}

    for month in months:
        logger.info(f"Running advanced analytics for {month}")

        anomalies    = detect_anomalies(month, config.app.anomaly_threshold, config.app.rolling_window)
        behaviors    = analyze_behavior(month, config.app.high_freq_threshold)
        efficiency   = compute_efficiency_flags(month)
        savings      = identify_savings_opportunities(month)
        rolling_avgs = compute_rolling_averages(config.app.rolling_window)

        month_agg = next((m for m in monthly_aggs if m["month"] == month), {})
        cat_aggs  = [c for c in category_aggs if c["month"] == month]

        # AI receives only pre-computed structured data — never raw transactions
        analytics_payload: Dict[str, Any] = {
            "summary":               month_agg,
            "category_breakdown":    cat_aggs,
            "anomalies":             anomalies,
            "behavioral_patterns":   behaviors,
            "efficiency_flags":      efficiency,
            "savings_opportunities": savings,
            "rolling_averages":      rolling_avgs,
        }

        insight_text = generate_and_cache_insights(month, analytics_payload)

        all_results[month] = {
            "analytics": analytics_payload,
            "insights":  insight_text,
        }

    logger.info("Full pipeline complete")
    return all_results


def get_latest_month() -> str:
    """Return the most recent YYYY-MM with transaction data."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT MAX(strftime('%Y-%m', date)) as month FROM transactions"
        ).fetchone()
        return row["month"] if row and row["month"] else ""
