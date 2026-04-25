import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


def render_category_breakdown(data: dict) -> None:
    st.header("Category Breakdown")

    cat_data = data.get("category_aggregates", [])
    if not cat_data:
        st.info("No category data available.")
        return

    df = pd.DataFrame(cat_data)
    months = sorted(df["month"].unique(), reverse=True)
    selected_month = st.selectbox("Select Month", months, key="cat_month")

    mdf = df[df["month"] == selected_month].sort_values("total_amount", ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        fig_pie = px.pie(
            mdf, values="total_amount", names="category",
            title=f"Expense Distribution — {selected_month}",
            color_discrete_sequence=px.colors.qualitative.Set3,
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        fig_bar = px.bar(
            mdf, x="total_amount", y="category", orientation="h",
            title=f"Category Spend — {selected_month}",
            color="tag",
            color_discrete_map={
                "essential": "#2ecc71",
                "discretionary": "#e74c3c",
                "uncategorized": "#95a5a6",
            },
            labels={"total_amount": "Amount (₹)", "category": ""},
        )
        fig_bar.update_layout(height=400, showlegend=True)
        st.plotly_chart(fig_bar, use_container_width=True)

    # Detail table
    with st.expander("View Category Detail Table"):
        display = mdf[["category", "tag", "total_amount", "percentage_of_total_expense"]].copy()
        display.columns = ["Category", "Tag", "Amount (₹)", "% of Total Expense"]
        st.dataframe(display, use_container_width=True)
