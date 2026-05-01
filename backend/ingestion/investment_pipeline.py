"""
investment_pipeline.py — ingestion for broker CSV exports.

Supported sources (passed as ?source= on the upload endpoint):
  zerodha  — Zerodha Kite trade book CSV
  groww    — Groww transaction statement CSV
  kuvera   — Kuvera portfolio export CSV
  cams     — CAMS/KFintech consolidated account statement CSV
  generic  — any CSV with the canonical column set

Canonical columns after normalization:
  date, month, instrument_type, name, symbol, isin, folio_number,
  units, price_per_unit, amount, transaction_type, account, notes
"""

import logging
from datetime import date as date_type

import pandas as pd
from sqlalchemy.orm import Session

from models_investment import Investment

logger = logging.getLogger("finsight.ingestion.investment")

_CANONICAL_TRANSACTION_TYPES = {"buy", "sell", "dividend", "sip", "interest", "maturity", "redemption"}
_CANONICAL_INSTRUMENT_TYPES  = {"mutual_fund", "stock", "fd", "ppf", "nps", "gold", "crypto", "bonds", "other"}


# ── Broker mappers ────────────────────────────────────────────────────────────

class _BaseMapper:
    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError


class ZerodhaMapper(_BaseMapper):
    """Zerodha Kite trade book CSV format."""

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.columns = [c.strip() for c in df.columns]

        col_map = {
            "symbol":       "name",
            "isin":         "isin",
            "trade date":   "date",
            "quantity":     "units",
            "price":        "price_per_unit",
            "trade type":   "transaction_type",
            "exchange":     "notes",
        }
        df = df.rename(columns={k: v for k, v in col_map.items()
                                 if k in df.columns.str.lower().tolist()})
        df = _rename_ci(df, col_map)

        df["instrument_type"] = "stock"
        df["amount"] = df.get("amount", df["units"] * df["price_per_unit"])
        df["folio_number"] = None
        df["symbol"] = df.get("name", "")
        df["account"] = "Zerodha"
        df["transaction_type"] = df["transaction_type"].str.lower().map(
            {"buy": "buy", "sell": "sell", "b": "buy", "s": "sell"}
        ).fillna("buy")
        return _finalize(df)


class GrowwMapper(_BaseMapper):
    """Groww transaction statement CSV format."""

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        col_map = {
            "scheme name":       "name",
            "fund name":         "name",
            "isin":              "isin",
            "date":              "date",
            "transaction date":  "date",
            "units":             "units",
            "nav":               "price_per_unit",
            "amount":            "amount",
            "type":              "transaction_type",
            "transaction type":  "transaction_type",
            "folio":             "folio_number",
            "folio number":      "folio_number",
        }
        df = _rename_ci(df, col_map)
        df["instrument_type"] = "mutual_fund"
        df["symbol"] = None
        df["account"] = "Groww"
        df["transaction_type"] = df.get("transaction_type", pd.Series(dtype=str)).astype(str).str.lower().map({
            "purchase": "buy", "sip": "sip", "redemption": "sell", "redeem": "sell",
            "dividend": "dividend", "switch in": "buy", "switch out": "sell",
        }).fillna("buy")
        return _finalize(df)


class KuveraMapper(_BaseMapper):
    """Kuvera portfolio export CSV format."""

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        col_map = {
            "fund name":         "name",
            "isin":              "isin",
            "folio":             "folio_number",
            "units":             "units",
            "avg cost":          "price_per_unit",
            "current nav":       "price_per_unit",
            "invested":          "amount",
            "invested value":    "amount",
            "date":              "date",
        }
        df = _rename_ci(df, col_map)
        df["instrument_type"] = "mutual_fund"
        df["transaction_type"] = "buy"
        df["symbol"] = None
        df["account"] = "Kuvera"
        if "date" not in df.columns:
            df["date"] = date_type.today()
        return _finalize(df)


class CamsMapper(_BaseMapper):
    """CAMS/KFintech Consolidated Account Statement CSV."""

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        col_map = {
            "scheme":            "name",
            "scheme name":       "name",
            "isin":              "isin",
            "folio no.":         "folio_number",
            "folio number":      "folio_number",
            "units":             "units",
            "nav":               "price_per_unit",
            "amount":            "amount",
            "transaction date":  "date",
            "date":              "date",
            "transaction type":  "transaction_type",
            "type":              "transaction_type",
        }
        df = _rename_ci(df, col_map)
        df["instrument_type"] = "mutual_fund"
        df["symbol"] = None
        df["account"] = "CAMS"
        df["transaction_type"] = df.get("transaction_type", pd.Series(dtype=str)).astype(str).str.lower().map({
            "purchase": "buy", "sip": "sip", "redemption": "sell", "dividend": "dividend",
            "switch in": "buy", "switch out": "sell",
        }).fillna("buy")
        return _finalize(df)


class GenericMapper(_BaseMapper):
    """Generic mapper for CSVs that already use canonical column names."""

    _ALIASES = {
        "fund name":         "name",
        "scheme name":       "name",
        "scheme":            "name",
        "ticker":            "symbol",
        "nav":               "price_per_unit",
        "price":             "price_per_unit",
        "trade date":        "date",
        "transaction date":  "date",
        "quantity":          "units",
        "type":              "transaction_type",
        "folio":             "folio_number",
        "folio no.":         "folio_number",
    }

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df = _rename_ci(df, self._ALIASES)
        if "instrument_type" not in df.columns:
            df["instrument_type"] = "other"
        if "account" not in df.columns:
            df["account"] = "Manual"
        if "transaction_type" not in df.columns:
            df["transaction_type"] = "buy"
        return _finalize(df)


SUPPORTED_SOURCES: dict[str, type[_BaseMapper]] = {
    "zerodha": ZerodhaMapper,
    "groww":   GrowwMapper,
    "kuvera":  KuveraMapper,
    "cams":    CamsMapper,
    "generic": GenericMapper,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _rename_ci(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    """Case-insensitive column rename."""
    lower_map = {k.lower(): v for k, v in mapping.items()}
    rename = {c: lower_map[c.strip().lower()] for c in df.columns if c.strip().lower() in lower_map}
    return df.rename(columns=rename)


def _finalize(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce types and ensure all canonical columns exist."""
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    else:
        df["date"] = date_type.today()

    df["month"] = pd.to_datetime(df["date"].astype(str)).dt.to_period("M").astype(str)

    for col in ["units", "price_per_unit", "amount"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").abs()
        else:
            df[col] = None

    # Derive amount if missing
    if df["amount"].isna().all() and not df["units"].isna().all() and not df["price_per_unit"].isna().all():
        df["amount"] = df["units"] * df["price_per_unit"]

    for col in ["symbol", "isin", "folio_number", "notes"]:
        if col not in df.columns:
            df[col] = None

    df = df.dropna(subset=["date", "amount", "name"])
    return df


# ── Insert logic ──────────────────────────────────────────────────────────────

def run_investment_pipeline(df: pd.DataFrame, source: str, db: Session) -> dict:
    mapper_cls = SUPPORTED_SOURCES.get(source.lower(), GenericMapper)
    mapper = mapper_cls()
    df = mapper.normalize(df)

    _validate_investment(df)

    inserted = 0
    skipped = 0

    for _, row in df.iterrows():
        existing = (
            db.query(Investment)
            .filter(
                Investment.date == row["date"],
                Investment.name == row["name"],
                Investment.amount == float(row["amount"]),
                Investment.transaction_type == row.get("transaction_type"),
                Investment.account == row.get("account"),
            )
            .first()
        )
        if existing:
            skipped += 1
            continue

        inv = Investment(
            date=row["date"],
            month=row["month"],
            instrument_type=str(row.get("instrument_type", "other")),
            name=str(row["name"]),
            symbol=row.get("symbol") or None,
            isin=row.get("isin") or None,
            folio_number=row.get("folio_number") or None,
            units=float(row["units"]) if pd.notna(row.get("units")) else None,
            price_per_unit=float(row["price_per_unit"]) if pd.notna(row.get("price_per_unit")) else None,
            amount=float(row["amount"]),
            transaction_type=str(row.get("transaction_type", "buy")),
            account=str(row.get("account", "Manual")),
            notes=str(row["notes"]) if pd.notna(row.get("notes")) else None,
        )
        db.add(inv)
        inserted += 1

    db.commit()
    logger.info("Investment pipeline: inserted=%d skipped=%d source=%s", inserted, skipped, source)
    return {"inserted": inserted, "skipped": skipped}


def _validate_investment(df: pd.DataFrame) -> None:
    required = {"date", "name", "amount"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Investment CSV missing required columns: {missing}")
    if df.empty:
        raise ValueError("Investment CSV has no rows after cleaning")
