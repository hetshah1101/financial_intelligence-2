import pandas as pd
from sqlalchemy.orm import Session

from database import engine
from models import Transaction, CategoryAggregate


def compute_category_aggregates(db: Session, months: list[str] | None = None) -> None:
    query = db.query(Transaction).filter(Transaction.type == "expense")
    if months:
        query = query.filter(Transaction.month.in_(months))

    df = pd.read_sql(query.statement, engine)
    if df.empty:
        return

    target_months = df["month"].unique()

    for month in target_months:
        mdf = df[df["month"] == month]
        total_expense = mdf["amount"].sum()

        by_cat = (
            mdf.groupby(["category", "tag"])["amount"]
            .sum()
            .reset_index()
            .rename(columns={"amount": "total_amount"})
        )
        by_cat["percentage_of_total_expense"] = (
            (by_cat["total_amount"] / total_expense * 100).round(2)
            if total_expense > 0
            else 0.0
        )

        for _, row in by_cat.iterrows():
            existing = (
                db.query(CategoryAggregate)
                .filter_by(month=month, category=row["category"])
                .first()
            )
            if existing:
                existing.total_amount = float(row["total_amount"])
                existing.percentage_of_total_expense = float(row["percentage_of_total_expense"])
                existing.tag = row["tag"]
            else:
                db.add(CategoryAggregate(
                    month=month,
                    category=row["category"],
                    total_amount=float(row["total_amount"]),
                    percentage_of_total_expense=float(row["percentage_of_total_expense"]),
                    tag=row["tag"],
                ))

    db.commit()
