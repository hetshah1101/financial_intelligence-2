# Financial Intelligence System — Complete UI/UX Revamp Spec for Claude Code

## MISSION

Revamp the existing Streamlit frontend into a production-grade, dark-themed personal finance
dashboard inspired by the Cashmate UI aesthetic: deep dark backgrounds, monospaced typography
for financial numbers, muted color palette with sharp semantic accents, and data-dense but
visually calm layouts.

The system already has a working FastAPI backend at `http://localhost:8000/api/v1`.
**Do NOT modify any backend files.** Only revamp `frontend/streamlit_app.py`.

---

## VISUAL IDENTITY (Non-negotiable)

### Color Palette
```python
COLORS = {
    # Backgrounds
    "bg_base":       "#0a0a0a",   # page background
    "bg_card":       "#111111",   # card surfaces
    "bg_elevated":   "#1c1c1c",   # inputs, dropdowns
    "border":        "#242424",   # card borders
    "border_subtle": "#1a1a1a",   # inner dividers

    # Text
    "text_primary":   "#e8e6e0",
    "text_secondary": "#888780",
    "text_tertiary":  "#4a4a48",

    # Semantic
    "green":   "#4caf7d",   # income, positive delta
    "red":     "#e05252",   # expense, negative delta
    "amber":   "#c9883a",   # investment, warning
    "blue":    "#4a90c4",   # neutral info
    "purple":  "#7c6fcd",   # savings, active nav

    # Chart series (muted, cohesive — use in order)
    "chart": ["#7c6fcd", "#4caf7d", "#c9883a", "#4a90c4", "#e05252", "#888780"],
}
```

### Typography Rules
- **Financial numbers**: `DM Mono` or `JetBrains Mono` — always monospaced
- **Labels / body**: `DM Sans` or `Inter`
- **Section headers**: ALL CAPS + `letter-spacing: 0.1em`, `font-size: 11px`, `color: #888780`
- **KPI values**: `28px`, monospaced, `#e8e6e0`

### Spacing System
- Base unit: `8px`
- Card padding: `24px`
- Gap between cards: `12px`
- Border radius: `10px` cards, `6px` chips/badges

---

## GLOBAL LAYOUT

```
┌─────────────────┬──────────────────────────────────────────────┐
│  SIDEBAR 260px  │  MAIN CONTENT AREA (fluid)                   │
│                 │                                              │
│  ₹ Finsight    │  [Active Tab Content]                        │
│                 │                                              │
│  ─ Navigation   │                                              │
│  ─ Date Range   │                                              │
│  ─ Upload       │                                              │
│  ─ API Status   │                                              │
└─────────────────┴──────────────────────────────────────────────┘
```

### Sidebar CSS Overrides
```python
st.markdown("""
<style>
    #MainMenu, footer, header { visibility: hidden; }
    .stDeployButton { display: none; }
    [data-testid="stSidebar"] { width: 260px !important; }
    [data-testid="stSidebar"] > div {
        background: #0d0d0d !important;
        border-right: 1px solid #1a1a1a;
    }
    .main .block-container { padding: 24px 32px !important; max-width: 100% !important; }
    div[data-testid="stHorizontalBlock"] { gap: 12px !important; }
    /* Metric cards */
    [data-testid="stMetric"] { background: #111; border: 1px solid #242424;
        border-radius: 10px; padding: 20px 24px; }
    [data-testid="stMetricLabel"] { font-size: 11px; letter-spacing: 0.1em;
        text-transform: uppercase; color: #888780 !important; }
    [data-testid="stMetricValue"] { font-family: 'DM Mono', monospace;
        font-size: 28px; color: #e8e6e0 !important; }
    /* Dataframe */
    [data-testid="stDataFrame"] { background: #111; border: 1px solid #242424; }
    /* Tabs */
    .stTabs [data-baseweb="tab"] { background: transparent;
        color: #4a4a48; font-size: 13px; }
    .stTabs [aria-selected="true"] { color: #e8e6e0 !important;
        border-bottom: 2px solid #7c6fcd !important; }
    /* Selectbox, slider */
    .stSelectbox > div > div { background: #1c1c1c !important;
        border-color: #242424 !important; color: #e8e6e0 !important; }
    /* Alert-style info boxes */
    .alert-card { background: #111; border-left: 3px solid #e05252;
        border-radius: 0 8px 8px 0; padding: 16px 20px; margin-bottom: 8px; }
</style>
""", unsafe_allow_html=True)
```

### Date Range Selector (Global State — top of sidebar)
```python
DATE_RANGE_OPTIONS = {
    "Last 3 Months": "3m",
    "Last 6 Months": "6m",
    "This Year":     "1y",
    "All Time":      "all",
}
```
- Drives all visualizations across tabs
- Show selected range below: e.g. `Jan 2024 – Jun 2024`
- Store in `st.session_state["date_range"]`

---

## NAVIGATION (5 Intent-Based Tabs)

```python
TABS = {
    "overview": ("▣", "Overview",  "What's my current state?"),
    "compare":  ("⟺", "Compare",   "Am I better or worse?"),
    "trends":   ("↗",  "Trends",    "How is behavior evolving?"),
    "alerts":   ("⚠",  "Alerts",    "What's wrong or unusual?"),
    "data":     ("⊞",  "Data",      "Upload and manage data"),
}
```

Use `st.tabs()` or radio-button nav. Active tab: `#7c6fcd` accent.

---

## STATE MANAGEMENT

Initialize ALL state upfront, no cross-tab leakage:
```python
DEFAULTS = {
    "date_range":        "3m",
    "compare_month":     None,        # YYYY-MM, auto-set to latest
    "compare_baseline":  "recent_avg",
    "trend_granularity": "monthly",
    "trend_mode":        "system",    # "system" | "category"
    "trend_metric":      "total_expense",
    "trend_category":    None,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v
```

---

## NUMBER FORMATTING

```python
def fmt_inr(val: float, compact: bool = False) -> str:
    """Indian number system formatting."""
    if compact:
        if abs(val) >= 1_00_000:
            return f"₹{val/1_00_000:.1f}L"
        elif abs(val) >= 1_000:
            return f"₹{val/1_000:.1f}K"
        return f"₹{val:.0f}"
    # Full Indian grouping: ₹1,23,456
    neg = val < 0
    s = f"{abs(val):.0f}"
    if len(s) > 3:
        last3, rest = s[-3:], s[:-3]
        parts = []
        while len(rest) > 2:
            parts.append(rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.append(rest)
        s = ",".join(reversed(parts)) + "," + last3
    return f"{'−' if neg else ''}₹{s}"

def fmt_delta(val: float) -> tuple[str, str]:
    """Returns (formatted_string, color)."""
    if val > 0:
        return f"▲ +{val:.1f}%", "#e05252"   # expense up = bad
    elif val < 0:
        return f"▼ {val:.1f}%", "#4caf7d"    # expense down = good
    return "─ 0%", "#888780"

def fmt_pct(val: float) -> str:
    sign = "+" if val > 0 else ""
    return f"{sign}{val:.1f}%"
```

---

## API LAYER

```python
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

@st.cache_data(ttl=60)
def api_dashboard() -> dict | None:
    try:
        r = requests.get(f"{API_BASE}/dashboard", timeout=8)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

@st.cache_data(ttl=300)
def api_insights(month: str, refresh: bool = False) -> str | None:
    try:
        r = requests.get(f"{API_BASE}/insights/{month}",
                         params={"refresh": refresh}, timeout=120)
        r.raise_for_status()
        return r.json().get("insights")
    except Exception:
        return None

@st.cache_data(ttl=60)
def api_months() -> list[str]:
    try:
        r = requests.get(f"{API_BASE}/months", timeout=5)
        return r.json().get("months", [])
    except Exception:
        return []

def api_upload(endpoint: str, file) -> dict | None:
    try:
        r = requests.post(f"{API_BASE}{endpoint}",
                          files={"file": (file.name, file.read())},
                          timeout=300)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Upload failed: {e}")
        return None
```

---

## ANALYTICS (Compute Client-Side from API Data)

### Filter by Date Range
```python
def filter_by_date_range(monthly_data: list, date_range: str) -> list:
    if not monthly_data:
        return []
    n = {"3m": 3, "6m": 6, "1y": 12, "all": 999}.get(date_range, 3)
    return monthly_data[-n:]
```

### Compute Baseline
```python
from statistics import mean

def compute_baseline(monthly_data: list, baseline_type: str) -> dict | None:
    if len(monthly_data) < 2:
        return None
    history = monthly_data[:-1]   # exclude current month
    if baseline_type == "last_month":
        window = [history[-1]] if history else []
    elif baseline_type == "recent_avg":
        window = history[-3:]
    elif baseline_type == "longterm_avg":
        window = history[-6:]
    else:  # all_time
        window = history
    if not window:
        return None
    return {
        "total_income":     mean(m["total_income"]     for m in window),
        "total_expense":    mean(m["total_expense"]    for m in window),
        "total_investment": mean(m["total_investment"] for m in window),
        "net_savings":      mean(m["net_savings"]      for m in window),
        "savings_rate":     mean(m["savings_rate"]     for m in window),
    }
```

### Behavioral Split
```python
ESSENTIAL_CATEGORIES = {
    "Food", "Utilities", "Health", "Transport", "Tax",
    "Insurance", "Rent", "EMI", "Education"
}

def behavioral_split(categories: list) -> dict:
    essential = sum(c["total_amount"] for c in categories
                    if c["category"] in ESSENTIAL_CATEGORIES)
    discr = sum(c["total_amount"] for c in categories
                if c["category"] not in ESSENTIAL_CATEGORIES)
    total = essential + discr or 1
    return {
        "essential_pct": essential / total * 100,
        "discretionary_pct": discr / total * 100,
        "essential_amount": essential,
        "discretionary_amount": discr,
        "essential_cats": [c for c in categories if c["category"] in ESSENTIAL_CATEGORIES][:3],
        "discr_cats": [c for c in categories if c["category"] not in ESSENTIAL_CATEGORIES][:3],
    }
```

### Key Takeaways (auto-generated, deterministic)
```python
def generate_takeaways(latest: dict, baseline: dict | None, categories: list) -> list[str]:
    tips = []
    if baseline and baseline["total_expense"] > 0:
        delta = (latest["total_expense"] - baseline["total_expense"]) / baseline["total_expense"] * 100
        direction = "above" if delta > 0 else "below"
        if abs(delta) > 3:
            tips.append(f"Expenses {abs(delta):.0f}% {direction} your recent 3-month average")
    if categories:
        top = categories[0]
        tips.append(f"{top['category']} is your largest expense at {top['percentage_of_total']:.0f}% of spending")
    rate = latest.get("savings_rate", 0)
    status = "on track" if rate >= 20 else "below recommended 20% threshold"
    tips.append(f"Savings rate {rate:.0f}% this month — {status}")
    inv = latest.get("total_investment", 0)
    if inv > 0:
        tips.append(f"₹{inv/1000:.0f}K invested this month")
    return tips[:4]
```

---

## PLOTLY THEME

```python
import plotly.graph_objects as go

def base_layout(**kwargs) -> dict:
    layout = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color="#888780", size=12),
        margin=dict(l=0, r=0, t=36, b=0),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#242424",
                    borderwidth=1, font=dict(size=11, color="#888780")),
        xaxis=dict(gridcolor="#1a1a1a", linecolor="#242424", tickcolor="#242424",
                   tickfont=dict(size=11, color="#888780"), showgrid=True, zeroline=False),
        yaxis=dict(gridcolor="#1a1a1a", linecolor="rgba(0,0,0,0)", tickcolor="#242424",
                   tickfont=dict(size=11, family="DM Mono, monospace", color="#888780"),
                   showgrid=True, zeroline=False, tickprefix="₹"),
        hoverlabel=dict(bgcolor="#1c1c1c", bordercolor="#242424",
                        font=dict(size=12, color="#e8e6e0")),
    )
    layout.update(kwargs)
    return layout

CHART_COLORS = ["#7c6fcd", "#4caf7d", "#c9883a", "#4a90c4", "#e05252", "#888780"]
```

---

## TAB 1: OVERVIEW

Render in this order:

### 1a. Key Takeaways Banner
```python
# Compute takeaways and render as styled HTML bullets
takeaways = generate_takeaways(latest, baseline_3m, categories)
bullets = "".join(f"<li>{t}</li>" for t in takeaways)
st.markdown(f"""
<div style="background:#111;border:1px solid #1a1a1a;border-radius:10px;
            padding:16px 20px;margin-bottom:20px">
  <div style="font-size:11px;letter-spacing:.1em;color:#4a4a48;
              text-transform:uppercase;margin-bottom:10px">This Month</div>
  <ul style="margin:0;padding-left:18px;color:#888780;font-size:13px;
             line-height:1.8">{bullets}</ul>
</div>
""", unsafe_allow_html=True)
```

### 1b. KPI Row — 4 columns
Each column: `st.metric()` with `label`, `value=fmt_inr(...)`, `delta=fmt_delta_str`

Custom delta colors using `st.markdown` HTML cards if `st.metric` delta colors insufficient.

Columns:
1. INCOME — `total_income`, delta vs baseline income
2. EXPENSES — `total_expense`, delta vs baseline (positive delta = red, negative = green)
3. INVESTMENTS — `total_investment`, delta vs baseline
4. NET SAVINGS — `net_savings`, secondary metric = `f"Rate: {savings_rate:.0f}%"`

### 1c. Charts Row — 2 columns (col ratio 6:4)

**Left: Income vs Expense Line Chart**
```python
fig = go.Figure()
# Income line
fig.add_trace(go.Scatter(
    x=[m["month"] for m in filtered_monthly],
    y=[m["total_income"] for m in filtered_monthly],
    name="Income", line=dict(color="#4caf7d", width=2),
    fill="tozeroy", fillcolor="rgba(76,175,125,0.06)",
    hovertemplate="<b>%{x}</b><br>Income: ₹%{y:,.0f}<extra></extra>",
))
# Expense line
fig.add_trace(go.Scatter(
    x=[m["month"] for m in filtered_monthly],
    y=[m["total_expense"] for m in filtered_monthly],
    name="Expenses", line=dict(color="#e05252", width=2),
    fill="tozeroy", fillcolor="rgba(224,82,82,0.06)",
    hovertemplate="<b>%{x}</b><br>Expense: ₹%{y:,.0f}<extra></extra>",
))
# Rolling avg (dashed)
if len(filtered_monthly) >= 3:
    avgs = [mean([m["total_expense"] for m in filtered_monthly[max(0,i-2):i+1]])
            for i in range(len(filtered_monthly))]
    fig.add_trace(go.Scatter(
        x=[m["month"] for m in filtered_monthly], y=avgs,
        name="3m Avg", line=dict(color="#7c6fcd", width=1, dash="dash"),
        hoverinfo="skip",
    ))
fig.update_layout(**base_layout(height=280))
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
```

**Right: Category Donut**
```python
top5 = categories[:5]
other_amt = sum(c["total_amount"] for c in categories[5:])
labels = [c["category"] for c in top5] + (["Other"] if other_amt > 0 else [])
values = [c["total_amount"] for c in top5] + ([other_amt] if other_amt > 0 else [])
colors = CHART_COLORS[:5] + (["#4a4a48"] if other_amt > 0 else [])

fig = go.Figure(go.Pie(
    labels=labels, values=values, hole=0.65,
    marker=dict(colors=colors, line=dict(color="#0a0a0a", width=2)),
    textposition="none",
    hovertemplate="<b>%{label}</b><br>₹%{value:,.0f} (%{percent})<extra></extra>",
))
# Center annotation
fig.update_layout(
    **base_layout(height=280),
    annotations=[dict(
        text=f"<b>{fmt_inr(sum(values), compact=True)}</b><br><span style='color:#888'>expenses</span>",
        x=0.5, y=0.5, font_size=14, showarrow=False,
        font=dict(color="#e8e6e0", family="DM Mono, monospace"),
    )],
    showlegend=True,
)
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
```

### 1d. Behavioral Split
```python
split = behavioral_split(categories)
ess_pct = split["essential_pct"]
dis_pct = split["discretionary_pct"]

st.markdown(f"""
<div style="background:#111;border:1px solid #242424;border-radius:10px;padding:20px 24px">
  <div style="font-size:11px;letter-spacing:.1em;color:#4a4a48;
              text-transform:uppercase;margin-bottom:12px">Spending Behavior</div>
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">
    <span style="color:#888780;font-size:12px;width:120px">Essential</span>
    <div style="flex:1;height:8px;background:#1c1c1c;border-radius:4px;overflow:hidden">
      <div style="width:{ess_pct:.0f}%;height:100%;background:#4a90c4;border-radius:4px"></div>
    </div>
    <span style="color:#e8e6e0;font-size:12px;font-family:monospace;width:40px;
                 text-align:right">{ess_pct:.0f}%</span>
  </div>
  <div style="display:flex;align-items:center;gap:12px">
    <span style="color:#888780;font-size:12px;width:120px">Discretionary</span>
    <div style="flex:1;height:8px;background:#1c1c1c;border-radius:4px;overflow:hidden">
      <div style="width:{dis_pct:.0f}%;height:100%;background:#c9883a;border-radius:4px"></div>
    </div>
    <span style="color:#e8e6e0;font-size:12px;font-family:monospace;width:40px;
                 text-align:right">{dis_pct:.0f}%</span>
  </div>
</div>
""", unsafe_allow_html=True)
```

---

## TAB 2: COMPARE

### Controls Row
```python
col_month, col_baseline = st.columns([1, 2])
with col_month:
    months = api_months()
    idx = 0  # default to latest
    selected_month = st.selectbox("Month", months, index=idx, key="compare_month_sel")
    st.session_state["compare_month"] = selected_month

with col_baseline:
    BASELINE_OPTIONS = {
        "Last Month":       "last_month",
        "Recent Avg (3m)":  "recent_avg",
        "Long-term (6m)":   "longterm_avg",
        "All Time Avg":     "all_time",
    }
    baseline_label = st.radio("Compare against", list(BASELINE_OPTIONS.keys()),
                               horizontal=True, key="compare_baseline_radio")
    baseline_type = BASELINE_OPTIONS[baseline_label]
    st.session_state["compare_baseline"] = baseline_type
```

### Delta KPI Cards (3 columns)
Compute and display:
1. Total Expense — `fmt_inr(current_expense)`, delta vs baseline
2. Biggest Increase — category with highest positive diff
3. Biggest Saving — category with highest negative diff

### Grouped Bar Chart
```python
# Build per-category comparison
current_cats = {c["category"]: c["total_amount"] for c in current_categories}
# Baseline cats: recompute from historical months or use rolling category avg
all_cats = sorted(set(current_cats.keys()), key=lambda c: -current_cats.get(c, 0))[:10]

fig = go.Figure()
fig.add_trace(go.Bar(
    name=f"{selected_month}", x=all_cats,
    y=[current_cats.get(c, 0) for c in all_cats],
    marker_color="#7c6fcd", marker_line_width=0, width=0.35,
    hovertemplate="<b>%{x}</b><br>Current: ₹%{y:,.0f}<extra></extra>",
))
fig.add_trace(go.Bar(
    name="Baseline", x=all_cats,
    y=[baseline_cats.get(c, 0) for c in all_cats],
    marker_color="#3a3a3a", marker_line_width=0, width=0.35,
    hovertemplate="<b>%{x}</b><br>Baseline: ₹%{y:,.0f}<extra></extra>",
))
fig.update_layout(**base_layout(barmode="group", height=320))
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
```

### Category Comparison Table
```python
# Build dataframe with diff and pct columns
df_compare["Diff"] = df_compare["Current"] - df_compare["Baseline"]
df_compare["% Change"] = (df_compare["Diff"] / df_compare["Baseline"] * 100).round(1)

# Style: color % change column
def color_diff(val):
    color = "#e05252" if val > 0 else "#4caf7d"
    return f"color: {color}"

styled = df_compare.style.applymap(color_diff, subset=["% Change"])
st.dataframe(styled, use_container_width=True, hide_index=True)
```

---

## TAB 3: TRENDS

### Controls Row
```python
col_gran, col_mode, col_cat = st.columns([2, 2, 2])

with col_gran:
    gran = st.radio("Granularity", ["Weekly", "Monthly", "Yearly"],
                    horizontal=True, key="trend_gran")

with col_mode:
    mode = st.radio("View", ["System Metrics", "By Category"],
                    horizontal=True, key="trend_mode_radio")

with col_cat:
    if mode == "By Category":
        cats = list({c["category"] for m_data in all_monthly_cats for c in m_data})
        st.selectbox("Category", sorted(cats), key="trend_category_sel")
```

### Main Line Chart
```python
fig = go.Figure()

if mode == "System Metrics":
    metrics = [
        ("total_expense",    "Expenses",    "#e05252"),
        ("total_income",     "Income",      "#4caf7d"),
        ("net_savings",      "Savings",     "#7c6fcd"),
    ]
    for key, label, color in metrics:
        y = [m[key] for m in filtered_monthly]
        fig.add_trace(go.Scatter(
            x=[m["month"] for m in filtered_monthly], y=y,
            name=label, line=dict(color=color, width=2),
            hovertemplate=f"<b>%{{x}}</b><br>{label}: ₹%{{y:,.0f}}<extra></extra>",
        ))
        # Rolling 3m avg overlay
        if len(y) >= 3:
            avgs = [mean(y[max(0,i-2):i+1]) for i in range(len(y))]
            fig.add_trace(go.Scatter(
                x=[m["month"] for m in filtered_monthly], y=avgs,
                name=f"{label} avg", line=dict(color=color, width=1, dash="dash"),
                opacity=0.5, hoverinfo="skip",
            ))
else:
    # Single category
    selected_cat = st.session_state.get("trend_category_sel")
    y = []  # build from category_aggregates by month
    fig.add_trace(go.Scatter(
        x=[m["month"] for m in filtered_monthly], y=y,
        name=selected_cat, line=dict(color="#7c6fcd", width=2),
    ))

# Annotate peak and trough
# ... add shapes/annotations for min/max points

fig.update_layout(**base_layout(height=320))
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
```

### Insight Strip (below chart)
```python
# Compute: trend direction, peak month, avg, volatility
trend_dir = "Increasing" if y[-1] > y[0] else "Decreasing" if y[-1] < y[0] else "Stable"
peak_month = months[y.index(max(y))]
avg_val = mean(y)

chips = [
    f"{'↗' if trend_dir == 'Increasing' else '↘' if trend_dir == 'Decreasing' else '→'} Trend: {trend_dir}",
    f"Peak: {fmt_inr(max(y), compact=True)} in {peak_month}",
    f"Avg: {fmt_inr(avg_val, compact=True)}/month",
]
chips_html = " &nbsp; ".join(
    f'<span style="background:#1c1c1c;border:1px solid #242424;border-radius:6px;'
    f'padding:4px 12px;font-size:12px;color:#888780">{c}</span>'
    for c in chips
)
st.markdown(f'<div style="margin-top:12px">{chips_html}</div>', unsafe_allow_html=True)
```

---

## TAB 4: ALERTS

### Alert Cards
Render each anomaly from `dashboard["anomalies"]` as a styled HTML card.

```python
ALERT_BORDER_COLORS = {
    "spike":    "#e05252",
    "variance": "#c9883a",
    "new_cat":  "#4a90c4",
    "savings":  "#7c6fcd",
}

for anomaly in anomalies:
    excess = anomaly["current_month_amount"] - anomaly["three_month_avg"]
    color = "#e05252"  # spike

    with st.expander(
        f"⚠  {anomaly['category']} — {anomaly['ratio']:.1f}× above average",
        expanded=False
    ):
        col1, col2, col3 = st.columns(3)
        col1.metric("This Month",    fmt_inr(anomaly["current_month_amount"]))
        col2.metric("3-Month Avg",   fmt_inr(anomaly["three_month_avg"]))
        col3.metric("Excess Spend",  fmt_inr(excess), delta=f"+{anomaly['ratio']:.1f}×")
```

Custom border color using CSS injection per-card via `st.markdown`.

**Empty state:**
```python
if not anomalies:
    st.markdown("""
    <div style="background:#111;border:1px solid #1f2e1f;border-radius:10px;
                padding:24px;text-align:center;color:#4caf7d">
      ✓ &nbsp; All clear — no anomalies detected this period
    </div>
    """, unsafe_allow_html=True)
```

### Savings Opportunities Table
Render `dashboard["savings_opportunities"]` as a clean table with:
- "Could Save" column highlighted in `#4caf7d`
- Sort by `potential_savings` descending

---

## TAB 5: DATA

### Upload Panels (2 columns)
```python
col_initial, col_update = st.columns(2)

with col_initial:
    st.markdown("#### Initial Load")
    st.caption("Upload your full transaction history")
    file = st.file_uploader("", type=["csv","xlsx"], key="upload_initial",
                             label_visibility="collapsed")
    if st.button("Load Dataset →", key="btn_initial") and file:
        with st.spinner("Processing..."):
            result = api_upload("/upload", file)
            if result:
                st.success(result["message"])
                st.cache_data.clear()

with col_update:
    st.markdown("#### Monthly Update")
    st.caption("Append new month data safely")
    file2 = st.file_uploader("", type=["csv","xlsx"], key="upload_update",
                              label_visibility="collapsed")
    if st.button("Update →", key="btn_update") and file2:
        with st.spinner("Updating..."):
            result = api_upload("/update", file2)
            if result:
                st.success(result["message"])
                st.cache_data.clear()
```

### Expected Columns Info Box
```python
st.markdown("""
<div style="background:#111;border:1px solid #242424;border-radius:10px;padding:16px 20px;margin-top:16px">
  <div style="font-size:11px;letter-spacing:.1em;color:#4a4a48;text-transform:uppercase;margin-bottom:10px">
    Supported Column Formats
  </div>
  <div style="font-size:12px;color:#888780;line-height:2">
    <b style="color:#e8e6e0">Original:</b>
    <code style="background:#1c1c1c;padding:2px 6px;border-radius:4px;color:#7c6fcd">date</code>
    <code>account</code> <code>category</code> <code>subcategory</code>
    <code>description</code> <code>amount</code>
    <code style="background:#1c1c1c;padding:2px 6px;border-radius:4px;color:#7c6fcd">type</code>
    <br>
    <b style="color:#e8e6e0">Export format:</b>
    <code style="background:#1c1c1c;padding:2px 6px;border-radius:4px;color:#7c6fcd">Period</code>
    <code>Accounts</code> <code>Category</code> <code>Subcategory</code>
    <code>Note</code>
    <code style="background:#1c1c1c;padding:2px 6px;border-radius:4px;color:#7c6fcd">INR</code>
    <code style="background:#1c1c1c;padding:2px 6px;border-radius:4px;color:#7c6fcd">Income/Expense</code>
    <code>Description</code> <code>Amount</code> <code>Currency</code>
  </div>
</div>
""", unsafe_allow_html=True)
```

### Database Status
```python
months_list = api_months()
if dashboard:
    latest = dashboard.get("latest_month", {})
    st.markdown(f"""
    <div style="...">
      <span>Months: {len(months_list)}</span>
      <span>Latest: {latest.get('month','—')}</span>
      <span>Date range: {months_list[-1] if months_list else '—'} – {months_list[0] if months_list else '—'}</span>
    </div>
    """, unsafe_allow_html=True)
```

---

## EMPTY STATE (No Data)

Show when `dashboard` is `None`:
```python
st.markdown("""
<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;
            min-height:60vh;text-align:center">
  <div style="font-size:48px;color:#242424;margin-bottom:24px">₹</div>
  <h2 style="color:#e8e6e0;font-weight:500;margin-bottom:8px">Welcome to Finsight</h2>
  <p style="color:#888780;font-size:14px;margin-bottom:24px">
    Upload your transaction data to get started
  </p>
  <div style="display:flex;gap:8px;font-size:12px;color:#4a4a48">
    <span style="background:#1c1c1c;padding:4px 12px;border-radius:6px">CSV</span>
    <span style="background:#1c1c1c;padding:4px 12px;border-radius:6px">XLSX</span>
  </div>
</div>
""", unsafe_allow_html=True)
st.stop()
```

---

## ANOMALY RULES (for Alerts tab — compute client-side)

```python
def classify_anomalies(dashboard: dict) -> list[dict]:
    """Extend API anomalies with type classification."""
    anomalies = dashboard.get("anomalies", [])
    result = []
    for a in anomalies:
        ratio = a["ratio"]
        alert_type = "spike" if ratio > 1.4 else "variance"
        result.append({**a, "alert_type": alert_type})

    # Savings drop alert
    latest = dashboard.get("latest_month", {})
    rolling = dashboard.get("rolling_averages", {})
    if rolling and latest:
        avg_savings_rate = rolling.get("avg_net_savings", 0)
        current_savings = latest.get("net_savings", 0)
        if avg_savings_rate > 0 and current_savings < avg_savings_rate * 0.8:
            result.append({
                "category":             "Savings",
                "current_month_amount": current_savings,
                "three_month_avg":      avg_savings_rate,
                "ratio":                current_savings / avg_savings_rate if avg_savings_rate else 0,
                "month":                latest.get("month",""),
                "alert_type":           "savings",
            })

    return sorted(result, key=lambda x: x["ratio"], reverse=True)
```

---

## SCIENTIFIC / BEHAVIORAL FINANCE PRINCIPLES BAKED IN

These are NOT decorative — each maps to a specific UI decision:

| Principle | Source | UI Implementation |
|-----------|--------|-------------------|
| **Prospect Theory** | Kahneman & Tversky (1979) | Expense deltas RED, savings deltas GREEN — asymmetric emotional weight |
| **Anchoring Bias** | Tversky & Kahneman (1974) | Every KPI shows "vs 3m avg" — forces relative not absolute judgment |
| **Choice Architecture** | Thaler & Sunstein (2008) | Default = 3m range, Recent Avg baseline — nudges meaningful comparisons |
| **Miller's Law (7±2)** | Miller (1956) | Max 4 KPIs, max 4 takeaways, max 5 chart categories before "Other" |
| **Cognitive Load Theory** | Sweller (1988) | Essential/Discretionary split reduces 10+ categories to 2 mental buckets |
| **Temporal Discounting** | Behavioral economics | Previous period overlay on trends counters recency bias |
| **Savings Rate primacy** | Vanguard/Morningstar research | Savings Rate shown as primary metric — most controllable wealth driver |
| **Goal Gradient Effect** | Hull (1932) | Savings opportunity table shows "Could Save" — concrete progress target |

---

## FINAL ENGINEERING CHECKLIST

Before submitting:
- [ ] All 5 tabs render without errors with data loaded
- [ ] All 5 tabs render gracefully with no data (empty state + `st.stop()`)
- [ ] Sidebar date range selector filters all charts in all tabs
- [ ] Compare tab: changing baseline rerenders chart and table instantly
- [ ] Trends tab: mode toggle switches system ↔ category without error
- [ ] Alerts tab: expander shows category breakdown on click
- [ ] Data tab: upload → result message → cache cleared
- [ ] `fmt_inr()` used for ALL monetary display values
- [ ] All Plotly charts use `base_layout()` — no hardcoded light colors
- [ ] `latest_month` always derived from API, never hardcoded
- [ ] `@st.cache_data` on all API fetch functions
- [ ] `ConnectionError` → offline banner, not Python exception
- [ ] No hardcoded test data anywhere — all from API
- [ ] `st.session_state` initialized with defaults at top of file
- [ ] No cross-tab state leakage