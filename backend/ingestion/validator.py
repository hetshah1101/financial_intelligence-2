import pandas as pd


REQUIRED_COLUMNS = {"Date", "Account", "Category", "Amount (INR)", "Type"}
VALID_TYPES = {"income", "expense", "investment"}


def validate_columns(df: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def validate_date_format(df: pd.DataFrame) -> None:
    try:
        pd.to_datetime(df["Date"])
    except Exception as e:
        raise ValueError(f"Invalid date format in 'Date' column: {e}")


def validate_amount(df: pd.DataFrame) -> None:
    non_numeric = pd.to_numeric(df["Amount (INR)"], errors="coerce").isna()
    if non_numeric.any():
        bad = df.loc[non_numeric, "Amount (INR)"].tolist()[:5]
        raise ValueError(f"Non-numeric values in 'Amount (INR)': {bad}")


def validate(df: pd.DataFrame) -> None:
    validate_columns(df)
    validate_date_format(df)
    validate_amount(df)
