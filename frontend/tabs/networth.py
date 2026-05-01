import math
import streamlit as st
import plotly.graph_objects as go
from datetime import date

from config import COLORS, API_BASE
from formatters import fmt_inr, fmt_month


def _months_compound(pv: float, pmt: float, annual_rate: float = 0.12) -> int:
    r = annual_rate / 12
    if r == 0:
        return math.ceil(pv / pmt) if pmt > 0 else 99999
    if pmt <= r * pv:
        return 99999
    return math.ceil(math.log(pmt / (pmt - r * pv)) / math.log(1 + r))


def _api(path: str, method: str = "GET", json: dict | None = None):
    import requests
    try:
        fn = getattr(requests, method.lower())
        r = fn(f"{API_BASE}{path}", timeout=15, json=json)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error ({path}): {e}")
        return None


def render_networth() -> None:
    st.markdown(f"""
    <div style="font-size:11px;letter-spacing:.12em;text-transform:uppercase;
                color:{COLORS['text_secondary']};margin-bottom:20px">
      Net Worth
    </div>
    """, unsafe_allow_html=True)

    networth = _api("/networth/summary")
    history  = _api("/networth/history") or []
    goals    = _api("/goals") or []

    if networth:
        _render_waterfall(networth)
        if len(history) >= 2:
            _render_trend(history)
    else:
        st.info("Upload a portfolio snapshot to see net worth.")

    _render_goals(goals)
    _render_add_goal_form()


def _render_waterfall(nw: dict) -> None:
    assets = nw.get("total_assets", 0)
    liabilities = nw.get("total_liabilities", 0)
    net = nw.get("net_worth", 0)
    net_color = COLORS["green"] if net >= 0 else COLORS["red"]

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Assets",       fmt_inr(assets))
    c2.metric("Total Liabilities",  fmt_inr(liabilities))
    c3.metric("Net Worth",          fmt_inr(net))

    # Waterfall chart
    asset_breakdown = nw.get("asset_breakdown", {})
    liability_breakdown = nw.get("liability_breakdown", {})

    measures, x_labels, y_values = [], [], []
    for k, v in asset_breakdown.items():
        measures.append("relative"); x_labels.append(k.replace("_", " ").title()); y_values.append(v)
    for k, v in liability_breakdown.items():
        measures.append("relative"); x_labels.append(k.replace("_", " ").title()); y_values.append(-v)
    measures.append("total"); x_labels.append("Net Worth"); y_values.append(0)

    if x_labels:
        fig = go.Figure(go.Waterfall(
            measure=measures,
            x=x_labels,
            y=y_values,
            connector=dict(line=dict(color=COLORS["border"])),
            increasing=dict(marker=dict(color=COLORS["green"])),
            decreasing=dict(marker=dict(color=COLORS["red"])),
            totals=dict(marker=dict(color=net_color)),
            texttemplate="₹%{y:,.0f}",
            textposition="outside",
            textfont=dict(color=COLORS["text_primary"], size=11),
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(color=COLORS["text_secondary"], gridcolor=COLORS["border"]),
            yaxis=dict(color=COLORS["text_secondary"], gridcolor=COLORS["border"]),
            margin=dict(t=20, b=10, l=10, r=10), height=300,
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Goal gap banner ───────────────────────────────────────────────────────
    goals = _api("/goals") or []
    house_goals = [
        g for g in goals
        if any(kw in g.get("name", "").lower()
               for kw in ("house", "home", "property", "flat", "apartment"))
    ]
    for g in house_goals:
        target = g["target_amount"]
        net = nw.get("net_worth", 0)
        gap = max(0, target - net)
        pct = min(100, net / target * 100) if target > 0 else 0
        color = COLORS["red"] if pct < 25 else COLORS["amber"] if pct < 75 else COLORS["green"]
        st.markdown(
            f"""
            <div style="background:{COLORS['bg_elevated']};
                        border-left:4px solid {color};
                        border-radius:6px;padding:14px 18px;margin-top:14px">
              <div style="font-size:11px;letter-spacing:.08em;text-transform:uppercase;
                          color:{COLORS['text_secondary']};margin-bottom:4px">
                {g['name']} — Gap to target
              </div>
              <div style="display:flex;align-items:baseline;gap:12px">
                <div style="font-size:22px;color:{color};
                            font-family:'DM Mono',monospace;font-weight:600">
                  ₹{gap:,.0f}
                </div>
                <div style="font-size:13px;color:{COLORS['text_tertiary']}">
                  remaining &nbsp;·&nbsp; {pct:.1f}% complete
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_trend(history: list) -> None:
    st.markdown(f"""
    <div style="font-size:11px;letter-spacing:.1em;color:{COLORS['text_tertiary']};
                text-transform:uppercase;margin:12px 0 8px">
      Net Worth Over Time
    </div>
    """, unsafe_allow_html=True)
    dates = [h["date"] for h in history]
    values = [h["net_worth"] for h in history]

    fig = go.Figure(go.Scatter(
        x=dates, y=values,
        mode="lines+markers",
        line=dict(color=COLORS["purple"], width=2),
        marker=dict(color=COLORS["purple"], size=6),
        fill="tozeroy",
        fillcolor="rgba(124,111,205,0.1)",
        hovertemplate="%{x}: ₹%{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(color=COLORS["text_secondary"], gridcolor=COLORS["border"]),
        yaxis=dict(color=COLORS["text_secondary"], gridcolor=COLORS["border"]),
        margin=dict(t=10, b=10, l=10, r=10), height=240,
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_goals(goals: list) -> None:
    if not goals:
        return
    st.markdown(f"""
    <div style="font-size:11px;letter-spacing:.1em;color:{COLORS['text_tertiary']};
                text-transform:uppercase;margin:20px 0 12px">
      Financial Goals
    </div>
    """, unsafe_allow_html=True)

    cols = st.columns(min(len(goals), 2))
    for i, goal in enumerate(goals):
        col = cols[i % 2]
        target = goal["target_amount"]
        current = goal["current_amount"] or 0
        pct = min(100, int(current / target * 100)) if target > 0 else 0
        sip = goal.get("monthly_sip", 0) or 0

        remaining = max(0, target - current)
        months_needed = _months_compound(current, sip) if sip > 0 else None

        fill_color = COLORS["green"] if pct >= 80 else COLORS["blue"] if pct >= 50 else COLORS["amber"]

        sip_line = (
            f'Monthly SIP: <strong>{fmt_inr(sip)}</strong> &nbsp;✓'
            if sip > 0 else
            'No SIP linked'
        )
        months_line = (
            f'Need {fmt_inr(sip)}/month &nbsp;· &nbsp;~{months_needed} months'
            if months_needed else ""
        )

        td_str = ""
        if goal.get("target_date"):
            td_str = f"by <strong>{goal['target_date']}</strong>"

        with col:
            st.markdown(f"""
            <div style="background:{COLORS['bg_card']};border:1px solid {COLORS['border']};
                        border-radius:12px;padding:20px;margin-bottom:12px">
              <div style="font-size:14px;color:{COLORS['text_primary']};
                          font-weight:600;margin-bottom:4px">{goal['name']}</div>
              <div style="font-size:12px;color:{COLORS['text_secondary']};margin-bottom:12px">
                Target: <strong>{fmt_inr(target)}</strong> {td_str}
              </div>
              <div style="background:{COLORS['bg_elevated']};border-radius:4px;
                          height:8px;margin-bottom:8px;overflow:hidden">
                <div style="background:{fill_color};width:{pct}%;height:8px;border-radius:4px"></div>
              </div>
              <div style="display:flex;justify-content:space-between;
                          font-size:12px;color:{COLORS['text_secondary']};margin-bottom:10px">
                <span>{fmt_inr(current)} saved</span>
                <span style="color:{fill_color}">{pct}%</span>
              </div>
              <div style="font-size:12px;color:{COLORS['text_secondary']}">{sip_line}</div>
              <div style="font-size:12px;color:{COLORS['text_tertiary']}">{months_line}</div>
            </div>
            """, unsafe_allow_html=True)

            if goal.get("target_date"):
                slider_key = f"hypo_sip_{goal['id']}"
                hypo = st.slider(
                    "Scenario: monthly investment →",
                    min_value=0,
                    max_value=300000,
                    step=5000,
                    value=int(sip),
                    key=slider_key,
                    format="₹%d",
                )
                if hypo > 0:
                    alt_months = _months_compound(current, hypo)
                    if alt_months < 99999:
                        from datetime import date as _d
                        _today = _d.today().replace(day=1)
                        _m = _today.month - 1 + alt_months
                        alt_date = _today.replace(
                            year=_today.year + _m // 12,
                            month=_m % 12 + 1, day=1
                        )
                        delta_months = months_needed - alt_months if months_needed else 0
                        delta_str = (
                            f" ({abs(delta_months)} months {'faster' if delta_months > 0 else 'slower'})"
                            if delta_months != 0 and months_needed else ""
                        )
                        st.markdown(
                            f"<div style='font-size:12px;color:{COLORS['text_secondary']};"
                            f"padding:6px 0'>→ At <strong>₹{hypo:,}/month</strong>: goal in "
                            f"<strong>{alt_months} months</strong> (~{alt_date.strftime('%b %Y')})"
                            f"<span style='color:{COLORS['amber']}'>{delta_str}</span></div>",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            f"<div style='font-size:12px;color:{COLORS['red']};padding:6px 0'>"
                            f"₹{hypo:,}/month is below the monthly interest on current corpus — "
                            f"increase SIP to make progress.</div>",
                            unsafe_allow_html=True,
                        )


def _render_add_goal_form() -> None:
    with st.expander("+ Add / Update Goal"):
        with st.form("add_goal"):
            name          = st.text_input("Goal name (e.g. House Down Payment)")
            target_amount = st.number_input("Target amount (₹)", min_value=0.0, step=10000.0)
            current_amount= st.number_input("Currently saved (₹)", min_value=0.0, step=1000.0)
            monthly_sip   = st.number_input("Monthly SIP / contribution (₹)", min_value=0.0, step=500.0)
            target_date   = st.date_input("Target date", value=None)
            notes         = st.text_area("Notes (optional)")
            submitted = st.form_submit_button("Save Goal")

        if submitted and name:
            payload = {
                "name": name,
                "target_amount": target_amount,
                "current_amount": current_amount,
                "monthly_sip": monthly_sip,
                "target_date": str(target_date) if target_date else None,
                "notes": notes or None,
            }
            result = _api("/goals", method="POST", json=payload)
            if result:
                st.success(f"Goal '{name}' saved.")
                st.rerun()
