import plotly.graph_objects as go

from config import COLORS
from formatters import fmt_inr, fmt_month_axis


def base_layout(**kwargs) -> dict:
    """Dark-themed base layout applied to every chart."""
    layout = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color=COLORS["text_secondary"], size=12),
        margin=dict(l=0, r=0, t=36, b=0),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor=COLORS["border"],
            borderwidth=1,
            font=dict(size=11, color=COLORS["text_secondary"]),
        ),
        xaxis=dict(
            gridcolor=COLORS["border_subtle"],
            linecolor=COLORS["border"],
            tickcolor=COLORS["border"],
            tickfont=dict(size=11, color=COLORS["text_secondary"]),
            showgrid=True,
            zeroline=False,
        ),
        yaxis=dict(
            gridcolor=COLORS["border_subtle"],
            linecolor="rgba(0,0,0,0)",
            tickcolor=COLORS["border"],
            tickfont=dict(size=11, family="DM Mono, monospace", color=COLORS["text_secondary"]),
            showgrid=True,
            zeroline=False,
            tickprefix="₹",
        ),
        hoverlabel=dict(
            bgcolor=COLORS["bg_elevated"],
            bordercolor=COLORS["border"],
            font=dict(size=12, color=COLORS["text_primary"]),
        ),
    )
    layout.update(kwargs)
    return layout


def make_overview_bar(
    monthly_data: list,
    selected_month: str | None = None,
    account_monthly: list | None = None,
) -> go.Figure:
    """4-group bar chart: Income / Expense(stacked Bank+Card) / Investment / Net Savings."""
    if selected_month:
        recent = [m for m in monthly_data if m["month"] <= selected_month][-12:]
    else:
        recent = monthly_data[-12:]
    months_raw = [m["month"] for m in recent]
    months_fmt = fmt_month_axis(months_raw)

    # Build per-account expense arrays if account data available
    bank_exp = [0.0] * len(recent)
    card_exp = [0.0] * len(recent)
    has_acct = False
    if account_monthly:
        by_key = {(r["month"], r["account_type"]): r for r in account_monthly}
        for i, m in enumerate(recent):
            b = by_key.get((m["month"], "Bank"))
            c = by_key.get((m["month"], "Card"))
            bank_exp[i] = b["expense"] if b else 0.0
            card_exp[i] = c["expense"] if c else 0.0
        has_acct = any(v > 0 for v in card_exp)  # only split if card data exists

    fig = go.Figure()

    # Group 0 — Income
    fig.add_trace(go.Bar(
        name="Income",
        x=months_fmt,
        y=[m["total_income"] for m in recent],
        marker_color=COLORS["green"],
        marker_line_width=0,
        offsetgroup=0,
        hovertemplate="<b>%{x}</b><br>Income: ₹%{y:,.0f}<extra></extra>",
    ))

    # Group 1 — Expense (stacked Bank + Card, or single total)
    if has_acct:
        fig.add_trace(go.Bar(
            name="Bank Expense",
            x=months_fmt,
            y=bank_exp,
            marker_color=COLORS["red"],
            marker_line_width=0,
            offsetgroup=1,
            hovertemplate="<b>%{x}</b><br>Bank Expense: ₹%{y:,.0f}<extra></extra>",
        ))
        fig.add_trace(go.Bar(
            name="Card Expense",
            x=months_fmt,
            y=card_exp,
            base=bank_exp,
            marker_color=COLORS["amber"],
            marker_line_width=0,
            offsetgroup=1,
            hovertemplate="<b>%{x}</b><br>Card Expense: ₹%{y:,.0f}<extra></extra>",
        ))
    else:
        fig.add_trace(go.Bar(
            name="Expenses",
            x=months_fmt,
            y=[m["total_expense"] for m in recent],
            marker_color=COLORS["red"],
            marker_line_width=0,
            offsetgroup=1,
            hovertemplate="<b>%{x}</b><br>Expenses: ₹%{y:,.0f}<extra></extra>",
        ))

    # Group 2 — Investment
    fig.add_trace(go.Bar(
        name="Investment",
        x=months_fmt,
        y=[m["total_investment"] for m in recent],
        marker_color=COLORS["blue"],
        marker_line_width=0,
        offsetgroup=2,
        hovertemplate="<b>%{x}</b><br>Investment: ₹%{y:,.0f}<extra></extra>",
    ))

    # Group 3 — Net Savings
    fig.add_trace(go.Bar(
        name="Net Savings",
        x=months_fmt,
        y=[m["net_savings"] for m in recent],
        marker_color=COLORS["purple"],
        marker_line_width=0,
        offsetgroup=3,
        hovertemplate="<b>%{x}</b><br>Net Savings: ₹%{y:,.0f}<extra></extra>",
    ))

    if selected_month and selected_month in months_raw:
        idx = months_raw.index(selected_month)
        fig.add_vrect(
            x0=idx - 0.5, x1=idx + 0.5,
            fillcolor="rgba(124,111,205,0.12)",
            layer="below",
            line_width=0,
        )

    fig.update_layout(
        **base_layout(
            title=dict(text="12-Month Overview", font=dict(size=13, color=COLORS["text_secondary"])),
            barmode="group",
            height=320,
        )
    )
    return fig


def make_donut(categories: list) -> go.Figure:
    """Donut chart showing top 5 expense categories + Other."""
    top5 = categories[:5]
    other_amt = sum(c["total_amount"] for c in categories[5:])
    labels = [c["category"] for c in top5] + (["Other"] if other_amt > 0 else [])
    values = [c["total_amount"] for c in top5] + ([other_amt] if other_amt > 0 else [])
    chart_colors = COLORS["chart"][:5] + (["#4a4a48"] if other_amt > 0 else [])

    total = sum(values)
    total_fmt = fmt_inr(total, compact=True)
    sec_color = COLORS["text_secondary"]
    pri_color = COLORS["text_primary"]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.65,
        marker=dict(colors=chart_colors, line=dict(color=COLORS["bg_page"], width=2)),
        textposition="none",
        hovertemplate="<b>%{label}</b><br>₹%{value:,.0f} (%{percent})<extra></extra>",
    ))
    fig.update_layout(
        **base_layout(height=280),
        annotations=[dict(
            text=f"<b>{total_fmt}</b><br><span style='color:{sec_color}'>expenses</span>",
            x=0.5, y=0.5, font_size=14, showarrow=False,
            font=dict(color=pri_color, family="DM Mono, monospace"),
        )],
        showlegend=True,
    )
    return fig


def make_category_bar(
    categories: list,
    current_vals: list,
    baseline_vals: list,
    current_label: str,
    account_cat_data: dict | None = None,
) -> go.Figure:
    """Grouped bar: current (stacked Bank+Card if data available) vs baseline per category."""
    fig = go.Figure()

    if account_cat_data:
        bank_vals = [account_cat_data.get(c, {}).get("Bank", 0.0) for c in categories]
        card_vals = [account_cat_data.get(c, {}).get("Card", 0.0) for c in categories]
        fig.add_trace(go.Bar(
            name="Bank",
            x=categories,
            y=bank_vals,
            marker_color=COLORS["blue"],
            marker_line_width=0,
            offsetgroup="current",
            hovertemplate="<b>%{x}</b><br>Bank: ₹%{y:,.0f}<extra></extra>",
        ))
        fig.add_trace(go.Bar(
            name="Card",
            x=categories,
            y=card_vals,
            base=bank_vals,
            marker_color=COLORS["amber"],
            marker_line_width=0,
            offsetgroup="current",
            hovertemplate="<b>%{x}</b><br>Card: ₹%{y:,.0f}<extra></extra>",
        ))
    else:
        fig.add_trace(go.Bar(
            name=current_label,
            x=categories,
            y=current_vals,
            marker_color=COLORS["purple"],
            marker_line_width=0,
            offsetgroup="current",
            hovertemplate="<b>%{x}</b><br>Current: ₹%{y:,.0f}<extra></extra>",
        ))

    fig.add_trace(go.Bar(
        name="Baseline",
        x=categories,
        y=baseline_vals,
        marker_color=COLORS["border"],
        marker_line_width=0,
        offsetgroup="baseline",
        hovertemplate="<b>%{x}</b><br>Baseline: ₹%{y:,.0f}<extra></extra>",
    ))

    if baseline_vals:
        avg_baseline = sum(baseline_vals) / len(baseline_vals)
        fig.add_hline(
            y=avg_baseline,
            line_dash="dash",
            line_color=COLORS["amber"],
            line_width=1,
            opacity=0.5,
        )
    fig.update_layout(**base_layout(barmode="group", height=320))
    return fig


def make_trends_chart(
    periods: list,
    period_labels: list,
    traces: list,
) -> go.Figure:
    """
    Generic multi-line trend chart.
    traces: list of dicts with keys: y, name, color
    """
    fig = go.Figure()
    for t in traces:
        fig.add_trace(go.Scatter(
            x=period_labels,
            y=t["y"],
            name=t["name"],
            line=dict(color=t["color"], width=2),
            hovertemplate=f"<b>%{{x}}</b><br>{t['name']}: ₹%{{y:,.0f}}<extra></extra>",
        ))
    fig.update_layout(**base_layout(height=320))
    return fig
