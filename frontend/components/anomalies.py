import streamlit as st
import pandas as pd


def render_anomalies(data: dict) -> None:
    st.header("Anomalies & Erratic Spend")

    total_anomalies = data.get("anomalies_total_spend", [])
    cat_anomalies = data.get("anomalies_category", [])
    erratic = data.get("anomalies_erratic", [])

    total_count = len(total_anomalies) + len(cat_anomalies) + len(erratic)
    if total_count == 0:
        st.success("No anomalies detected. Your spending looks stable!")
        return

    st.warning(f"{total_count} anomaly / erratic-spend events detected.")

    if total_anomalies:
        st.subheader("Total Spend Anomalies")
        st.caption("Months where total expense exceeded 1.4× the 3-month average.")
        df = pd.DataFrame(total_anomalies)[["month", "reason", "amount", "threshold"]]
        df.columns = ["Month", "Reason", "Amount (₹)", "Threshold (₹)"]
        st.dataframe(df, use_container_width=True)

    if cat_anomalies:
        st.subheader("Category Anomalies")
        st.caption("Categories where spend exceeded 1.5× the 3-month average.")
        df = pd.DataFrame(cat_anomalies)[["month", "category", "reason", "amount", "threshold"]]
        df.columns = ["Month", "Category", "Reason", "Amount (₹)", "Threshold (₹)"]
        st.dataframe(df, use_container_width=True)

    if erratic:
        st.subheader("Erratic Spend Events")
        st.caption("High variance, sudden spikes, or large first-time category spend.")
        rows = []
        for e in erratic:
            rows.append({
                "Month": e.get("month", ""),
                "Category": e.get("category", "—"),
                "Reason": e.get("reason", ""),
                "Amount (₹)": e.get("amount", ""),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
