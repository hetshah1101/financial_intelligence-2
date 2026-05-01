import pandas as pd
from schemas import SpendingBehavior, TopCategory


def compute_spending_behavior(category_df: pd.DataFrame) -> SpendingBehavior:
    if category_df.empty:
        return SpendingBehavior(
            top_5_categories=[],
            top3_concentration_pct=0.0,
            essential_pct=0.0,
            discretionary_pct=0.0,
            uncategorized_pct=0.0,
        )

    # Use only the latest month so percentages reflect current, not lifetime, spending
    latest_month = category_df["month"].max()
    by_cat = (
        category_df[category_df["month"] == latest_month]
        .groupby(["category", "tag"])["total_amount"]
        .sum()
        .reset_index()
        .sort_values("total_amount", ascending=False)
    )
    total = by_cat["total_amount"].sum()

    # Top 5 categories
    top5 = by_cat.head(5)
    top_5 = [
        TopCategory(
            category=row["category"],
            total_amount=round(float(row["total_amount"]), 2),
            percentage=round(float(row["total_amount"] / total * 100), 2) if total > 0 else 0.0,
        )
        for _, row in top5.iterrows()
    ]

    # Top 3 concentration
    top3_sum = by_cat.head(3)["total_amount"].sum()
    top3_pct = round(float(top3_sum / total * 100), 2) if total > 0 else 0.0

    # Essential vs Discretionary split
    essential_sum = by_cat[by_cat["tag"] == "essential"]["total_amount"].sum()
    discretionary_sum = by_cat[by_cat["tag"] == "discretionary"]["total_amount"].sum()
    uncategorized_sum = by_cat[by_cat["tag"] == "uncategorized"]["total_amount"].sum()

    return SpendingBehavior(
        top_5_categories=top_5,
        top3_concentration_pct=top3_pct,
        essential_pct=round(float(essential_sum / total * 100), 2) if total > 0 else 0.0,
        discretionary_pct=round(float(discretionary_sum / total * 100), 2) if total > 0 else 0.0,
        uncategorized_pct=round(float(uncategorized_sum / total * 100), 2) if total > 0 else 0.0,
    )
