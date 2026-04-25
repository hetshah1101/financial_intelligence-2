import pandas as pd

ESSENTIAL = {
    "rent", "utilities", "groceries", "insurance", "medical",
    "healthcare", "electricity", "water", "gas", "internet",
    "mobile", "transport", "commute",
}

DISCRETIONARY = {
    "food delivery", "dining out", "entertainment", "shopping",
    "travel", "subscriptions", "personal care", "fitness",
    "clothing", "accessories", "gadgets", "gifts",
}


def tag_category(category: str) -> str:
    c = category.strip().lower()
    if c in ESSENTIAL:
        return "essential"
    if c in DISCRETIONARY:
        return "discretionary"
    return "uncategorized"


def tag_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["tag"] = df["Category"].apply(tag_category)
    return df
