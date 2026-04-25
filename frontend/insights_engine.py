"""
Key Financial Insights Engine

Derives actionable, deterministic insights from financial data.
Based on: Cognitive Load Theory (reduce complexity) + Data Storytelling principles
"""
import pandas as pd
from typing import List


def derive_insights(data: dict) -> List[dict]:
    """
    Derive 3-5 key insights from financial data.
    Each insight explains 'what' and 'why it matters' to reduce cognitive load.
    """
    insights = []

    monthly = data.get("monthly_aggregates", [])
    if len(monthly) < 2:
        return insights

    # Sort by month
    monthly = sorted(monthly, key=lambda x: x["month"])
    current = monthly[-1]
    previous = monthly[-2]
    last_3 = monthly[-4:-1] if len(monthly) >= 4 else monthly[:-1]

    # ─── Insight 1: Month-over-Month Expense Change ───────────────────────────
    # (Principle: Pre-attentive processing - % change is instantly understood)
    if previous["total_expense"] > 0:
        exp_change_pct = (
            (current["total_expense"] - previous["total_expense"])
            / previous["total_expense"]
            * 100
        )
        if abs(exp_change_pct) > 5:  # Only flag significant changes (>5%)
            direction = "increased" if exp_change_pct > 0 else "decreased"
            insights.append({
                "title": f"Expenses {direction}",
                "value": f"{abs(exp_change_pct):.1f}%",
                "description": f"vs last month",
                "type": "warning" if exp_change_pct > 0 else "success",
                "explanation": "Track spending patterns to identify cost drivers",
            })

    # ─── Insight 2: Savings Rate ──────────────────────────────────────────────
    # (Principle: Visual hierarchy - savings rate is a key metric)
    if current["total_income"] > 0:
        insights.append({
            "title": "Savings Rate",
            "value": f"{current['savings_rate']:.1f}%",
            "description": f"of income retained",
            "type": "success" if current["savings_rate"] >= 20 else "warning",
            "explanation": "Financial experts recommend 20%+ savings rate",
        })

    # ─── Insight 3: Category Concentration ─────────────────────────────────────
    # (Principle: Gestalt principle of grouping + information reduction)
    behavior = data.get("spending_behavior", {})
    concentration = behavior.get("top3_concentration_pct", 0)
    if concentration > 0:
        insights.append({
            "title": "Top 3 Categories",
            "value": f"{concentration:.1f}%",
            "description": "of total expenses",
            "type": "info",
            "explanation": "High concentration means few categories dominate your spend",
        })

    # ─── Insight 4: Essential vs Discretionary Ratio ──────────────────────────
    # (Principle: Pre-attentive processing - ratio is instantly recognized)
    essential = behavior.get("essential_pct", 0)
    discretionary = behavior.get("discretionary_pct", 0)
    total_tagged = essential + discretionary
    if total_tagged > 0:
        ratio = essential / discretionary if discretionary > 0 else float('inf')
        if ratio < 2:  # If essential < 2× discretionary, flag it
            insights.append({
                "title": "High Discretionary Spend",
                "value": f"{discretionary:.1f}%",
                "description": "of total spend",
                "type": "warning",
                "explanation": "Discretionary expenses exceed essential by a significant margin. Review areas for cost reduction.",
            })

    # ─── Insight 5: Anomalies Detected ────────────────────────────────────────
    # (Principle: Pre-attentive processing - count is instantly understood)
    anomaly_count = (
        len(data.get("anomalies_total_spend", []))
        + len(data.get("anomalies_category", []))
    )
    if anomaly_count > 0:
        insights.append({
            "title": "Anomalies Detected",
            "value": str(anomaly_count),
            "description": "unusual spending events",
            "type": "warning" if anomaly_count > 3 else "info",
            "explanation": "Review these events to understand one-time vs recurring unusual expenses",
        })

    # ─── Insight 6: Savings Opportunities ──────────────────────────────────────
    savings_opps = data.get("savings_opportunities", [])
    if savings_opps:
        total_potential = sum(s.get("potential_savings", 0) for s in savings_opps)
        if total_potential > 0:
            insights.append({
                "title": "Potential Monthly Savings",
                "value": f"₹{total_potential:,.0f}",
                "description": "by reverting to 3-month median",
                "type": "success",
                "explanation": f"Found {len(savings_opps)} categories where current spend exceeds baseline. Reducing to median would save this amount monthly.",
            })

    return insights[:5]  # Return top 5 insights
