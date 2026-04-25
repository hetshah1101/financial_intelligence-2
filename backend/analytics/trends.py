import pandas as pd
from schemas import MonthlyTrendPoint, YearlyTrendPoint, CategoryTrendPoint


def compute_monthly_trends(monthly_df: pd.DataFrame) -> list[MonthlyTrendPoint]:
    df = monthly_df.sort_values("month").copy()
    df["mom_income_change"] = df["total_income"].pct_change() * 100
    df["mom_expense_change"] = df["total_expense"].pct_change() * 100
    df["rolling_3m_expense"] = df["total_expense"].rolling(3, min_periods=1).mean()

    result = []
    for _, row in df.iterrows():
        result.append(MonthlyTrendPoint(
            month=row["month"],
            income=round(row["total_income"], 2),
            expense=round(row["total_expense"], 2),
            investment=round(row["total_investment"], 2),
            mom_income_change=round(row["mom_income_change"], 2) if pd.notna(row["mom_income_change"]) else None,
            mom_expense_change=round(row["mom_expense_change"], 2) if pd.notna(row["mom_expense_change"]) else None,
            rolling_3m_expense=round(row["rolling_3m_expense"], 2) if pd.notna(row["rolling_3m_expense"]) else None,
        ))
    return result


def compute_yearly_trends(yearly_df: pd.DataFrame) -> list[YearlyTrendPoint]:
    df = yearly_df.sort_values("year").copy()
    df["yoy_income_change"] = df["total_income"].pct_change() * 100
    df["yoy_expense_change"] = df["total_expense"].pct_change() * 100

    result = []
    for _, row in df.iterrows():
        result.append(YearlyTrendPoint(
            year=int(row["year"]),
            total_income=round(row["total_income"], 2),
            total_expense=round(row["total_expense"], 2),
            yoy_income_change=round(row["yoy_income_change"], 2) if pd.notna(row["yoy_income_change"]) else None,
            yoy_expense_change=round(row["yoy_expense_change"], 2) if pd.notna(row["yoy_expense_change"]) else None,
        ))
    return result


def compute_category_trends(category_df: pd.DataFrame) -> list[CategoryTrendPoint]:
    df = category_df.sort_values(["category", "month"]).copy()
    result = []

    for category, grp in df.groupby("category"):
        grp = grp.sort_values("month").copy()
        grp["last_3m_avg"] = grp["total_amount"].rolling(3, min_periods=1).mean()
        grp["pct_deviation"] = (
            (grp["total_amount"] - grp["last_3m_avg"]) / grp["last_3m_avg"] * 100
        ).where(grp["last_3m_avg"] > 0)

        for _, row in grp.iterrows():
            result.append(CategoryTrendPoint(
                category=row["category"],
                month=row["month"],
                amount=round(row["total_amount"], 2),
                last_3m_avg=round(row["last_3m_avg"], 2) if pd.notna(row["last_3m_avg"]) else None,
                pct_deviation=round(row["pct_deviation"], 2) if pd.notna(row.get("pct_deviation")) else None,
            ))
    return result
