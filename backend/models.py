from sqlalchemy import Column, Integer, Float, String, Date, UniqueConstraint
from database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    month = Column(String(7), nullable=False, index=True)   # YYYY-MM
    year = Column(Integer, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    type = Column(String(20), nullable=False)               # income/expense/investment
    category = Column(String(100), nullable=False, default="uncategorized")
    subcategory = Column(String(100), nullable=True)
    description = Column(String(500), default="")
    account = Column(String(100), nullable=False)
    tag = Column(String(50), default="uncategorized")       # essential/discretionary/uncategorized

    __table_args__ = (
        UniqueConstraint("date", "amount", "description", name="uq_transaction"),
    )


class MonthlyAggregate(Base):
    __tablename__ = "monthly_aggregates"

    id = Column(Integer, primary_key=True, index=True)
    month = Column(String(7), unique=True, nullable=False, index=True)
    total_income = Column(Float, default=0.0)
    total_expense = Column(Float, default=0.0)
    total_investment = Column(Float, default=0.0)
    net_savings = Column(Float, default=0.0)
    savings_rate = Column(Float, default=0.0)


class CategoryAggregate(Base):
    __tablename__ = "category_aggregates"

    id = Column(Integer, primary_key=True, index=True)
    month = Column(String(7), nullable=False, index=True)
    category = Column(String(100), nullable=False)
    total_amount = Column(Float, default=0.0)
    percentage_of_total_expense = Column(Float, default=0.0)
    tag = Column(String(50), default="uncategorized")

    __table_args__ = (
        UniqueConstraint("month", "category", name="uq_category_month"),
    )


class YearlyAggregate(Base):
    __tablename__ = "yearly_aggregates"

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, unique=True, nullable=False, index=True)
    total_income = Column(Float, default=0.0)
    total_expense = Column(Float, default=0.0)
    total_investment = Column(Float, default=0.0)
    avg_monthly_expense = Column(Float, default=0.0)
    savings_rate = Column(Float, default=0.0)
