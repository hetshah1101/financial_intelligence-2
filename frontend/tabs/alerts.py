import pandas as pd
import streamlit as st
from statistics import mean

from analytics import classify_anomalies
from config import COLORS, classify_category
from formatters import fmt_inr, fmt_month


# ── Financial Health Score ────────────────────────────────────────────────────

def _compute_health_score(dashboard: dict, anomalies: list) -> tuple[int, str]:
    """Return (score 0-100, verdict string)."""
    monthly = dashboard.get("monthly_aggregates", [])
    if not monthly:
        return 50, "Not enough data to score"

    latest = monthly[-1]
    savings_rate = latest.get("savings_rate", 0)
    total_expense = latest.get("total_expense", 0)

    # Component 1: Savings rate vs 20% target (weight 30)
    savings_score = min(30, savings_rate / 20 * 30)

    # Component 2: Expense vs 12-month baseline (weight 25)
    history = monthly[:-1][-12:]
    if history:
        avg_expense = mean(m["total_expense"] for m in history)
        overspend_pct = ((total_expense - avg_expense) / avg_expense * 100) if avg_expense > 0 else 0
        expense_score = max(0, 25 - (overspend_pct / 4))
    else:
        expense_score = 12.5

    # Component 3: Active anomaly penalty (weight 20)
    critical = sum(
        1 for a in anomalies
        if a.get("ratio", 0) >= 2.0
        or (a.get("alert_type") == "savings" and a.get("ratio", 1) < 0.6)
    )
    warnings = sum(
        1 for a in anomalies
        if 1.4 <= a.get("ratio", 0) < 2.0
        or (a.get("alert_type") == "savings" and 0.6 <= a.get("ratio", 1) < 0.8)
    )
    anomaly_score = max(0, 20 - (critical * 5) - (warnings * 2))

    # Component 4: Essential/discretionary ratio (weight 25)
    cats = dashboard.get("category_aggregates", [])
    latest_month = latest.get("month", "")
    cur_cats = [c for c in cats if c["month"] == latest_month]
    essential = sum(c["total_amount"] for c in cur_cats if classify_category(c["category"]) == "essential")
    total_cat  = sum(c["total_amount"] for c in cur_cats) or 1
    essential_pct = essential / total_cat * 100
    ratio_score = 25 if essential_pct >= 40 else essential_pct / 40 * 25

    score = int(savings_score + expense_score + anomaly_score + ratio_score)
    score = max(0, min(100, score))

    if score >= 80:
        verdict = "Strong control — on track"
    elif score >= 60:
        verdict = "Good, with a few areas to watch"
    elif score >= 40:
        verdict = "Some overspending — review alerts below"
    else:
        verdict = "Spending needs attention this month"

    return score, verdict


def _render_health_score(score: int, verdict: str) -> None:
    if score >= 80:
        color = COLORS["green"]
    elif score >= 60:
        color = COLORS["blue"]
    elif score >= 40:
        color = COLORS["amber"]
    else:
        color = COLORS["red"]

    st.markdown(f"""
    <div style="background:{COLORS['bg_card']};border:1px solid {COLORS['border']};
                border-radius:12px;padding:24px 28px;margin-bottom:20px;
                display:flex;align-items:center;gap:28px">
      <div style="font-size:52px;font-weight:700;color:{color};
                  font-family:'DM Mono',monospace;line-height:1">{score}</div>
      <div>
        <div style="font-size:11px;letter-spacing:.1em;color:{COLORS['text_secondary']};
                    text-transform:uppercase;margin-bottom:4px">Financial Health Score</div>
        <div style="font-size:16px;color:{COLORS['text_primary']}">{verdict}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ── Alert Cards ───────────────────────────────────────────────────────────────

def _severity(ratio: float, alert_type: str) -> tuple[str, str, str]:
    """Return (emoji, label, border_color)."""
    if alert_type == "savings":
        if ratio < 0.6:
            return "🔴", "SAVINGS", COLORS["red"]
        return "🟡", "SAVINGS", COLORS["amber"]
    if ratio >= 2.0:
        return "🔴", "SPIKE", COLORS["red"]
    if ratio >= 1.4:
        return "🟡", "SPIKE", COLORS["amber"]
    return "🔵", "INFO", COLORS["blue"]


def _render_alert_cards(anomalies: list) -> None:
    if not anomalies:
        return
    st.markdown(f"""
    <div style="font-size:11px;letter-spacing:.1em;color:{COLORS['text_tertiary']};
                text-transform:uppercase;margin-bottom:12px">
      Active Alerts
    </div>
    """, unsafe_allow_html=True)

    for a in anomalies:
        emoji, badge, border = _severity(a["ratio"], a["alert_type"])
        current  = a["current_month_amount"]
        baseline = a["three_month_avg"]
        excess   = max(0.0, current - baseline)
        ratio_s  = f"{a['ratio']:.1f}×" if a["ratio"] > 0 else "N/A"
        month_s  = fmt_month(a["month"]) if a.get("month") else ""
        cat      = a["category"]

        # Progress bar fill: capped at 100% of card width, ratio drives fill
        fill_pct = min(100, int((a["ratio"] / 3.0) * 100)) if a["ratio"] > 0 else 0

        st.markdown(f"""
        <div style="background:{COLORS['bg_card']};
                    border:1px solid {COLORS['border']};
                    border-left:4px solid {border};
                    border-radius:10px;padding:16px 20px;margin-bottom:10px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
            <div>
              <span style="font-size:13px;color:{border};font-weight:600">{emoji} {badge}</span>
              <span style="font-size:13px;color:{COLORS['text_primary']};margin-left:8px;font-weight:500">{cat}</span>
            </div>
            <div style="font-size:12px;color:{COLORS['text_secondary']}">{month_s}</div>
          </div>
          <div style="display:flex;gap:24px;margin-bottom:10px">
            <div>
              <div style="font-size:10px;color:{COLORS['text_secondary']};text-transform:uppercase;letter-spacing:.08em">This month</div>
              <div style="font-size:18px;color:{COLORS['text_primary']};font-family:'DM Mono',monospace">{fmt_inr(current)}</div>
            </div>
            <div>
              <div style="font-size:10px;color:{COLORS['text_secondary']};text-transform:uppercase;letter-spacing:.08em">3-month avg</div>
              <div style="font-size:18px;color:{COLORS['text_secondary']};font-family:'DM Mono',monospace">{fmt_inr(baseline)}</div>
            </div>
            <div>
              <div style="font-size:10px;color:{COLORS['text_secondary']};text-transform:uppercase;letter-spacing:.08em">Excess</div>
              <div style="font-size:18px;color:{border};font-family:'DM Mono',monospace">+{fmt_inr(excess)}</div>
            </div>
          </div>
          <div style="background:{COLORS['bg_elevated']};border-radius:4px;height:6px;margin-bottom:8px">
            <div style="background:{border};width:{fill_pct}%;height:6px;border-radius:4px"></div>
          </div>
          <div style="font-size:12px;color:{COLORS['text_secondary']}">{ratio_s} above baseline — {a.get('reason','')}</div>
        </div>
        """, unsafe_allow_html=True)


# ── Month-over-Month Digest Table ─────────────────────────────────────────────

def _render_mom_table(dashboard: dict, anomaly_cats: set) -> None:
    all_cats = dashboard.get("category_aggregates", [])
    if not all_cats:
        return

    months_avail = sorted({c["month"] for c in all_cats})
    last3 = months_avail[-3:]
    if len(last3) < 2:
        return

    st.markdown(f"""
    <div style="font-size:11px;letter-spacing:.1em;color:{COLORS['text_tertiary']};
                text-transform:uppercase;margin:20px 0 10px">
      Month-over-Month Digest
    </div>
    """, unsafe_allow_html=True)

    # Build pivot: category → {month: amount}
    pivot: dict[str, dict[str, float]] = {}
    for c in all_cats:
        if c["month"] in last3:
            pivot.setdefault(c["category"], {})[c["month"]] = c["total_amount"]

    rows = []
    for cat, monthly in pivot.items():
        amounts = [monthly.get(m, 0) for m in last3]
        last = amounts[-1]
        prev = amounts[-2]
        pct_change = ((last - prev) / prev * 100) if prev else 0

        if pct_change <= -5:
            trend = "↓"
            trend_color = COLORS["green"]
        elif pct_change > 10:
            trend = "↑↑"
            trend_color = COLORS["red"]
        elif pct_change > 0:
            trend = "↑"
            trend_color = COLORS["amber"]
        else:
            trend = "↘"
            trend_color = COLORS["green"]

        warn = " ⚠" if cat in anomaly_cats else ""
        row = {"Category": cat}
        for i, m in enumerate(last3):
            row[fmt_month(m)] = f"₹{amounts[i]:,.0f}"
        row["Trend"] = f'<span style="color:{trend_color}">{trend}{warn}</span>'
        rows.append(row)

    rows.sort(key=lambda r: -pivot.get(r["Category"], {}).get(last3[-1], 0))

    col_headers = ["Category"] + [fmt_month(m) for m in last3] + ["Trend"]
    header_html = "".join(f'<th style="text-align:left;padding:6px 10px;font-size:11px;'
                          f'letter-spacing:.08em;text-transform:uppercase;color:{COLORS["text_secondary"]}">{h}</th>'
                          for h in col_headers)

    body_html = ""
    for row in rows:
        cells = f'<td style="padding:6px 10px;font-size:13px;color:{COLORS["text_primary"]}">{row["Category"]}</td>'
        for m in last3:
            cells += f'<td style="padding:6px 10px;font-size:13px;font-family:\'DM Mono\',monospace;color:{COLORS["text_secondary"]}">{row[fmt_month(m)]}</td>'
        cells += f'<td style="padding:6px 10px;font-size:13px">{row["Trend"]}</td>'
        body_html += f'<tr style="border-bottom:1px solid {COLORS["border_subtle"]}">{cells}</tr>'

    st.markdown(f"""
    <div style="background:{COLORS['bg_card']};border:1px solid {COLORS['border']};
                border-radius:10px;overflow:hidden;margin-bottom:20px">
      <table style="width:100%;border-collapse:collapse">
        <thead><tr style="background:{COLORS['bg_elevated']}">{header_html}</tr></thead>
        <tbody>{body_html}</tbody>
      </table>
    </div>
    """, unsafe_allow_html=True)


# ── Savings Opportunities (narrative) ─────────────────────────────────────────

def _render_savings_narrative(dashboard: dict) -> None:
    opps = sorted(
        dashboard.get("savings_opportunities", []),
        key=lambda x: -x["potential_savings"],
    )
    if not opps:
        st.markdown(
            f'<div style="color:{COLORS["text_tertiary"]};font-size:13px;padding:12px">'
            "No savings opportunities identified this month.</div>",
            unsafe_allow_html=True,
        )
        return

    st.markdown(f"""
    <div style="font-size:11px;letter-spacing:.1em;color:{COLORS['text_tertiary']};
                text-transform:uppercase;margin:20px 0 10px">
      Savings Opportunities
    </div>
    """, unsafe_allow_html=True)

    essential_opps = [o for o in opps if o.get("tag") == "essential"]
    discr_opps     = [o for o in opps if o.get("tag") != "essential"]
    total_savings  = sum(o["potential_savings"] for o in opps)
    annualised     = total_savings * 12

    def _group_html(items: list, label: str) -> str:
        if not items:
            return ""
        rows_html = ""
        group_total = 0.0
        for o in items:
            ps = o["potential_savings"]
            group_total += ps
            rows_html += (
                f'<div style="display:flex;justify-content:space-between;padding:5px 0;'
                f'font-size:13px;color:{COLORS["text_secondary"]}">'
                f'<span>{o["category"]}</span>'
                f'<span style="color:{COLORS["amber"]};font-family:\'DM Mono\',monospace">+{fmt_inr(ps)}</span>'
                f'</div>'
            )
        rows_html += (
            f'<div style="display:flex;justify-content:space-between;padding:6px 0;'
            f'margin-top:4px;border-top:1px solid {COLORS["border"]};'
            f'font-size:13px;font-weight:600;color:{COLORS["text_primary"]}">'
            f'<span>Total</span>'
            f'<span style="font-family:\'DM Mono\',monospace">+{fmt_inr(group_total)}</span>'
            f'</div>'
        )
        return (
            f'<div style="margin-bottom:14px">'
            f'<div style="font-size:11px;text-transform:uppercase;letter-spacing:.08em;'
            f'color:{COLORS["text_tertiary"]};margin-bottom:6px">{label}</div>'
            f'{rows_html}</div>'
        )

    ann_display = f"₹{annualised/100000:.2f}L" if annualised >= 100000 else fmt_inr(annualised)

    body = _group_html(essential_opps, "Essential Spending")
    body += _group_html(discr_opps, "Discretionary Spending")
    body += (
        f'<div style="background:{COLORS["bg_elevated"]};border-radius:8px;padding:12px;margin-top:8px">'
        f'<div style="font-size:12px;color:{COLORS["text_secondary"]};margin-bottom:6px">'
        f'If you spent at your baseline this month:</div>'
        f'<div style="font-size:15px;color:{COLORS["green"]};font-family:\'DM Mono\',monospace">'
        f'Save {fmt_inr(total_savings)} this month</div>'
        f'<div style="font-size:13px;color:{COLORS["text_secondary"]};margin-top:4px">'
        f'Annualised: {ann_display} per year</div>'
        f'</div>'
    )

    st.markdown(f"""
    <div style="background:{COLORS['bg_card']};border:1px solid {COLORS['border']};
                border-radius:10px;padding:20px 24px">
      <div style="font-size:13px;color:{COLORS['text_secondary']};margin-bottom:14px">
        💡 Savings available this month vs your 6-month baseline:
      </div>
      {body}
    </div>
    """, unsafe_allow_html=True)


# ── All-Clear State ───────────────────────────────────────────────────────────

def _render_all_clear(dashboard: dict) -> None:
    monthly = dashboard.get("monthly_aggregates", [])

    best_rate_month = ""
    best_rate = 0.0
    for m in monthly:
        if m.get("savings_rate", 0) > best_rate:
            best_rate = m["savings_rate"]
            best_rate_month = m["month"]

    # Count how many consecutive months expense stayed below 12m rolling avg
    streak = 0
    for m in reversed(monthly):
        history = [x for x in monthly if x["month"] < m["month"]][-12:]
        if not history:
            break
        avg = mean(x["total_expense"] for x in history)
        if m["total_expense"] < avg:
            streak += 1
        else:
            break

    # Discretionary downtrend — count months the discretionary spend fell MoM
    cats = dashboard.get("category_aggregates", [])
    months_sorted = sorted({c["month"] for c in cats})
    discr_trend_count = 0
    prev_discr = None
    for mo in months_sorted[-6:]:
        mo_cats = [c for c in cats if c["month"] == mo]
        discr = sum(c["total_amount"] for c in mo_cats
                    if classify_category(c["category"]) == "discretionary")
        if prev_discr is not None and discr < prev_discr:
            discr_trend_count += 1
        else:
            discr_trend_count = 0
        prev_discr = discr

    best_line = (
        f"Best savings rate this year: <strong>{best_rate:.0f}%</strong> in {fmt_month(best_rate_month)}"
        if best_rate_month else ""
    )
    streak_line = (
        f"Expense streak: below 12-month average for <strong>{streak} consecutive months</strong>"
        if streak > 0 else ""
    )
    discr_line = (
        f"Top discipline: discretionary spending trending down for <strong>{discr_trend_count} months</strong>"
        if discr_trend_count >= 2 else ""
    )

    extras = "".join(
        f'<div style="margin-top:8px;font-size:13px;color:{COLORS["text_secondary"]}">{ln}</div>'
        for ln in [best_line, streak_line, discr_line] if ln
    )

    st.markdown(f"""
    <div style="background:{COLORS['bg_card']};border:1px solid #1f2e1f;border-radius:12px;
                padding:28px;margin-bottom:20px">
      <div style="font-size:22px;color:{COLORS['green']};margin-bottom:8px">✓ &nbsp; All clear this period</div>
      <div style="font-size:14px;color:{COLORS['text_secondary']};margin-bottom:12px">
        Your finances look healthy this month.
      </div>
      {extras}
    </div>
    """, unsafe_allow_html=True)


# ── Main render ───────────────────────────────────────────────────────────────

def render_alerts(dashboard: dict | None) -> None:
    if not dashboard:
        st.markdown(f"""
        <div style="background:{COLORS['bg_card']};border:1px solid {COLORS['border']};
                    border-radius:10px;padding:24px;text-align:center;color:{COLORS['text_secondary']}">
          No data available.
        </div>
        """, unsafe_allow_html=True)
        return

    anomalies = classify_anomalies(dashboard)
    score, verdict = _compute_health_score(dashboard, anomalies)

    # ── Filter bar ────────────────────────────────────────────────────────────
    f_col1, f_col2 = st.columns([3, 2])
    with f_col1:
        sev_filter = st.radio(
            "Severity",
            ["All", "Critical only", "Warnings+"],
            horizontal=True,
            index=1,
            key="alerts_sev_filter",
        )
    with f_col2:
        period_filter = st.radio(
            "Period",
            ["This month", "Last 3 months", "All time"],
            horizontal=True,
            index=0,
            key="alerts_period_filter",
        )

    # Apply period filter
    all_months = sorted(
        {a["month"] for a in anomalies if a.get("month")}, reverse=True
    )
    if period_filter == "This month" and all_months:
        anomalies = [a for a in anomalies if a.get("month") == all_months[0]]
    elif period_filter == "Last 3 months" and all_months:
        keep = set(all_months[:3])
        anomalies = [a for a in anomalies if a.get("month") in keep]

    # Apply severity filter
    if sev_filter == "Critical only":
        anomalies = [
            a for a in anomalies
            if a.get("ratio", 0) >= 2.0
            or (a.get("alert_type") == "savings" and a.get("ratio", 1) < 0.6)
        ]
    elif sev_filter == "Warnings+":
        anomalies = [
            a for a in anomalies
            if a.get("ratio", 0) >= 1.4 or a.get("alert_type") == "savings"
        ]

    _render_health_score(score, verdict)

    if not anomalies:
        _render_all_clear(dashboard)
    else:
        _render_alert_cards(anomalies)

        anomaly_cats = {a["category"] for a in anomalies}
        _render_mom_table(dashboard, anomaly_cats)

    _render_savings_narrative(dashboard)
