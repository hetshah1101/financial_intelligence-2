import logging
import pandas as pd

logger = logging.getLogger("finsight.ingestion.cleaner")

_CANONICAL_TYPES = {"expense", "income", "investment"}

_TYPE_MAP = {
    "expense":      "expense",
    "expenses":     "expense",
    "exp.":         "expense",
    "exp":          "expense",
    "debit":        "expense",
    "dr":           "expense",
    "withdrawal":   "expense",
    "withdraw":     "expense",
    "income":       "income",
    "credit":       "income",
    "cr":           "income",
    "deposit":      "income",
    "investment":   "investment",
    "invest":       "investment",
    "transfer":     "investment",
    "transfer-in":  "investment",
    "transfer-out": "investment",
    "transfer in":  "investment",
    "transfer out": "investment",
    "sip":          "investment",
}


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Normalise column names — strip extra whitespace
    df.columns = [c.strip() for c in df.columns]

    # Date → YYYY-MM-DD (handle datetime with timestamps)
    df["Date"] = pd.to_datetime(df["Date"]).dt.date

    # Amount → float (absolute value)
    df["Amount (INR)"] = pd.to_numeric(df["Amount (INR)"], errors="coerce").abs()

    # Type → lowercase strip; normalize variations
    df["Type"] = (
        df["Type"]
        .astype(str)
        .str.strip()
        .str.lower()
        .map(lambda x: _TYPE_MAP.get(x, x))
    )

    # Warn about any rows whose type didn't resolve to a canonical value
    unresolved = df[~df["Type"].isin(_CANONICAL_TYPES)]["Type"].unique()
    for raw_type in unresolved:
        logger.warning("Unrecognized transaction type %r — row will be stored as-is and excluded from analytics", raw_type)

    # Fill missing fields
    df["Category"] = df["Category"].fillna("uncategorized").astype(str).str.strip()
    df["Subcategory"] = df.get("Subcategory", pd.Series(dtype=str)).where(
        df.get("Subcategory", pd.Series(dtype=str)).notna(), other=None
    )

    # Preserve description: case-insensitive match against known column name variants.
    _desc_candidates = {
        "note / description", "description", "narration", "note",
        "memo", "remarks", "particulars", "details",
        "transaction description", "transaction narration",
    }
    _desc_col = next((c for c in df.columns if c.strip().lower() in _desc_candidates), None)
    logger.debug("columns=%s  desc_col=%r", df.columns.tolist(), _desc_col)
    if _desc_col:
        df["description"] = df[_desc_col].fillna("").astype(str).str.strip()
    else:
        df["description"] = ""

    # Derive month and year
    df["month"] = pd.to_datetime(df["Date"]).dt.to_period("M").astype(str)
    df["year"] = pd.to_datetime(df["Date"]).dt.year

    # Drop rows where amount is NaN after coercion
    df = df.dropna(subset=["Amount (INR)"])

    # Remove duplicates by (date, amount, description, account)
    df = df.drop_duplicates(subset=["Date", "Amount (INR)", "description", "Account"])

    return df
