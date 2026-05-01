import time
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from analytics.engine import build_dashboard
from models import MonthlyAggregate
from schemas import DashboardResponse

router = APIRouter()

_cache: dict = {"data": None, "ts": 0.0}
_CACHE_TTL = 60.0


def invalidate_dashboard_cache() -> None:
    """Call after any write that changes aggregate data."""
    _cache["ts"] = 0.0


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(db: Session = Depends(get_db)):
    now = time.time()
    if _cache["data"] is not None and now - _cache["ts"] < _CACHE_TTL:
        return _cache["data"]
    result = build_dashboard(db)
    _cache["data"] = result
    _cache["ts"] = now
    return result


@router.get("/months")
def get_months(db: Session = Depends(get_db)):
    months = (
        db.query(MonthlyAggregate.month)
        .order_by(MonthlyAggregate.month.desc())
        .all()
    )
    return {"months": [m[0] for m in months]}
