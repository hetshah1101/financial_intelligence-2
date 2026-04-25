import pandas as pd

# Map user column names to required columns
# Ordered by preference (more specific first)
COLUMN_PRIORITY = {
    "Date": [
        "date",
        "transaction date",
        "trans date",
        "period",
    ],
    "Account": [
        "account",
        "accounts",
        "account name",
        "from account",
    ],
    "Amount (INR)": [
        "amount (inr)",
        "amount inr",
        "amount",
        "inr",
        "value",
    ],
    "Type": [
        "type",
        "transaction type",
        "trans type",
        "income/expense",
        "income / expense",
    ],
    "Category": [
        "category",
        "primary category",
        "cat",
    ],
    "Subcategory": [
        "subcategory",
        "sub-category",
        "secondary category",
    ],
    "Note / Description": [
        "note / description",
        "description",
        "note",
        "memo",
    ],
}


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize user column names to standard schema."""
    df = df.copy()

    # Create reverse lookup: actual column name -> standard name
    actual_to_standard = {}

    # For each required standard column, find the best matching actual column
    for standard_col, variations in COLUMN_PRIORITY.items():
        for variation in variations:
            # Check if this variation exists in the dataframe
            matching_cols = [c for c in df.columns if c.strip().lower() == variation]
            if matching_cols:
                # Use the first (and should be only) matching column
                actual_col = matching_cols[0]
                actual_to_standard[actual_col] = standard_col
                break  # Found the best match for this standard column

    # Rename columns
    if actual_to_standard:
        df = df.rename(columns=actual_to_standard)
        # Drop duplicate columns (keep only the renamed ones)
        # Drop unnamed columns and duplicates
        cols_to_drop = [c for c in df.columns if c not in actual_to_standard.values()
                       and not c.startswith('Unnamed')]
        df = df.drop(columns=cols_to_drop, errors='ignore')

    return df
