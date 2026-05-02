"""
frontend/tabs/action_plan.py

The Action Plan tab — a single scrollable page that answers one question:
"What do I need to do THIS month to maximise net worth and hit my goals?"

Four sections, top to bottom:
  1. Monthly Pulse      — three hard targets for this month
  2. Cut These First    — spending overages turned into specific actions
  3. Goal Runway        — per-goal gap analysis with required SIP
  4. Stale Data Checks  — reminders to keep data fresh

No charts. No historical analysis. Only decisions and numbers.
"""

import math
import time
import requests
from datetime import date
from statistics import mean

import streamlit as st

from config import COLORS, API_BASE
from formatters import fmt_inr, fmt_month


# ── API helpers ───────────────────────────────────────────────────────────────

def _api(path: str) -> dict | None:
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=8)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _api_action_plan() -> dict | None:
    """Fetch action plan data with 60s session cache (same pattern as api_dashboard)."""
    now = time.time()
    cached = st.session_state.get("_ap_cache")
    ts = st.session_state.get("_ap_ts", 0)
    if cached is not None and now - ts < 60:
        return cached
    data = _api("/action-plan")
    if data is not None:
        st.session_state["_ap_cache"] = data
        st.session_state["_ap_ts"] = now
    return data


# ── Math helpers ──────────────────────────────────────────────────────────────

def _required_sip(pv: float, target: float, months: int, rate: float = 0.12) -> float:
    """Monthly SIP needed to reach `target` from `pv` in `months` months."""
    if months <= 0:
        return float("inf")
    r = rate / 12
    if r == 0:
        return max(0.0, (target - pv) / months)
    growth = (1 + r) ** months
    if growth <= 1:
        return float("inf")
    return max(0.0, (target - pv * growth) * r / (growth - 1))


def _months_to_goal(pv: float, pmt: float, target: float, rate: float = 0.12) -> int | None:
    """Months to reach `target` with monthly SIP `pmt` starting from `pv`."""
    if pmt <= 0:
        return None
    r = rate / 12
    if r == 0:
        return math.ceil((target - pv) / pmt) if pmt > 0 else None
    remaining = target - pv
    if remaining <= 0:
        return 0
    # n = log(pmt / (pmt - r*remaining)) / log(1+r)
    denom = pmt - r * pv
    if denom <= 0:
        return None
    try:
        n = math.log(pmt / denom) / math.log(1 + r)
        return math.ceil(n)
    except (ValueError, ZeroDivisionError):
        return None


def _months_between(from_date: date, to_date: date) -> int:
    return max(0, (to_date.year - from_date.year) * 12 + (to_date.month - from_date.month))


# ── Section divider ───────────────────────────────────────────────────────────

def _section_header(title: str, subtitle: str = "") -> None:
    sub_html = (
        f"<span style='color:{COLORS['text_tertiary']};font-size:12px;"
        f"font-weight:400;margin-left:10px'>{subtitle}</span>"
        if subtitle else ""
    )
    st.markdown(
        f"<div style='font-size:11px;letter-spacing:.12em;text-transform:uppercase;"
        f"color:{COLORS['text_secondary']};margin:32px 0 14px;display:flex;"
        f"align-items:baseline'>{title}{sub_html}</div>",
        unsafe_allow_html=True,
    )


def _thin_rule() -> None:
    st.markdown(
        f'<hr style="border:none;border-top:1px solid {COLORS["border_subtle"]};margin:0 0 16px">',
        unsafe_allow_html=True,
    )


# ── Section 1 — Monthly Pulse ─────────────────────────────────────────────────

def _render_monthly_pulse(monthly: list, budget_baseline: list) -> None:
    if not monthly:
        return

    latest = monthly[-1]
    history = monthly[:-1]

    # ── Target 1: Expense ceiling ─────────────────────────────────────────────
    baseline_total = sum(b["median_3m"] for b in budget_baseline) if budget_baseline else 0
    current_exp = latest.get("total_expense", 0)
    days_in_month = 30  # approximation for "days remaining" framing

    if baseline_total > 0:
        delta = baseline_total - current_exp
        if delta >= 0:
            label_exp = "under ceiling"
            val_exp = delta
            color_exp = COLORS["green"]
            sub_exp = f"{fmt_inr(baseline_total, compact=True)} ceiling"
            context_exp = f"You have {fmt_inr(delta, compact=True)} of room left in your budget baseline."
        else:
            label_exp = "over ceiling"
            val_exp = abs(delta)
            color_exp = COLORS["red"]
            sub_exp = f"{fmt_inr(baseline_total, compact=True)} ceiling"
            context_exp = f"You are {fmt_inr(abs(delta), compact=True)} above your 6-month median. Review the cuts below."
        pct_used = min(100, int(current_exp / baseline_total * 100))
        bar_color = COLORS["green"] if delta >= 0 else COLORS["red"]
    else:
        label_exp = "this month"
        val_exp = current_exp
        color_exp = COLORS["text_secondary"]
        sub_exp = "no baseline yet"
        context_exp = "Upload more months to establish a baseline."
        pct_used = 0
        bar_color = COLORS["border"]

    # ── Target 2: Savings rate ────────────────────────────────────────────────
    h12 = history[-12:]
    avg_rate = mean(m["savings_rate"] for m in h12) if h12 else 20.0
    target_rate = round(max(avg_rate + 2, 20), 1)
    current_rate = latest.get("savings_rate", 0)
    income = latest.get("total_income", 0)
    target_sav_inr = income * target_rate / 100
    current_sav_inr = latest.get("net_savings", 0)
    sav_gap = target_sav_inr - current_sav_inr
    rate_delta = current_rate - target_rate

    if current_rate >= target_rate:
        color_rate = COLORS["green"]
        rate_label = "above target"
        rate_context = f"At {current_rate:.0f}% you are {abs(rate_delta):.1f}pp ahead of your {target_rate:.0f}% target. Strong month."
    elif current_rate >= target_rate - 3:
        color_rate = COLORS["amber"]
        rate_label = "just under"
        rate_context = f"Spend {fmt_inr(abs(sav_gap), compact=True)} less to hit {target_rate:.0f}%. Within reach."
    else:
        color_rate = COLORS["red"]
        rate_label = "below target"
        rate_context = f"Need {fmt_inr(abs(sav_gap), compact=True)} more in savings to reach {target_rate:.0f}% this month."

    rate_bar_pct = min(100, int(current_rate / target_rate * 100)) if target_rate > 0 else 0

    # ── Target 3: Investment floor ────────────────────────────────────────────
    inv_history = [m["total_investment"] for m in history[-3:]] if len(history) >= 1 else []
    inv_floor = mean(inv_history) if inv_history else 0
    current_inv = latest.get("total_investment", 0)
    inv_gap = inv_floor - current_inv

    if inv_floor == 0:
        color_inv = COLORS["text_secondary"]
        inv_label = "no floor yet"
        inv_context = "No investment history to establish a floor. Start investing to set a baseline."
        inv_bar_pct = 0
    elif current_inv >= inv_floor:
        color_inv = COLORS["green"]
        inv_label = "above floor"
        inv_context = f"{fmt_inr(current_inv, compact=True)} invested — {fmt_inr(current_inv - inv_floor, compact=True)} above your 3-month average."
        inv_bar_pct = 100
    else:
        color_inv = COLORS["amber"] if inv_gap < inv_floor * 0.3 else COLORS["red"]
        inv_label = "below floor"
        inv_context = f"Invest {fmt_inr(inv_gap, compact=True)} more to match your 3-month average of {fmt_inr(inv_floor, compact=True)}."
        inv_bar_pct = min(99, int(current_inv / inv_floor * 100)) if inv_floor > 0 else 0

    # ── Render three cards ────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)

    def _pulse_card(col, icon, heading, big_val, big_color, label, bar_pct, bar_color_inner, sub_line, context):
        col.markdown(
            f"""
            <div style="background:{COLORS['bg_card']};border:1px solid {COLORS['border']};
                        border-radius:12px;padding:22px 24px;height:100%">
              <div style="display:flex;align-items:center;gap:8px;margin-bottom:16px">
                <span style="font-size:14px">{icon}</span>
                <span style="font-size:10px;letter-spacing:.1em;text-transform:uppercase;
                             color:{COLORS['text_tertiary']}">{heading}</span>
              </div>
              <div style="font-size:28px;font-family:'DM Mono',monospace;font-weight:600;
                          color:{big_color};line-height:1;margin-bottom:4px">
                {fmt_inr(big_val, compact=True)}
              </div>
              <div style="font-size:12px;color:{big_color};margin-bottom:12px;font-weight:500">
                {label}
                <span style="color:{COLORS['text_tertiary']};font-weight:400;margin-left:4px">
                  · {sub_line}
                </span>
              </div>
              <div style="background:{COLORS['bg_elevated']};border-radius:3px;height:3px;margin-bottom:12px">
                <div style="background:{bar_color_inner};width:{bar_pct}%;height:3px;
                            border-radius:3px;transition:width .3s"></div>
              </div>
              <div style="font-size:12px;color:{COLORS['text_secondary']};line-height:1.6">
                {context}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    _pulse_card(col1, "◎", "Expense Ceiling",
                val_exp, color_exp, label_exp,
                pct_used, bar_color, sub_exp, context_exp)

    _pulse_card(col2, "◈", "Savings Rate",
                abs(sav_gap) if abs(rate_delta) > 0.5 else current_sav_inr,
                color_rate, rate_label,
                rate_bar_pct, color_rate,
                f"target {target_rate:.0f}%", rate_context)

    _pulse_card(col3, "◆", "Investment Floor",
                current_inv if inv_floor == 0 else abs(inv_gap) if inv_gap > 0 else current_inv,
                color_inv, inv_label,
                inv_bar_pct, color_inv,
                f"floor {fmt_inr(inv_floor, compact=True)}/mo", inv_context)


# ── Section 2 — Cut These First ──────────────────────────────────────────────

def _render_spending_actions(savings_opps: list) -> None:
    # Filter noise: only overages > ₹500
    opps = sorted(
        [o for o in savings_opps if o.get("potential_savings", 0) >= 500],
        key=lambda x: -x["potential_savings"],
    )

    if not opps:
        st.markdown(
            f"""
            <div style="background:{COLORS['bg_card']};border:1px solid {COLORS['border']};
                        border-left:3px solid {COLORS['green']};border-radius:10px;
                        padding:18px 22px;display:flex;align-items:center;gap:12px">
              <span style="font-size:18px">✓</span>
              <div>
                <div style="font-size:14px;color:{COLORS['text_primary']};font-weight:500">
                  All spending within baseline
                </div>
                <div style="font-size:12px;color:{COLORS['text_secondary']};margin-top:3px">
                  Every category is at or below your 6-month median. Nothing to cut.
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    total_recoverable = sum(o["potential_savings"] for o in opps)
    annualised = total_recoverable * 12
    ann_fmt = f"₹{annualised/100000:.1f}L/yr" if annualised >= 100000 else fmt_inr(annualised, compact=True) + "/yr"

    # Summary strip
    st.markdown(
        f"""
        <div style="background:{COLORS['bg_elevated']};border-radius:8px;
                    padding:12px 18px;margin-bottom:14px;
                    display:flex;justify-content:space-between;align-items:center">
          <span style="font-size:13px;color:{COLORS['text_secondary']}">
            {len(opps)} categories over baseline
          </span>
          <span style="font-size:13px;color:{COLORS['amber']};font-family:'DM Mono',monospace;font-weight:600">
            {fmt_inr(total_recoverable, compact=True)} recoverable
            <span style="color:{COLORS['text_tertiary']};font-weight:400;font-size:11px">
              &nbsp;· {ann_fmt} if sustained
            </span>
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Action rows — two columns
    col_a, col_b = st.columns(2)
    cols = [col_a, col_b]

    for i, opp in enumerate(opps):
        cat = opp["category"]
        excess = opp["potential_savings"]
        tag = opp.get("tag", "discretionary")
        current = opp.get("current_month_amount", 0)
        baseline_amt = opp.get("median_3m", 0)

        # Severity: >2× baseline = red, 1.5–2× = amber, else blue
        ratio = current / baseline_amt if baseline_amt > 0 else 0
        if ratio >= 2.0:
            severity_color = COLORS["red"]
            severity_dot = "🔴"
        elif ratio >= 1.5:
            severity_color = COLORS["amber"]
            severity_dot = "🟡"
        else:
            severity_color = COLORS["blue"]
            severity_dot = "🔵"

        action = (
            f"Optimize — {fmt_inr(excess, compact=True)} above usual"
            if tag == "essential"
            else f"Cut by {fmt_inr(excess, compact=True)} to hit baseline"
        )

        bar_fill = min(100, int((current / (baseline_amt * 2.5)) * 100)) if baseline_amt > 0 else 50

        cols[i % 2].markdown(
            f"""
            <div style="background:{COLORS['bg_card']};border:1px solid {COLORS['border']};
                        border-left:3px solid {severity_color};
                        border-radius:10px;padding:16px 18px;margin-bottom:10px">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;
                          margin-bottom:10px">
                <div>
                  <span style="font-size:13px;color:{COLORS['text_primary']};font-weight:500">
                    {severity_dot}&nbsp; {cat}
                  </span>
                  <span style="font-size:11px;color:{COLORS['text_tertiary']};margin-left:6px;
                               background:{COLORS['bg_elevated']};padding:2px 7px;border-radius:4px">
                    {tag}
                  </span>
                </div>
                <span style="font-size:14px;font-family:'DM Mono',monospace;
                             color:{severity_color};font-weight:600">
                  +{fmt_inr(excess, compact=True)}
                </span>
              </div>
              <div style="background:{COLORS['bg_elevated']};border-radius:3px;height:3px;margin-bottom:10px">
                <div style="background:{severity_color};opacity:0.7;width:{bar_fill}%;
                            height:3px;border-radius:3px"></div>
              </div>
              <div style="display:flex;justify-content:space-between;
                          font-size:11px;color:{COLORS['text_tertiary']};margin-bottom:8px">
                <span>This month: <span style="color:{COLORS['text_secondary']}">{fmt_inr(current, compact=True)}</span></span>
                <span>Baseline: <span style="color:{COLORS['text_secondary']}">{fmt_inr(baseline_amt, compact=True)}</span></span>
              </div>
              <div style="font-size:12px;color:{COLORS['text_secondary']}">{action}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ── Section 3 — Goal Runway ───────────────────────────────────────────────────

def _render_goal_runway(goals: list, monthly: list) -> None:
    if not goals:
        st.markdown(
            f"""
            <div style="background:{COLORS['bg_card']};border:1px solid {COLORS['border']};
                        border-radius:10px;padding:18px 22px">
              <div style="font-size:13px;color:{COLORS['text_secondary']}">
                No goals set yet.
              </div>
              <div style="font-size:12px;color:{COLORS['text_tertiary']};margin-top:4px">
                Add a goal in the Net Worth tab to see required monthly investment here.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    today = date.today()

    # Compute total available monthly surplus for context
    if monthly:
        latest = monthly[-1]
        monthly_surplus = latest.get("net_savings", 0) - latest.get("total_investment", 0)
    else:
        monthly_surplus = 0

    total_required_sip = 0.0
    goal_rows = []

    for goal in goals:
        target = goal.get("target_amount", 0)
        current_saved = goal.get("current_amount", 0) or 0
        sip = goal.get("monthly_sip", 0) or 0
        name = goal.get("name", "Goal")
        target_date_str = goal.get("target_date")

        if target <= 0:
            continue

        remaining = max(0, target - current_saved)
        pct = min(100, int(current_saved / target * 100)) if target > 0 else 0

        # Months remaining
        if target_date_str:
            try:
                td = date.fromisoformat(str(target_date_str))
                months_left = _months_between(today, td)
                horizon_str = fmt_month(td.strftime("%Y-%m"))
            except Exception:
                months_left = 60
                horizon_str = "5 yr"
        else:
            months_left = 60
            horizon_str = "5 yr est."

        req_sip = _required_sip(current_saved, target, months_left) if months_left > 0 else float("inf")
        total_required_sip += max(0, req_sip - sip)  # only the gap counts as "additional needed"

        # Projection with current SIP
        proj_months = _months_to_goal(current_saved, sip, target) if sip > 0 else None
        if proj_months and proj_months < 99999:
            m = today.month - 1 + proj_months
            proj_date = today.replace(year=today.year + m // 12, month=m % 12 + 1, day=1)
            proj_str = fmt_month(proj_date.strftime("%Y-%m"))
        else:
            proj_str = None

        # On-track logic
        if req_sip == float("inf") or months_left == 0:
            on_track = False
            status = "overdue"
            status_color = COLORS["red"]
        elif sip >= req_sip * 0.98:  # 2% tolerance
            on_track = True
            sip_gap = 0
            status = "on track"
            status_color = COLORS["green"]
        else:
            on_track = False
            sip_gap = req_sip - sip
            if sip >= req_sip * 0.8:
                status = f"₹{sip_gap:,.0f}/mo short"
                status_color = COLORS["amber"]
            else:
                status = f"₹{sip_gap:,.0f}/mo short"
                status_color = COLORS["red"]

        goal_rows.append({
            "name": name,
            "target": target,
            "current_saved": current_saved,
            "remaining": remaining,
            "pct": pct,
            "sip": sip,
            "req_sip": req_sip,
            "on_track": on_track,
            "status": status,
            "status_color": status_color,
            "months_left": months_left,
            "horizon_str": horizon_str,
            "proj_str": proj_str,
        })

    # Total SIP context strip
    if monthly_surplus > 0 and total_required_sip > 0:
        coverage = min(100, int((monthly_surplus / total_required_sip) * 100))
        strip_color = COLORS["green"] if coverage >= 100 else COLORS["amber"] if coverage >= 60 else COLORS["red"]
        st.markdown(
            f"""
            <div style="background:{COLORS['bg_elevated']};border-radius:8px;
                        padding:12px 18px;margin-bottom:14px;
                        display:flex;justify-content:space-between;align-items:center">
              <span style="font-size:13px;color:{COLORS['text_secondary']}">
                {len(goal_rows)} active goals
              </span>
              <span style="font-size:13px;font-family:'DM Mono',monospace;color:{strip_color}">
                {fmt_inr(total_required_sip, compact=True)}/mo additional SIP needed
                <span style="color:{COLORS['text_tertiary']};font-size:11px;font-weight:400">
                  &nbsp;· current surplus covers {coverage}%
                </span>
              </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # One card per goal
    for g in goal_rows:
        pct = g["pct"]
        fill_color = COLORS["green"] if pct >= 80 else COLORS["blue"] if pct >= 40 else COLORS["amber"]
        req_fmt = (
            f"₹{g['req_sip']:,.0f}/mo required"
            if g["req_sip"] != float("inf")
            else "Can't reach by target"
        )
        sip_fmt = f"₹{g['sip']:,.0f}/mo current SIP" if g["sip"] > 0 else "No SIP set"

        # Projection line
        proj_line = ""
        if g["proj_str"]:
            proj_line = f"· At current SIP: done by <strong>{g['proj_str']}</strong>"
        elif g["sip"] == 0:
            proj_line = "· Set a SIP in the Net Worth tab"

        st.markdown(
            f"""
            <div style="background:{COLORS['bg_card']};border:1px solid {COLORS['border']};
                        border-left:3px solid {g['status_color']};
                        border-radius:10px;padding:18px 22px;margin-bottom:10px">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;
                          margin-bottom:14px">
                <div>
                  <div style="font-size:14px;color:{COLORS['text_primary']};font-weight:500;
                              margin-bottom:3px">{g['name']}</div>
                  <div style="font-size:12px;color:{COLORS['text_tertiary']}">
                    Target: <strong style="color:{COLORS['text_secondary']}">{fmt_inr(g['target'], compact=True)}</strong>
                    &nbsp;by&nbsp;<strong style="color:{COLORS['text_secondary']}">{g['horizon_str']}</strong>
                    &nbsp;· {g['months_left']} months left
                  </div>
                </div>
                <div style="text-align:right">
                  <div style="font-size:13px;color:{g['status_color']};font-weight:600">
                    {g['status']}
                  </div>
                  <div style="font-size:11px;color:{COLORS['text_tertiary']};margin-top:2px">
                    {fmt_inr(g['remaining'], compact=True)} remaining
                  </div>
                </div>
              </div>
              <div style="background:{COLORS['bg_elevated']};border-radius:3px;
                          height:4px;margin-bottom:12px;overflow:hidden">
                <div style="background:{fill_color};width:{pct}%;height:4px;border-radius:3px"></div>
              </div>
              <div style="display:flex;justify-content:space-between;align-items:center;
                          font-size:12px;flex-wrap:wrap;gap:6px">
                <div style="display:flex;gap:18px">
                  <span style="color:{COLORS['text_tertiary']}">{sip_fmt}</span>
                  <span style="color:{COLORS['text_secondary']};font-weight:500">{req_fmt}</span>
                </div>
                <span style="color:{COLORS['text_tertiary']}">{proj_line}</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ── Section 4 — Stale Data Checks ────────────────────────────────────────────

def _render_stale_checks(snapshot_date_str: str | None, monthly: list) -> None:
    reminders = []

    # Check 1: portfolio snapshot age
    if snapshot_date_str is None:
        reminders.append({
            "icon": "📂",
            "title": "No portfolio snapshot",
            "body": "Upload a holdings CSV in the Portfolio tab to track net worth and goal progress accurately.",
            "color": COLORS["amber"],
        })
    else:
        try:
            snap_date = date.fromisoformat(snapshot_date_str)
            days_ago = (date.today() - snap_date).days
            if days_ago > 30:
                reminders.append({
                    "icon": "📂",
                    "title": f"Portfolio snapshot is {days_ago} days old",
                    "body": "Export a fresh holdings CSV from your broker and upload it in the Portfolio tab.",
                    "color": COLORS["amber"] if days_ago < 60 else COLORS["red"],
                })
        except (ValueError, TypeError):
            pass

    # Check 2: latest month has investment but no portfolio record
    if monthly:
        latest = monthly[-1]
        inv_amount = latest.get("total_investment", 0)
        latest_month_str = latest.get("month", "")
        if inv_amount > 0 and snapshot_date_str:
            # Check if snapshot covers the latest month
            try:
                snap_date = date.fromisoformat(snapshot_date_str)
                latest_month_date = date.fromisoformat(latest_month_str + "-01")
                if snap_date < latest_month_date:
                    reminders.append({
                        "icon": "◆",
                        "title": f"{fmt_inr(inv_amount, compact=True)} invested in {fmt_month(latest_month_str)} not reflected in portfolio",
                        "body": "Your portfolio snapshot predates this month's investments. Upload a fresh snapshot to keep net worth accurate.",
                        "color": COLORS["blue"],
                    })
            except (ValueError, TypeError):
                pass

    # Check 3: no data at all
    if not monthly:
        reminders.append({
            "icon": "⊞",
            "title": "No transaction data",
            "body": "Upload a CSV in the Data tab to get started.",
            "color": COLORS["border"],
        })

    if not reminders:
        st.markdown(
            f"""
            <div style="background:{COLORS['bg_card']};border:1px solid {COLORS['border']};
                        border-left:3px solid {COLORS['green']};
                        border-radius:10px;padding:14px 18px;
                        display:flex;align-items:center;gap:10px">
              <span style="font-size:14px">✓</span>
              <span style="font-size:13px;color:{COLORS['text_secondary']}">
                All data sources up to date
              </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    for r in reminders:
        st.markdown(
            f"""
            <div style="background:{COLORS['bg_card']};border:1px solid {COLORS['border']};
                        border-left:3px solid {r['color']};
                        border-radius:10px;padding:14px 18px;margin-bottom:8px;
                        display:flex;align-items:flex-start;gap:12px">
              <span style="font-size:16px;margin-top:1px">{r['icon']}</span>
              <div>
                <div style="font-size:13px;color:{COLORS['text_primary']};font-weight:500;
                            margin-bottom:3px">{r['title']}</div>
                <div style="font-size:12px;color:{COLORS['text_secondary']}">{r['body']}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ── Top summary bar ───────────────────────────────────────────────────────────

def _render_summary_bar(monthly: list, goals: list) -> None:
    """Single-line context strip at the very top — month + net worth direction."""
    if not monthly:
        return

    latest = monthly[-1]
    current_month = fmt_month(latest["month"])
    net_sav = latest.get("net_savings", 0)
    rate = latest.get("savings_rate", 0)

    # Goals: how many on track (re-compute quickly for summary)
    today = date.today()
    on_track_count = 0
    total_goals = 0
    for g in goals:
        target = g.get("target_amount", 0)
        current_saved = g.get("current_amount", 0) or 0
        sip = g.get("monthly_sip", 0) or 0
        target_date_str = g.get("target_date")
        if target <= 0:
            continue
        total_goals += 1
        if target_date_str and sip > 0:
            try:
                td = date.fromisoformat(str(target_date_str))
                months_left = _months_between(today, td)
                req = _required_sip(current_saved, target, months_left)
                if sip >= req * 0.98:
                    on_track_count += 1
            except Exception:
                pass

    sav_color = COLORS["green"] if net_sav >= 0 else COLORS["red"]
    goal_str = (
        f"&nbsp;·&nbsp; {on_track_count}/{total_goals} goals on track"
        if total_goals > 0 else ""
    )

    st.markdown(
        f"""
        <div style="background:{COLORS['bg_elevated']};border-radius:8px;
                    padding:10px 16px;margin-bottom:24px;
                    display:flex;justify-content:space-between;align-items:center">
          <span style="font-size:12px;color:{COLORS['text_secondary']}">
            {current_month}
          </span>
          <span style="font-size:12px;color:{COLORS['text_tertiary']}">
            Net savings&nbsp;
            <span style="color:{sav_color};font-family:'DM Mono',monospace;font-weight:600">
              {fmt_inr(net_sav, compact=True)}
            </span>
            &nbsp;·&nbsp; Savings rate&nbsp;
            <span style="color:{sav_color};font-family:'DM Mono',monospace;font-weight:600">
              {rate:.0f}%
            </span>
            {goal_str}
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Main render ───────────────────────────────────────────────────────────────

def render_action_plan(dashboard: dict | None) -> None:
    if not dashboard:
        st.markdown(
            f"""
            <div style="display:flex;flex-direction:column;align-items:center;
                        justify-content:center;min-height:40vh;text-align:center;padding-top:48px">
              <div style="font-size:32px;color:{COLORS['border']};margin-bottom:16px">⊕</div>
              <div style="font-size:15px;color:{COLORS['text_primary']};margin-bottom:8px">
                No data yet
              </div>
              <div style="font-size:13px;color:{COLORS['text_secondary']}">
                Upload transaction data to generate your action plan.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # Fetch action-plan-specific data (goals + snapshot date)
    ap = _api_action_plan() or {}
    goals = ap.get("goals", [])
    snapshot_date = ap.get("portfolio_snapshot_date")

    monthly = sorted(dashboard.get("monthly_aggregates", []), key=lambda x: x["month"])
    budget_baseline = dashboard.get("budget_baseline", [])
    savings_opps = dashboard.get("savings_opportunities", [])

    if not monthly:
        st.info("No monthly data available.")
        return

    # ── Top bar ───────────────────────────────────────────────────────────────
    _render_summary_bar(monthly, goals)

    # ── Section 1 ─────────────────────────────────────────────────────────────
    _section_header("This Month's Targets", "three numbers to beat")
    _render_monthly_pulse(monthly, budget_baseline)

    # ── Section 2 ─────────────────────────────────────────────────────────────
    _section_header("Cut These First", "spending above your 6-month baseline")
    _render_spending_actions(savings_opps)

    # ── Section 3 ─────────────────────────────────────────────────────────────
    _section_header("Goal Runway", "required SIP vs current SIP")
    _render_goal_runway(goals, monthly)

    # ── Section 4 ─────────────────────────────────────────────────────────────
    _section_header("Keep Data Fresh")
    _render_stale_checks(snapshot_date, monthly)
