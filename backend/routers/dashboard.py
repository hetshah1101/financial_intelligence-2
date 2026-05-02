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


@router.get("/action-plan")
def get_action_plan(db: Session = Depends(get_db)):
    """Single endpoint for the Action Plan tab."""
    from models_investment import Holding, Goal
    from sqlalchemy import func as _sqlfunc

    dash = build_dashboard(db)

    latest_snap = db.query(_sqlfunc.max(Holding.snapshot_date)).scalar()

    goals = db.query(Goal).order_by(Goal.name).all()

    def _goal_dict(g: Goal) -> dict:
        return {
            "id":             g.id,
            "name":           g.name,
            "target_amount":  float(g.target_amount),
            "target_date":    str(g.target_date) if g.target_date else None,
            "current_amount": float(g.current_amount or 0),
            "monthly_sip":    float(g.monthly_sip or 0),
            "notes":          g.notes,
        }

    return {
        "monthly_aggregates":    dash.monthly_aggregates,
        "budget_baseline":       dash.budget_baseline,
        "savings_opportunities": dash.savings_opportunities,
        "goals":                 [_goal_dict(g) for g in goals],
        "portfolio_snapshot_date": str(latest_snap) if latest_snap else None,
    }


@router.get("/months")
def get_months(db: Session = Depends(get_db)):
    months = (
        db.query(MonthlyAggregate.month)
        .order_by(MonthlyAggregate.month.desc())
        .all()
    )
    return {"months": [m[0] for m in months]}
