import pandas as pd

# Categories classified as essential needs
ESSENTIAL = {
    # Housing & utilities
    "rent", "home", "emi", "housing",
    "utilities", "electricity", "water", "gas", "internet", "mobile",
    # Food staples
    "groceries", "grocery", "food",
    # Health
    "medical", "healthcare", "health", "pharmacy", "doctor", "medicine",
    "insurance",
    # Transport
    "transport", "commute", "petrol", "fuel",
    # Education & tax
    "education", "tax",
}

# Categories classified as discretionary spending
DISCRETIONARY = {
    # Food & drink out
    "dining out", "food delivery", "restaurant", "cafe",
    # Entertainment & leisure
    "entertainment", "ott", "subscriptions", "streaming", "gaming",
    "books", "music",
    # Shopping
    "shopping", "clothing", "electronics", "accessories", "gadgets",
    "fashion",
    # Travel & stays
    "travel", "hotel", "flights", "vacation",
    # Personal & social
    "personal care", "fitness", "gym", "sports",
    "gifts", "gift", "social life", "family",
    # Misc
    "miscellaneous", "other",
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
