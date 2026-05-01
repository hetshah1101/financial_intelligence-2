import streamlit as st
import math
from datetime import date

from config import COLORS, API_BASE
from formatters import fmt_inr


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


def render_loans() -> None:
    st.markdown(f"""
    <div style="font-size:11px;letter-spacing:.12em;text-transform:uppercase;
                color:{COLORS['text_secondary']};margin-bottom:20px">
      Loans & Liabilities
    </div>
    """, unsafe_allow_html=True)

    liabilities = _api("/liabilities") or []

    if liabilities:
        _render_summary(liabilities)
        _render_loan_cards(liabilities)
    else:
        st.info("No liabilities recorded. Add one below.")

    _render_add_form()
    _render_prepayment_simulator(liabilities)


def _render_summary(liabilities: list) -> None:
    total_outstanding = sum(l["outstanding"] for l in liabilities)
    total_emi = sum(l.get("emi_amount") or 0 for l in liabilities)
    rates = [l["interest_rate"] for l in liabilities if l.get("interest_rate")]
    # Weighted average rate by outstanding
    total_out = sum(l["outstanding"] for l in liabilities if l.get("interest_rate")) or 1
    wavg_rate = sum(l["interest_rate"] * l["outstanding"] for l in liabilities
                    if l.get("interest_rate")) / total_out

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Outstanding",   fmt_inr(total_outstanding))
    c2.metric("Monthly EMI Outflow", fmt_inr(total_emi))
    c3.metric("Weighted Avg Rate",   f"{wavg_rate:.1f}%" if rates else "—")


def _render_loan_cards(liabilities: list) -> None:
    st.markdown(f"""
    <div style="font-size:11px;letter-spacing:.1em;color:{COLORS['text_tertiary']};
                text-transform:uppercase;margin:20px 0 10px">
      Loan Details
    </div>
    """, unsafe_allow_html=True)

    for loan in liabilities:
        name        = loan["name"]
        outstanding = loan["outstanding"]
        principal   = loan.get("principal") or outstanding
        emi         = loan.get("emi_amount") or 0
        rate        = loan.get("interest_rate") or 0
        end_date    = loan.get("end_date", "")

        paid_pct = max(0, min(100, int((1 - outstanding / principal) * 100))) if principal > 0 else 0

        months_left_str = ""
        if emi > 0 and outstanding > 0:
            months_left = math.ceil(outstanding / emi)
            months_left_str = f"{months_left} months remaining"

        st.markdown(f"""
        <div style="background:{COLORS['bg_card']};border:1px solid {COLORS['border']};
                    border-left:4px solid {COLORS['amber']};
                    border-radius:10px;padding:16px 20px;margin-bottom:10px">
          <div style="display:flex;justify-content:space-between;margin-bottom:10px">
            <div>
              <div style="font-size:14px;color:{COLORS['text_primary']};font-weight:600">{name}</div>
              <div style="font-size:12px;color:{COLORS['text_secondary']}">{loan.get('liability_type','').replace('_',' ').title()}</div>
            </div>
            <div style="text-align:right">
              <div style="font-size:18px;color:{COLORS['text_primary']};font-family:'DM Mono',monospace">{fmt_inr(outstanding)}</div>
              <div style="font-size:12px;color:{COLORS['text_secondary']}">outstanding</div>
            </div>
          </div>
          <div style="background:{COLORS['bg_elevated']};border-radius:4px;height:6px;margin-bottom:8px">
            <div style="background:{COLORS['green']};width:{paid_pct}%;height:6px;border-radius:4px"></div>
          </div>
          <div style="display:flex;justify-content:space-between;font-size:12px;color:{COLORS['text_secondary']}">
            <span>{paid_pct}% paid off</span>
            <span>{months_left_str}</span>
          </div>
          <div style="margin-top:10px;display:flex;gap:20px;font-size:12px;color:{COLORS['text_tertiary']}">
            <span>EMI: <strong style="color:{COLORS['text_secondary']}">{fmt_inr(emi)}/mo</strong></span>
            <span>Rate: <strong style="color:{COLORS['text_secondary']}">{rate}%</strong></span>
            {f'<span>Payoff: <strong style="color:{COLORS["text_secondary"]}">{end_date}</strong></span>' if end_date else ''}
          </div>
        </div>
        """, unsafe_allow_html=True)


def _render_add_form() -> None:
    with st.expander("+ Add / Update Loan"):
        with st.form("add_loan"):
            c1, c2 = st.columns(2)
            name     = c1.text_input("Loan name (e.g. SBI Home Loan)")
            l_type   = c2.selectbox("Type", [
                "home_loan", "car_loan", "personal_loan",
                "education_loan", "credit_card", "other"
            ])
            c3, c4 = st.columns(2)
            principal   = c3.number_input("Principal (₹)", min_value=0.0, step=10000.0)
            outstanding = c4.number_input("Outstanding (₹)", min_value=0.0, step=1000.0)
            c5, c6 = st.columns(2)
            rate   = c5.number_input("Interest rate (%)", min_value=0.0, step=0.1, format="%.2f")
            emi    = c6.number_input("EMI (₹/month)", min_value=0.0, step=500.0)
            c7, c8 = st.columns(2)
            start  = c7.date_input("Start date", value=None)
            end    = c8.date_input("End date / payoff date", value=None)
            submitted = st.form_submit_button("Save Loan")

        if submitted and name and outstanding > 0:
            payload = {
                "name": name,
                "liability_type": l_type,
                "principal": principal or None,
                "outstanding": outstanding,
                "interest_rate": rate or None,
                "emi_amount": emi or None,
                "start_date": str(start) if start else None,
                "end_date": str(end) if end else None,
                "as_of_date": str(date.today()),
            }
            result = _api("/liabilities", method="POST", json=payload)
            if result:
                st.success(f"Loan '{name}' saved.")
                st.rerun()


def _render_prepayment_simulator(liabilities: list) -> None:
    if not liabilities:
        return

    st.markdown(f"""
    <div style="font-size:11px;letter-spacing:.1em;color:{COLORS['text_tertiary']};
                text-transform:uppercase;margin:20px 0 10px">
      Prepayment Simulator
    </div>
    """, unsafe_allow_html=True)

    loan_names = [l["name"] for l in liabilities if l.get("interest_rate") and l.get("emi_amount")]
    if not loan_names:
        st.markdown(f'<div style="color:{COLORS["text_tertiary"]};font-size:13px">Add a loan with rate and EMI to use the simulator.</div>',
                    unsafe_allow_html=True)
        return

    selected = st.selectbox("Select loan", loan_names, key="sim_loan")
    loan = next((l for l in liabilities if l["name"] == selected), None)
    if not loan:
        return

    extra = st.number_input("Extra payment this month (₹)", min_value=0.0, step=1000.0, key="sim_extra")

    if extra > 0 and loan.get("interest_rate") and loan.get("emi_amount"):
        r = loan["interest_rate"] / 100 / 12
        emi = loan["emi_amount"]
        outstanding = loan["outstanding"]

        def months_to_payoff(bal: float, emi_: float, rate: float) -> int:
            if rate == 0:
                return math.ceil(bal / emi_)
            return math.ceil(math.log(emi_ / (emi_ - rate * bal)) / math.log(1 + rate)) if (emi_ - rate * bal) > 0 else 9999

        base_months   = months_to_payoff(outstanding, emi, r)
        extra_months  = months_to_payoff(outstanding - extra, emi, r)
        months_saved  = max(0, base_months - extra_months)

        # Interest saved: rough approximation
        interest_saved = months_saved * emi * (r / (1 + r)) if r > 0 else extra

        st.markdown(f"""
        <div style="background:{COLORS['bg_card']};border:1px solid {COLORS['border']};
                    border-radius:10px;padding:16px 20px;margin-top:8px">
          <div style="display:flex;gap:32px">
            <div>
              <div style="font-size:11px;color:{COLORS['text_secondary']};text-transform:uppercase;letter-spacing:.08em">Months saved</div>
              <div style="font-size:22px;color:{COLORS['green']};font-family:'DM Mono',monospace">{months_saved}</div>
            </div>
            <div>
              <div style="font-size:11px;color:{COLORS['text_secondary']};text-transform:uppercase;letter-spacing:.08em">Interest saved</div>
              <div style="font-size:22px;color:{COLORS['green']};font-family:'DM Mono',monospace">{fmt_inr(interest_saved)}</div>
            </div>
          </div>
          <div style="font-size:12px;color:{COLORS['text_tertiary']};margin-top:10px">
            Paying extra {fmt_inr(extra)} reduces payoff from {base_months} to {extra_months} months.
          </div>
        </div>
        """, unsafe_allow_html=True)
