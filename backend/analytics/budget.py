import pandas as pd
from schemas import BudgetBaseline


def compute_budget_baseline(category_df: pd.DataFrame) -> list[BudgetBaseline]:
    if category_df.empty:
        return []

    months_sorted = sorted(category_df["month"].unique())
    last_3 = months_sorted[-3:] if len(months_sorted) >= 3 else months_sorted
    recent = category_df[category_df["month"].isin(last_3)]

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
