"""
exception.py — post-tagging fixup rules applied before DB insert.

Current rules
─────────────
1. Card Settlement
   Transactions that represent a bank-account payment TO a credit/charge card
   are not real expenses — they settle a balance already recorded on the card.
   We reclassify their `type` to "card settlement" so they are excluded from
   expense and savings aggregates.

   Detection (any one of):
   a) Category name matches known card-payment phrases
   b) Description matches card-payment regex patterns (requires payment context,
      not bare issuer name, to avoid false positives on real purchases)
   c) Account = "Card" AND Type = "investment" — this catches the dedup-surviving
      side of paired bank→card transfers (Transfer-In to card account), which have
      Category="Bank Accounts" and would otherwise be missed by (a).
"""

import re
import pandas as pd


# Exact category names (case-insensitive) that indicate a card payment
_CARD_CATEGORIES: set[str] = {
    "card",
    "card payment",
    "credit card",
    "card settlement",
    "cc payment",
    "credit card payment",
    "credit card bill",
    "card bill",
}

# Account names (case-insensitive) that represent a credit/charge card account
_CARD_ACCOUNTS: set[str] = {
    "card",
    "credit card",
    "hdfc card",
    "sbi card",
    "axis card",
    "icici card",
    "kotak card",
    "amex",
    "onecard",
    "slice",
}

# Regex patterns matched against the description field (case-insensitive).
# Each pattern requires explicit payment/settlement context so bare issuer names
# (e.g. "Amex travel portal", "Bajaj Finance EMI") are not mis-reclassified.
_CARD_DESC_PATTERNS: list[str] = [
    r"credit\s*card\s*(?:payment|bill|settlement|due|repayment)",
    r"card\s*(?:payment|settlement|bill|due|repayment)",
    r"\bcc\s*(?:payment|bill|settlement|due)\b",
    r"(?:payment|repayment|bill\s*pay)\s+(?:to\s+)?(?:hdfc|sbi|axis|icici|kotak|indusind)\s*(?:credit|card)",
    r"payment\s+to\s+(?:amex|american\s*express)",
    r"payment\s+to\s+(?:one\s*card|onecard)",
    r"payment\s+to\s+(?:slice|uni\s*card)",
    r"payment\s+to\s+bajaj\s*(?:fin|card|finserv)",
]

_CARD_PATTERN = re.compile("|".join(_CARD_DESC_PATTERNS), re.IGNORECASE)


def apply_exceptions(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = _mark_card_settlements(df)
    return df


def _mark_card_settlements(df: pd.DataFrame) -> pd.DataFrame:
    cat_lower  = df["Category"].astype(str).str.strip().str.lower()
    desc_lower = df["description"].astype(str).str.strip()
    acc_lower  = df["Account"].astype(str).str.strip().str.lower() if "Account" in df.columns else pd.Series("", index=df.index)
    type_lower = df["Type"].astype(str).str.strip().str.lower()

    cat_match  = cat_lower.isin(_CARD_CATEGORIES)
    desc_match = desc_lower.str.contains(_CARD_PATTERN, na=False)
    # Card account receiving a bank-side transfer (dedup keeps this row, Category="Bank Accounts")
    acc_match  = acc_lower.isin(_CARD_ACCOUNTS) & (type_lower == "investment")

    mask = cat_match | desc_match | acc_match
    df.loc[mask, "Type"] = "card settlement"
    return df
