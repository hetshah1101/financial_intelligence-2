import pandas as pd
from sqlalchemy.orm import Session

from models import Transaction, MonthlyAggregate


def compute_monthly_aggregates(db: Session, months: list[str] | None = None) -> None:
    query = db.query(Transaction)
    if months:
        query = query.filter(Transaction.month.in_(months))

    df = pd.read_sql(query.statement, db.bind)
    if df.empty:
        return

    target_months = df["month"].unique()

    for month in target_months:
        mdf = df[df["month"] == month]
        total_income = float(mdf[mdf["type"] == "income"]["amount"].sum())
        total_expense = float(mdf[mdf["type"] == "expense"]["amount"].sum())
        total_investment = float(mdf[mdf["type"] == "investment"]["amount"].sum())
        net_savings = total_income - total_expense - total_investment
        savings_rate = (net_savings / total_income * 100) if total_income > 0 else 0.0

        existing = db.query(MonthlyAggregate).filter_by(month=month).first()
        if existing:
            existing.total_income = total_income
            existing.total_expense = total_expense
            existing.total_investment = total_investment
            existing.net_savings = net_savings
            existing.savings_rate = round(savings_rate, 2)
        else:
            db.add(MonthlyAggregate(
                month=month,
                total_income=total_income,
                total_expense=total_expense,
                total_investment=total_investment,
                net_savings=net_savings,
                savings_rate=round(savings_rate, 2),
            ))

    db.commit()
