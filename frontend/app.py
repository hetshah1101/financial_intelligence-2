"""
Personal Financial Analytics Dashboard — Redesigned

UX Principles Applied Throughout:
1. Visual Hierarchy: Critical info prominent, secondary info subdued
2. Progressive Disclosure: Summary first, details in expanders
3. Cognitive Load: Chunked information (7±2 items per section)
4. Pre-attentive Processing: Color conveys meaning instantly
5. Consistency: Uniform spacing, typography, interactions
6. Contextual Explanation: Every component has title + purpose

Research Backing:
- Cognitive Load Theory (Sweller): Reduces extraneous load via chunking
- Gestalt Principles: Proximity, similarity for grouping
- Nielsen Norman Group UX Heuristics: Visibility, system status
- Tufte's Data-ink Ratio: Remove clutter, emphasize data
- Few's Perceptual Edge: Color, size, position for instant understanding
"""
import streamlit as st
import requests
import pandas as pd
from datetime import datetime

from components.key_takeaways import render_key_takeaways
from insights_engine import derive_insights
from components.overview import render_overview
from components.monthly_trends import render_monthly_trends
from components.yearly_trends import render_yearly_trends
from components.category_breakdown import render_category_breakdown
from components.tag_analysis import render_tag_analysis
from components.anomalies import render_anomalies
from components.savings import render_savings
from components.comparison import render_comparison

API_BASE = "http://localhost:8000"

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Personal Financial Analytics",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better visual hierarchy and spacing
# (Visual Hierarchy principle + Consistency)
st.markdown("""
<style>
    /* Section spacing (Gestalt: Proximity for grouping) */
    .section-divider { margin: 32px 0 24px 0; }

    /* Metric card styling (Pre-attentive processing) */
    .metric-card {
        padding: 16px;
        border-radius: 8px;
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-left: 4px solid #3498db;
    }

    /* Text hierarchy (Nielsen: Clear labeling) */
    .metric-label { font-size: 12px; color: #7f8c8d; font-weight: 600; }
    .metric-value { font-size: 28px; font-weight: 700; color: #2c3e50; }
    .metric-context { font-size: 13px; color: #95a5a6; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR: CLEAN UPLOAD INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 💰 Financial Dashboard")
    st.markdown("Your personal financial analytics engine")
    st.divider()

    # Upload section (Progressive disclosure)
    with st.expander("📤 Upload Financial Data", expanded=False):
        upload_type = st.radio(
            "Upload Mode",
            ["Initial Upload", "Incremental Update"],
            help="Initial: Load new dataset. Incremental: Add new transactions."
        )
        uploaded_file = st.file_uploader(
            "Choose CSV or Excel file",
            type=["csv", "xlsx", "xls"],
            help="Required columns: Date, Account, Category, Amount, Type"
        )

        if uploaded_file and st.button("🔄 Process File", type="primary", use_container_width=True):
            endpoint = "/upload" if upload_type == "Initial Upload" else "/update"
            with st.spinner("Processing transactions..."):
                try:
                    resp = requests.post(
                        f"{API_BASE}{endpoint}",
                        files={"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)},
                        timeout=60,
                    )
                    if resp.status_code == 200:
                        result = resp.json()
                        st.success(f"✓ {result['message']}")
                        st.rerun()
                    else:
                        st.error(f"Error: {resp.json().get('detail', 'Upload failed')}")
                except requests.exceptions.ConnectionError:
                    st.error("❌ Backend not running. Start with: `cd backend && uvicorn main:app`")

    st.divider()
    st.caption("**System Status:**\nBackend: FastAPI + SQLite\nAnalytics: Pandas + NumPy\nFrontend: Streamlit")

# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=10)
def load_dashboard():
    """Load analytics data from backend API"""
    try:
        resp = requests.get(f"{API_BASE}/dashboard", timeout=30)
        if resp.status_code == 200:
            return resp.json(), None
        return None, f"API error {resp.status_code}"
    except requests.exceptions.ConnectionError:
        return None, "❌ Backend API not accessible on port 8000"


data, error = load_dashboard()

if error:
    st.error(error)
    st.info("**To start:**\n1. Open terminal in `backend/` directory\n2. Run: `uvicorn main:app --port 8000`\n3. Reload this page")
    st.stop()

if not data or not data.get("monthly_aggregates"):
    st.title("💰 Personal Financial Analytics")
    st.info("**No transaction data loaded yet.**")
    st.markdown("""
    ### Getting Started
    1. Prepare your financial data in CSV or Excel format
    2. Required columns: `Date`, `Account`, `Category`, `Amount (INR)`, `Type`
    3. Use the sidebar to upload your file

    #### Example Format
    | Date | Account | Category | Amount | Type |
    |------|---------|----------|--------|------|
    | 2024-01-15 | HDFC | Groceries | 1200 | Expense |
    | 2024-01-01 | HDFC | Salary | 95000 | Income |
    """)
    st.stop()

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE HEADER: FINANCIAL SNAPSHOT
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("## 📊 Your Financial Overview")

monthly = sorted(data.get("monthly_aggregates", []), key=lambda x: x["month"])
latest = monthly[-1]
date_range = f"{monthly[0]['month']} → {latest['month']}"

st.caption(f"Data span: **{date_range}** ({len(monthly)} months)")

# Financial Snapshot Cards
# (Visual Hierarchy + Pre-attentive processing: Green=income, Red=expense, Blue=investment)
metric_cols = st.columns(5)

with metric_cols[0]:
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #d5f4e6 0%, #2ecc71 100%); padding: 16px; border-radius: 8px; text-align: center; border-left: 4px solid #27ae60;">
        <p style="margin: 0; font-size: 11px; color: #1e8449; font-weight: 700;">INCOME</p>
        <p style="margin: 4px 0; font-size: 22px; font-weight: 700; color: #27ae60;">₹{latest['total_income']:,.0f}</p>
        <p style="margin: 0; font-size: 10px; color: #16a085;">This month</p>
    </div>
    """, unsafe_allow_html=True)

with metric_cols[1]:
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #fadbd8 0%, #e74c3c 100%); padding: 16px; border-radius: 8px; text-align: center; border-left: 4px solid #c0392b;">
        <p style="margin: 0; font-size: 11px; color: #922b21; font-weight: 700;">EXPENSE</p>
        <p style="margin: 4px 0; font-size: 22px; font-weight: 700; color: #e74c3c;">₹{latest['total_expense']:,.0f}</p>
        <p style="margin: 0; font-size: 10px; color: #c0392b;">This month</p>
    </div>
    """, unsafe_allow_html=True)

with metric_cols[2]:
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #d6eaf8 0%, #3498db 100%); padding: 16px; border-radius: 8px; text-align: center; border-left: 4px solid #2874a6;">
        <p style="margin: 0; font-size: 11px; color: #1b4f72; font-weight: 700;">INVESTMENT</p>
        <p style="margin: 4px 0; font-size: 22px; font-weight: 700; color: #3498db;">₹{latest['total_investment']:,.0f}</p>
        <p style="margin: 0; font-size: 10px; color: #2874a6;">This month</p>
    </div>
    """, unsafe_allow_html=True)

with metric_cols[3]:
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #d5f5e3 0%, #1abc9c 100%); padding: 16px; border-radius: 8px; text-align: center; border-left: 4px solid #0e6251;">
        <p style="margin: 0; font-size: 11px; color: #0e6251; font-weight: 700;">NET SAVINGS</p>
        <p style="margin: 4px 0; font-size: 22px; font-weight: 700; color: #16a085;">₹{latest['net_savings']:,.0f}</p>
        <p style="margin: 0; font-size: 10px; color: #0e6251;">Income − Expense − Investment</p>
    </div>
    """, unsafe_allow_html=True)

with metric_cols[4]:
    rate_color = "#2ecc71" if latest['savings_rate'] >= 20 else "#e74c3c" if latest['savings_rate'] < 10 else "#f39c12"
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #e8daef 0%, {rate_color} 100%); padding: 16px; border-radius: 8px; text-align: center; border-left: 4px solid {rate_color};">
        <p style="margin: 0; font-size: 11px; color: #4a235a; font-weight: 700;">SAVINGS RATE</p>
        <p style="margin: 4px 0; font-size: 22px; font-weight: 700; color: {rate_color};">{latest['savings_rate']:.1f}%</p>
        <p style="margin: 0; font-size: 10px; color: #7d3c98;">Goal: 20%+</p>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# KEY TAKEAWAYS: DERIVED INSIGHTS
# ═══════════════════════════════════════════════════════════════════════════════
insights = derive_insights(data)
if insights:
    render_key_takeaways(insights)

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN DASHBOARD TABS
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("## 📈 Detailed Analysis")

tabs = st.tabs([
    "📊 Trends",
    "🎯 Categories",
    "📌 Breakdown",
    "⚠️ Anomalies",
    "💡 Savings",
    "🔄 Comparison",
])

with tabs[0]:
    # Trends Tab: Monthly and Yearly analysis
    # (Information Architecture: Related content grouped + Progressive disclosure)
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.markdown("### Monthly Expense Trend")
        st.caption("Track month-over-month spending changes and 3-month moving average")
        render_monthly_trends(data)
    with col_t2:
        st.markdown("### Yearly Overview")
        st.caption("Year-over-year income and expense comparison")
        render_yearly_trends(data)

with tabs[1]:
    # Category Analysis: Essential vs Discretionary
    st.markdown("### Essential vs Discretionary Spending")
    st.caption("Understanding your spending composition helps identify optimization opportunities")
    render_tag_analysis(data)

with tabs[2]:
    # Category Breakdown: Pie and Bar charts
    st.markdown("### Category Distribution")
    st.caption("See where your money goes. Click 'View Detail Table' for granular breakdown")
    render_category_breakdown(data)

with tabs[3]:
    # Anomalies: Unusual spending events
    st.markdown("### Unusual Spending Events")
    st.caption("Anomalies help identify one-time expenses vs recurring patterns")
    render_anomalies(data)

with tabs[4]:
    # Savings Opportunities: Where to cut
    st.markdown("### Savings Opportunities")
    st.caption("Categories where you're spending above your 3-month average. Consider reverting to baseline.")
    render_savings(data)

with tabs[5]:
    # Comparison: Month vs Month
    st.markdown("### Spending Comparison")
    st.caption("Compare current month to previous or rolling average to spot trends")
    render_comparison(data)

# ═══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════════
st.divider()
st.caption(
    "**Personal Financial Analytics** — Data-driven insights, no AI. "
    "All calculations deterministic & reproducible. "
    f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
)
