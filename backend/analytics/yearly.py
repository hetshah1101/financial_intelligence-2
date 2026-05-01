import pandas as pd
from sqlalchemy.orm import Session

from database import engine
from models import Transaction, YearlyAggregate


def compute_yearly_aggregates(db: Session, years: list[int] | None = None) -> None:
    query = db.query(Transaction)
    if years:
        query = query.filter(Transaction.year.in_(years))

    df = pd.read_sql(query.statement, engine)
    if df.empty:
        return

    target_years = df["year"].unique()

    for year in target_years:
        ydf = df[df["year"] == year]
        total_income = float(ydf[ydf["type"] == "income"]["amount"].sum())
        total_expense = float(ydf[ydf["type"] == "expense"]["amount"].sum())
        total_investment = float(ydf[ydf["type"] == "investment"]["amount"].sum())

        # Average monthly expense across months that had any expense
        expense_by_month = (
            ydf[ydf["type"] == "expense"].groupby("month")["amount"].sum()
        )
        avg_monthly_expense = float(expense_by_month.mean()) if not expense_by_month.empty else 0.0

        net_savings = total_income - total_expense - total_investment
        savings_rate = (net_savings / total_income * 100) if total_income > 0 else 0.0

        existing = db.query(YearlyAggregate).filter_by(year=int(year)).first()
        if existing:
            existing.total_income = total_income
            existing.total_expense = total_expense
            existing.total_investment = total_investment
            existing.avg_monthly_expense = round(avg_monthly_expense, 2)
            existing.savings_rate = round(savings_rate, 2)
        else:
            db.add(YearlyAggregate(
                year=int(year),
                total_income=total_income,
                total_expense=total_expense,
                total_investment=total_investment,
                avg_monthly_expense=round(avg_monthly_expense, 2),
                savings_rate=round(savings_rate, 2),
            ))

    db.commit()
