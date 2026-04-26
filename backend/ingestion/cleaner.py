import pandas as pd


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Normalise column names — strip extra whitespace
    df.columns = [c.strip() for c in df.columns]

    # Date → YYYY-MM-DD (handle datetime with timestamps)
    df["Date"] = pd.to_datetime(df["Date"]).dt.date

    # Amount → float (absolute value)
    df["Amount (INR)"] = pd.to_numeric(df["Amount (INR)"], errors="coerce").abs()

    # Type → lowercase strip; normalize variations
    type_map = {
        "exp.": "expense",
        "expense": "expense",
        "income": "income",
        "transfer-in": "investment",
        "transfer-out": "investment",
        "transfer": "investment",
        "investment": "investment",
    }
    df["Type"] = (
        df["Type"]
        .astype(str)
        .str.strip()
        .str.lower()
        .map(lambda x: type_map.get(x, x))  # Use map, fallback to original
    )

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
    print(f"[DEBUG cleaner] columns={df.columns.tolist()} desc_col={_desc_col!r}")
    if _desc_col:
        df["description"] = df[_desc_col].fillna("").astype(str).str.strip()
    else:
        df["description"] = ""

    # Derive month and year
    df["month"] = pd.to_datetime(df["Date"]).dt.to_period("M").astype(str)
    df["year"] = pd.to_datetime(df["Date"]).dt.year

    # Drop rows where amount is NaN after coercion
    df = df.dropna(subset=["Amount (INR)"])

    # Remove duplicates by (date, amount, description)
    df = df.drop_duplicates(subset=["Date", "Amount (INR)", "description"])

    return df
