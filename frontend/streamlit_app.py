# frontend/streamlit_app.py - Personal Financial Intelligence Dashboard

import os
import requests
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

st.set_page_config(
    page_title="Financial Intelligence",
    page_icon="₹",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }
    h1, h2, h3 {
        font-family: 'DM Serif Display', serif;
    }
    .metric-card {
        background: linear-gradient(135deg, #1a1f36 0%, #16213e 100%);
        border: 1px solid rgba(99, 179, 237, 0.2);
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 8px;
    }
    .metric-label {
        color: #a0aec0;
        font-size: 0.75rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 4px;
    }
    .metric-value {
        color: #e2e8f0;
        font-size: 1.8rem;
        font-weight: 600;
    }
    .metric-delta-pos { color: #68d391; font-size: 0.85rem; }
    .metric-delta-neg { color: #fc8181; font-size: 0.85rem; }
    .anomaly-card {
        background: rgba(252, 129, 74, 0.1);
        border-left: 3px solid #fc814a;
        border-radius: 6px;
        padding: 12px 16px;
        margin-bottom: 8px;
    }
    .insight-box {
        background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
        border-radius: 12px;
        padding: 24px;
        color: #e2e8f0;
        line-height: 1.7;
        font-size: 0.95rem;
    }
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 500;
    }
    .upload-section {
        background: rgba(99, 179, 237, 0.05);
        border: 1px dashed rgba(99, 179, 237, 0.3);
        border-radius: 12px;
        padding: 24px;
    }
</style>
""", unsafe_allow_html=True)


# ── Helpers ──────────────────────────────────────────────────────────────────

def fmt_inr(val: float) -> str:
    """Format number as Indian currency."""
    if abs(val) >= 1_00_000:
        return f"₹{val/1_00_000:.1f}L"
    elif abs(val) >= 1_000:
        return f"₹{val/1_000:.1f}K"
    return f"₹{val:.0f}"


def api_get(endpoint: str) -> dict | None:
    try:
        r = requests.get(f"{API_BASE}{endpoint}", timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to backend. Ensure the FastAPI server is running on port 8000.")
        return None
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            return None
        st.error(f"API error: {e}")
        return None


def api_upload(endpoint: str, file_bytes: bytes, filename: str) -> dict | None:
    try:
        r = requests.post(
            f"{API_BASE}{endpoint}",
            files={"file": (filename, file_bytes, "text/csv")},
            timeout=300,
        )
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        st.error(f"Upload failed: {e.response.text}")
        return None
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to backend.")
        return None


# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ₹ Financial Intelligence")
    st.markdown("---")

    st.markdown("### 📤 Upload Data")

    tab_upload, tab_update = st.tabs(["Initial Load", "Monthly Update"])

    with tab_upload:
        st.markdown('<div class="upload-section">', unsafe_allow_html=True)
        uploaded = st.file_uploader(
            "Upload full dataset (CSV/Excel)",
            type=["csv", "xlsx"],
            key="initial_upload",
        )
        if st.button("🚀 Load Dataset", key="btn_initial") and uploaded:
            with st.spinner("Processing..."):
                result = api_upload("/upload", uploaded.read(), uploaded.name)
                if result:
                    st.success(result["message"])
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with tab_update:
        st.markdown('<div class="upload-section">', unsafe_allow_html=True)
        updated = st.file_uploader(
            "Upload new month data",
            type=["csv", "xlsx"],
            key="monthly_update",
        )
        if st.button("🔄 Update Data", key="btn_update") and updated:
            with st.spinner("Updating..."):
                result = api_upload("/update", updated.read(), updated.name)
                if result:
                    st.success(result["message"])
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    # Month selector
    months_data = api_get("/months")
    available_months = months_data["months"] if months_data else []
    selected_month = None
    if available_months:
        selected_month = st.selectbox(
            "📅 Select Month",
            available_months,
            index=0,
        )

    st.markdown("---")
    st.markdown("**Backend:** `localhost:8000`")
    st.markdown("**AI:** Ollama / OpenAI")
    health = api_get("/health")
    if health:
        st.success("✅ API Connected")
    else:
        st.error("❌ API Offline")


# ── Main Content ──────────────────────────────────────────────────────────────

st.markdown("# Personal Financial Intelligence")
st.markdown("*AI-powered cashflow analysis & actionable insights*")
st.markdown("---")

dashboard = api_get("/dashboard")

if not dashboard:
    st.info("👋 Welcome! Upload a dataset using the sidebar to get started.")
    st.markdown("""
    **Expected CSV columns:**
    | date | account | category | subcategory | description | amount | type |
    |------|---------|----------|-------------|-------------|--------|------|
    
    `type` must be one of: `income`, `expense`, `investment`
    """)
    st.stop()


# ── Overview Metrics ──────────────────────────────────────────────────────────

latest = dashboard.get("latest_month", {})
mom    = dashboard.get("mom_change", {})
rolling = dashboard.get("rolling_averages", {})

st.markdown("## 📊 Overview")

col1, col2, col3, col4, col5 = st.columns(5)
metrics = [
    ("Income",      latest.get("total_income", 0),     mom.get("income_change_pct",     0)),
    ("Expenses",    latest.get("total_expense", 0),    mom.get("expense_change_pct",    0)),
    ("Investments", latest.get("total_investment", 0), mom.get("investment_change_pct", 0)),
    ("Net Savings", latest.get("net_savings", 0),      mom.get("savings_change_pct",    0)),
    ("Savings Rate",f"{latest.get('savings_rate', 0):.1f}%", None),
]

for col, (label, value, delta) in zip([col1, col2, col3, col4, col5], metrics):
    with col:
        val_str = value if isinstance(value, str) else fmt_inr(value)
        delta_html = ""
        if delta is not None:
            arrow = "▲" if delta >= 0 else "▼"
            cls   = "metric-delta-pos" if delta >= 0 else "metric-delta-neg"
            delta_html = f'<div class="{cls}">{arrow} {abs(delta):.1f}% MoM</div>'

        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{val_str}</div>
            {delta_html}
        </div>
        """, unsafe_allow_html=True)


# ── Trends ────────────────────────────────────────────────────────────────────

st.markdown("## 📈 Trends")

all_monthly = dashboard.get("all_monthly", [])
if len(all_monthly) >= 2:
    df_monthly = pd.DataFrame(all_monthly)

    col_left, col_right = st.columns([3, 2])

    with col_left:
        fig = go.Figure()
        colors = {"total_income": "#68d391", "total_expense": "#fc8181", "total_investment": "#76e4f7", "net_savings": "#f6e05e"}
        labels = {"total_income": "Income", "total_expense": "Expenses", "total_investment": "Investments", "net_savings": "Net Savings"}

        for col_name, color in colors.items():
            fig.add_trace(go.Scatter(
                x=df_monthly["month"],
                y=df_monthly[col_name],
                name=labels[col_name],
                line=dict(color=color, width=2),
                mode="lines+markers",
                marker=dict(size=5),
            ))

        fig.update_layout(
            title="Monthly Cashflow Trends",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#a0aec0"),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
            xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.05)", tickprefix="₹"),
            height=320,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=df_monthly["month"],
            y=df_monthly["savings_rate"],
            marker_color=["#68d391" if v >= 20 else "#f6e05e" if v >= 10 else "#fc8181"
                          for v in df_monthly["savings_rate"]],
            name="Savings Rate %",
        ))
        fig2.update_layout(
            title="Savings Rate %",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#a0aec0"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.05)", ticksuffix="%"),
            xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
            height=320,
        )
        st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("Upload at least 2 months of data to see trends.")


# ── Category Breakdown ────────────────────────────────────────────────────────

st.markdown("## 🗂️ Category Breakdown")

categories = dashboard.get("latest_categories", [])
if categories:
    df_cat = pd.DataFrame(categories)

    col_pie, col_bar = st.columns([1, 2])

    with col_pie:
        fig_pie = px.pie(
            df_cat,
            values="total_amount",
            names="category",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set3,
        )
        fig_pie.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#a0aec0"),
            showlegend=True,
            height=320,
            title=f"Expenses — {latest.get('month', '')}",
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_bar:
        fig_bar = px.bar(
            df_cat.sort_values("total_amount", ascending=True),
            x="total_amount",
            y="category",
            orientation="h",
            color="percentage_of_total",
            color_continuous_scale="Blues",
            labels={"total_amount": "Amount (₹)", "percentage_of_total": "% of Total"},
            title="Category Spend",
        )
        fig_bar.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#a0aec0"),
            xaxis=dict(gridcolor="rgba(255,255,255,0.05)", tickprefix="₹"),
            height=320,
        )
        st.plotly_chart(fig_bar, use_container_width=True)


# ── Anomalies ─────────────────────────────────────────────────────────────────

st.markdown("## 🚨 Anomalies")

anomalies = dashboard.get("anomalies", [])
if anomalies:
    cols = st.columns(min(len(anomalies), 3))
    for i, anomaly in enumerate(anomalies[:6]):
        with cols[i % 3]:
            excess = anomaly["current_month_amount"] - anomaly["three_month_avg"]
            st.markdown(f"""
            <div class="anomaly-card">
                <strong>⚠️ {anomaly['category']}</strong><br>
                <span style="color:#a0aec0;">This month:</span> <strong>{fmt_inr(anomaly['current_month_amount'])}</strong><br>
                <span style="color:#a0aec0;">3-month avg:</span> {fmt_inr(anomaly['three_month_avg'])}<br>
                <span style="color:#fc8181;">+{fmt_inr(excess)} ({anomaly['ratio']:.1f}×)</span>
            </div>
            """, unsafe_allow_html=True)
else:
    st.success("✅ No spending anomalies detected this month.")


# ── Savings Opportunities ─────────────────────────────────────────────────────

st.markdown("## 💡 Savings Opportunities")

savings_ops = dashboard.get("savings_opportunities", [])
if savings_ops:
    df_sav = pd.DataFrame(savings_ops)
    df_sav["current"] = df_sav["current"].apply(fmt_inr)
    df_sav["potential_savings"] = df_sav["potential_savings"].apply(fmt_inr)
    df_sav.columns = ["Category", "Current Spend", "Optimal Range", "Potential Savings"]
    st.dataframe(df_sav, use_container_width=True, hide_index=True)
else:
    st.success("✅ Your spending is within optimal ranges this month.")


# ── AI Insights ───────────────────────────────────────────────────────────────

st.markdown("## 🤖 AI Insights")

if selected_month:
    col_insight_header, col_refresh = st.columns([4, 1])
    with col_refresh:
        refresh = st.button("🔄 Regenerate", key="refresh_insights")

    refresh_param = "?refresh=true" if refresh else ""
    insight_data = api_get(f"/insights/{selected_month}{refresh_param}")

    if insight_data and insight_data.get("insights"):
        source_badge = "🤖 AI Generated" if insight_data.get("source") == "generated" else "💾 Cached"
        st.caption(f"{source_badge} — {selected_month}")
        st.markdown(
            f'<div class="insight-box">{insight_data["insights"].replace(chr(10), "<br>")}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.warning("No insights available. Ensure Ollama is running or configure an OpenAI API key.")
else:
    st.info("Select a month from the sidebar to view AI insights.")


# ── Footer ────────────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#4a5568;font-size:0.8rem;'>"
    "Personal Financial Intelligence System • Powered by Llama 3 via Ollama"
    "</div>",
    unsafe_allow_html=True,
)
