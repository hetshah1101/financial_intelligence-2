"""
exception.py — post-tagging fixup rules applied before DB insert.

Current rules
─────────────
1. Card Settlement
   Transactions that represent a bank-account payment TO a credit/charge card
   are not real expenses — they settle a balance already recorded on the card.
   We reclassify their `type` to "card settlement" so they are excluded from
   expense and savings aggregates.

   Detection: category name OR description matches known card-payment phrases.
"""

import re
import pandas as pd


# Exact category names (case-insensitive) that indicate a card payment
_CARD_CATEGORIES: set[str] = {
    "card payment",
    "credit card",
    "card settlement",
    "cc payment",
    "credit card payment",
    "credit card bill",
    "card bill",
}

# Regex patterns matched against the description field (case-insensitive)
_CARD_DESC_PATTERNS: list[str] = [
    r"credit\s*card",
    r"card\s*payment",
    r"card\s*settlement",
    r"\bcc\s*payment\b",
    r"hdfc\s*credit",
    r"sbi\s*card",
    r"axis\s*credit",
    r"icici\s*credit",
    r"kotak\s*credit",
    r"indusind\s*credit",
    r"\bcitibank\b",
    r"\bamex\b",
    r"american\s*express",
    r"bajaj\s*(fin|card)",
    r"one\s*card",
    r"slice\s*card",
    r"uni\s*card",
]

_CARD_PATTERN = re.compile("|".join(_CARD_DESC_PATTERNS), re.IGNORECASE)


def apply_exceptions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply all post-tagging exception rules and return the updated DataFrame.
    Modifies a copy — does not mutate the input.
    """
    df = df.copy()
    df = _mark_card_settlements(df)
    return df


def _mark_card_settlements(df: pd.DataFrame) -> pd.DataFrame:
    cat_lower = df["Category"].astype(str).str.strip().str.lower()
    desc_lower = df["description"].astype(str).str.strip()

    cat_match  = cat_lower.isin(_CARD_CATEGORIES)
    desc_match = desc_lower.str.contains(_CARD_PATTERN, na=False)

    mask = cat_match | desc_match
    df.loc[mask, "Type"] = "card settlement"
    return df
