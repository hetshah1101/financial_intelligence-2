import os

COLORS = {
    "bg_page":        "#0f0f0f",
    "bg_card":        "#161616",
    "bg_elevated":    "#1e1e1e",
    "border":         "#2a2a2a",
    "border_subtle":  "#1e1e1e",
    "text_primary":   "#e8e6e0",
    "text_secondary": "#888780",
    "text_tertiary":  "#4a4a48",
    "green":          "#4caf7d",
    "red":            "#e05252",
    "amber":          "#c9883a",
    "blue":           "#4a90c4",
    "purple":         "#7c6fcd",
    "chart":          ["#7c6fcd", "#4caf7d", "#c9883a", "#4a90c4", "#e05252", "#6b9e8f", "#888780"],
}

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

GLOBAL_CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500&display=swap');

  html, body, [data-testid="stApp"],
  [data-testid="stAppViewContainer"],
  section[data-testid="stMain"],
  .main { background-color: #0f0f0f !important; }

  #MainMenu, footer, header, .stDeployButton { display: none !important; }

  /* Remove ALL white chart backgrounds */
  .js-plotly-plot .plotly, .plot-container { background: transparent !important; }
  .js-plotly-plot .plotly .bg { fill: transparent !important; }

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid #2a2a2a;
    gap: 8px;
  }
  .stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #4a4a48 !important;
    font-size: 13px;
    padding: 8px 16px;
    border-radius: 6px 6px 0 0;
  }
  .stTabs [aria-selected="true"] {
    color: #e8e6e0 !important;
    border-bottom: 2px solid #7c6fcd !important;
    background: transparent !important;
  }

  /* Inputs / selects */
  .stSelectbox > div > div,
  .stMultiSelect > div > div { background: #1e1e1e !important; border-color: #2a2a2a !important; color: #e8e6e0 !important; }

  /* Radio buttons */
  .stRadio > div { gap: 4px; }
  .stRadio label { color: #888780 !important; font-size: 13px !important; }

  /* Dataframe */
  [data-testid="stDataFrame"] iframe { background: #161616 !important; }

  /* Metrics */
  [data-testid="metric-container"] {
    background: #161616;
    border: 1px solid #2a2a2a;
    border-radius: 10px;
    padding: 20px 24px;
  }
  [data-testid="stMetricLabel"] p { font-size: 11px !important; letter-spacing: .1em; text-transform: uppercase; color: #888780 !important; }
  [data-testid="stMetricValue"] { font-family: 'DM Mono', monospace !important; color: #e8e6e0 !important; }
  [data-testid="stMetricDelta"] svg { display: none; }

  /* Expanders */
  [data-testid="stExpander"] {
    background: #161616 !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 10px !important;
  }
  [data-testid="stExpander"] summary { color: #888780 !important; }

  /* File uploader */
  [data-testid="stFileUploader"] {
    background: #1e1e1e !important;
    border: 1px dashed #2a2a2a !important;
    border-radius: 10px !important;
  }

  /* Scrollbar */
  ::-webkit-scrollbar { width: 4px; height: 4px; }
  ::-webkit-scrollbar-track { background: #0f0f0f; }
  ::-webkit-scrollbar-thumb { background: #2a2a2a; border-radius: 2px; }

  .main .block-container { padding: 24px 32px !important; max-width: 100% !important; }
  div[data-testid="stHorizontalBlock"] { gap: 12px !important; }

  /* Sidebar */
  [data-testid="stSidebar"] > div {
    background: #0d0d0d !important;
    border-right: 1px solid #1a1a1a;
  }
</style>
"""

# ── Category classification ──────────────────────────────────────────────────
# Edit this dict to reclassify categories. Change takes effect on next page load.
CATEGORY_CLASSIFICATION: dict = {
    # Essential
    "Food":        "essential",
    "Grocery":     "essential",
    "Groceries":   "essential",
    "Utilities":   "essential",
    "Electricity": "essential",
    "Water":       "essential",
    "Gas":         "essential",
    "Internet":    "essential",
    "Mobile":      "essential",
    "Rent":        "essential",
    "Home":        "essential",
    "EMI":         "essential",
    "Insurance":   "essential",
    "Health":      "essential",
    "Medical":     "essential",
    "Pharmacy":    "essential",
    "Doctor":      "essential",
    "Transport":   "essential",
    "Petrol":      "essential",
    "Fuel":        "essential",
    "Tax":         "essential",
    "Education":   "essential",
    "Healthcare":  "essential",
    "Commute":     "essential",

    # Discretionary
    "Entertainment":  "discretionary",
    "OTT":            "discretionary",
    "Dining Out":     "discretionary",
    "Restaurant":     "discretionary",
    "Travel":         "discretionary",
    "Hotel":          "discretionary",
    "Flights":        "discretionary",
    "Shopping":       "discretionary",
    "Clothing":       "discretionary",
    "Electronics":    "discretionary",
    "Books":          "discretionary",
    "Gym":            "discretionary",
    "Sports":         "discretionary",
    "Social Life":    "discretionary",
    "Family":         "discretionary",
    "Gifts":          "discretionary",
    "Subscriptions":  "discretionary",
    "Other":          "discretionary",
    "Miscellaneous":  "discretionary",
    "Personal Care":  "discretionary",
    "Fitness":        "discretionary",
    "Accessories":    "discretionary",
    "Gadgets":        "discretionary",
    "Food Delivery":  "discretionary",
}

CATEGORY_DEFAULT_TYPE = "discretionary"


def classify_category(category: str) -> str:
    """Return 'essential' or 'discretionary'. Case-insensitive lookup."""
    if category in CATEGORY_CLASSIFICATION:
        return CATEGORY_CLASSIFICATION[category]
    lower = category.lower()
    for key, val in CATEGORY_CLASSIFICATION.items():
        if key.lower() == lower:
            return val
    return CATEGORY_DEFAULT_TYPE
