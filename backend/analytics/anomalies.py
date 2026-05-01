import pandas as pd
from schemas import AnomalyRecord

TOTAL_SPEND_MULTIPLIER = 1.4
CATEGORY_SPEND_MULTIPLIER = 1.5
SPIKE_MULTIPLIER = 2.0
NEW_CATEGORY_THRESHOLD = 5000.0   # INR
ERRATIC_STD_MULTIPLIER = 1.5      # mean + N*std as threshold


def detect_total_spend_anomalies(monthly_df: pd.DataFrame) -> list[AnomalyRecord]:
    df = monthly_df.sort_values("month").copy()
    # min_periods=2 so a single prior month isn't treated as a stable baseline
    df["rolling_3m_avg"] = df["total_expense"].shift(1).rolling(3, min_periods=2).mean()

    anomalies = []
    for _, row in df.iterrows():
        if pd.isna(row["rolling_3m_avg"]) or row["rolling_3m_avg"] == 0:
            continue
        threshold = row["rolling_3m_avg"] * TOTAL_SPEND_MULTIPLIER
        if row["total_expense"] > threshold:
            anomalies.append(AnomalyRecord(
                month=row["month"],
                reason=f"Total expense {row['total_expense']:.0f} exceeds 1.4× 3-month avg {row['rolling_3m_avg']:.0f}",
                amount=round(row["total_expense"], 2),
                threshold=round(threshold, 2),
            ))
    return anomalies


def detect_category_anomalies(category_df: pd.DataFrame) -> list[AnomalyRecord]:
    df = category_df.sort_values(["category", "month"]).copy()
    anomalies = []

    for category, grp in df.groupby("category"):
        grp = grp.sort_values("month").copy()
        grp["rolling_3m_avg"] = grp["total_amount"].shift(1).rolling(3, min_periods=2).mean()

        for _, row in grp.iterrows():
            if pd.isna(row["rolling_3m_avg"]) or row["rolling_3m_avg"] == 0:
                continue
            threshold = row["rolling_3m_avg"] * CATEGORY_SPEND_MULTIPLIER
            if row["total_amount"] > threshold:
                anomalies.append(AnomalyRecord(
                    month=row["month"],
                    category=row["category"],
                    reason=f"{category} spend {row['total_amount']:.0f} exceeds 1.5× 3-month avg {row['rolling_3m_avg']:.0f}",
                    amount=round(row["total_amount"], 2),
                    threshold=round(threshold, 2),
                ))
    return anomalies


def detect_erratic_spend(category_df: pd.DataFrame) -> list[AnomalyRecord]:
    df = category_df.sort_values(["category", "month"]).copy()
    anomalies = []

    for category, grp in df.groupby("category"):
        grp = grp.sort_values("month").reset_index(drop=True)
        amounts = grp["total_amount"]

        # Condition 1: high std deviation
        if len(amounts) >= 3:
            mean_val = amounts.mean()
            std_val = amounts.std()
            threshold = mean_val + ERRATIC_STD_MULTIPLIER * std_val
            last_amount = amounts.iloc[-1]
            last_month = grp["month"].iloc[-1]
            if std_val > 0 and last_amount > threshold:
                anomalies.append(AnomalyRecord(
                    month=last_month,
                    category=category,
                    reason=f"High variance: std {std_val:.0f} > threshold; last spend {last_amount:.0f}",
                    amount=round(float(last_amount), 2),
                ))

        # Condition 2: sudden spike (current > 2× last month)
        if len(amounts) >= 2:
            for i in range(1, len(amounts)):
                prev = amounts.iloc[i - 1]
                curr = amounts.iloc[i]
                month = grp["month"].iloc[i]
                if prev > 0 and curr > SPIKE_MULTIPLIER * prev:
                    anomalies.append(AnomalyRecord(
                        month=month,
                        category=category,
                        reason=f"Spike: {curr:.0f} is {curr/prev:.1f}× last month ({prev:.0f})",
                        amount=round(float(curr), 2),
                    ))

        # Condition 3: new category with large first transaction
        if len(amounts) == 1 and amounts.iloc[0] > NEW_CATEGORY_THRESHOLD:
            anomalies.append(AnomalyRecord(
                month=grp["month"].iloc[0],
                category=category,
                reason=f"New category with large first spend: {amounts.iloc[0]:.0f}",
                amount=round(float(amounts.iloc[0]), 2),
            ))

    # Deduplicate by (month, category, reason prefix) — 60 chars avoids prefix collisions
    seen: set[tuple] = set()
    unique = []
    for a in anomalies:
        key = (a.month, a.category or "", a.reason[:60])
        if key not in seen:
            seen.add(key)
            unique.append(a)
    return unique
