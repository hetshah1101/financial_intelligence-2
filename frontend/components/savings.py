import streamlit as st
import plotly.express as px
import pandas as pd


def render_savings(data: dict) -> None:
    st.header("Savings Opportunities")

    opps = data.get("savings_opportunities", [])
    if not opps:
        st.success("Great job! No categories are over their 3-month median baseline.")
        return

    total_potential = sum(o["potential_savings"] for o in opps)
    st.info(f"Total potential monthly savings: **₹{total_potential:,.0f}**")

    df = pd.DataFrame(opps).sort_values("potential_savings", ascending=False)

    # Bar chart
    fig = px.bar(
        df, x="potential_savings", y="category", orientation="h",
        color="tag",
        color_discrete_map={
            "essential": "#2ecc71",
            "discretionary": "#e74c3c",
            "uncategorized": "#95a5a6",
        },
        title="Potential Savings by Category",
        labels={"potential_savings": "Potential Savings (₹)", "category": ""},
    )
    fig.update_layout(height=max(300, len(df) * 40))
    st.plotly_chart(fig, use_container_width=True)

    # Detail table
    display = df[["category", "tag", "current_month_amount", "median_3m", "potential_savings"]].copy()
    display.columns = ["Category", "Tag", "Current Month (₹)", "3M Median (₹)", "Potential Savings (₹)"]
    st.dataframe(display, use_container_width=True)

    st.subheader("Budget Baseline (3-Month Medians)")
    budget = data.get("budget_baseline", [])
    if budget:
        bdf = pd.DataFrame(budget).sort_values("median_3m", ascending=False)
        bdf.columns = ["Category", "3M Median (₹)", "Tag"]
        st.dataframe(bdf, use_container_width=True)
