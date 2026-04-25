You are a senior software engineer and data systems architect.

Your task is to build a complete MVP of a **Personal Financial Analytics System** that processes structured transaction data, performs deterministic analytics, and provides deep visibility into spending behavior, trends, anomalies, and savings opportunities.

This MVP must NOT use any AI/LLM. All outputs must be deterministic, reproducible, and derived from data.

---

# 1. INPUT DATA FORMAT (STRICT)

The input is an Excel/CSV file with the following columns:

* Date
* Account
* Category
* Subcategory
* Note / Description
* Amount (INR)
* Type (Income / Expense / Investment)

---

# 2. SYSTEM GOAL

The system should:

1. Ingest and clean transaction data
2. Store it reliably
3. Generate structured analytics
4. Identify:

   * spending patterns
   * trends
   * anomalies
   * erratic behavior
5. Provide:

   * category-level breakdowns
   * monthly and yearly views
   * budget baselines
   * savings opportunities

---

# 3. TECH STACK

Backend:

* Python
* FastAPI

Processing:

* Pandas, NumPy

Database:

* SQLite (structured for PostgreSQL upgrade)

Frontend:

* Streamlit

---

# 4. DATABASE DESIGN

## transactions

* id (PK)
* date (DATE)
* month (YYYY-MM)
* year (YYYY)
* amount (FLOAT, always positive)
* type (income / expense / investment)
* category (TEXT)
* subcategory (TEXT)
* description (TEXT)
* account (TEXT)
* tag (essential / discretionary / uncategorized)

---

## monthly_aggregates

* month
* total_income
* total_expense
* total_investment
* net_savings
* savings_rate

---

## category_aggregates

* month
* category
* total_amount
* percentage_of_total_expense
* tag

---

## yearly_aggregates

* year
* total_income
* total_expense
* total_investment
* avg_monthly_expense
* savings_rate

---

# 5. DATA INGESTION PIPELINE

## Step 1: Validation

* Ensure required columns exist
* Validate date format
* Validate numeric amount

---

## Step 2: Cleaning

* Convert:

  * Date → YYYY-MM-DD
  * Amount → float (absolute value)
* Normalize:

  * Type → lowercase
* Fill missing:

  * Category → "uncategorized"
  * Subcategory → null
  * Description → ""
* Remove duplicates:

  * (date, amount, description)

---

## Step 3: Derive Fields

* month = YYYY-MM
* year = YYYY

---

## Step 4: Category Tagging (CRITICAL FEATURE)

Implement rule-based tagging:

### Essential Categories:

* Rent
* Utilities
* Groceries
* Insurance
* Medical

### Discretionary Categories:

* Food Delivery
* Dining Out
* Entertainment
* Shopping
* Travel

### Logic:

* Map category → tag
* If unknown → "uncategorized"

---

## Step 5: Store Data

* Insert into transactions table
* Ensure idempotency (no duplicates)

---

# 6. ANALYTICS ENGINE

---

## 6.1 MONTHLY AGGREGATES

For each month:

* total_income
* total_expense
* total_investment
* net_savings = income - expense - investment
* savings_rate

---

## 6.2 CATEGORY ANALYSIS

For each month:

* total spend per category
* percentage contribution
* tag-based grouping:

  * essential vs discretionary split

---

## 6.3 YEARLY AGGREGATES

For each year:

* total income
* total expense
* total investment
* avg monthly expense
* savings rate

---

## 6.4 TREND ANALYSIS

### Monthly:

* MoM change (income, expense)
* 3-month rolling average (expense)

### Yearly:

* YoY growth (income, expense)

---

## 6.5 CATEGORY TRENDS

For each category:

* monthly trend
* last 3-month average
* % deviation

---

## 6.6 ANOMALY DETECTION

### A. Total Spend Anomaly:

Flag if:
current_month_expense > 1.4 × avg(last 3 months)

---

### B. Category Anomaly:

Flag if:
current_category_spend > 1.5 × avg(last 3 months)

---

### C. Erratic Spend Detection (IMPORTANT)

Flag if ANY condition is met:

1. Category spend variance is high:

   * std deviation > threshold

2. Sudden spike:

   * current > 2× last month

3. First-time large transaction:

   * new category AND amount > threshold

Output:

* month
* category
* reason

---

## 6.7 SPENDING BEHAVIOR METRICS

* Top 5 categories

* Category concentration:

  * % share of top 3 categories

* Essential vs Discretionary ratio:

  * discretionary_spend / total_expense

---

## 6.8 BUDGET BASELINE

For each category:

* median(last 3 months)

---

## 6.9 SAVINGS OPPORTUNITIES

For each category:

If:
current > median(last 3 months)

Then:

* potential_savings = difference

---

# 7. INCREMENTAL UPDATE FLOW

* Upload new data
* Clean and validate
* Skip duplicates
* Append to transactions

Recompute ONLY:

* current month
* last 3 months
* current year

---

# 8. API DESIGN

POST /upload

* initial dataset

POST /update

* new data

GET /dashboard

* full analytics

---

# 9. FRONTEND (STREAMLIT)

---

## Section 1: Overview

* income, expense, investments, savings rate

---

## Section 2: Monthly Trends

* line charts

---

## Section 3: Yearly Trends

* yearly charts

---

## Section 4: Category Breakdown

* pie chart
* bar chart

---

## Section 5: Tag Analysis

* essential vs discretionary split

---

## Section 6: Anomalies & Erratic Spend

* table:

  * month
  * category
  * reason

---

## Section 7: Savings Opportunities

* table:

  * category
  * current
  * median
  * potential savings

---

## Section 8: Comparison View

* current vs last month
* current vs 3-month average

---

# 10. SYSTEM RULES

* No AI usage
* All analytics must be deterministic
* No duplicate data
* Handle missing data gracefully
* All outputs derived from stored data
* Modular code structure

---

# 11. OUTPUT EXPECTATION

Return:

1. Full codebase
2. File structure
3. Setup instructions
4. Sample dataset
5. Example API usage

---

Focus on clarity, modularity, and correctness. Avoid overengineering but ensure the system is extensible.
