import io
import pandas as pd
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from ingestion.pipeline import run_pipeline
from analytics.engine import recompute_aggregates
from models import Transaction, MonthlyAggregate, CategoryAggregate, YearlyAggregate
from schemas import UploadResponse

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


@router.post("/upload", response_model=UploadResponse)
async def upload_initial(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        df = _read_upload(file)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse file: {e}")

    print(f"[DEBUG] File read: {df.shape[0]} rows, columns: {df.columns.tolist()}")

    try:
        result = run_pipeline(df, db)
        print(f"[DEBUG] Pipeline result: inserted={result['inserted']}, skipped={result['skipped']}")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        print(f"[DEBUG] Unexpected error in pipeline: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

    if result["inserted"] > 0:
        recompute_aggregates(db)

    return UploadResponse(
        status="success",
        rows_inserted=result["inserted"],
        rows_skipped=result["skipped"],
        message=f"Inserted {result['inserted']} transactions, skipped {result['skipped']} duplicates.",
    )


@router.post("/update", response_model=UploadResponse)
async def upload_incremental(file: UploadFile = File(...), db: Session = Depends(get_db)):
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
        # Incremental recompute: only affected months + their year
        recompute_aggregates(db, months=affected)

    return UploadResponse(
        status="success",
        rows_inserted=result["inserted"],
        rows_skipped=result["skipped"],
        message=f"Inserted {result['inserted']} new transactions, skipped {result['skipped']} duplicates.",
    )
