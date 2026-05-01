"""
portfolio.py — API endpoints for investments, portfolio snapshots, net worth,
liabilities, goals, and category tag overrides.
"""

import io
import logging
from datetime import date, datetime
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from database import get_db
from ingestion.investment_pipeline import run_investment_pipeline, SUPPORTED_SOURCES
from models_investment import Investment, Holding, Liability, Goal, CategoryTagOverride
from routers.dashboard import invalidate_dashboard_cache
from schemas import (
    InvestmentSchema, HoldingSchema, LiabilitySchema, LiabilityCreate,
    GoalSchema, GoalCreate, GoalUpdate, PortfolioSummary,
    NetWorthSummary, CategoryTagOverrideSchema, GoalSimulation, UploadResponse,
)

router = APIRouter()
logger = logging.getLogger("finsight.portfolio")


# ── Helpers ───────────────────────────────────────────────────────────────────

_EXCEL_HEADER_NAMES = frozenset({
    "stock name", "fund name", "scheme name", "scheme",
    "scrip name", "security name", "instrument name",
})


def _read_excel_smart(content: bytes) -> pd.DataFrame:
    """Read Excel, skipping broker metadata rows to find the real data table.
    Groww and many broker exports put Name/Client-code/Summary rows above the
    actual column headers.  Scan for the first row whose first cell matches a
    known header name and use that row as the header.
    """
    raw = pd.read_excel(io.BytesIO(content), header=None)
    header_row = None
    for i, row in raw.iterrows():
        cell = str(row.iloc[0]).strip().lower()
        if cell in _EXCEL_HEADER_NAMES:
            header_row = i
            break
    if header_row is None:
        return pd.read_excel(io.BytesIO(content))
    return pd.read_excel(io.BytesIO(content), header=header_row)


def _read_csv_or_excel(file: UploadFile) -> pd.DataFrame:
    content = file.file.read()
    name = (file.filename or "").lower()
    if name.endswith(".csv"):
        return pd.read_csv(io.BytesIO(content))
    elif name.endswith((".xlsx", ".xls")):
        return _read_excel_smart(content)
    try:
        return pd.read_csv(io.BytesIO(content))
    except Exception:
        return _read_excel_smart(content)


# ── Investment transactions ────────────────────────────────────────────────────

@router.post("/investments/upload", response_model=UploadResponse)
async def upload_investments(
    file: UploadFile = File(...),
    source: str = Query("generic", description=f"Broker source: {', '.join(SUPPORTED_SOURCES)}"),
    db: Session = Depends(get_db),
):
    try:
        df = _read_csv_or_excel(file)
    except Exception as e:
        raise HTTPException(400, f"Could not parse file: {e}")
    try:
        result = run_investment_pipeline(df, source, db)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return UploadResponse(
        status="success",
        rows_inserted=result["inserted"],
        rows_skipped=result["skipped"],
        message=f"Inserted {result['inserted']} investment records, skipped {result['skipped']} duplicates.",
    )


@router.get("/investments/transactions")
def get_investment_transactions(
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
):
    offset = (page - 1) * page_size
    total = db.query(Investment).count()
    rows = (
        db.query(Investment)
        .order_by(Investment.date.desc())
        .offset(offset).limit(page_size).all()
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "transactions": [_inv_to_dict(r) for r in rows],
    }


@router.get("/investments/transactions/{month}")
def get_investment_transactions_month(month: str, db: Session = Depends(get_db)):
    rows = (
        db.query(Investment)
        .filter(Investment.month == month)
        .order_by(Investment.date.desc())
        .all()
    )
    return {"month": month, "transactions": [_inv_to_dict(r) for r in rows]}


def _inv_to_dict(r: Investment) -> dict:
    return {
        "id": r.id, "date": str(r.date), "month": r.month,
        "instrument_type": r.instrument_type, "name": r.name,
        "symbol": r.symbol, "isin": r.isin, "folio_number": r.folio_number,
        "units": r.units, "price_per_unit": r.price_per_unit,
        "amount": r.amount, "transaction_type": r.transaction_type,
        "account": r.account, "notes": r.notes,
    }


# ── Portfolio snapshots ────────────────────────────────────────────────────────

@router.post("/portfolio/snapshot", response_model=UploadResponse)
async def upload_snapshot(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a broker holdings CSV. Columns: name, instrument_type, units,
    avg_cost_per_unit, current_price, current_value, invested_value, account.
    isin and folio_number are optional."""
    try:
        df = _read_csv_or_excel(file)
    except Exception as e:
        raise HTTPException(400, f"Could not parse file: {e}")

    df.columns = [str(c).strip().lower() for c in df.columns]
    df = df.dropna(how="all")
    aliases = {
        # name variants
        "fund name": "name", "scheme name": "name", "scheme": "name",
        "stock name": "name", "scrip name": "name", "security name": "name",
        # avg cost variants  (Groww: "average buy price")
        "avg cost": "avg_cost_per_unit", "average cost": "avg_cost_per_unit",
        "average buy price": "avg_cost_per_unit", "avg buy price": "avg_cost_per_unit",
        # current price variants  (Groww: "closing price")
        "current nav": "current_price", "nav": "current_price", "ltp": "current_price",
        "closing price": "current_price", "close price": "current_price",
        # current value variants  (Groww: "closing value")
        "current value": "current_value", "market value": "current_value",
        "closing value": "current_value", "close value": "current_value",
        # invested value variants  (Groww: "buy value")
        "invested": "invested_value", "invested value": "invested_value",
        "cost": "invested_value", "buy value": "invested_value", "cost value": "invested_value",
        # folio
        "folio": "folio_number", "folio no.": "folio_number",
        # instrument type
        "type": "instrument_type",
        # units  (Groww: "quantity")
        "qty": "units", "quantity": "units",
        # P&L variants
        "p&l": "unrealised_pnl", "pnl": "unrealised_pnl", "gain/loss": "unrealised_pnl",
        "unrealised p&l": "unrealised_pnl", "unrealized p&l": "unrealised_pnl",
        "p&l%": "unrealised_pnl_pct", "pnl%": "unrealised_pnl_pct", "return%": "unrealised_pnl_pct",
    }
    rename = {}
    for alias, canonical in aliases.items():
        if alias in df.columns and canonical not in df.columns:
            rename[alias] = canonical
    df = df.rename(columns=rename)

    if "name" not in df.columns:
        raise HTTPException(422, "Column 'name' (fund/scheme/stock name) is required")

    for col in ["units", "avg_cost_per_unit", "current_price", "current_value", "invested_value",
                "unrealised_pnl", "unrealised_pnl_pct"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "instrument_type" not in df.columns:
        if "isin" in df.columns:
            def _infer_type(isin_val) -> str:
                s = str(isin_val).strip().upper()
                if s.startswith("INF"):
                    return "mutual_fund"
                if s.startswith("INE"):
                    return "stock"
                return "other"
            df["instrument_type"] = df["isin"].apply(_infer_type)
        else:
            df["instrument_type"] = "other"
    if "account" not in df.columns:
        df["account"] = "Manual"

    # Derive missing computed columns
    if "current_value" not in df.columns and "units" in df.columns and "current_price" in df.columns:
        df["current_value"] = df["units"] * df["current_price"]
    if "invested_value" not in df.columns and "units" in df.columns and "avg_cost_per_unit" in df.columns:
        df["invested_value"] = df["units"] * df["avg_cost_per_unit"]
    if "unrealised_pnl" not in df.columns and "current_value" in df.columns and "invested_value" in df.columns:
        df["unrealised_pnl"] = df["current_value"] - df["invested_value"]
    if "unrealised_pnl_pct" not in df.columns and "unrealised_pnl" in df.columns and "invested_value" in df.columns:
        df["unrealised_pnl_pct"] = (df["unrealised_pnl"] / df["invested_value"].replace(0, float("nan")) * 100)

    snap_date = date.today()
    inserted = 0
    skipped = 0

    for _, row in df.iterrows():
        if pd.isna(row.get("name")):
            continue
        existing = (
            db.query(Holding)
            .filter(
                Holding.snapshot_date == snap_date,
                Holding.name == str(row["name"]),
                Holding.account == str(row.get("account", "Manual")),
            )
            .first()
        )
        if existing:
            skipped += 1
            continue

        db.add(Holding(
            snapshot_date=snap_date,
            instrument_type=str(row.get("instrument_type", "other")),
            name=str(row["name"]),
            symbol=str(row["symbol"]) if "symbol" in df.columns and pd.notna(row.get("symbol")) else None,
            isin=str(row["isin"]) if "isin" in df.columns and pd.notna(row.get("isin")) else None,
            folio_number=str(row["folio_number"]) if "folio_number" in df.columns and pd.notna(row.get("folio_number")) else None,
            units=float(row["units"]) if "units" in df.columns and pd.notna(row.get("units")) else None,
            avg_cost_per_unit=float(row["avg_cost_per_unit"]) if "avg_cost_per_unit" in df.columns and pd.notna(row.get("avg_cost_per_unit")) else None,
            current_price=float(row["current_price"]) if "current_price" in df.columns and pd.notna(row.get("current_price")) else None,
            current_value=float(row["current_value"]) if "current_value" in df.columns and pd.notna(row.get("current_value")) else None,
            invested_value=float(row["invested_value"]) if "invested_value" in df.columns and pd.notna(row.get("invested_value")) else None,
            unrealised_pnl=float(row["unrealised_pnl"]) if "unrealised_pnl" in df.columns and pd.notna(row.get("unrealised_pnl")) else None,
            unrealised_pnl_pct=float(row["unrealised_pnl_pct"]) if "unrealised_pnl_pct" in df.columns and pd.notna(row.get("unrealised_pnl_pct")) else None,
            account=str(row.get("account", "Manual")),
        ))
        inserted += 1

    db.commit()
    logger.info("Snapshot uploaded: inserted=%d skipped=%d date=%s", inserted, skipped, snap_date)
    return UploadResponse(
        status="success",
        rows_inserted=inserted,
        rows_skipped=skipped,
        message=f"Snapshot saved for {snap_date}: {inserted} holdings added.",
    )


@router.get("/portfolio/latest")
def get_portfolio_latest(db: Session = Depends(get_db)):
    from sqlalchemy import func as _func
    latest_date = db.query(_func.max(Holding.snapshot_date)).scalar()
    if not latest_date:
        return {"snapshot_date": None, "holdings": [], "summary": None}

    holdings = db.query(Holding).filter(Holding.snapshot_date == latest_date).all()
    rows = [_holding_to_dict(h) for h in holdings]

    total_current = sum(h.current_value or 0 for h in holdings)
    total_invested = sum(h.invested_value or 0 for h in holdings)
    total_pnl = total_current - total_invested

    by_type: dict = {}
    for h in holdings:
        t = h.instrument_type or "other"
        by_type[t] = by_type.get(t, 0) + (h.current_value or 0)

    summary = PortfolioSummary(
        snapshot_date=str(latest_date),
        total_current_value=round(total_current, 2),
        total_invested_value=round(total_invested, 2),
        total_unrealised_pnl=round(total_pnl, 2),
        total_unrealised_pnl_pct=round(total_pnl / total_invested * 100, 2) if total_invested > 0 else 0,
        by_instrument_type={k: round(v, 2) for k, v in by_type.items()},
    )

    return {"snapshot_date": str(latest_date), "holdings": rows, "summary": summary}


@router.get("/portfolio/history")
def get_portfolio_history(db: Session = Depends(get_db)):
    """Net portfolio value per snapshot date."""
    from sqlalchemy import func
    rows = (
        db.query(Holding.snapshot_date, func.sum(Holding.current_value).label("total"))
        .group_by(Holding.snapshot_date)
        .order_by(Holding.snapshot_date)
        .all()
    )
    return [{"date": str(r.snapshot_date), "total_value": round(float(r.total or 0), 2)} for r in rows]


def _holding_to_dict(h: Holding) -> dict:
    return {
        "id": h.id, "snapshot_date": str(h.snapshot_date),
        "instrument_type": h.instrument_type, "name": h.name,
        "symbol": h.symbol, "isin": h.isin, "folio_number": h.folio_number,
        "units": h.units, "avg_cost_per_unit": h.avg_cost_per_unit,
        "current_price": h.current_price, "current_value": h.current_value,
        "invested_value": h.invested_value, "unrealised_pnl": h.unrealised_pnl,
        "unrealised_pnl_pct": h.unrealised_pnl_pct, "account": h.account,
    }


# ── Net worth ─────────────────────────────────────────────────────────────────

@router.get("/networth/summary", response_model=NetWorthSummary)
def get_networth_summary(db: Session = Depends(get_db)):
    from sqlalchemy import func as _func
    latest_date = db.query(_func.max(Holding.snapshot_date)).scalar()
    holdings = db.query(Holding).filter(Holding.snapshot_date == latest_date).all() if latest_date else []

    liabilities = (
        db.query(Liability)
        .order_by(Liability.as_of_date.desc())
        .all()
    )
    # Most recent snapshot per loan
    seen_loans: set[str] = set()
    latest_liabilities = []
    for l in liabilities:
        if l.name not in seen_loans:
            seen_loans.add(l.name)
            latest_liabilities.append(l)

    total_assets = sum(h.current_value or 0 for h in holdings)
    total_liabilities = sum(l.outstanding for l in latest_liabilities)

    asset_breakdown: dict = {}
    for h in holdings:
        t = h.instrument_type or "other"
        asset_breakdown[t] = asset_breakdown.get(t, 0) + (h.current_value or 0)

    liability_breakdown: dict = {}
    for l in latest_liabilities:
        t = l.liability_type or "other"
        liability_breakdown[t] = liability_breakdown.get(t, 0) + l.outstanding

    return NetWorthSummary(
        as_of_date=str(latest_date) if latest_date else str(date.today()),
        total_assets=round(total_assets, 2),
        total_liabilities=round(total_liabilities, 2),
        net_worth=round(total_assets - total_liabilities, 2),
        asset_breakdown={k: round(v, 2) for k, v in asset_breakdown.items()},
        liability_breakdown={k: round(v, 2) for k, v in liability_breakdown.items()},
    )


@router.get("/networth/history")
def get_networth_history(db: Session = Depends(get_db)):
    from sqlalchemy import func
    asset_rows = (
        db.query(Holding.snapshot_date, func.sum(Holding.current_value).label("assets"))
        .group_by(Holding.snapshot_date)
        .order_by(Holding.snapshot_date)
        .all()
    )
    # Use latest liability snapshot for each date (approximation)
    total_liabilities = sum(
        l.outstanding for l in db.query(Liability).all()
    ) if db.query(Liability).count() > 0 else 0

    return [
        {
            "date": str(r.snapshot_date),
            "assets": round(float(r.assets or 0), 2),
            "liabilities": total_liabilities,
            "net_worth": round(float(r.assets or 0) - total_liabilities, 2),
        }
        for r in asset_rows
    ]


# ── Liabilities ───────────────────────────────────────────────────────────────

@router.get("/liabilities", response_model=list[LiabilitySchema])
def list_liabilities(db: Session = Depends(get_db)):
    return db.query(Liability).order_by(Liability.name).all()


@router.post("/liabilities", response_model=LiabilitySchema)
def create_liability(body: LiabilityCreate, db: Session = Depends(get_db)):
    from datetime import date as dt
    as_of = dt.fromisoformat(body.as_of_date) if body.as_of_date else dt.today()
    existing = db.query(Liability).filter(
        Liability.name == body.name, Liability.as_of_date == as_of
    ).first()
    if existing:
        # Update in-place
        for field, val in body.model_dump(exclude_none=True).items():
            setattr(existing, field, val)
        db.commit()
        db.refresh(existing)
        return existing
    obj = Liability(**body.model_dump(), as_of_date=as_of)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


# ── Goals ─────────────────────────────────────────────────────────────────────

@router.get("/goals", response_model=list[GoalSchema])
def list_goals(db: Session = Depends(get_db)):
    return db.query(Goal).order_by(Goal.name).all()


@router.post("/goals", response_model=GoalSchema)
def create_goal(body: GoalCreate, db: Session = Depends(get_db)):
    from datetime import date as dt
    obj = Goal(**body.model_dump(), created_at=dt.today())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/goals/{goal_id}", response_model=GoalSchema)
def update_goal(goal_id: int, body: GoalUpdate, db: Session = Depends(get_db)):
    obj = db.query(Goal).filter(Goal.id == goal_id).first()
    if not obj:
        raise HTTPException(404, "Goal not found")
    for field, val in body.model_dump(exclude_none=True).items():
        setattr(obj, field, val)
    db.commit()
    db.refresh(obj)
    return obj


def _months_compound(pv: float, pmt: float, annual_rate: float = 0.12) -> int:
    """
    Months to reach a Future Value target starting from present value `pv`
    with monthly contributions `pmt` at `annual_rate` CAGR.

    Formula: n = log(pmt / (pmt - r*pv)) / log(1+r)
    Returns 99999 if SIP is too small to ever reach target growth rate.
    """
    import math
    r = annual_rate / 12
    if r == 0:
        return math.ceil(pv / pmt) if pmt > 0 else 99999
    if pmt <= r * pv:
        return 99999
    return math.ceil(math.log(pmt / (pmt - r * pv)) / math.log(1 + r))


@router.get("/goals/{goal_id}/simulation", response_model=GoalSimulation)
def simulate_goal(goal_id: int, db: Session = Depends(get_db)):
    """Pure maths: months to reach target at current monthly SIP."""
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(404, "Goal not found")

    remaining = max(0, goal.target_amount - goal.current_amount)
    sip = goal.monthly_sip or 0

    if sip > 0:
        months = _months_compound(goal.current_amount, sip)
        from datetime import date as dt
        import calendar
        projected = dt.today().replace(day=1)
        m = projected.month - 1 + months
        projected = projected.replace(year=projected.year + m // 12, month=m % 12 + 1, day=1)
        on_track = True
        if goal.target_date:
            from datetime import date as dt2
            td = goal.target_date if isinstance(goal.target_date, dt2) else dt2.fromisoformat(str(goal.target_date))
            on_track = projected <= td
    else:
        months = None
        projected = None
        on_track = False

    return GoalSimulation(
        goal_name=goal.name,
        target_amount=goal.target_amount,
        current_amount=goal.current_amount,
        monthly_sip=sip,
        months_to_goal=months,
        projected_date=str(projected) if projected else None,
        shortfall=round(remaining, 2),
        on_track=on_track,
    )


# ── Category tag overrides ─────────────────────────────────────────────────────

@router.get("/category-tags", response_model=list[CategoryTagOverrideSchema])
def list_category_tags(db: Session = Depends(get_db)):
    return db.query(CategoryTagOverride).all()


@router.post("/category-tags", response_model=CategoryTagOverrideSchema)
def upsert_category_tag(body: CategoryTagOverrideSchema, db: Session = Depends(get_db)):
    if body.tag not in ("essential", "discretionary", "uncategorized"):
        raise HTTPException(422, "tag must be 'essential', 'discretionary', or 'uncategorized'")
    existing = db.query(CategoryTagOverride).filter(CategoryTagOverride.category == body.category).first()
    if existing:
        existing.tag = body.tag
        existing.updated_at = datetime.utcnow()
    else:
        db.add(CategoryTagOverride(category=body.category, tag=body.tag))
    db.commit()
    invalidate_dashboard_cache()
    return db.query(CategoryTagOverride).filter(CategoryTagOverride.category == body.category).first()
