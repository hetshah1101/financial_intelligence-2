# Frontend Developer Guide

## Running the frontend

Run from the **project root** (not from within `frontend/`):

```bash
streamlit run frontend/streamlit_app.py
```

The entry point adds `frontend/` to `sys.path` automatically, so all sibling modules
(`config`, `formatters`, `api`, etc.) resolve correctly regardless of where you launch from.

---

## Module responsibilities

### `streamlit_app.py`
Entry point only — page config, global CSS injection, session state defaults, sidebar,
and tab routing. Target: under 60 lines. No chart construction or business logic here.

### `config.py`
Single source of truth for visual constants and business logic configuration.
- `COLORS` — all hex values. Change here, applies everywhere.
- `GLOBAL_CSS` — complete dark-theme CSS block injected at startup.
- `CATEGORY_CLASSIFICATION` — manually map categories to `"essential"` or `"discretionary"`.
- `classify_category(name)` — case-insensitive lookup with fallback to `CATEGORY_DEFAULT_TYPE`.

### `formatters.py`
Pure formatting functions with no side effects.
- `fmt_inr(val, compact)` — Indian number formatting (₹1,23,456 or ₹1.2L).
- `fmt_month(ym)` — converts `"2025-01"` → `"Jan'25"`.
- `fmt_month_axis(months)` — batch-converts a list for chart tick labels.
- `fmt_delta(val)` — returns `(label, color)` tuple.
- `fmt_pct(val)` — formats a percentage with sign.

### `api.py`
All HTTP calls go here. Tab files never call `requests` directly.
- `api_dashboard()` — `@st.cache_data(ttl=60)`, returns full dashboard dict.
- `api_months()` — tries `/months` endpoint, falls back to deriving from dashboard.
- `api_upload(endpoint, file)` — handles `/upload` and `/update`.
- `categories_for_month(dashboard, month)` — pure helper, filters category_aggregates.

### `analytics.py`
All computation happens here — never in tab files.
Tab files call functions from analytics.py and pass results to charts.py.

Key functions:
- `compute_baseline(monthly_data, type)` — returns baseline dict for KPI deltas.
  Types: `"last_month"`, `"recent_avg"` (3m), `"longterm_avg"` (6m), `"12m_avg"`, `"all_time"`.
- `aggregate_by_granularity(data, granularity)` — re-aggregates for trends chart.
  Supports `"monthly"`, `"quarterly"`, `"yearly"`.
- `aggregate_category_by_granularity(all_cat_agg, granularity, category)` — category time series.
- `behavioral_split(categories)` — uses `classify_category()` from config.
- `generate_takeaways(latest, baseline, categories)` — deterministic bullet points.
- `classify_anomalies(dashboard)` — merges 3 anomaly lists, deduplicates, computes ratio.
- `build_category_diffs(current_cats, baseline_cats)` — per-category delta list for Compare tab.
- `build_baseline_cats(all_cat_agg, baseline_months_set)` — per-category baseline averages.

### `charts.py`
All Plotly figure construction is here.
Tab files call `make_*` functions and pass the result to `st.plotly_chart()`.
`base_layout(**kwargs)` provides the dark-theme base for every chart.

Chart factories:
- `make_overview_bar(monthly_data, selected_month)` — 12-month grouped bar, highlights selected.
- `make_donut(categories)` — top-5 expense donut with "Other" bucket.
- `make_category_bar(categories, current_vals, baseline_vals, label)` — Compare tab bar.
- `make_trends_chart(periods, period_labels, traces)` — generic multi-line trend chart.

---

## Scaling guidelines

- **Adding a new tab**: create `tabs/new_tab.py`, add to `streamlit_app.py`, done.
- **Adding a new KPI**: add computation to `analytics.py`, render in the relevant tab.
- **Adding a new chart type**: add factory to `charts.py`, call from tab.
- **Changing a color**: edit `COLORS` in `config.py` — applies globally.
- **Adding a new API endpoint**: add `@st.cache_data` function to `api.py`.
- **Reclassifying a category**: edit `CATEGORY_CLASSIFICATION` in `config.py`.

---

## Session state keys

| Key | Default | Owner |
|-----|---------|-------|
| `overview_month` | `None` (→ latest) | Overview tab |
| `date_range` | `"12m"` | Global |
| `compare_month` | `None` | Compare tab |
| `compare_baseline` | `"12m_avg"` | Compare tab |
| `trend_granularity` | `"monthly"` | Trends tab |
| `trend_mode` | `"system"` | Trends tab |
| `trend_metric` | `"total_expense"` | Trends tab |
| `trend_category` | `None` | Trends tab |
