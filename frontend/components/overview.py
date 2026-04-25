import streamlit as st


def render_overview(data: dict) -> None:
    st.header("Overview")

    monthly = data.get("monthly_aggregates", [])
    if not monthly:
        st.info("No data yet. Upload a transaction file to get started.")
        return

    # Use the latest month for headline metrics
    latest = sorted(monthly, key=lambda x: x["month"])[-1]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Income", f"₹{latest['total_income']:,.0f}")
    col2.metric("Expenses", f"₹{latest['total_expense']:,.0f}")
    col3.metric("Investments", f"₹{latest['total_investment']:,.0f}")
    col4.metric(
        "Savings Rate",
        f"{latest['savings_rate']:.1f}%",
        delta=f"₹{latest['net_savings']:,.0f} net",
    )
    st.caption(f"Latest month: **{latest['month']}**")
