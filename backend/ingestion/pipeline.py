import pandas as pd
from sqlalchemy.orm import Session

from ingestion.column_mapper import normalize_column_names
from ingestion.validator import validate
from ingestion.cleaner import clean
from ingestion.tagger import tag_dataframe
from ingestion.exception import apply_exceptions
from models import Transaction


def run_pipeline(df: pd.DataFrame, db: Session) -> dict:
    # Step 0: Normalize column names
    df = normalize_column_names(df)

    # Step 1: Validate
    validate(df)

    # Step 2: Clean
    df = clean(df)

    # Step 3: Tag essential / discretionary
    df = tag_dataframe(df)

    # Step 4: Apply exceptions (e.g. card settlement reclassification)
    df = apply_exceptions(df)

    # Step 5: Insert with idempotency
    inserted = 0
    skipped = 0
    affected_months: set[str] = set()

    for _, row in df.iterrows():
        existing = (
            db.query(Transaction)
            .filter(
                Transaction.date == row["Date"],
                Transaction.amount == row["Amount (INR)"],
                Transaction.description == row["description"],
            )
            .first()
        )
        if existing:
            skipped += 1
            continue

        txn = Transaction(
            date=row["Date"],
            month=row["month"],
            year=int(row["year"]),
            amount=float(row["Amount (INR)"]),
            type=row["Type"],
            category=row["Category"],
            subcategory=row.get("Subcategory") if pd.notna(row.get("Subcategory", None)) else None,
            description=row["description"],
            account=row["Account"],
            tag=row["tag"],
        )
        db.add(txn)
        inserted += 1
        affected_months.add(row["month"])

    db.commit()

    return {
        "inserted": inserted,
        "skipped": skipped,
        "affected_months": sorted(affected_months),
    }
