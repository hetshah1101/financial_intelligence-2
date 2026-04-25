# Personal Financial Analytics System

A fully deterministic personal finance analytics MVP. No AI — all outputs are computed from your transaction data using Pandas and NumPy.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI |
| Database | SQLite (via SQLAlchemy — upgradeable to PostgreSQL) |
| Analytics | Pandas, NumPy |
| Frontend | Streamlit + Plotly |

---

## Project Structure

```
financial_intelligence/
├── backend/
│   ├── main.py                  # FastAPI entry point
│   ├── database.py              # SQLAlchemy engine + session
│   ├── models.py                # ORM models (4 tables)
│   ├── schemas.py               # Pydantic response schemas
│   ├── ingestion/
│   │   ├── validator.py         # Column, date, amount checks
│   │   ├── cleaner.py           # Normalise + fill missing fields
│   │   ├── tagger.py            # essential / discretionary tagging
│   │   └── pipeline.py          # Orchestrates ingestion + dedup
│   ├── analytics/
│   │   ├── monthly.py           # Monthly aggregate computation
│   │   ├── yearly.py            # Yearly aggregate computation
│   │   ├── category.py          # Category aggregate computation
│   │   ├── trends.py            # MoM, YoY, rolling averages
│   │   ├── anomalies.py         # 3 anomaly detection strategies
│   │   ├── behavior.py          # Top categories, concentration
│   │   ├── budget.py            # 3-month median baselines
│   │   ├── savings.py           # Savings opportunity detection
│   │   └── engine.py            # Orchestrates all analytics
│   └── routers/
│       ├── upload.py            # POST /upload  POST /update
│       └── dashboard.py         # GET /dashboard
├── frontend/
│   ├── app.py                   # Streamlit main app
│   └── components/
│       ├── overview.py
│       ├── monthly_trends.py
│       ├── yearly_trends.py
│       ├── category_breakdown.py
│       ├── tag_analysis.py
│       ├── anomalies.py
│       ├── savings.py
│       └── comparison.py
├── data/
│   └── sample_data.csv          # 12-month sample dataset
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Start the backend API

```bash
cd backend
uvicorn main:app --reload --port 8000
```

The SQLite database (`financial_intelligence.db`) is created automatically on first run.

### 3. Start the Streamlit frontend

In a separate terminal:

```bash
cd frontend
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Input File Format

Upload a CSV or Excel file with these columns:

| Column | Required | Notes |
|---|---|---|
| Date | Yes | Any standard date format |
| Account | Yes | e.g. "HDFC Savings" |
| Category | Yes | e.g. "Groceries", "Rent" |
| Subcategory | No | Optional detail |
| Note / Description | No | Transaction note |
| Amount (INR) | Yes | Numeric, always positive |
| Type | Yes | `Income`, `Expense`, or `Investment` |

---

## API Reference

### `POST /upload`
Upload initial transaction dataset.

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@data/sample_data.csv"
```

### `POST /update`
Incrementally add new transactions (skips duplicates, recomputes only affected months).

```bash
curl -X POST http://localhost:8000/update \
  -F "file=@data/new_transactions.csv"
```

### `GET /dashboard`
Returns full analytics payload.

```bash
curl http://localhost:8000/dashboard | python3 -m json.tool
```

### `GET /health`
```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

Interactive API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Analytics Coverage

| Feature | Description |
|---|---|
| Monthly Aggregates | Income / Expense / Investment / Net Savings / Savings Rate |
| Yearly Aggregates | Totals + avg monthly expense + savings rate |
| Category Breakdown | Per-category spend + % of total expense + tag |
| Monthly Trends | MoM % change + 3-month rolling average |
| Yearly Trends | YoY % change |
| Category Trends | Per-category monthly trend + % deviation from 3M avg |
| Total Spend Anomaly | Flags if monthly expense > 1.4× 3-month avg |
| Category Anomaly | Flags if category spend > 1.5× 3-month avg |
| Erratic Spend | Detects high variance, sudden spikes, large new-category spend |
| Spending Behavior | Top 5 categories, top-3 concentration %, essential vs discretionary |
| Budget Baseline | Median of last 3 months per category |
| Savings Opportunities | Categories above their 3-month median |

---

## Category Tagging Rules

**Essential:** Rent, Utilities, Groceries, Insurance, Medical, Healthcare, Electricity, Water, Gas, Internet, Mobile, Transport, Commute

**Discretionary:** Food Delivery, Dining Out, Entertainment, Shopping, Travel, Subscriptions, Personal Care, Fitness, Clothing, Accessories, Gadgets, Gifts

**Uncategorized:** Everything else

---

## Upgrading to PostgreSQL

In `backend/database.py`, replace:

```python
SQLALCHEMY_DATABASE_URL = "sqlite:///./financial_intelligence.db"
```

with:

```python
SQLALCHEMY_DATABASE_URL = "postgresql://user:password@localhost/findb"
```

No other code changes needed — SQLAlchemy handles the rest.
