from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from analytics.engine import build_dashboard
from schemas import DashboardResponse

router = APIRouter()


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(db: Session = Depends(get_db)):
    return build_dashboard(db)
