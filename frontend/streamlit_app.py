import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import requests
import streamlit as st

from api import api_dashboard
from config import API_BASE, COLORS, GLOBAL_CSS
from sidebar import render_sidebar
from tabs.alerts import render_alerts
from tabs.compare import render_compare
from tabs.data import render_data
from tabs.overview import render_overview
from tabs.trends import render_trends

st.set_page_config(page_title="Finsight", page_icon="₹", layout="wide",
                   initial_sidebar_state="collapsed")
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

DEFAULTS = {
    "overview_month":    None,
    "date_range":        "12m",
    "compare_month":     None,
    "compare_baseline":  "12m_avg",
    "trend_granularity": "monthly",
    "trend_mode":        "system",
    "trend_metric":      "total_expense",
    "trend_category":    None,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

render_sidebar()

dashboard = api_dashboard()

if dashboard is None:
    try:
        requests.get(f"{API_BASE}/health", timeout=2)
    except Exception:
        st.markdown(f"""
        <div style="background:{COLORS['bg_card']};border:1px solid #2e1a1a;border-radius:10px;
                    padding:16px 20px;margin-bottom:16px">
          <span style="color:{COLORS['red']};font-size:13px">
            ⚠ Backend offline — start with:
            <code style="background:{COLORS['bg_elevated']};padding:2px 6px;border-radius:4px">
              cd backend &amp;&amp; uvicorn main:app
            </code>
          </span>
        </div>
        """, unsafe_allow_html=True)

tabs = st.tabs(["▣  Overview", "⟺  Compare", "↗  Trends", "⚠  Alerts", "⊞  Data"])
with tabs[0]: render_overview(dashboard)
with tabs[1]: render_compare(dashboard)
with tabs[2]: render_trends(dashboard)
with tabs[3]: render_alerts(dashboard)
with tabs[4]: render_data()
