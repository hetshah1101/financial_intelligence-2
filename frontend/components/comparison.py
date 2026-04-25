import streamlit as st
import plotly.graph_objects as go
import pandas as pd


def render_comparison(data: dict) -> None:
    st.header("Comparison View")

    monthly = data.get("monthly_aggregates", [])
    trends = data.get("monthly_trends", [])
    if not monthly or len(monthly) < 2:
        st.info("Need at least 2 months of data for comparison.")
        return

    months_sorted = sorted(monthly, key=lambda x: x["month"])
    current = months_sorted[-1]
    prev = months_sorted[-2]

    # Current vs Last Month
    st.subheader(f"Current Month ({current['month']}) vs Last Month ({prev['month']})")
    cols = st.columns(3)
    metrics = [
        ("Income", "total_income"),
        ("Expense", "total_expense"),
        ("Investment", "total_investment"),
    ]
    for col, (label, key) in zip(cols, metrics):
        delta = current[key] - prev[key]
        col.metric(label, f"₹{current[key]:,.0f}", delta=f"₹{delta:+,.0f}")

    # Current vs 3-Month Average
    st.subheader("Current Month vs 3-Month Average")
    if len(monthly) >= 3:
        last_3 = months_sorted[-4:-1]  # 3 months before current
        avg_income = sum(m["total_income"] for m in last_3) / 3
        avg_expense = sum(m["total_expense"] for m in last_3) / 3
        avg_investment = sum(m["total_investment"] for m in last_3) / 3

        cols2 = st.columns(3)
        cols2[0].metric("Income vs 3M Avg", f"₹{current['total_income']:,.0f}",
                        delta=f"₹{current['total_income'] - avg_income:+,.0f}")
        cols2[1].metric("Expense vs 3M Avg", f"₹{current['total_expense']:,.0f}",
                        delta=f"₹{current['total_expense'] - avg_expense:+,.0f}")
        cols2[2].metric("Investment vs 3M Avg", f"₹{current['total_investment']:,.0f}",
                        delta=f"₹{current['total_investment'] - avg_investment:+,.0f}")

    # Category-level comparison
    cat_data = data.get("category_aggregates", [])
    if cat_data:
        df = pd.DataFrame(cat_data)
        all_months = sorted(df["month"].unique(), reverse=True)
        if len(all_months) >= 2:
            cur_m, prev_m = all_months[0], all_months[1]
            cur_df = df[df["month"] == cur_m][["category", "total_amount"]].set_index("category")
            prev_df = df[df["month"] == prev_m][["category", "total_amount"]].set_index("category")
            comp = cur_df.join(prev_df, how="outer", lsuffix="_cur", rsuffix="_prev").fillna(0)
            comp["delta"] = comp["total_amount_cur"] - comp["total_amount_prev"]
            comp = comp.sort_values("delta")

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=comp.index, y=comp["total_amount_prev"],
                name=prev_m, marker_color="#3498db",
            ))
            fig.add_trace(go.Bar(
                x=comp.index, y=comp["total_amount_cur"],
                name=cur_m, marker_color="#e74c3c",
            ))
            fig.update_layout(
                barmode="group", title="Category: Current vs Previous Month",
                xaxis_title="Category", yaxis_title="Amount (₹)",
                height=420,
            )
            st.plotly_chart(fig, use_container_width=True)
