import io
import logging
import pandas as pd
from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from ingestion.pipeline import run_pipeline
from analytics.engine import recompute_aggregates
from routers.dashboard import invalidate_dashboard_cache
from models import Transaction, MonthlyAggregate, CategoryAggregate, YearlyAggregate
from schemas import UploadResponse

logger = logging.getLogger("finsight.upload")

router = APIRouter()


def _read_upload(file: UploadFile) -> pd.DataFrame:
    content = file.file.read()
    name = (file.filename or "").lower()
    if name.endswith(".csv"):
        return pd.read_csv(io.BytesIO(content))
    elif name.endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(content))
    else:
        # Try CSV first, then Excel
        try:
            return pd.read_csv(io.BytesIO(content))
        except Exception:
            return pd.read_excel(io.BytesIO(content))


@router.delete("/reset")
def reset_all(db: Session = Depends(get_db)):
    for model in [CategoryAggregate, MonthlyAggregate, YearlyAggregate, Transaction]:
        db.query(model).delete()
    db.commit()
    return {"status": "ok", "message": "All tables truncated."}


def _bg_recompute(months: list[str] | None = None) -> None:
    """Run aggregate recompute in background and bust the dashboard cache."""
    from database import SessionLocal
    db = SessionLocal()
    try:
        recompute_aggregates(db, months=months)
        invalidate_dashboard_cache()
        logger.info("Aggregate recompute complete (months=%s)", months)
    finally:
        db.close()


@router.post("/upload", response_model=UploadResponse)
async def upload_initial(
    file: UploadFile = File(...),
    bg: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
):
    try:
        df = _read_upload(file)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse file: {e}")

    logger.info("File read: %d rows, columns: %s", df.shape[0], df.columns.tolist())

    try:
        result = run_pipeline(df, db)
        logger.info("Pipeline: inserted=%d skipped=%d", result["inserted"], result["skipped"])
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in pipeline")
        raise HTTPException(status_code=500, detail=str(e))

    if result["inserted"] > 0:
        bg.add_task(_bg_recompute)

    return UploadResponse(
        status="processing" if result["inserted"] > 0 else "success",
        rows_inserted=result["inserted"],
        rows_skipped=result["skipped"],
        message=f"Inserted {result['inserted']} transactions, skipped {result['skipped']} duplicates.",
    )


@router.post("/update", response_model=UploadResponse)
async def upload_incremental(
    file: UploadFile = File(...),
    bg: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
):
    try:
        df = _read_upload(file)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse file: {e}")

    try:
        result = run_pipeline(df, db)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    affected = result["affected_months"]
    if affected:
        bg.add_task(_bg_recompute, affected)

    return UploadResponse(
        status="processing" if affected else "success",
        rows_inserted=result["inserted"],
        rows_skipped=result["skipped"],
        message=f"Inserted {result['inserted']} new transactions, skipped {result['skipped']} duplicates.",
    )
