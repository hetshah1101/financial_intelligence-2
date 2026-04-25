import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd


def render_tag_analysis(data: dict) -> None:
    st.header("Tag Analysis — Essential vs Discretionary")

    behavior = data.get("spending_behavior")
    if not behavior:
        st.info("No behavior data available.")
        return

    # Donut chart
    labels = ["Essential", "Discretionary", "Uncategorized"]
    values = [
        behavior["essential_pct"],
        behavior["discretionary_pct"],
        behavior["uncategorized_pct"],
    ]
    colors = ["#2ecc71", "#e74c3c", "#95a5a6"]

    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.55,
        marker_colors=colors,
        textinfo="label+percent",
    ))
    fig.update_layout(title="Spending Composition", height=380)

    col1, col2 = st.columns([1, 1])
    with col1:
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Spending Behavior Metrics")
        st.metric("Essential Spending", f"{behavior['essential_pct']:.1f}%")
        st.metric("Discretionary Spending", f"{behavior['discretionary_pct']:.1f}%")
        st.metric("Top 3 Category Concentration", f"{behavior['top3_concentration_pct']:.1f}%")

        st.subheader("Top 5 Categories")
        top5 = behavior.get("top_5_categories", [])
        if top5:
            top_df = pd.DataFrame(top5)
            top_df.columns = ["Category", "Total Amount (₹)", "% of Total"]
            st.dataframe(top_df, use_container_width=True)

    # Monthly tag trend
    cat_data = data.get("category_aggregates", [])
    if cat_data:
        df = pd.DataFrame(cat_data)
        tag_month = df.groupby(["month", "tag"])["total_amount"].sum().reset_index()
        fig2 = px.area(
            tag_month.sort_values("month"), x="month", y="total_amount",
            color="tag",
            color_discrete_map={
                "essential": "#2ecc71",
                "discretionary": "#e74c3c",
                "uncategorized": "#95a5a6",
            },
            title="Monthly Essential vs Discretionary Spend",
            labels={"total_amount": "Amount (₹)", "month": "Month"},
        )
        st.plotly_chart(fig2, use_container_width=True)
