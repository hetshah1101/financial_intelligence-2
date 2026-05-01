import streamlit as st

from analytics import (
    aggregate_by_granularity,
    aggregate_category_by_granularity,
    aggregate_account_by_granularity,
    aggregate_account_category_by_granularity,
    fmt_period_label,
)
from charts import make_trends_chart
from config import COLORS
from formatters import fmt_inr


METRIC_OPTIONS = {
    "Expenses":       "total_expense",
    "Income":         "total_income",
    "Savings":        "net_savings",
    "Savings Rate %": "savings_rate",
    "Investments":    "total_investment",
}

METRIC_COLORS = {
    "total_expense":    COLORS["red"],
    "total_income":     COLORS["green"],
    "net_savings":      COLORS["purple"],
    "savings_rate":     COLORS["amber"],
    "total_investment": COLORS["blue"],
}


def render_trends(dashboard: dict | None) -> None:
    if not dashboard:
        st.info("No data available.")
        return

    monthly = sorted(dashboard.get("monthly_aggregates", []), key=lambda x: x["month"])
    all_cat_agg = dashboard.get("category_aggregates", [])
    account_monthly = dashboard.get("account_monthly_aggregates", [])
    account_cat_agg = dashboard.get("account_category_aggregates", [])
    if not monthly:
        st.info("Upload data to see trends.")
        return

    # ── Controls (3 columns: Granularity | View | Metric-or-Category) ────────
    col_gran, col_mode, col_control = st.columns([2, 2, 3])

    with col_gran:
        granularity = st.radio(
            "Granularity",
            options=["monthly", "quarterly", "yearly"],
            format_func=lambda x: x.capitalize(),
            key="trend_granularity",
        )

    with col_mode:
        mode = st.radio(
            "View",
            options=["system", "category"],
            format_func=lambda x: "System" if x == "system" else "By Category",
            key="trend_mode",
        )

    all_trend_cats = sorted({c["category"] for c in all_cat_agg})

    with col_control:
        if mode == "system":
            metric_label = st.selectbox(
                "Metric",
                list(METRIC_OPTIONS.keys()),
                key="trend_metric_sel",
            )
            metric = METRIC_OPTIONS[metric_label]
            st.session_state["trend_metric"] = metric
            sel_cat = st.session_state.get("trend_category") or (
                all_trend_cats[0] if all_trend_cats else None
            )
        else:
            metric = st.session_state.get("trend_metric", "total_expense")
            if all_trend_cats:
                sel_cat = st.selectbox("Category", all_trend_cats, key="trend_category")
            else:
                sel_cat = None

    # ── Re-aggregate based on selected granularity ────────────────────────────
    # Metric → account schema field (net_savings is derived, no per-account split)
    _metric_to_acct_field = {
        "total_expense":    "expense",
        "total_income":     "income",
        "total_investment": "investment",
    }
    _acct_colors = {"Bank": COLORS["blue"], "Card": COLORS["amber"]}

    if mode == "system":
        aggregated = aggregate_by_granularity(monthly, granularity)
        periods = [r["period"] for r in aggregated]
        period_labels = [fmt_period_label(p, granularity) for p in periods]
        y_primary = [r.get(metric, 0) for r in aggregated]

        acct_field = _metric_to_acct_field.get(metric)
        acct_data = aggregate_account_by_granularity(account_monthly, granularity, acct_field) if acct_field else {}

        if len(acct_data) > 1:
            # Build one trace per account type, aligned to canonical periods
            traces = []
            for acct_type in sorted(acct_data.keys()):
                p_list, _, amt_list = acct_data[acct_type]
                p_map = dict(zip(p_list, amt_list))
                aligned = [p_map.get(p, 0) for p in periods]
                traces.append({
                    "y":    aligned,
                    "name": f"{acct_type} {metric_label}",
                    "color": _acct_colors.get(acct_type, COLORS["purple"]),
                })
        else:
            traces = [
                {
                    "y":     y_primary,
                    "name":  next(k for k, v in METRIC_OPTIONS.items() if v == metric),
                    "color": METRIC_COLORS.get(metric, COLORS["purple"]),
                }
            ]
    else:
        if sel_cat:
            all_months = [m["month"] for m in monthly]
            cat_periods, period_labels, amounts = aggregate_category_by_granularity(
                all_cat_agg, granularity, sel_cat, all_months=all_months
            )
            y_primary = amounts
            acct_cat_data = aggregate_account_category_by_granularity(
                account_cat_agg, granularity, sel_cat
            )
            if len(acct_cat_data) > 1:
                traces = []
                for acct_type in sorted(acct_cat_data.keys()):
                    p_list, _, amt_list = acct_cat_data[acct_type]
                    p_map = dict(zip(p_list, amt_list))
                    aligned = [p_map.get(p, 0) for p in cat_periods]
                    traces.append({
                        "y":     aligned,
                        "name":  f"{acct_type} ({sel_cat})",
                        "color": _acct_colors.get(acct_type, COLORS["purple"]),
                    })
            else:
                traces = [{"y": amounts, "name": sel_cat, "color": COLORS["purple"]}]
        else:
            period_labels, traces, y_primary = [], [], []

    has_data = bool(traces and any(t["y"] for t in traces))

    if not has_data:
        st.markdown(
            f'<div style="color:{COLORS["text_tertiary"]};padding:48px;text-align:center">'
            "No data for this selection.</div>",
            unsafe_allow_html=True,
        )
        return

    # ── Trend insights + KPIs (above chart) ───────────────────────────────────
    _render_trend_insights(y_primary, period_labels, metric, mode, sel_cat)
    _render_trend_kpis(y_primary, metric, mode)

    # ── Chart ─────────────────────────────────────────────────────────────────
    fig = make_trends_chart(
        [], period_labels, traces,
        is_percentage=(metric == "savings_rate" and mode == "system"),
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def _render_trend_insights(
    values: list, period_labels: list, metric: str, mode: str, sel_cat: str | None
) -> None:
    if len(values) < 2:
        return

    first, last = values[0], values[-1]
    overall_pct = ((last - first) / first * 100) if first != 0 else 0
    direction = "increasing" if overall_pct > 5 else "decreasing" if overall_pct < -5 else "stable"
    avg_val = sum(values) / len(values)
    peak_idx = values.index(max(values))
    trough_idx = values.index(min(values))
    span = f"{period_labels[0]} to {period_labels[-1]}"

    metric_labels = {
        "total_expense": "expenses", "total_income": "income",
        "net_savings": "savings", "total_investment": "investments",
    }
    metric_name = sel_cat if mode == "category" else metric_labels.get(metric, metric)

    if metric == "total_expense" and mode == "system":
        dir_color = COLORS["red"] if direction == "increasing" else COLORS["green"]
    else:
        dir_color = COLORS["green"] if direction == "increasing" else COLORS["red"]
    if direction == "stable":
        dir_color = COLORS["amber"]

    # Build strings separately to avoid multi-line f-string markdown parsing issues
    pct_span = (
        f" by <span style=\"color:{COLORS['text_primary']};font-weight:600\">"
        f"{abs(overall_pct):.1f}%</span>"
        if overall_pct != 0 else ""
    )
    _is_pct = metric == "savings_rate" and mode == "system"
    peak_fmt   = f"{max(values):.1f}%"   if _is_pct else fmt_inr(max(values), compact=True)
    trough_fmt = f"{min(values):.1f}%"   if _is_pct else fmt_inr(min(values), compact=True)
    avg_fmt    = f"{avg_val:.1f}%"        if _is_pct else fmt_inr(avg_val, compact=True)

    card = (
        f"<div style=\"background:{COLORS['bg_card']};border:1px solid {COLORS['border']};"
        f"border-radius:10px;padding:20px 24px;margin-bottom:12px\">"
        f"<div style=\"font-size:10px;letter-spacing:.1em;text-transform:uppercase;"
        f"color:{COLORS['text_tertiary']};margin-bottom:14px\">Trend Analysis</div>"
        f"<div style=\"font-size:14px;color:{COLORS['text_secondary']};margin-bottom:10px\">"
        f"Overall <b>{metric_name}</b> is "
        f"<span style=\"color:{dir_color};font-weight:600\">{direction}</span>"
        f"{pct_span} from {span}.</div>"
        f"<div style=\"font-size:13px;color:{COLORS['text_secondary']};line-height:1.9\">"
        f"Peak <span style=\"color:{COLORS['text_primary']};font-family:monospace\">{peak_fmt}</span>"
        f" in <b>{period_labels[peak_idx]}</b>"
        f" &nbsp;·&nbsp; "
        f"Lowest <span style=\"color:{COLORS['text_primary']};font-family:monospace\">{trough_fmt}</span>"
        f" in <b>{period_labels[trough_idx]}</b>"
        f" &nbsp;·&nbsp; "
        f"Average <span style=\"color:{COLORS['text_primary']};font-family:monospace\">{avg_fmt}</span>"
        f"</div></div>"
    )
    st.markdown(card, unsafe_allow_html=True)


def _render_trend_kpis(values: list, metric: str, mode: str = "system") -> None:
    if len(values) < 2:
        return

    overall_pct = ((values[-1] - values[0]) / values[0] * 100) if values[0] != 0 else 0
    avg_val = sum(values) / len(values)
    volatility = (max(values) - min(values)) / avg_val * 100 if avg_val != 0 else 0

    is_expense = metric == "total_expense"
    trend_color = COLORS["red"] if (is_expense and overall_pct > 0) else COLORS["green"]
    if abs(overall_pct) < 5:
        trend_color = COLORS["amber"]

    vol_label = "High" if volatility > 50 else "Medium" if volatility > 20 else "Low"
    vol_color = COLORS["red"] if volatility > 50 else COLORS["amber"] if volatility > 20 else COLORS["green"]

    col1, col2, col3, col4 = st.columns(4)

    def chip(col, label: str, val_str: str, color: str | None = None) -> None:
        c = color or COLORS["text_primary"]
        col.markdown(
            f"<div style=\"background:{COLORS['bg_card']};border:1px solid {COLORS['border']};"
            f"border-radius:8px;padding:14px 18px;text-align:center;margin-bottom:16px\">"
            f"<div style=\"font-size:10px;letter-spacing:.08em;text-transform:uppercase;"
            f"color:{COLORS['text_tertiary']};margin-bottom:6px\">{label}</div>"
            f"<div style=\"font-size:18px;font-family:monospace;color:{c}\">{val_str}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    is_pct = metric == "savings_rate" and mode == "system"
    arrow = "↑" if overall_pct > 0 else "↓" if overall_pct < 0 else "→"
    chip(col1, "Overall Trend",  f"{arrow} {abs(overall_pct):.1f}%", trend_color)
    chip(col2, "Period Average", f"{avg_val:.1f}%" if is_pct else fmt_inr(avg_val, compact=True))
    chip(col3, "Peak",           f"{max(values):.1f}%" if is_pct else fmt_inr(max(values), compact=True))
    chip(col4, "Volatility",     vol_label, vol_color)
