import pandas as pd
from schemas import BudgetBaseline


def compute_budget_baseline(
    category_df: pd.DataFrame, window_months: int = 6
) -> list[BudgetBaseline]:
    if category_df.empty:
        return []

    months_sorted = sorted(category_df["month"].unique())
    window = months_sorted[-window_months:] if len(months_sorted) >= window_months else months_sorted
    recent = category_df[category_df["month"].isin(window)]

    baseline = (
        recent.groupby(["category", "tag"])["total_amount"]
        .median()
        .reset_index()
        .rename(columns={"total_amount": "median_3m"})
    )

    return [
        BudgetBaseline(
            category=row["category"],
            median_3m=round(float(row["median_3m"]), 2),
            tag=row["tag"],
        )
        for _, row in baseline.iterrows()
    ]
