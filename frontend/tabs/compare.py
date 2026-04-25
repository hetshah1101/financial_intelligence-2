import pandas as pd
import streamlit as st

from analytics import build_baseline_cats, build_category_diffs, compute_baseline
from api import api_months
from charts import make_category_bar
from config import COLORS
from formatters import fmt_inr, fmt_month, fmt_pct


BASELINE_OPTIONS = {
    "Last Month":       "last_month",
    "Recent Avg (3m)":  "recent_avg",
    "Long-term (6m)":   "longterm_avg",
    "12-Month Avg":     "12m_avg",
    "All Time Avg":     "all_time",
}


def render_compare(dashboard: dict | None) -> None:
    if not dashboard:
        st.info("No data available.")
        return

    monthly = sorted(dashboard.get("monthly_aggregates", []), key=lambda x: x["month"])
    all_cat_agg = dashboard.get("category_aggregates", [])
    latest = monthly[-1] if monthly else {}

    months_list = api_months()

    col_month, col_baseline = st.columns([3, 5])

    with col_month:
        if months_list:
            month_display = {fmt_month(m): m for m in months_list}
            sel_disp = st.selectbox(
                "Month",
                list(month_display.keys()),
                index=0,
                key="compare_month_sel",
            )
            selected_month = month_display[sel_disp]
        else:
            selected_month = latest.get("month", "")
            st.markdown(f"**Month:** {fmt_month(selected_month)}")
        st.session_state["compare_month"] = selected_month

    with col_baseline:
        baseline_label = st.radio(
            "Compare against",
            list(BASELINE_OPTIONS.keys()),
            index=3,  # default: 12-Month Avg
            horizontal=True,
            key="compare_baseline_radio",
        )
        baseline_type = BASELINE_OPTIONS[baseline_label]
        st.session_state["compare_baseline"] = baseline_type

    # ── Resolve data ──────────────────────────────────────────────────────────
    sel_month_data = next(
        (m for m in monthly if m["month"] == selected_month), latest
    )
    current_cats = {
        c["category"]: c["total_amount"]
        for c in all_cat_agg if c["month"] == selected_month
    }

    sel_idx = next(
        (i for i, m in enumerate(monthly) if m["month"] == selected_month),
        len(monthly) - 1,
    )
    history_all = monthly[:sel_idx]
    window_sizes = {
        "last_month":   1,
        "recent_avg":   3,
        "longterm_avg": 6,
        "12m_avg":      12,
        "all_time":     999,
    }
    n = window_sizes.get(baseline_type, 12)
    history_window = history_all[-n:] if n < 999 else history_all

    baseline_months_set = {m["month"] for m in history_window}
    baseline_cats = build_baseline_cats(all_cat_agg, baseline_months_set)
    baseline_agg = compute_baseline(monthly[:sel_idx + 1], baseline_type)

    # ── Category diffs ────────────────────────────────────────────────────────
    cat_diffs = build_category_diffs(current_cats, baseline_cats)

    # ── Delta KPI section ─────────────────────────────────────────────────────
    if baseline_agg and baseline_agg["total_expense"] > 0:
        d_exp_pct = (
            (sel_month_data.get("total_expense", 0) - baseline_agg["total_expense"])
            / baseline_agg["total_expense"] * 100
        )
        increases = sorted(
            [d for d in cat_diffs if d["diff"] > 0], key=lambda x: x["diff"], reverse=True
        )[:3]
        savings = sorted(
            [d for d in cat_diffs if d["diff"] < 0], key=lambda x: x["diff"]
        )[:3]

        col_total, col_inc, col_sav = st.columns([2, 3, 3])

        card_style = (
            f"background:{COLORS['bg_card']};border:1px solid {COLORS['border']};"
            f"border-radius:10px;padding:20px 24px;min-height:180px"
        )
        row_style = (
            f"display:flex;justify-content:space-between;align-items:center;"
            f"margin-bottom:10px;padding-bottom:10px;border-bottom:1px solid {COLORS['border_subtle']}"
        )

        with col_total:
            d_color = COLORS["red"] if d_exp_pct > 0 else COLORS["green"]
            arrow = "↑" if d_exp_pct > 0 else "↓"
            st.markdown(
                f"<div style=\"{card_style}\">"
                f"<div style=\"font-size:11px;letter-spacing:.1em;text-transform:uppercase;"
                f"color:{COLORS['text_tertiary']};margin-bottom:10px\">Total Expense</div>"
                f"<div style=\"font-size:24px;font-family:'DM Mono',monospace;"
                f"color:{COLORS['text_primary']};margin-bottom:8px\">"
                f"{fmt_inr(sel_month_data.get('total_expense', 0))}</div>"
                f"<div style=\"font-size:12px;color:{d_color}\">"
                f"{arrow} {abs(d_exp_pct):.1f}%"
                f"<span style=\"color:{COLORS['text_tertiary']}\"> vs baseline</span>"
                f"</div></div>",
                unsafe_allow_html=True,
            )

        with col_inc:
            rows_html = "".join(
                f"<div style=\"{row_style}\">"
                f"<span style=\"color:{COLORS['text_primary']};font-size:13px\">{d['category']}</span>"
                f"<span style=\"color:{COLORS['red']};font-family:monospace;font-size:13px\">"
                f"+{fmt_inr(d['diff'], compact=True)}"
                f"<span style=\"color:{COLORS['text_tertiary']};font-size:11px\">"
                f"&nbsp;(+{d['pct_change']:.0f}%)</span></span></div>"
                for d in increases
            )
            no_data = (
                f"<div style=\"color:{COLORS['text_tertiary']};font-size:13px;padding:8px 0\">"
                f"No increases vs baseline</div>"
            ) if not increases else ""
            st.markdown(
                f"<div style=\"{card_style}\">"
                f"<div style=\"font-size:10px;letter-spacing:.1em;text-transform:uppercase;"
                f"color:{COLORS['text_tertiary']};margin-bottom:14px\">Top 3 Increases</div>"
                f"{rows_html or no_data}</div>",
                unsafe_allow_html=True,
            )

        with col_sav:
            rows_html = "".join(
                f"<div style=\"{row_style}\">"
                f"<span style=\"color:{COLORS['text_primary']};font-size:13px\">{d['category']}</span>"
                f"<span style=\"color:{COLORS['green']};font-family:monospace;font-size:13px\">"
                f"{fmt_inr(d['diff'], compact=True)}"
                f"<span style=\"color:{COLORS['text_tertiary']};font-size:11px\">"
                f"&nbsp;({d['pct_change']:.0f}%)</span></span></div>"
                for d in savings
            )
            no_data = (
                f"<div style=\"color:{COLORS['text_tertiary']};font-size:13px;padding:8px 0\">"
                f"No savings vs baseline</div>"
            ) if not savings else ""
            st.markdown(
                f"<div style=\"{card_style}\">"
                f"<div style=\"font-size:10px;letter-spacing:.1em;text-transform:uppercase;"
                f"color:{COLORS['text_tertiary']};margin-bottom:14px\">Top 3 Savings</div>"
                f"{rows_html or no_data}</div>",
                unsafe_allow_html=True,
            )

    # ── Grouped bar chart ─────────────────────────────────────────────────────
    top10 = sorted(cat_diffs, key=lambda x: -x["current"])[:10]
    if top10:
        cats      = [d["category"] for d in top10]
        curr_vals = [d["current"]  for d in top10]
        base_vals = [d["baseline"] for d in top10]
        fig = make_category_bar(cats, curr_vals, base_vals, fmt_month(selected_month))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ── Comparison table ──────────────────────────────────────────────────────
    if cat_diffs:
        rows = [
            {
                "Category": d["category"],
                "Current":  fmt_inr(d["current"]),
                "Baseline": fmt_inr(d["baseline"]),
                "Diff":     fmt_inr(d["diff"]),
                "% Change": round(d["pct_change"], 1),
            }
            for d in sorted(cat_diffs, key=lambda x: -abs(x["diff"]))
        ]
        df_compare = pd.DataFrame(rows)

        def _color_pct(val):
            try:
                v = float(val)
                if v > 0:
                    return f"color: {COLORS['red']}"
                elif v < 0:
                    return f"color: {COLORS['green']}"
            except (ValueError, TypeError):
                pass
            return f"color: {COLORS['text_secondary']}"

        try:
            styled = df_compare.style.map(_color_pct, subset=["% Change"])
        except AttributeError:
            styled = df_compare.style.applymap(_color_pct, subset=["% Change"])
        st.dataframe(styled, use_container_width=True, hide_index=True)
