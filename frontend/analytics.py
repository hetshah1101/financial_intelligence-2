from collections import defaultdict
from statistics import mean

import pandas as pd

from config import classify_category
from formatters import fmt_month


def filter_by_date_range(monthly_data: list, date_range: str) -> list:
    if not monthly_data:
        return []
    n = {"3m": 3, "6m": 6, "12m": 12, "1y": 12, "all": 999}.get(date_range, 12)
    return monthly_data[-n:]


def compute_baseline(monthly_data: list, baseline_type: str) -> dict | None:
    if len(monthly_data) < 2:
        return None
    history = monthly_data[:-1]
    windows = {
        "last_month":   history[-1:],
        "recent_avg":   history[-3:],
        "longterm_avg": history[-6:],
        "12m_avg":      history[-12:],
        "all_time":     history,
    }
    window = windows.get(baseline_type, history[-12:])
    if not window:
        return None
    return {
        "total_income":     mean(m["total_income"]     for m in window),
        "total_expense":    mean(m["total_expense"]    for m in window),
        "total_investment": mean(m["total_investment"] for m in window),
        "net_savings":      mean(m["net_savings"]      for m in window),
        "savings_rate":     mean(m["savings_rate"]     for m in window),
    }


def behavioral_split(categories: list) -> dict:
    essential = sum(c["total_amount"] for c in categories
                    if classify_category(c["category"]) == "essential")
    discr = sum(c["total_amount"] for c in categories
                if classify_category(c["category"]) == "discretionary")
    total = essential + discr or 1
    return {
        "essential_pct":        essential / total * 100,
        "discretionary_pct":    discr / total * 100,
        "essential_amount":     essential,
        "discretionary_amount": discr,
        "essential_cats":       [c for c in categories
                                 if classify_category(c["category"]) == "essential"][:4],
        "discr_cats":           [c for c in categories
                                 if classify_category(c["category"]) == "discretionary"][:4],
    }


def generate_takeaways(latest: dict, baseline: dict | None, categories: list) -> list:
    tips = []
    if baseline and baseline["total_expense"] > 0:
        delta = (latest["total_expense"] - baseline["total_expense"]) / baseline["total_expense"] * 100
        direction = "above" if delta > 0 else "below"
        if abs(delta) > 3:
            tips.append(f"Expenses {abs(delta):.0f}% {direction} your 12-month average")
    if categories:
        top = categories[0]
        pct = top.get("percentage_of_total_expense") or top.get("percentage_of_total", 0)
        tips.append(f"{top['category']} is your largest expense at {pct:.0f}% of spending")
    rate = latest.get("savings_rate", 0)
    status = "on track" if rate >= 20 else "below recommended 20% threshold"
    tips.append(f"Savings rate {rate:.0f}% this month — {status}")
    inv = latest.get("total_investment", 0)
    if inv > 0:
        tips.append(f"₹{inv / 1000:.0f}K invested this month")
    return tips[:4]


def classify_anomalies(dashboard: dict) -> list:
    import re as _re
    seen: set = set()
    result = []

    def _add(a: dict, multiplier: float) -> None:
        key = (a.get("month", ""), a.get("category", ""))
        if key in seen:
            return
        seen.add(key)
        amount    = a.get("amount", 0) or 0
        threshold = a.get("threshold") or 0
        reason    = a.get("reason", "")

        if threshold and multiplier > 0:
            # threshold = rolling_avg * multiplier  →  baseline = threshold / multiplier
            baseline = round(threshold / multiplier, 2)
        elif "last month" in reason:
            # Erratic spike reason: "Spike: X is Y× last month (Z)"
            m = _re.search(r'\((\d+(?:\.\d+)?)\)', reason)
            baseline = float(m.group(1)) if m else 0.0
        else:
            baseline = 0.0

        ratio = round(amount / baseline, 4) if baseline > 0 else 0.0
        result.append({
            "category":             a.get("category", "Unknown"),
            "current_month_amount": amount,
            "three_month_avg":      baseline,
            "ratio":                ratio,
            "month":                a.get("month", ""),
            "reason":               reason,
            "alert_type":           "spike" if ratio > 1.4 else "variance",
        })

    for a in dashboard.get("anomalies_total_spend", []):
        _add(a, 1.4)
    for a in dashboard.get("anomalies_category", []):
        _add(a, 1.5)
    for a in dashboard.get("anomalies_erratic", []):
        _add(a, 0)

    monthly = dashboard.get("monthly_aggregates", [])
    if len(monthly) >= 4:
        history = monthly[-4:-1]
        avg_sav = mean(m["net_savings"] for m in history)
        cur_sav = monthly[-1].get("net_savings", 0)
        if avg_sav > 0 and cur_sav < avg_sav * 0.8:
            result.append({
                "category":             "Savings",
                "current_month_amount": cur_sav,
                "three_month_avg":      avg_sav,
                "ratio":                round(cur_sav / avg_sav, 4),
                "month":                monthly[-1].get("month", ""),
                "reason":               "Savings dropped >20% below 3-month average",
                "alert_type":           "savings",
            })
    return sorted(result, key=lambda x: x["ratio"], reverse=True)


def aggregate_by_granularity(monthly_data: list, granularity: str) -> list:
    """Re-aggregate monthly records into monthly / quarterly / yearly buckets."""
    if not monthly_data:
        return []

    df = pd.DataFrame(monthly_data)
    df["date"] = pd.to_datetime(df["month"] + "-01")

    sum_cols = ["total_income", "total_expense", "total_investment", "net_savings"]
    # Ensure columns exist
    for col in sum_cols:
        if col not in df.columns:
            df[col] = 0

    if granularity == "monthly":
        df["period"] = df["month"]
        result = df[["period"] + sum_cols].copy()
        result = result.sort_values("period")
    elif granularity == "quarterly":
        df["period"] = df["date"].dt.to_period("Q").astype(str)
        result = df.groupby("period")[sum_cols].sum().reset_index()
        result = result.sort_values("period")
    elif granularity == "yearly":
        df["period"] = df["date"].dt.year.astype(str)
        result = df.groupby("period")[sum_cols].sum().reset_index()
        result = result.sort_values("period")
    else:
        df["period"] = df["month"]
        result = df[["period"] + sum_cols].copy()

    result["savings_rate"] = (
        result["net_savings"] / result["total_income"].replace(0, float("nan")) * 100
    ).fillna(0)

    return result.to_dict(orient="records")


def aggregate_category_by_granularity(
    all_cat_agg: list, granularity: str, category: str
) -> tuple:
    """Return (periods, period_labels, amounts) for a single category."""
    cat_rows = [r for r in all_cat_agg if r["category"] == category]
    if not cat_rows:
        return [], [], []

    df = pd.DataFrame(cat_rows)
    df["date"] = pd.to_datetime(df["month"] + "-01")

    if granularity == "monthly":
        df["period"] = df["month"]
    elif granularity == "quarterly":
        df["period"] = df["date"].dt.to_period("Q").astype(str)
    elif granularity == "yearly":
        df["period"] = df["date"].dt.year.astype(str)
    else:
        df["period"] = df["month"]

    agg = df.groupby("period")["total_amount"].sum().reset_index().sort_values("period")
    periods = agg["period"].tolist()
    labels = [fmt_period_label(p, granularity) for p in periods]
    amounts = agg["total_amount"].tolist()
    return periods, labels, amounts


def fmt_period_label(period: str, granularity: str) -> str:
    """Format a period string for display."""
    if granularity == "monthly":
        return fmt_month(period)
    elif granularity == "quarterly":
        try:
            year = period[:4]
            q = period[-1]
            return f"Q{q}'{year[2:]}"
        except Exception:
            return period
    elif granularity == "yearly":
        return f"'{period[2:]}"
    return period


def aggregate_account_by_granularity(
    account_monthly: list, granularity: str, metric: str
) -> dict:
    """Return {account_type: (periods, period_labels, values)} aggregated by granularity.
    metric is one of 'expense', 'income', 'investment'.
    """
    if not account_monthly:
        return {}

    df = pd.DataFrame(account_monthly)
    if metric not in df.columns:
        return {}

    df["date"] = pd.to_datetime(df["month"] + "-01")
    if granularity == "monthly":
        df["period"] = df["month"]
    elif granularity == "quarterly":
        df["period"] = df["date"].dt.to_period("Q").astype(str)
    elif granularity == "yearly":
        df["period"] = df["date"].dt.year.astype(str)
    else:
        df["period"] = df["month"]

    result = {}
    for acct_type, group in df.groupby("account_type"):
        agg = group.groupby("period")[metric].sum().reset_index().sort_values("period")
        periods = agg["period"].tolist()
        labels = [fmt_period_label(p, granularity) for p in periods]
        amounts = agg[metric].tolist()
        result[str(acct_type)] = (periods, labels, amounts)
    return result


def aggregate_account_category_by_granularity(
    account_cat: list, granularity: str, category: str
) -> dict:
    """Return {account_type: (periods, period_labels, amounts)} for a specific category."""
    cat_rows = [r for r in account_cat if r["category"] == category]
    if not cat_rows:
        return {}

    df = pd.DataFrame(cat_rows)
    df["date"] = pd.to_datetime(df["month"] + "-01")
    if granularity == "monthly":
        df["period"] = df["month"]
    elif granularity == "quarterly":
        df["period"] = df["date"].dt.to_period("Q").astype(str)
    elif granularity == "yearly":
        df["period"] = df["date"].dt.year.astype(str)
    else:
        df["period"] = df["month"]

    result = {}
    for acct_type, group in df.groupby("account_type"):
        agg = group.groupby("period")["total_amount"].sum().reset_index().sort_values("period")
        periods = agg["period"].tolist()
        labels = [fmt_period_label(p, granularity) for p in periods]
        amounts = agg["total_amount"].tolist()
        result[str(acct_type)] = (periods, labels, amounts)
    return result


def build_category_diffs(
    current_cats: dict, baseline_cats: dict
) -> list:
    """Build list of category diff dicts for the Compare tab."""
    all_cats = sorted(
        set(list(current_cats) + list(baseline_cats)),
        key=lambda c: -current_cats.get(c, 0),
    )
    rows = []
    for cat in all_cats:
        curr = current_cats.get(cat, 0)
        base = baseline_cats.get(cat, 0)
        diff = curr - base
        pct  = (diff / base * 100) if base else 0
        rows.append({
            "category":   cat,
            "current":    curr,
            "baseline":   base,
            "diff":       diff,
            "pct_change": pct,
        })
    return rows


def build_baseline_cats(all_cat_agg: list, baseline_months_set: set) -> dict:
    """Compute per-category average amounts over the baseline window months."""
    totals: dict = defaultdict(list)
    for c in all_cat_agg:
        if c["month"] in baseline_months_set:
            totals[c["category"]].append(c["total_amount"])
    return {cat: mean(v) for cat, v in totals.items()}
