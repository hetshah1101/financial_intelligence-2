import io

import pandas as pd
import requests
import streamlit as st
import plotly.graph_objects as go

from config import COLORS, API_BASE
from formatters import fmt_inr


def _api(path: str, method: str = "GET", **kwargs):
    import requests
    try:
        fn = getattr(requests, method.lower())
        r = fn(f"{API_BASE}{path}", timeout=15, **kwargs)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error ({path}): {e}")
        return None


def _render_upload_section() -> None:
    with st.expander("📥 Upload Holdings Snapshot"):
        uploaded = st.file_uploader(
            "Choose a holdings file",
            type=["csv", "xlsx", "xls"],
            key="portfolio_upload",
        )
        if uploaded and st.button("Upload", key="portfolio_upload_btn"):
            resp = requests.post(
                f"{API_BASE}/portfolio/snapshot",
                files={"file": (uploaded.name, uploaded.read())},
                timeout=30,
            )
            if resp.ok:
                data = resp.json()
                st.success(
                    f"Saved {data['rows_inserted']} holdings "
                    f"(skipped {data['rows_skipped']} duplicates)"
                )
                st.rerun()
            else:
                st.error(resp.text)


def _render_crypto_form() -> None:
    with st.expander("₿  Add / Update Crypto Position"):
        with st.form("add_crypto"):
            name   = st.text_input("Asset name (e.g. Bitcoin)")
            symbol = st.text_input("Symbol (e.g. BTC)")
            units  = st.number_input("Units held", min_value=0.0, format="%.8f", step=0.00001)
            avg_px = st.number_input("Avg buy price (₹)", min_value=0.0, step=100.0)
            cur_px = st.number_input("Current price (₹) — enter manually", min_value=0.0, step=100.0)
            submitted = st.form_submit_button("Save Position")

        if submitted and name and units > 0:
            df = pd.DataFrame([{
                "name": name, "symbol": symbol, "instrument_type": "crypto",
                "units": units, "avg_cost_per_unit": avg_px,
                "current_price": cur_px, "account": "Crypto",
            }])
            buf = io.BytesIO(df.to_csv(index=False).encode())
            resp = requests.post(
                f"{API_BASE}/portfolio/snapshot",
                files={"file": ("crypto.csv", buf, "text/csv")},
                timeout=30,
            )
            if resp.ok:
                st.success(f"{name} position saved.")
                st.rerun()
            else:
                st.error(resp.text)


def render_portfolio() -> None:
    st.markdown(f"""
    <div style="font-size:11px;letter-spacing:.12em;text-transform:uppercase;
                color:{COLORS['text_secondary']};margin-bottom:20px">
      Portfolio
    </div>
    """, unsafe_allow_html=True)

    _render_upload_section()
    _render_crypto_form()

    data = _api("/portfolio/latest")
    if not data or not data.get("holdings"):
        _empty_state()
        return

    summary = data["summary"]
    holdings = data["holdings"]
    snap_date = data.get("snapshot_date", "")

    _render_net_worth_header(summary)
    _render_allocation_donut(summary)
    _render_holdings_table(holdings, snap_date)
    _render_sip_tracker(holdings)


def _render_net_worth_header(summary: dict) -> None:
    cv  = summary["total_current_value"]
    iv  = summary["total_invested_value"]
    pnl = summary["total_unrealised_pnl"]
    pct = summary["total_unrealised_pnl_pct"]
    pnl_color = COLORS["green"] if pnl >= 0 else COLORS["red"]
    sign = "+" if pnl >= 0 else ""

    st.markdown(f"""
    <div style="background:{COLORS['bg_card']};border:1px solid {COLORS['border']};
                border-radius:12px;padding:24px 28px;margin-bottom:20px">
      <div style="display:flex;align-items:flex-end;gap:16px;margin-bottom:16px">
        <div>
          <div style="font-size:11px;letter-spacing:.1em;color:{COLORS['text_secondary']};
                      text-transform:uppercase;margin-bottom:4px">Portfolio Value</div>
          <div style="font-size:36px;color:{COLORS['text_primary']};
                      font-family:'DM Mono',monospace;font-weight:600">{fmt_inr(cv)}</div>
        </div>
        <div style="font-size:16px;color:{pnl_color};padding-bottom:4px;
                    font-family:'DM Mono',monospace">
          {sign}{fmt_inr(pnl)} ({sign}{pct:.1f}%)
        </div>
      </div>
      <div style="display:flex;gap:32px">
        <div>
          <div style="font-size:11px;color:{COLORS['text_tertiary']};text-transform:uppercase;
                      letter-spacing:.08em;margin-bottom:2px">Invested</div>
          <div style="font-size:15px;color:{COLORS['text_secondary']};
                      font-family:'DM Mono',monospace">{fmt_inr(iv)}</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def _render_allocation_donut(summary: dict) -> None:
    by_type = summary.get("by_instrument_type", {})
    if not by_type:
        return

    labels = list(by_type.keys())
    values = [by_type[k] for k in labels]
    colors = COLORS["chart"]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.6,
        marker=dict(colors=colors[:len(labels)], line=dict(color=COLORS["bg_page"], width=2)),
        textinfo="label+percent",
        textfont=dict(color=COLORS["text_primary"], size=12),
        hovertemplate="%{label}: ₹%{value:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        legend=dict(font=dict(color=COLORS["text_secondary"], size=11)),
        margin=dict(t=10, b=10, l=10, r=10),
        height=280,
        annotations=[dict(
            text="Allocation",
            x=0.5, y=0.5, font_size=13,
            showarrow=False,
            font=dict(color=COLORS["text_secondary"]),
        )],
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_holdings_table(holdings: list, snap_date: str) -> None:
    st.markdown(f"""
    <div style="font-size:11px;letter-spacing:.1em;color:{COLORS['text_tertiary']};
                text-transform:uppercase;margin:8px 0 10px">
      Holdings &nbsp;<span style="color:{COLORS['text_tertiary']};font-size:10px">
      as of {snap_date}</span>
    </div>
    """, unsafe_allow_html=True)

    col_sort = st.selectbox("Sort by", ["Current Value", "Name", "P&L %", "Instrument Type"],
                            key="holdings_sort", label_visibility="collapsed")

    key_map = {
        "Current Value":    lambda h: -(h.get("current_value") or 0),
        "Name":             lambda h: h.get("name", ""),
        "P&L %":            lambda h: -(h.get("unrealised_pnl_pct") or 0),
        "Instrument Type":  lambda h: h.get("instrument_type", ""),
    }
    holdings = sorted(holdings, key=key_map[col_sort])

    header_html = "".join(
        f'<th style="text-align:left;padding:8px 10px;font-size:11px;'
        f'letter-spacing:.08em;text-transform:uppercase;color:{COLORS["text_secondary"]}">{h}</th>'
        for h in ["Name", "Type", "Units", "Avg Cost", "Current", "Invested", "P&L", "P&L %"]
    )

    row_parts = []
    for h in holdings:
        pnl = h.get("unrealised_pnl") or 0
        pnl_pct = h.get("unrealised_pnl_pct") or 0
        pnl_color = COLORS["green"] if pnl >= 0 else COLORS["red"]
        sign = "+" if pnl >= 0 else ""
        row_parts.append(
            f'<tr style="border-bottom:1px solid {COLORS["border_subtle"]}">'
            f'<td style="padding:8px 10px;font-size:13px;color:{COLORS["text_primary"]}">{h.get("name","")}</td>'
            f'<td style="padding:8px 10px;font-size:12px;color:{COLORS["text_secondary"]}">{h.get("instrument_type","")}</td>'
            f'<td style="padding:8px 10px;font-size:12px;color:{COLORS["text_secondary"]};font-family:\'DM Mono\',monospace">{h.get("units") or "—"}</td>'
            f'<td style="padding:8px 10px;font-size:12px;color:{COLORS["text_secondary"]};font-family:\'DM Mono\',monospace">{fmt_inr(h.get("avg_cost_per_unit") or 0)}</td>'
            f'<td style="padding:8px 10px;font-size:12px;color:{COLORS["text_primary"]};font-family:\'DM Mono\',monospace">{fmt_inr(h.get("current_value") or 0)}</td>'
            f'<td style="padding:8px 10px;font-size:12px;color:{COLORS["text_secondary"]};font-family:\'DM Mono\',monospace">{fmt_inr(h.get("invested_value") or 0)}</td>'
            f'<td style="padding:8px 10px;font-size:12px;color:{pnl_color};font-family:\'DM Mono\',monospace">{sign}{fmt_inr(pnl)}</td>'
            f'<td style="padding:8px 10px;font-size:12px;color:{pnl_color};font-family:\'DM Mono\',monospace">{sign}{pnl_pct:.1f}%</td>'
            f'</tr>'
        )
    rows_html = "".join(row_parts)

    st.markdown(f"""
    <div style="background:{COLORS['bg_card']};border:1px solid {COLORS['border']};
                border-radius:10px;overflow:hidden;margin-bottom:20px">
      <table style="width:100%;border-collapse:collapse">
        <thead><tr style="background:{COLORS['bg_elevated']}">{header_html}</tr></thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>
    """, unsafe_allow_html=True)


def _render_sip_tracker(holdings: list) -> None:
    mf_holdings = [h for h in holdings if h.get("instrument_type") == "mutual_fund"]
    if not mf_holdings:
        return

    st.markdown(f"""
    <div style="font-size:11px;letter-spacing:.1em;color:{COLORS['text_tertiary']};
                text-transform:uppercase;margin:8px 0 10px">
      Mutual Fund Holdings
    </div>
    """, unsafe_allow_html=True)

    for h in mf_holdings:
        cv = h.get("current_value") or 0
        iv = h.get("invested_value") or 0
        pnl = cv - iv
        pnl_color = COLORS["green"] if pnl >= 0 else COLORS["red"]

        st.markdown(f"""
        <div style="background:{COLORS['bg_card']};border:1px solid {COLORS['border']};
                    border-radius:8px;padding:12px 16px;margin-bottom:8px;
                    display:flex;justify-content:space-between;align-items:center">
          <div>
            <div style="font-size:13px;color:{COLORS['text_primary']};margin-bottom:2px">{h.get('name','')}</div>
            <div style="font-size:11px;color:{COLORS['text_secondary']}">{h.get('folio_number') or h.get('isin') or ''}</div>
          </div>
          <div style="text-align:right">
            <div style="font-size:15px;color:{COLORS['text_primary']};font-family:'DM Mono',monospace">{fmt_inr(cv)}</div>
            <div style="font-size:12px;color:{pnl_color};font-family:'DM Mono',monospace">
              {"+" if pnl >= 0 else ""}{fmt_inr(pnl)}
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)


def _empty_state() -> None:
    st.markdown(f"""
    <div style="background:{COLORS['bg_card']};border:1px dashed {COLORS['border']};
                border-radius:12px;padding:40px;text-align:center;margin-top:20px">
      <div style="font-size:32px;margin-bottom:12px">📂</div>
      <div style="font-size:15px;color:{COLORS['text_primary']};margin-bottom:8px">No portfolio data yet</div>
      <div style="font-size:13px;color:{COLORS['text_secondary']}">
        Use the upload section above to import your holdings.
      </div>
    </div>
    """, unsafe_allow_html=True)
