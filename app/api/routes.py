# app/api/routes.py - FastAPI route handlers

import logging
from fastapi import APIRouter, File, UploadFile, HTTPException, Query

from app.config import config
from app.db.database import get_connection
from app.models.schemas import UploadResponse
from app.utils.ingestion import parse_upload, upsert_transactions, get_affected_months
from app.services.analytics_orchestrator import run_full_pipeline, get_latest_month
from app.services.cashflow_engine import get_all_monthly_aggregates, get_monthly_aggregate
from app.services.category_engine import get_category_aggregates
from app.services.trend_engine import compute_mom_change, compute_rolling_averages
from app.services.anomaly_engine import detect_anomalies
from app.services.behavior_engine import analyze_behavior
from app.services.efficiency_engine import compute_efficiency_flags
from app.services.savings_engine import identify_savings_opportunities
from app.services.ai_service import get_cached_insights, generate_and_cache_insights

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Upload ────────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=UploadResponse, summary="Initial full dataset upload")
async def upload_initial(file: UploadFile = File(...)):
    """
    Flow 1: Upload full historical dataset.
    Parses file, inserts transactions, runs full analytics pipeline.
    """
    try:
        contents = await file.read()
        filename = file.filename or ""  # FIX: don't force .csv
        df = parse_upload(contents, filename)
    except ValueError as e:
        print("UPLOAD ERROR:", str(e)) 
        raise HTTPException(status_code=422, detail=str(e))
    
    if df is None or df.empty:  # FIX: basic safety check
        raise HTTPException(status_code=400, detail="Uploaded file is empty or invalid")

    inserted, skipped = upsert_transactions(df)
    months = get_affected_months(df)

    if not months:
        raise HTTPException(status_code=400, detail="No valid data found in file")

    run_full_pipeline(months)

    return UploadResponse(
        status="success",
        rows_inserted=inserted,
        rows_skipped=skipped,
        months_processed=months,
        message=f"Processed {len(months)} month(s). {inserted} rows inserted, {skipped} skipped.",
    )


@router.post("/update", response_model=UploadResponse, summary="Incremental monthly update")
async def upload_incremental(file: UploadFile = File(...)):
    """
    Flow 2: Incremental update — appends safely (no duplicates),
    recomputes only affected months, generates fresh insights.
    """
    try:
        contents = await file.read()
        df = parse_upload(contents, file.filename or "update.csv")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    inserted, skipped = upsert_transactions(df)
    months = get_affected_months(df)

    if not months:
        raise HTTPException(status_code=400, detail="No valid new data found in file")

    run_full_pipeline(months)

    return UploadResponse(
        status="success",
        rows_inserted=inserted,
        rows_skipped=skipped,
        months_processed=months,
        message=(
            f"Incremental update: {len(months)} month(s) recomputed. "
            f"{inserted} new rows, {skipped} duplicates skipped."
        ),
    )


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", summary="Full dashboard metrics")
async def get_dashboard():
    """
    Return aggregated metrics for the latest month plus all historical trends.
    """
    latest = get_latest_month()
    if not latest:
        raise HTTPException(
            status_code=404,
            detail="No data available. Please upload a dataset first.",
        )

    return {
        "latest_month":          get_monthly_aggregate(latest),
        "all_monthly":           get_all_monthly_aggregates(),
        "latest_categories":     get_category_aggregates(latest),
        "anomalies":             detect_anomalies(latest, config.app.anomaly_threshold),
        "savings_opportunities": identify_savings_opportunities(latest),
        "mom_change":            compute_mom_change(latest),
        "rolling_averages":      compute_rolling_averages(config.app.rolling_window),
    }


# ── Insights ──────────────────────────────────────────────────────────────────

@router.get("/insights/{month}", summary="AI insights for a given month")
async def get_insights(
    month: str,
    refresh: bool = Query(False, description="Force regenerate insights"),
):
    """
    Return AI-generated insights for a given YYYY-MM month.
    Uses insights_cache by default; pass ?refresh=true to regenerate.
    """
    if not refresh:
        cached = get_cached_insights(month)
        if cached:
            return {"month": month, "insights": cached, "source": "cache"}

    month_agg = get_monthly_aggregate(month)
    if not month_agg:
        raise HTTPException(status_code=404, detail=f"No data found for month {month}")

    analytics_payload = {
        "summary":               month_agg,
        "category_breakdown":    get_category_aggregates(month),
        "anomalies":             detect_anomalies(month, config.app.anomaly_threshold),
        "behavioral_patterns":   analyze_behavior(month),
        "efficiency_flags":      compute_efficiency_flags(month),
        "savings_opportunities": identify_savings_opportunities(month),
        "rolling_averages":      compute_rolling_averages(config.app.rolling_window),
    }

    content = generate_and_cache_insights(month, analytics_payload)
    return {"month": month, "insights": content, "source": "generated"}


# ── Utility ───────────────────────────────────────────────────────────────────

@router.get("/months", summary="List all months with transaction data")
async def list_months():
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT strftime('%Y-%m', date) as month
            FROM transactions
            ORDER BY month DESC
            """
        ).fetchall()
        return {"months": [r["month"] for r in rows]}


@router.get("/health", summary="Health check")
async def health():
    return {"status": "ok"}
