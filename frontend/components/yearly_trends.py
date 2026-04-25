import streamlit as st
import plotly.graph_objects as go
import pandas as pd


def render_yearly_trends(data: dict) -> None:
    st.header("Yearly Trends")

    trends = data.get("yearly_trends", [])
    if not trends:
        st.info("No yearly trend data available.")
        return

    df = pd.DataFrame(trends).sort_values("year")

    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["year"].astype(str), y=df["total_income"],
                         name="Income", marker_color="#2ecc71"))
    fig.add_trace(go.Bar(x=df["year"].astype(str), y=df["total_expense"],
                         name="Expense", marker_color="#e74c3c"))

    fig.update_layout(
        barmode="group", xaxis_title="Year", yaxis_title="Amount (₹)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        height=380,
    )
    st.plotly_chart(fig, use_container_width=True)

    # YoY table
    ydf = data.get("yearly_aggregates", [])
    if ydf:
        st.subheader("Year-over-Year Summary")
        rows = pd.DataFrame(ydf)[["year", "total_income", "total_expense",
                                   "total_investment", "avg_monthly_expense", "savings_rate"]]
        rows.columns = ["Year", "Income", "Expense", "Investment", "Avg Monthly Exp", "Savings Rate %"]
        rows["Year"] = rows["Year"].astype(str)
        st.dataframe(rows, use_container_width=True)
