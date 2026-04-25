import streamlit as st
import plotly.graph_objects as go
import pandas as pd


def render_monthly_trends(data: dict) -> None:
    st.header("Monthly Trends")

    trends = data.get("monthly_trends", [])
    if not trends:
        st.info("No monthly trend data available.")
        return

    df = pd.DataFrame(trends).sort_values("month")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["month"], y=df["income"], name="Income",
                             mode="lines+markers", line=dict(color="#2ecc71", width=2)))
    fig.add_trace(go.Scatter(x=df["month"], y=df["expense"], name="Expense",
                             mode="lines+markers", line=dict(color="#e74c3c", width=2)))
    fig.add_trace(go.Scatter(x=df["month"], y=df["investment"], name="Investment",
                             mode="lines+markers", line=dict(color="#3498db", width=2)))
    if "rolling_3m_expense" in df.columns:
        fig.add_trace(go.Scatter(x=df["month"], y=df["rolling_3m_expense"],
                                 name="3M Avg Expense", mode="lines",
                                 line=dict(color="#e74c3c", width=1, dash="dash")))

    fig.update_layout(
        xaxis_title="Month", yaxis_title="Amount (₹)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        hovermode="x unified", height=420,
    )
    st.plotly_chart(fig, use_container_width=True)

    # MoM change table
    mom_cols = ["month", "mom_income_change", "mom_expense_change"]
    available = [c for c in mom_cols if c in df.columns]
    if len(available) > 1:
        with st.expander("Month-over-Month Changes (%)"):
            display = df[available].dropna().copy()
            display.columns = ["Month", "Income MoM %", "Expense MoM %"][: len(available)]
            st.dataframe(display, use_container_width=True)
