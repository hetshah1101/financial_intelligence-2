# app/utils/ingestion.py - Parse and validate uploaded files

import io
import logging
from typing import Tuple, List, Dict, Any

import pandas as pd

from app.db.database import get_connection

logger = logging.getLogger(__name__)

VALID_TYPES = {"income", "expense", "investment"}

# Required columns AFTER normalisation (internal schema names)
REQUIRED_INTERNAL = {"date", "amount", "type", "category"}

# ── Column mapping ────────────────────────────────────────────────────────────
# Maps every known incoming column name (lowercased + underscored) to the
# internal schema column name.  Both the original schema and the new schema
# from the user's export file are covered, so either format can be uploaded.
#
# Input file columns (new format):
#   Period | Accounts | Category | Subcategory | Note | INR
#   Income/Expense | Description | Amount | Currency | Accounts
#
COLUMN_MAP: Dict[str, str] = {
    # ── date ──────────────────────────────────────────────────────────────────
    "period":           "date",
    "date":             "date",

    # ── type (income / expense / investment) ──────────────────────────────────
    "income/expense":   "type",
    "income_/_expense": "type",   # in case spaces collapse to underscores
    "income_expense":   "type",
    "type":             "type",

    # ── amount ────────────────────────────────────────────────────────────────
    # "INR" column holds the canonical amount in the new format.
    # "Amount" is a secondary amount column (may be in original currency).
    # We prefer INR when present; fall back to amount.
    "inr":              "amount_inr",   # kept separately; resolved later
    "amount":           "amount_raw",   # kept separately; resolved later

    # ── category ──────────────────────────────────────────────────────────────
    "category":         "category",

    # ── subcategory ───────────────────────────────────────────────────────────
    "subcategory":      "subcategory",

    # ── description / notes ───────────────────────────────────────────────────
    "description":      "description",
    "note":             "description_note",   # merged into description later
    "notes":            "description_note",

    # ── account ───────────────────────────────────────────────────────────────
    # The new format has TWO accounts columns; we take the first non-empty one.
    "accounts":         "account",
    "account":          "account",

    # ── ignored columns ───────────────────────────────────────────────────────
    "currency":         "_currency",   # kept for reference, not stored
}

# type values the new format may use, mapped to internal values
TYPE_ALIAS_MAP: Dict[str, str] = {
    "income":     "income",
    "expense":    "expense",
    "expenses":   "expense",
    "investment": "investment",
    "invest":     "investment",
    # MoneyMoney / similar app exports
    "transfer":   "expense",   # treat transfers as expense by default
    "debit":      "expense",
    "credit":     "income",
}


def parse_upload(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """Parse CSV or Excel upload into a cleaned DataFrame."""
    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(file_bytes))
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(file_bytes))
        else:
            raise ValueError(f"Unsupported file type: {filename}")
    except Exception as e:
        raise ValueError(f"Failed to parse file: {e}")

    return clean_dataframe(df)


def _normalise_col(col: str) -> str:
    """Lowercase, strip, collapse whitespace to underscores."""
    return col.strip().lower().replace(" ", "_").replace("/", "_").replace("-", "_")


def _remap_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rename incoming columns to internal schema names using COLUMN_MAP.
    Handles duplicate logical columns (e.g. two 'Accounts' columns) by
    suffixing them _1, _2 before the map so we pick the right one.
    """
    # Deduplicate column names BEFORE normalising (pandas may already have
    # appended .1 etc.)
    seen: Dict[str, int] = {}
    new_cols = []
    for col in df.columns:
        norm = _normalise_col(str(col))
        if norm in seen:
            seen[norm] += 1
            new_cols.append(f"{norm}_{seen[norm]}")
        else:
            seen[norm] = 0
            new_cols.append(norm)
    df.columns = new_cols

    # Apply COLUMN_MAP
    rename: Dict[str, str] = {}
    for col in df.columns:
        # Strip trailing _1, _2 suffixes for lookup but keep original for rename
        base = col.rstrip("_0123456789") if col[-1].isdigit() else col
        base = base.rstrip("_")
        mapped = COLUMN_MAP.get(col) or COLUMN_MAP.get(base)
        if mapped:
            # If a name is already taken (duplicate logical col), use _dup suffix
            if mapped in rename.values():
                mapped = mapped + "_dup"
            rename[col] = mapped

    df = df.rename(columns=rename)
    logger.debug(f"Column mapping applied: {rename}")
    return df


def _resolve_amount(df: pd.DataFrame) -> pd.DataFrame:
    """
    Resolve the canonical 'amount' column from amount_inr / amount_raw.

    Priority: amount_inr (INR column) > amount_raw (Amount column) > amount
    """
    if "amount_inr" in df.columns:
        # Use INR as primary; fall back to amount_raw where INR is null
        df["amount"] = pd.to_numeric(df["amount_inr"], errors="coerce")
        if "amount_raw" in df.columns:
            fallback = pd.to_numeric(df["amount_raw"], errors="coerce")
            df["amount"] = df["amount"].fillna(fallback)
        df.drop(columns=["amount_inr"], inplace=True, errors="ignore")
        df.drop(columns=["amount_raw"], inplace=True, errors="ignore")
    elif "amount_raw" in df.columns:
        df["amount"] = pd.to_numeric(df["amount_raw"], errors="coerce")
        df.drop(columns=["amount_raw"], inplace=True, errors="ignore")
    # else: 'amount' column already present from original format

    return df


def _resolve_description(df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge 'description' and 'description_note' (Note column) into one field.
    Result: "<description> | <note>" when both present, otherwise whichever exists.
    """
    has_desc = "description" in df.columns
    has_note = "description_note" in df.columns

    if has_desc and has_note:
        df["description"] = (
            df["description"].fillna("").astype(str).str.strip()
            + df.apply(
                lambda r: f" | {str(r['description_note']).strip()}"
                if pd.notna(r["description_note"]) and str(r["description_note"]).strip() not in ("", "nan")
                else "",
                axis=1,
            )
        ).str.strip(" |")
        df.drop(columns=["description_note"], inplace=True)
    elif has_note:
        df.rename(columns={"description_note": "description"}, inplace=True)

    return df


def _resolve_account(df: pd.DataFrame) -> pd.DataFrame:
    """
    If two 'accounts' columns were present they'll be 'account' and 'account_dup'.
    Pick the first non-empty value per row.
    """
    if "account_dup" in df.columns:
        df["account"] = df["account"].fillna("").astype(str).str.strip()
        df["account_dup"] = df["account_dup"].fillna("").astype(str).str.strip()
        df["account"] = df.apply(
            lambda r: r["account"] if r["account"] not in ("", "nan") else r["account_dup"],
            axis=1,
        )
        df.drop(columns=["account_dup"], inplace=True)
    return df


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Validate, clean, and normalise a raw transactions DataFrame."""

    # ── 1. Remap columns ──────────────────────────────────────────────────────
    df = _remap_columns(df)

    # ── 2. Resolve composite fields ───────────────────────────────────────────
    df = _resolve_amount(df)
    df = _resolve_description(df)
    df = _resolve_account(df)

    # Drop any leftover internal/unknown helper columns
    for drop_col in ["_currency", "_currency_dup"]:
        df.drop(columns=[drop_col], inplace=True, errors="ignore")

    # ── 3. Check required columns present ─────────────────────────────────────
    missing = REQUIRED_INTERNAL - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing required columns after mapping: {missing}. "
            f"Available columns: {list(df.columns)}"
        )

    # ── 4. Normalise 'type' ───────────────────────────────────────────────────
    df["type"] = (
        df["type"].astype(str).str.strip().str.lower()
        .map(lambda v: TYPE_ALIAS_MAP.get(v, v))
    )
    invalid_types = df[~df["type"].isin(VALID_TYPES)]
    if not invalid_types.empty:
        logger.warning(
            f"Dropping {len(invalid_types)} rows with unrecognised type values: "
            f"{invalid_types['type'].unique()}"
        )
        df = df[df["type"].isin(VALID_TYPES)]

    # ── 5. Normalise 'category' ───────────────────────────────────────────────
    df["category"] = df["category"].astype(str).str.strip()
    df = df[df["category"].str.lower() != "nan"]

    # ── 6. Parse dates ────────────────────────────────────────────────────────
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    null_dates = df["date"].isna().sum()
    if null_dates > 0:
        logger.warning(f"Dropping {null_dates} rows with unparseable dates")
        df = df.dropna(subset=["date"])
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")

    # ── 7. Parse amounts ──────────────────────────────────────────────────────
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").abs()
    null_amounts = df["amount"].isna().sum()
    if null_amounts > 0:
        logger.warning(f"Dropping {null_amounts} rows with invalid amounts")
        df = df.dropna(subset=["amount"])
    df = df[df["amount"] > 0]

    # ── 8. Fill optional string columns ──────────────────────────────────────
    for col in ["subcategory", "description", "account"]:
        if col not in df.columns:
            df[col] = ""
        else:
            df[col] = df[col].fillna("").astype(str).str.strip().replace("nan", "")

    df = df.reset_index(drop=True)
    logger.info(f"Cleaned DataFrame: {len(df)} valid rows")
    return df


def upsert_transactions(df: pd.DataFrame) -> Tuple[int, int]:
    """Insert transactions, skipping exact duplicates. Returns (inserted, skipped)."""
    inserted = 0
    skipped = 0
    rows: List[Dict[str, Any]] = df.to_dict(orient="records")

    with get_connection() as conn:
        for row in rows:
            try:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO transactions
                        (date, amount, type, category, subcategory, description, account)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["date"],
                        float(row["amount"]),
                        row["type"],
                        row["category"],
                        row.get("subcategory", ""),
                        row.get("description", ""),
                        row.get("account", ""),
                    ),
                )
                if conn.execute("SELECT changes()").fetchone()[0]:
                    inserted += 1
                else:
                    skipped += 1
            except Exception as e:
                logger.error(f"Failed to insert row {row}: {e}")
                skipped += 1

    logger.info(f"Upsert complete: {inserted} inserted, {skipped} skipped")
    return inserted, skipped


def get_affected_months(df: pd.DataFrame) -> List[str]:
    """Return sorted list of YYYY-MM strings present in the DataFrame."""
    months = pd.to_datetime(df["date"]).dt.to_period("M").astype(str).unique().tolist()
    return sorted(months)