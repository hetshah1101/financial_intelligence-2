import pandas as pd
from schemas import SavingsOpportunity, BudgetBaseline


def compute_savings_opportunities(
    category_df: pd.DataFrame,
    budget_baseline: list[BudgetBaseline],
) -> list[SavingsOpportunity]:
    if category_df.empty or not budget_baseline:
        return []

    # Current month is the latest month in the data
    latest_month = category_df["month"].max()
    current = category_df[category_df["month"] == latest_month]

    baseline_map = {b.category: b for b in budget_baseline}
    opportunities = []

    for _, row in current.iterrows():
        cat = row["category"]
        if cat not in baseline_map:
            continue
        baseline = baseline_map[cat]
        current_amount = float(row["total_amount"])
        median_3m = baseline.median_3m

        if current_amount > median_3m:
            opportunities.append(SavingsOpportunity(
                category=cat,
                current_month_amount=round(current_amount, 2),
                median_3m=round(median_3m, 2),
                potential_savings=round(current_amount - median_3m, 2),
                tag=baseline.tag,
            ))

    opportunities.sort(key=lambda x: x.potential_savings, reverse=True)
    return opportunities
