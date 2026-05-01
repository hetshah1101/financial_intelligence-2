# Finsight v1 — Deep Dive Analysis & Improvement Roadmap

---

## How to read this document

I read every line of your backend and frontend source. Each finding below identifies the
exact file + line region, explains the root cause, and proposes a concrete fix.
Findings are ordered by impact — correctness bugs first, then UX/architecture, then vision.

---

# PART 1 — BACKEND BUGS & CORRECTNESS

---

## 1.1 `db.bind` is deprecated and will break silently

**Files:** `backend/analytics/monthly.py`, `yearly.py`, `category.py`

Every aggregate compute function reads:

```python
df = pd.read_sql(query.statement, db.bind)
```

`Session.bind` was deprecated in SQLAlchemy 1.4 and removed in 2.0. You are running
SQLAlchemy **2.0.49** (visible in your venv). It currently works via a compatibility
shim, but that shim can vanish in a point release. When it does, every analytics
recompute will silently fail with an `AttributeError`, wiping your aggregates after
each upload.

**Fix — pass the engine directly:**
```python
from database import engine
df = pd.read_sql(query.statement, engine)
```

Add `engine` as a module-level import in `database.py` (it already exists there)
and import it in each analytics file. Three files, three one-line changes.

---

## 1.2 Weak deduplication key — legitimate transactions are silently dropped

**Files:** `backend/models.py`, `backend/ingestion/pipeline.py`

```python
# models.py
UniqueConstraint("date", "amount", "description", name="uq_transaction")

# pipeline.py — same triple used for the pre-insert check
existing = db.query(Transaction).filter(
    Transaction.date == row["Date"],
    Transaction.amount == row["Amount (INR)"],
    Transaction.description == row["description"],
).first()
```

Two identical ₹500 Swiggy orders on the same day — which happens regularly — have
the same date + amount + description. The second one is **silently skipped** every
time you re-upload data. You will never see an error; the transaction simply never
appears in your analytics. With recurring SIP entries, electricity bills, or any
fixed-amount recurring vendor this will materially under-count.

**Fix:** Add `account` to both the constraint and the pipeline lookup:
```python
# models.py
UniqueConstraint("date", "amount", "description", "account", name="uq_transaction")

# pipeline.py
existing = db.query(Transaction).filter(
    Transaction.date == row["Date"],
    Transaction.amount == row["Amount (INR)"],
    Transaction.description == row["description"],
    Transaction.account == row["Account"],
).first()
```

This is still not perfectly collision-proof (two truly identical entries from the same
account), but it reduces false dedup dramatically for real-world data.

---

## 1.3 `type_map` in `cleaner.py` is missing critical variants — transactions are silently invisible

**File:** `backend/ingestion/cleaner.py`

```python
type_map = {
    "exp.":       "expense",
    "expense":    "expense",
    "income":     "income",
    "transfer-in":  "investment",
    "transfer-out": "investment",
    "transfer":   "investment",
    "investment": "investment",
}
```

Any `Type` value that does not exactly match a key above falls through to the original
string via:

```python
.map(lambda x: type_map.get(x, x))
```

So a row with `Type = "Expenses"` (plural) becomes type `"Expenses"` in the database.
Every downstream query that filters `Transaction.type.in_(["expense", "income", "investment"])`
silently skips those rows. Common missing variants from Indian finance apps and bank exports:

| Raw value | Should map to |
|-----------|--------------|
| `"Expenses"` | `"expense"` |
| `"Credit"` | `"income"` |
| `"Debit"` | `"expense"` |
| `"DR"` / `"CR"` | `"expense"` / `"income"` |
| `"Withdrawal"` / `"Deposit"` | `"expense"` / `"income"` |
| `"Transfer In"` / `"Transfer Out"` | `"investment"` |

**Fix:**
```python
type_map = {
    "expense":      "expense",
    "expenses":     "expense",
    "exp.":         "expense",
    "exp":          "expense",
    "debit":        "expense",
    "dr":           "expense",
    "withdrawal":   "expense",
    "withdraw":     "expense",
    "income":       "income",
    "credit":       "income",
    "cr":           "income",
    "deposit":      "income",
    "investment":   "investment",
    "invest":       "investment",
    "transfer":     "investment",
    "transfer-in":  "investment",
    "transfer-out": "investment",
    "transfer in":  "investment",
    "transfer out": "investment",
    "sip":          "investment",
}
```

Also add a warning log for any row whose type does not resolve to the three canonical
values, so you know when a new export format introduces a new variant.

---

## 1.4 Card settlement detection over-matches and excludes real expenses

**File:** `backend/ingestion/exception.py`

```python
_CARD_DESC_PATTERNS = [
    ...
    r"\bamex\b",
    r"\bcitibank\b",
    r"bajaj\s*(?:fin|card)",
    ...
]
```

Any transaction where the description *mentions* one of these words — a flight booked
through an Amex travel portal, a Bajaj Finance loan EMI, a Citibank branch visit fee —
gets reclassified to `"card settlement"` and excluded from expense aggregates entirely.
This is silent: the transaction exists in the DB but is never counted.

Similarly:
```python
acc_match = acc_lower.isin(_CARD_ACCOUNTS) & (type_lower == "investment")
```

A legitimate SIP or FD made from a card account (e.g. Slice) will be reclassified away
from `"investment"` and disappear from investment totals.

**Fixes:**
1. Require description patterns to appear in a financial context — e.g.
   `r"payment\s+to\s+amex"` rather than bare `r"\bamex\b"`.
2. Add a `reclassification_reason` column to `Transaction` and log every change.
3. Build a small admin endpoint `GET /card-settlements` that lists all reclassified
   rows so you can audit them manually.

---

## 1.5 `budget.py` always uses only the last 3 months — baseline is too volatile

**File:** `backend/analytics/budget.py`

```python
last_3 = months_sorted[-3:] if len(months_sorted) >= 3 else months_sorted
```

A 3-month median is extremely sensitive to outliers. If you had a big travel month
2 months ago, every category baseline is inflated and your savings opportunities are
invisible. If you had 3 cheap months in a row, every category looks like an overspend.

**Fix:** Make the window configurable with a sensible default of 6 months:
```python
def compute_budget_baseline(
    category_df: pd.DataFrame, window_months: int = 6
) -> list[BudgetBaseline]:
    months_sorted = sorted(category_df["month"].unique())
    window = months_sorted[-window_months:]
```

Expose this as a query param: `GET /dashboard?baseline_window=6`. The frontend
can pass the user's selection from a dropdown.

---

## 1.6 `behavior.py` aggregates across ALL months, not the current month

**File:** `backend/analytics/behavior.py`

```python
by_cat = (
    category_df.groupby(["category", "tag"])["total_amount"]
    .sum()
    .reset_index()
    ...
)
```

`SpendingBehavior.essential_pct` and `.discretionary_pct` in the dashboard response are
**lifetime** aggregates — the sum of every month you've ever uploaded. The frontend
displays these as if they describe the current month. A month where you had unusually
high medical expenses will be diluted by 11 months of normal spending. The frontend
`analytics.py:behavioral_split()` actually recomputes this correctly on the client
side using only the selected month's categories, which means the backend field is
redundant and misleading.

**Fix:** Either filter to the latest month before computing, or remove
`spending_behavior` from `DashboardResponse` since the frontend re-derives it anyway.

---

## 1.7 `anomalies.py` — rolling average includes insufficient history → false positives

**File:** `backend/analytics/anomalies.py`

```python
df["rolling_3m_avg"] = df["total_expense"].shift(1).rolling(3, min_periods=1).mean()
```

`min_periods=1` means in your second month of data, the "3-month average" is literally
just the previous single month. Any increase from month 1 to month 2 will trigger
an anomaly. This generates a wave of false-positive alerts when you first load data.

```python
# detect_erratic_spend: also has duplicate firing
# Both "high std dev" and "spike" conditions can fire for the same month+category.
# The dedup key (month, category, reason[:30]) is not unique enough when
# reason strings share a 30-char prefix.
```

**Fixes:**
```python
# Require at least 2 months of history
df["rolling_3m_avg"] = df["total_expense"].shift(1).rolling(3, min_periods=2).mean()

# Stronger dedup key
key = (a.month, a.category or "", a.reason[:60])
```

---

## 1.8 Dashboard endpoint has no caching — recomputes everything on every page load

**File:** `backend/routers/dashboard.py`

`build_dashboard()` loads ALL transactions into memory via `pd.read_sql` on every
request. With 12 months of data this is ~200ms. With 36+ months (your goal) it will
be 2–5 seconds. Since Streamlit rerenders on every user interaction, this endpoint
is called very frequently.

**Quick fix — backend cache:**
```python
import time
_cache = {"data": None, "ts": 0.0}
CACHE_TTL = 60

@router.get("/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    now = time.time()
    if _cache["data"] and now - _cache["ts"] < CACHE_TTL:
        return _cache["data"]
    result = build_dashboard(db)
    _cache.update({"data": result, "ts": now})
    return result
```

**Better fix (medium-term):** Add a `/dashboard/month/{ym}` endpoint that loads only
one month's aggregate data, and use the existing `/dashboard` only for top-level summary
KPIs. This turns a full-table scan into indexed point lookups.

---

## 1.9 Upload endpoint is synchronous — will time out with large files

**File:** `backend/routers/upload.py`

```python
result = run_pipeline(df, db)
if result["inserted"] > 0:
    recompute_aggregates(db)   # blocks the HTTP response
```

`recompute_aggregates` runs four DB scans and four writes synchronously. With a large
historical export (1,000+ rows), the HTTP response can timeout before it completes,
leaving the DB in a partially computed state with no error message to the user.

**Fix — FastAPI background tasks:**
```python
from fastapi import BackgroundTasks

@router.post("/upload")
async def upload_initial(
    file: UploadFile,
    db: Session = Depends(get_db),
    bg: BackgroundTasks = BackgroundTasks(),
):
    ...
    if result["inserted"] > 0:
        bg.add_task(recompute_aggregates, db)
    return UploadResponse(status="processing", ...)
```

Add `GET /status` that returns `{"computing": true/false}` so the frontend can show
a spinner and auto-refresh when done.

---

# PART 2 — FRONTEND BUGS & IMPROVEMENTS

---

## 2.1 `api_dashboard` caches `None` — backend recovery takes 60 seconds

**File:** `frontend/api.py`

```python
@st.cache_data(ttl=60)
def api_dashboard() -> dict | None:
    try:
        ...
        return r.json()
    except Exception:
        return None   # None is cached for the full 60s TTL
```

If the backend is momentarily down (restart, deploy), `None` is cached. Even after
the backend recovers, the UI shows "no data" for up to 60 more seconds. Users have
to manually force a cache clear.

**Fix:**
```python
@st.cache_data(ttl=60)
def api_dashboard() -> dict | None:
    try:
        r = requests.get(f"{API_BASE}/dashboard", timeout=8)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None   # return None but DON'T cache it

# Call st.cache_data.clear() only when result is not None
```

The cleanest approach: use a wrapper that skips caching on failure:
```python
def api_dashboard() -> dict | None:
    if "dashboard_cache" not in st.session_state:
        st.session_state["dashboard_cache"] = None
        st.session_state["dashboard_ts"] = 0
    now = time.time()
    if st.session_state["dashboard_cache"] and now - st.session_state["dashboard_ts"] < 60:
        return st.session_state["dashboard_cache"]
    try:
        r = requests.get(f"{API_BASE}/dashboard", timeout=8)
        r.raise_for_status()
        data = r.json()
        st.session_state["dashboard_cache"] = data
        st.session_state["dashboard_ts"] = now
        return data
    except Exception:
        return st.session_state["dashboard_cache"]  # serve stale data if available
```

---

## 2.2 `classify_anomalies` labels `threshold` as the baseline — wrong by 40%

**File:** `frontend/analytics.py`

```python
"three_month_avg": threshold,   # ← this is actually 1.4× the avg
```

`AnomalyRecord.threshold` from the backend is computed as `rolling_avg × 1.4`. The
frontend labels this `"three_month_avg"` and displays it in the Alerts tab metric card
as "3-Month Avg". The "Excess Spend" figure (`current - three_month_avg`) is therefore
understated by 40%. It makes alerts look less severe than they are.

**Fix:**
```python
# In classify_anomalies, recover the actual avg:
"three_month_avg": round(threshold / 1.4, 2) if threshold else 0,
```

Or — better — add a `baseline_amount` field to `AnomalyRecord` in `schemas.py`
so the backend sends the actual average, not just the threshold.

---

## 2.3 `classify_category` does a linear scan on every call — called in tight loops

**File:** `frontend/config.py`

```python
def classify_category(category: str) -> str:
    if category in CATEGORY_CLASSIFICATION:
        return CATEGORY_CLASSIFICATION[category]
    lower = category.lower()
    for key, val in CATEGORY_CLASSIFICATION.items():   # O(n) on every call
        if key.lower() == lower:
            return val
    return CATEGORY_DEFAULT_TYPE
```

This is called inside `behavioral_split()` which loops over every category row.
With 20 categories × 12 months = 240 calls per render, each doing a 50-item dict
scan, that's 12,000 comparisons per page load.

**Fix — build a lowercase lookup once at module load:**
```python
_LOWER_MAP = {k.lower(): v for k, v in CATEGORY_CLASSIFICATION.items()}

def classify_category(category: str) -> str:
    return (
        CATEGORY_CLASSIFICATION.get(category)
        or _LOWER_MAP.get(category.lower())
        or CATEGORY_DEFAULT_TYPE
    )
```

---

## 2.4 `percentage_of_total_expense` vs `percentage_of_total` inconsistency

**File:** `frontend/tabs/overview.py`

Multiple places defensively handle both names:
```python
pct = top_cat.get("percentage_of_total_expense") or top_cat.get("percentage_of_total", 0)
```

`CategoryAggregateSchema` defines it as `percentage_of_total_expense`. Somewhere in
the frontend it was also referenced as `percentage_of_total`, causing this defensive
double-check pattern to proliferate. Standardize to `percentage_of_total_expense`
everywhere and remove the fallback.

---

## 2.5 No schema migration system — adding a column will silently break the app

**Across backend**

Right now there is no Alembic or any migration system. If you add a column to any
model (which you will, extensively, for investments), two things happen:
1. Existing installs silently fail to start because `Base.metadata.create_all` does
   not alter existing tables — it only creates missing tables.
2. There is no rollback path.

**Fix — add Alembic now, before you add any new tables:**
```bash
pip install alembic
alembic init alembic
# Edit alembic/env.py to import your Base and engine
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

Every future schema change becomes a versioned migration file. This is table-stakes
for a multi-table finance app.

---

# PART 3 — ALERTS TAB REDESIGN

The current alerts tab has two problems: it shows raw anomaly data without context or
actionability, and the savings opportunities section is a flat table with no narrative.
Here is a concrete redesign with five sections.

---

## 3.1 Financial Health Score (header, always visible)

A single 0–100 composite score shown at the top of the tab, derived from:

| Component | Weight | How |
|-----------|--------|-----|
| Savings rate vs target (20%) | 30% | `savings_rate / 20 * 30`, capped at 30 |
| Expense vs 12m baseline | 25% | `max(0, 25 - (overspend_pct / 4))` |
| Active critical anomalies | 20% | `-5 per critical alert, -2 per warning` |
| Essential/discretionary ratio | 25% | `25 if essential_pct >= 40 else essential_pct / 40 * 25` |

Display as a large number with a color band and a one-line plain-English verdict:
- 80–100: "Strong control — on track"
- 60–79: "Good, with a few areas to watch"
- 40–59: "Some overspending — review alerts below"
- 0–39: "Spending needs attention this month"

---

## 3.2 Alert cards with severity tiers

Replace the generic expander list with structured cards. Every alert gets:

**Severity levels:**
- 🔴 Critical — >2× baseline, or savings rate dropped >40% MoM
- 🟡 Warning — 1.4×–2× baseline, or savings dropped 20–40% MoM
- 🔵 Info — new category appeared (first month), or erratic pattern starting

**Alert type badges:**
- `SPIKE` — sudden MoM jump in a single category
- `TREND` — gradual 3+ month increase in a category
- `TOTAL` — overall month spend exceeded baseline
- `SAVINGS` — net savings dropped significantly
- `NEW` — category seen for first time

**Each card shows:**
```
┌──────────────────────────────────────────────────────────┐
│  🔴 SPIKE                               Health · Aug'25  │
│                                                           │
│  ₹7,288   vs ₹2,638 avg    +₹4,650 excess (+176%)       │
│  [████████████████████████░░░░░░░] 2.8× above baseline   │
│                                                           │
│  Health jumped significantly vs 3-month average.          │
│  Possible one-time event. Review if it recurs next month. │
└──────────────────────────────────────────────────────────┘
```

Implementation note: severity coloring comes from the left border of the card, not
the body — this keeps the card readable while preserving the color signal.

---

## 3.3 Month-over-month digest table

A compact read-only table showing every category's last 3 months with directional arrows.
This is the "temperature check" view — you can see at a glance which categories are
creeping up even if they haven't crossed anomaly thresholds yet.

```
Category      Jul'25      Aug'25      Sep'25    Trend
──────────────────────────────────────────────────────
Food          ₹4,800      ₹5,200      ₹5,900     ↑↑
Home          ₹18,000     ₹13,000     ₹13,174    ↘
Travel        ₹17,310     ₹8,977      ₹0         ↓
Health        ₹2,600      ₹2,638      ₹7,288     ↑↑ ⚠
```

Color rules:
- Green: last month lower than prior month
- Red: last month >10% higher than prior month
- Amber: 0–10% increase
- ⚠ indicator: anomaly detected for that category

---

## 3.4 Savings opportunities — narrative redesign

Instead of a flat table, group by category type and add projections:

```
💡 Savings available this month vs your 6-month baseline:

  Essential spending
    Health       ₹4,650 above baseline
    Petrol         ₹700 above baseline
    ─────────────────────────────────
    Total        ₹5,350

  Discretionary spending
    Travel       ₹4,200 above baseline
    Social Life  ₹2,600 above baseline
    Shopping     ₹1,100 above baseline
    ─────────────────────────────────
    Total        ₹7,900

  If you spent at your baseline this month:
    You'd save ₹13,250 this month
    Annualised: ₹1.59L per year
```

The annualised figure is the hook — it makes the opportunity feel real.

---

## 3.5 All-clear state

When zero anomalies are detected, don't just show a green box. Show something useful:

```
✓  All clear this period

Your finances look healthy this month.

Best result this year:  Savings rate 34% in Jun'25
Expense streak:  Below 12-month average for 3 consecutive months
Top discipline:  Discretionary spending has been trending down for 4 months
```

This turns the empty state into positive reinforcement — a reason to come back.

---

# PART 4 — INVESTMENTS MODULE ARCHITECTURE

Your stated goal: bring all investment information onto this platform without
real-time stock price tracking. That scopes nicely — you need static snapshots,
not live feeds.

---

## 4.1 New database tables

Add these in the next Alembic migration:

```python
class Investment(Base):
    """Each purchase/SIP/redemption event."""
    __tablename__ = "investments"

    id               = Column(Integer, primary_key=True)
    date             = Column(Date, nullable=False, index=True)
    month            = Column(String(7), nullable=False, index=True)
    instrument_type  = Column(String(50), nullable=False)
    # "mutual_fund" | "stock" | "fd" | "ppf" | "nps" | "gold" | "crypto" | "bonds"
    name             = Column(String(200), nullable=False)
    symbol           = Column(String(50))       # NSE/BSE ticker for stocks
    isin             = Column(String(20))        # ISIN for unambiguous identity
    folio_number     = Column(String(100))       # for mutual funds
    units            = Column(Float, default=0)
    price_per_unit   = Column(Float)             # NAV or stock price at transaction
    amount           = Column(Float, nullable=False)  # total INR invested
    transaction_type = Column(String(20))
    # "buy" | "sell" | "dividend" | "sip" | "interest" | "maturity"
    account          = Column(String(100))       # demat / folio account name
    notes            = Column(String(500))


class Holding(Base):
    """Point-in-time snapshot of portfolio (updated manually or on demand)."""
    __tablename__ = "holdings"

    id               = Column(Integer, primary_key=True)
    snapshot_date    = Column(Date, nullable=False, index=True)
    instrument_type  = Column(String(50), nullable=False)
    name             = Column(String(200), nullable=False)
    symbol           = Column(String(50))
    isin             = Column(String(20))
    folio_number     = Column(String(100))
    units            = Column(Float)
    avg_cost_per_unit = Column(Float)           # average buy price
    current_price    = Column(Float)             # manually entered or fetched
    current_value    = Column(Float))            # units × current_price
    invested_value   = Column(Float)             # what you paid (total cost basis)
    unrealised_pnl   = Column(Float)             # current_value - invested_value
    unrealised_pnl_pct = Column(Float)
    account          = Column(String(100))

    __table_args__ = (
        UniqueConstraint("snapshot_date", "isin", "folio_number",
                         name="uq_holding_snapshot"),
    )


class Liability(Base):
    """Loans, EMIs, credit card balances."""
    __tablename__ = "liabilities"

    id             = Column(Integer, primary_key=True)
    name           = Column(String(200), nullable=False)  # "SBI Home Loan"
    liability_type = Column(String(50))
    # "home_loan" | "car_loan" | "personal_loan" | "credit_card" | "education_loan"
    principal      = Column(Float)
    outstanding    = Column(Float, nullable=False)
    interest_rate  = Column(Float)     # annual %
    emi_amount     = Column(Float)
    start_date     = Column(Date)
    end_date       = Column(Date)
    account        = Column(String(100))
    as_of_date     = Column(Date)      # when this snapshot was recorded


class Goal(Base):
    """Financial goal with progress tracking."""
    __tablename__ = "goals"

    id             = Column(Integer, primary_key=True)
    name           = Column(String(200), nullable=False)  # "House down payment"
    target_amount  = Column(Float, nullable=False)
    target_date    = Column(Date)
    current_amount = Column(Float, default=0)
    monthly_sip    = Column(Float, default=0)
    linked_isin    = Column(String(20))          # optional: link to a holding
    notes          = Column(String(500))
    created_at     = Column(Date)
```

---

## 4.2 Import formats to support

Since you're not doing live tracking, the ingestion path is: **manual CSV export → upload → parse → store**.

| Broker / Platform | Export type | Key columns |
|-------------------|-------------|-------------|
| Zerodha Kite | Trade book CSV | Symbol, ISIN, Qty, Price, Trade Type |
| Groww | Transaction statement CSV | Scheme, ISIN, Units, NAV, Amount, Type |
| Kuvera | Portfolio export CSV | Fund Name, ISIN, Folio, Units, Avg Cost, Current NAV |
| Paytm Money | Holdings CSV | similar to Groww |
| CAMS / KFintech | Consolidated Account Statement (CAS) | Standard format, all MF folios |
| FD receipt | Manual entry form | Bank, Principal, Rate, Start, Maturity |

Build an `InvestmentPipeline` parallel to `run_pipeline`:

```python
# backend/ingestion/investment_pipeline.py

SUPPORTED_SOURCES = {
    "zerodha":  ZerodhaMapper,
    "groww":    GrowwMapper,
    "kuvera":   KuveraMapper,
    "cams":     CamsMapper,
    "generic":  GenericInvestmentMapper,
}

def run_investment_pipeline(df: pd.DataFrame, source: str, db: Session) -> dict:
    mapper = SUPPORTED_SOURCES.get(source, GenericInvestmentMapper)()
    df = mapper.normalize(df)
    validate_investment(df)
    return insert_investments(df, db)
```

The `source` param is passed from the frontend upload form as a dropdown selection.

---

## 4.3 Manual snapshot workflow (no live prices required)

Since you don't want live stock tracking, use a **manual snapshot** model:

1. User exports holdings CSV from broker (Zerodha Console / Groww portfolio page)
2. Uploads via `POST /portfolio/snapshot`
3. System stores the snapshot in `Holding` with `snapshot_date = today`
4. Dashboard shows the latest snapshot for each holding

This means you update your portfolio view whenever you choose to export, not
automatically. It's simpler, more private, and doesn't require API keys.

For mutual fund NAVs, you can optionally integrate the **AMFI NAV API** (public, free):
```
https://api.mfapi.in/mf/{scheme_code}/latest
```
This gives you the current NAV for any mutual fund scheme without authentication.
Add a `POST /refresh-nav` endpoint that fetches NAV for every MF holding and updates
`Holding.current_price` — user triggers this manually when they want fresh numbers.

---

## 4.4 New API endpoints

```
# Investment transactions
POST   /investments/upload?source=zerodha   — upload a broker CSV
GET    /investments/transactions            — paginated transaction history
GET    /investments/transactions/{month}    — transactions for a specific month

# Portfolio snapshots
POST   /portfolio/snapshot                  — upload a holdings CSV
GET    /portfolio/latest                    — most recent snapshot of all holdings
GET    /portfolio/history                   — net portfolio value over time (from snapshots)
POST   /portfolio/refresh-nav               — fetch AMFI NAV for MF holdings

# Net worth
GET    /networth/summary                    — assets + liabilities → net worth
GET    /networth/history                    — monthly net worth time series

# Liabilities
POST   /liabilities                         — add/update a loan
GET    /liabilities                         — all loans with outstanding + EMI

# Goals
GET    /goals                               — all goals with progress
POST   /goals                               — create a goal
PUT    /goals/{id}                          — update goal (change target, link holding)
GET    /goals/{id}/simulation               — SIP simulation to reach target
```

---

## 4.5 New frontend tabs (in build order)

### Tab: Portfolio

**Section 1 — Net worth header**
```
Net Worth:  ₹28.4L    ↑ ₹1.2L this month

Assets ₹34.1L          Liabilities ₹5.7L
────────────────        ─────────────────
Equity MF   ₹14.2L     Home Loan  ₹4.8L
Stocks       ₹8.6L     Car Loan   ₹0.9L
FD / Debt    ₹6.1L
PPF / NPS    ₹5.2L
```

**Section 2 — Allocation donut**
Equity / Debt / Gold / Cash / Real Estate — current % vs your target %.
If target allocation drifts >5% from actual, show an amber indicator.

**Section 3 — Holdings table**
Sortable by: Name, Instrument Type, Current Value, P&L %, Last Updated.
Color code P&L column (green positive, red negative).
Show `snapshot_date` in the table header so it's clear this is a point-in-time view.

**Section 4 — SIP tracker**
List of active SIPs with: Fund name, Monthly amount, Start date, Total invested,
Projected value at target date (using historical CAGR as estimate).

---

### Tab: Net Worth

**Section 1 — Waterfall chart**
Liquid assets + MF + Stocks + FD + PPF − Home Loan − Car Loan = Net Worth

**Section 2 — Net worth trend**
Line chart of net worth per snapshot over time. Shows wealth accumulation visually.

**Section 3 — Goal progress cards**
One card per goal:
```
┌──────────────────────────────────────────┐
│  House Down Payment                       │
│  Target: ₹25L  by Dec'27                 │
│                                           │
│  [████████████░░░░░░░░░░░]  48%          │
│  ₹12.0L saved of ₹25.0L target           │
│                                           │
│  On track: Need ₹47K/month               │
│  Current SIP: ₹50K/month  ✓              │
└──────────────────────────────────────────┘
```

---

### Tab: Loans & Liabilities

**Section 1 — Outstanding summary**
Total outstanding, total monthly EMI outflow, weighted average interest rate.

**Section 2 — Per-loan details**
For each loan: Principal, Outstanding, Rate, EMI, Months remaining, Payoff date.
Show an amortization progress bar.

**Section 3 — Prepayment simulator**
Input: "Extra ₹_____ this month" →
Output: "Saves ₹X in interest, pays off Y months earlier."
(Pure frontend calculation, no API call needed.)

---

## 4.6 Analytics that become possible

Once you have investment data alongside expense data, these cross-cutting insights
become possible:

**Effective savings rate**
```
Net savings + Investments invested this month
─────────────────────────────────────────── × 100
                  Income
```
This is more meaningful than cash savings rate alone.

**Expense coverage ratio**
```
Portfolio value / Monthly expense burn
```
"Your portfolio can cover 18 months of expenses at current spending."

**SIP consistency score**
Did you invest at least ₹X in each of the last 12 months? Show as 12 green/red dots.

**Allocation drift alert**
"Your equity allocation is 82%, target is 70%. Consider rebalancing."
Appears in the Alerts tab alongside expense anomalies.

**Savings-to-investment conversion rate**
What % of your net cash savings is being invested rather than sitting in a bank account?

---

# PART 5 — ARCHITECTURE & CODE QUALITY

---

## 5.1 Add Alembic before adding any new tables

As noted in 2.5 — this is the single most important infrastructure change before
building the investments module. Every schema addition without Alembic risks breaking
existing installs with no recovery path.

## 5.2 Split the monolithic `build_dashboard` into focused builders

`engine.py:build_dashboard()` does 8 different analytics computations in a single
172-line function. When a bug exists in one section, it's hard to isolate. Split it:

```python
def build_expense_dashboard(db) -> dict:    # monthly/yearly/category aggs + trends
def build_anomaly_dashboard(db) -> dict:    # all three anomaly types
def build_behavior_dashboard(db) -> dict:   # behavior + budget + savings
def build_portfolio_dashboard(db) -> dict:  # NEW: holdings + net worth
```

And compose them in a thin `build_dashboard` coordinator.

## 5.3 Add structured logging throughout the pipeline

The current approach:
```python
print(f"[DEBUG] File read: {df.shape[0]} rows, columns: {df.columns.tolist()}")
```

This is development-time scaffolding left in production code. Replace with Python's
`logging` module:

```python
import logging
logger = logging.getLogger("finsight.ingestion")
logger.info("File read: %d rows, columns: %s", df.shape[0], df.columns.tolist())
```

This lets you configure log levels, redirect to files, and filter noise without
changing the code.

## 5.4 Add a `CategoryTagOverride` table

Right now, changing a category from "discretionary" to "essential" requires:
1. Editing `frontend/config.py`
2. Restarting the Streamlit process
3. The change doesn't retroactively update `tag` columns in the DB

Add a `CategoryTagOverride` table and `POST /category-tags` endpoint:

```python
class CategoryTagOverride(Base):
    __tablename__ = "category_tag_overrides"
    category   = Column(String(100), primary_key=True)
    tag        = Column(String(50), nullable=False)  # "essential" | "discretionary"
    updated_at = Column(DateTime, default=datetime.utcnow)
```

When `compute_category_aggregates` runs, it checks this table to override the default
tagger. The frontend reads overrides from `GET /category-tags` and merges them with
its local `CATEGORY_CLASSIFICATION`. This makes classification persistent, auditable,
and changeable without a code deploy.

---

# PART 6 — PRIORITIZED IMPROVEMENT ROADMAP

## Phase 1 — Fix correctness bugs (1–2 days)

| # | Item | Risk if skipped |
|---|------|-----------------|
| 1 | Replace `db.bind` with `engine` | Silent breakage on next SQLAlchemy update |
| 2 | Add `account` to dedup constraint | Recurring transactions silently lost |
| 3 | Expand `type_map` in `cleaner.py` | Unmapped transactions excluded from all analytics |
| 4 | Fix `min_periods=2` in anomalies | Wave of false-positive alerts |
| 5 | Fix `threshold` label in `classify_anomalies` | Wrong numbers in Alerts tab |

## Phase 2 — Alerts tab redesign (3–5 days)

| # | Item |
|---|------|
| 6 | Financial health score header |
| 7 | Severity-tiered alert cards (Critical / Warning / Info) |
| 8 | MoM digest table for all categories |
| 9 | Narrative savings opportunities with annualised figure |
| 10 | Positive "all-clear" state with streak stats |

## Phase 3 — Infrastructure (2–3 days)

| # | Item |
|---|------|
| 11 | Add Alembic migrations |
| 12 | Background recompute on upload |
| 13 | Backend dashboard cache |
| 14 | `CategoryTagOverride` table + endpoint |
| 15 | Structured logging |

## Phase 4 — Investments module (2–3 weeks)

| # | Item |
|---|------|
| 16 | Add Investment + Holding + Liability + Goal tables (Alembic migration) |
| 17 | Build `InvestmentPipeline` with Zerodha + Groww + generic mapper |
| 18 | `POST /portfolio/snapshot` + `GET /portfolio/latest` endpoints |
| 19 | Optional AMFI NAV refresh endpoint (no API key needed) |
| 20 | Portfolio tab: net worth header + allocation donut + holdings table |
| 21 | Net Worth tab: waterfall + trend + goal cards |
| 22 | Loans tab: outstanding summary + prepayment simulator |
| 23 | Cross-cutting analytics: effective savings rate, expense coverage, SIP consistency |
| 24 | Allocation drift alert in Alerts tab |

---

# Summary

The v1 codebase is well-structured and already modular — the tab system, analytics/charts
separation, and config-driven category classification are all solid foundations. The
issues are mostly in the data layer (silent failures, weak dedup, stale field references)
and in the Alerts tab (surface-level display of raw API data without interpretation).
None of the bugs require architectural changes to fix — they're targeted patches.

The investments module fits naturally onto the existing architecture. The pattern
of: **upload CSV → pipeline → aggregates → dashboard API → tab** is exactly right
for non-realtime investment data. The main additions are the new tables, new ingestion
mappers, and three new tabs — the backend and frontend patterns for all of these
already exist in v1.