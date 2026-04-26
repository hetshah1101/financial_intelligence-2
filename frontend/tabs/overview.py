import streamlit as st

from analytics import behavioral_split, compute_baseline, generate_takeaways
from api import api_months, categories_for_month
from charts import make_donut, make_overview_bar
from config import COLORS, classify_category
from formatters import fmt_inr, fmt_month


def render_overview(dashboard: dict | None) -> None:
    if not dashboard:
        _empty_state()
        return

    monthly = sorted(dashboard.get("monthly_aggregates", []), key=lambda x: x["month"])
    if not monthly:
        _empty_state()
        return

    # ── Month selector ───────────────────────────────────────────────────────
    months_desc = sorted({m["month"] for m in monthly}, reverse=True)
    month_display = {fmt_month(m): m for m in months_desc}

    col_filter, _ = st.columns([2, 6])
    with col_filter:
        sel_disp = st.selectbox(
            "Viewing month",
            list(month_display.keys()),
            index=0,
            key="overview_month_display",
        )
    selected_month = month_display[sel_disp]
    st.session_state["overview_month"] = selected_month

    st.markdown(f'<hr style="border:none;border-top:1px solid {COLORS["border"]};margin:12px 0 20px">', unsafe_allow_html=True)

    # ── Resolve data for selected month ──────────────────────────────────────
    month_agg = next((m for m in monthly if m["month"] == selected_month), None)
    if not month_agg:
        st.warning(f"No data found for {sel_disp}")
        return

    prior_months = [m for m in monthly if m["month"] < selected_month]
    baseline = compute_baseline(prior_months + [month_agg], "12m_avg")
    categories = categories_for_month(dashboard, selected_month)

    account_monthly = dashboard.get("account_monthly_aggregates", [])

    # ── Render sections ───────────────────────────────────────────────────────
    _render_takeaways(month_agg, baseline, categories)
    _render_kpi_row(month_agg, baseline)
    _render_charts_row(monthly, categories, selected_month, account_monthly)
    _render_behavioral_section(categories, monthly, selected_month)


def _render_takeaways(month_agg: dict, baseline: dict | None, categories: list) -> None:
    tips = generate_takeaways(month_agg, baseline, categories)
    bullets = "".join(f"<li>{t}</li>" for t in tips)
    st.markdown(f"""
    <div style="background:{COLORS['bg_card']};border:1px solid {COLORS['border']};
                border-radius:10px;padding:16px 20px;margin-bottom:20px">
      <div style="font-size:11px;letter-spacing:.1em;color:{COLORS['text_tertiary']};
                  text-transform:uppercase;margin-bottom:10px">This Month</div>
      <ul style="margin:0;padding-left:18px;color:{COLORS['text_secondary']};
                 font-size:13px;line-height:1.8">{bullets}</ul>
    </div>
    """, unsafe_allow_html=True)


def _render_kpi_row(month_agg: dict, baseline: dict | None) -> None:
    col1, col2, col3, col4 = st.columns(4)
    b = baseline or {}

    def kpi_card(col, label: str, value: float, baseline_value: float | None, invert: bool = False):
        delta_str = ""
        delta_color = COLORS["text_secondary"]
        if baseline_value is not None and baseline_value != 0:
            pct = (value - baseline_value) / abs(baseline_value) * 100
            arrow = "↑" if pct > 0 else "↓"
            if invert:
                delta_color = COLORS["red"] if pct > 0 else COLORS["green"]
            else:
                delta_color = COLORS["green"] if pct > 0 else COLORS["red"]
            delta_str = f"{arrow} {abs(pct):.1f}%"

        col.markdown(f"""
        <div style="background:{COLORS['bg_card']};border:1px solid {COLORS['border']};
                    border-radius:10px;padding:20px 24px;min-height:120px">
          <div style="font-size:11px;letter-spacing:.1em;text-transform:uppercase;
                      color:{COLORS['text_secondary']};margin-bottom:8px">{label}</div>
          <div style="font-size:26px;font-family:'DM Mono',monospace;
                      color:{COLORS['text_primary']};margin-bottom:6px">{fmt_inr(value)}</div>
          <div style="font-size:12px;color:{delta_color};font-weight:500">{delta_str}
            <span style="color:{COLORS['text_tertiary']};font-weight:400">
              {"&nbsp;vs 12m avg" if delta_str else ""}
            </span>
          </div>
        </div>
        """, unsafe_allow_html=True)

    kpi_card(col1, "Income",      month_agg["total_income"],     b.get("total_income"),     invert=False)
    kpi_card(col2, "Expenses",    month_agg["total_expense"],    b.get("total_expense"),    invert=True)
    kpi_card(col3, "Investments", month_agg["total_investment"], b.get("total_investment"), invert=False)
    kpi_card(col4, "Net Savings", month_agg["net_savings"],      b.get("net_savings"),      invert=False)


def _render_charts_row(monthly: list, categories: list, selected_month: str, account_monthly: list | None = None) -> None:
    col_bar, col_donut = st.columns([6, 4])
    with col_bar:
        fig = make_overview_bar(monthly, selected_month, account_monthly)
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    with col_donut:
        if categories:
            fig = make_donut(categories)
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        else:
            st.markdown(
                f'<div style="color:{COLORS["text_tertiary"]};padding:48px;text-align:center">'
                "No category data for this month.</div>",
                unsafe_allow_html=True,
            )


def _render_behavioral_section(categories: list, monthly: list, selected_month: str) -> None:
    if not categories:
        return

    split = behavioral_split(categories)
    ess_pct = split["essential_pct"]
    dis_pct = split["discretionary_pct"]

    st.markdown(
        f"<div style=\"font-size:11px;letter-spacing:.1em;color:{COLORS['text_tertiary']};"
        f"text-transform:uppercase;margin:24px 0 12px\">Spending Behaviour</div>",
        unsafe_allow_html=True,
    )

    col_bars, col_kpis, col_insight = st.columns([4, 3, 3])

    # Left: Essential / Discretionary bars
    with col_bars:
        st.markdown(
            f"<div style=\"background:{COLORS['bg_card']};border:1px solid {COLORS['border']};"
            f"border-radius:10px;padding:20px 24px;height:160px\">"
            f"<div style=\"margin-bottom:16px\">"
            f"<div style=\"display:flex;justify-content:space-between;margin-bottom:6px\">"
            f"<span style=\"color:{COLORS['text_secondary']};font-size:12px\">Essential</span>"
            f"<span style=\"color:{COLORS['text_primary']};font-family:monospace;font-size:12px\">"
            f"{ess_pct:.0f}% · {fmt_inr(split['essential_amount'], compact=True)}</span></div>"
            f"<div style=\"height:6px;background:{COLORS['bg_elevated']};border-radius:3px\">"
            f"<div style=\"width:{ess_pct:.0f}%;height:100%;background:{COLORS['blue']};border-radius:3px\"></div>"
            f"</div></div>"
            f"<div>"
            f"<div style=\"display:flex;justify-content:space-between;margin-bottom:6px\">"
            f"<span style=\"color:{COLORS['text_secondary']};font-size:12px\">Discretionary</span>"
            f"<span style=\"color:{COLORS['text_primary']};font-family:monospace;font-size:12px\">"
            f"{dis_pct:.0f}% · {fmt_inr(split['discretionary_amount'], compact=True)}</span></div>"
            f"<div style=\"height:6px;background:{COLORS['bg_elevated']};border-radius:3px\">"
            f"<div style=\"width:{dis_pct:.0f}%;height:100%;background:{COLORS['amber']};border-radius:3px\"></div>"
            f"</div></div></div>",
            unsafe_allow_html=True,
        )

    # Middle: Behavioural KPIs
    with col_kpis:
        top_cat = categories[0] if categories else {}
        top_pct = top_cat.get("percentage_of_total_expense") or top_cat.get("percentage_of_total", 0)
        top_name = top_cat.get("category", "—")

        savings_rate = next(
            (m["savings_rate"] for m in monthly if m["month"] == selected_month), 0
        )
        prior = [m for m in monthly if m["month"] < selected_month]
        avg_savings_12 = (
            sum(m["savings_rate"] for m in prior[-12:]) / len(prior[-12:])
            if prior else savings_rate
        )
        sr_color = COLORS["green"] if savings_rate >= avg_savings_12 else COLORS["red"]

        st.markdown(
            f"<div style=\"background:{COLORS['bg_card']};border:1px solid {COLORS['border']};"
            f"border-radius:10px;padding:20px 24px;height:160px\">"
            f"<div style=\"margin-bottom:14px\">"
            f"<div style=\"font-size:10px;letter-spacing:.08em;text-transform:uppercase;"
            f"color:{COLORS['text_tertiary']};margin-bottom:4px\">Top Category</div>"
            f"<div style=\"font-size:16px;color:{COLORS['text_primary']};font-weight:500\">"
            f"{top_name}"
            f"<span style=\"font-size:12px;color:{COLORS['text_secondary']}\"> · {top_pct:.0f}% of spend</span>"
            f"</div></div>"
            f"<div>"
            f"<div style=\"font-size:10px;letter-spacing:.08em;text-transform:uppercase;"
            f"color:{COLORS['text_tertiary']};margin-bottom:4px\">Savings Rate vs 12m Avg</div>"
            f"<div style=\"font-size:16px;font-family:monospace;color:{sr_color}\">"
            f"{savings_rate:.0f}%"
            f"<span style=\"font-size:12px;color:{COLORS['text_secondary']}\"> avg {avg_savings_12:.0f}%</span>"
            f"</div></div></div>",
            unsafe_allow_html=True,
        )

    # Right: Contextual insight note
    with col_insight:
        if dis_pct > 60:
            disc_note = (
                f"Discretionary spending dominates at <b>{dis_pct:.0f}%</b>. "
                f"Consider reviewing non-essential categories."
            )
        elif dis_pct > 40:
            disc_note = f"Spending is balanced — {ess_pct:.0f}% essential, {dis_pct:.0f}% discretionary."
        else:
            disc_note = f"Excellent — {ess_pct:.0f}% of spend is on essentials. Strong spending discipline."

        prior3 = [m for m in monthly if m["month"] < selected_month][-3:]
        avg_prior_exp = sum(m["total_expense"] for m in prior3) / len(prior3) if prior3 else 0
        current_exp = next((m["total_expense"] for m in monthly if m["month"] == selected_month), 0)
        exp_change = ((current_exp - avg_prior_exp) / avg_prior_exp * 100) if avg_prior_exp else 0

        exp_note = ""
        if abs(exp_change) > 5:
            direction = "up" if exp_change > 0 else "down"
            clr = COLORS["red"] if exp_change > 0 else COLORS["green"]
            exp_note = (
                f"Expenses are <span style=\"color:{clr}\"><b>{direction} {abs(exp_change):.0f}%</b></span>"
                f" vs your 3-month average."
            )

        note_body = disc_note + (f"<br><br>{exp_note}" if exp_note else "")
        st.markdown(
            f"<div style=\"background:{COLORS['bg_card']};border:1px solid {COLORS['border']};"
            f"border-radius:10px;padding:20px 24px;height:160px;"
            f"display:flex;flex-direction:column;justify-content:center\">"
            f"<div style=\"font-size:10px;letter-spacing:.08em;text-transform:uppercase;"
            f"color:{COLORS['text_tertiary']};margin-bottom:10px\">Behaviour Note</div>"
            f"<div style=\"font-size:13px;color:{COLORS['text_secondary']};line-height:1.7\">"
            f"{note_body}</div></div>",
            unsafe_allow_html=True,
        )

    # ── Category breakdown drilldown ──────────────────────────────────────────
    _render_category_breakdown(categories)


def _render_category_breakdown(categories: list) -> None:
    """Expandable essential / discretionary breakdown with per-category rows."""
    if not categories:
        return

    essential = [(c, c["total_amount"]) for c in categories
                 if classify_category(c["category"]) == "essential"]
    discretionary = [(c, c["total_amount"]) for c in categories
                     if classify_category(c["category"]) == "discretionary"]

    st.markdown(
        f"<div style=\"font-size:11px;letter-spacing:.1em;color:{COLORS['text_tertiary']};"
        f"text-transform:uppercase;margin:20px 0 8px\">Category Breakdown</div>",
        unsafe_allow_html=True,
    )

    col_ess, col_dis = st.columns(2)

    def _cat_rows(group: list, color: str) -> str:
        if not group:
            return (
                f"<div style=\"color:{COLORS['text_tertiary']};font-size:12px;"
                f"padding:12px 0\">No categories</div>"
            )
        rows = ""
        for cat, amt in group:
            pct = cat.get("percentage_of_total_expense") or cat.get("percentage_of_total", 0)
            bar_w = min(int(pct), 100)
            rows += (
                f"<div style=\"margin-bottom:12px\">"
                f"<div style=\"display:flex;justify-content:space-between;margin-bottom:4px\">"
                f"<span style=\"color:{COLORS['text_primary']};font-size:13px\">{cat['category']}</span>"
                f"<span style=\"color:{COLORS['text_secondary']};font-family:monospace;font-size:12px\">"
                f"{fmt_inr(amt, compact=True)}"
                f"<span style=\"color:{COLORS['text_tertiary']};font-size:11px\"> &nbsp;{pct:.0f}%</span>"
                f"</span></div>"
                f"<div style=\"height:3px;background:{COLORS['bg_elevated']};border-radius:2px\">"
                f"<div style=\"width:{bar_w}%;height:100%;background:{color};border-radius:2px;opacity:0.7\">"
                f"</div></div></div>"
            )
        return rows

    with col_ess:
        ess_total = sum(a for _, a in essential)
        with st.expander(f"Essential — {fmt_inr(ess_total, compact=True)}", expanded=False):
            st.markdown(
                f"<div style=\"padding:4px 0\">{_cat_rows(essential, COLORS['blue'])}</div>",
                unsafe_allow_html=True,
            )

    with col_dis:
        dis_total = sum(a for _, a in discretionary)
        with st.expander(f"Discretionary — {fmt_inr(dis_total, compact=True)}", expanded=False):
            st.markdown(
                f"<div style=\"padding:4px 0\">{_cat_rows(discretionary, COLORS['amber'])}</div>",
                unsafe_allow_html=True,
            )


def _empty_state() -> None:
    st.markdown(f"""
    <div style="display:flex;flex-direction:column;align-items:center;
                justify-content:center;min-height:60vh;text-align:center">
      <div style="font-size:48px;color:{COLORS['border']};margin-bottom:24px">₹</div>
      <h2 style="color:{COLORS['text_primary']};font-weight:500;margin-bottom:8px">Welcome to Finsight</h2>
      <p style="color:{COLORS['text_secondary']};font-size:14px;margin-bottom:24px">
        Upload your transaction data in the Data tab to get started
      </p>
      <div style="display:flex;gap:8px;font-size:12px;color:{COLORS['text_tertiary']}">
        <span style="background:{COLORS['bg_elevated']};padding:4px 12px;border-radius:6px">CSV</span>
        <span style="background:{COLORS['bg_elevated']};padding:4px 12px;border-radius:6px">XLSX</span>
      </div>
    </div>
    """, unsafe_allow_html=True)
