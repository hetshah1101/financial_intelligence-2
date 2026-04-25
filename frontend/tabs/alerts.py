import pandas as pd
import streamlit as st

from analytics import classify_anomalies
from config import COLORS
from formatters import fmt_inr, fmt_month


def render_alerts(dashboard: dict | None) -> None:
    if not dashboard:
        _empty()
        return

    anomalies = classify_anomalies(dashboard)

    if not anomalies:
        st.markdown(f"""
        <div style="background:{COLORS['bg_card']};border:1px solid #1f2e1f;border-radius:10px;
                    padding:24px;text-align:center;color:{COLORS['green']}">
          ✓ &nbsp; All clear — no anomalies detected this period
        </div>
        """, unsafe_allow_html=True)
    else:
        border_colors = {
            "spike":    COLORS["red"],
            "variance": COLORS["amber"],
            "new_cat":  COLORS["blue"],
            "savings":  COLORS["purple"],
        }
        for anomaly in anomalies:
            excess = anomaly["current_month_amount"] - anomaly["three_month_avg"]
            ratio_display = f"{anomaly['ratio']:.1f}×" if anomaly["ratio"] > 0 else "N/A"
            border = border_colors.get(anomaly["alert_type"], COLORS["amber"])
            month_label = fmt_month(anomaly["month"]) if anomaly.get("month") else ""
            title = f"⚠  {anomaly['category']}"
            if month_label:
                title += f" · {month_label}"
            title += f" — {ratio_display} above average"
            with st.expander(title, expanded=False):
                c1, c2, c3 = st.columns(3)
                c1.metric("This Month",   fmt_inr(anomaly["current_month_amount"]))
                c2.metric("3-Month Avg",  fmt_inr(anomaly["three_month_avg"]))
                c3.metric("Excess Spend", fmt_inr(max(0.0, excess)),
                          delta=f"+{ratio_display}")
                if anomaly.get("reason"):
                    st.caption(anomaly["reason"])

    st.markdown("---")
    st.markdown(f"""
    <div style="font-size:11px;letter-spacing:.1em;color:{COLORS['text_tertiary']};
                text-transform:uppercase;margin-bottom:12px;margin-top:4px">
      Savings Opportunities
    </div>
    """, unsafe_allow_html=True)

    savings_opps = sorted(
        dashboard.get("savings_opportunities", []),
        key=lambda x: -x["potential_savings"],
    )
    if savings_opps:
        rows = [
            {
                "Category":          o["category"],
                "Current":           fmt_inr(o["current_month_amount"]),
                "Baseline (3m avg)": fmt_inr(o["median_3m"]),
                "Could Save":        fmt_inr(o["potential_savings"]),
            }
            for o in savings_opps
        ]
        df_opp = pd.DataFrame(rows)

        def _green(_val):
            return f"color: {COLORS['green']}"

        try:
            styled = df_opp.style.map(_green, subset=["Could Save"])
        except AttributeError:
            styled = df_opp.style.applymap(_green, subset=["Could Save"])
        st.dataframe(styled, use_container_width=True, hide_index=True)
    else:
        st.markdown(
            f'<div style="color:{COLORS["text_tertiary"]};font-size:13px;padding:12px">'
            "No savings opportunities identified.</div>",
            unsafe_allow_html=True,
        )


def _empty() -> None:
    st.markdown(f"""
    <div style="background:{COLORS['bg_card']};border:1px solid {COLORS['border']};
                border-radius:10px;padding:24px;text-align:center;color:{COLORS['text_secondary']}">
      No data available.
    </div>
    """, unsafe_allow_html=True)
