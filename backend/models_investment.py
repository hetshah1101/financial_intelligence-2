from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, Date, DateTime, UniqueConstraint
from database import Base


class Investment(Base):
    """Each purchase / SIP / redemption event."""
    __tablename__ = "investments"

    id               = Column(Integer, primary_key=True)
    date             = Column(Date, nullable=False, index=True)
    month            = Column(String(7), nullable=False, index=True)   # YYYY-MM
    instrument_type  = Column(String(50), nullable=False)
    # "mutual_fund" | "stock" | "fd" | "ppf" | "nps" | "gold" | "crypto" | "bonds"
    name             = Column(String(200), nullable=False)
    symbol           = Column(String(50))
    isin             = Column(String(20))
    folio_number     = Column(String(100))
    units            = Column(Float, default=0)
    price_per_unit   = Column(Float)
    amount           = Column(Float, nullable=False)
    transaction_type = Column(String(20))
    # "buy" | "sell" | "dividend" | "sip" | "interest" | "maturity"
    account          = Column(String(100))
    notes            = Column(String(500))

    __table_args__ = (
        UniqueConstraint("date", "name", "amount", "transaction_type", "account",
                         name="uq_investment"),
    )


class Holding(Base):
    """Point-in-time snapshot of portfolio (updated manually on each upload)."""
    __tablename__ = "holdings"

    id                  = Column(Integer, primary_key=True)
    snapshot_date       = Column(Date, nullable=False, index=True)
    instrument_type     = Column(String(50), nullable=False)
    name                = Column(String(200), nullable=False)
    symbol              = Column(String(50))
    isin                = Column(String(20))
    folio_number        = Column(String(100))
    units               = Column(Float)
    avg_cost_per_unit   = Column(Float)
    current_price       = Column(Float)
    current_value       = Column(Float)
    invested_value      = Column(Float)
    unrealised_pnl      = Column(Float)
    unrealised_pnl_pct  = Column(Float)
    account             = Column(String(100))

    __table_args__ = (
        UniqueConstraint("snapshot_date", "name", "account",
                         name="uq_holding_snapshot"),
    )


class Liability(Base):
    """Loans, EMIs, credit card balances."""
    __tablename__ = "liabilities"

    id             = Column(Integer, primary_key=True)
    name           = Column(String(200), nullable=False)
    liability_type = Column(String(50))
    # "home_loan" | "car_loan" | "personal_loan" | "credit_card" | "education_loan"
    principal      = Column(Float)
    outstanding    = Column(Float, nullable=False)
    interest_rate  = Column(Float)
    emi_amount     = Column(Float)
    start_date     = Column(Date)
    end_date       = Column(Date)
    account        = Column(String(100))
    as_of_date     = Column(Date)

    __table_args__ = (
        UniqueConstraint("name", "as_of_date", name="uq_liability"),
    )


class Goal(Base):
    """Financial goal with progress tracking."""
    __tablename__ = "goals"

    id             = Column(Integer, primary_key=True)
    name           = Column(String(200), nullable=False, unique=True)
    target_amount  = Column(Float, nullable=False)
    target_date    = Column(Date)
    current_amount = Column(Float, default=0)
    monthly_sip    = Column(Float, default=0)
    linked_isin    = Column(String(20))
    notes          = Column(String(500))
    created_at     = Column(Date)


class CategoryTagOverride(Base):
    """User-defined essential/discretionary overrides for categories."""
    __tablename__ = "category_tag_overrides"

    category   = Column(String(100), primary_key=True)
    tag        = Column(String(50), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
