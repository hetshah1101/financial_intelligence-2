import requests
import streamlit as st

from config import API_BASE


@st.cache_data(ttl=60)
def api_dashboard() -> dict | None:
    try:
        r = requests.get(f"{API_BASE}/dashboard", timeout=8)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


@st.cache_data(ttl=60)
def api_months() -> list:
    """Return months in descending order (latest first)."""
    try:
        r = requests.get(f"{API_BASE}/months", timeout=5)
        data = r.json().get("months", [])
        if data:
            return data
    except Exception:
        pass
    # Fallback: derive from dashboard
    dash = api_dashboard()
    if dash:
        return sorted(
            list({m["month"] for m in dash.get("monthly_aggregates", [])}),
            reverse=True,
        )
    return []


def api_upload(endpoint: str, file) -> dict | None:
    try:
        r = requests.post(
            f"{API_BASE}{endpoint}",
            files={"file": (file.name, file.read())},
            timeout=300,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Upload failed: {e}")
        return None


def api_reset() -> dict | None:
    try:
        r = requests.delete(f"{API_BASE}/reset", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Reset failed: {e}")
        return None


def categories_for_month(dashboard: dict, month: str) -> list:
    """Filter category_aggregates for a specific month, sorted by amount desc."""
    return sorted(
        [c for c in dashboard.get("category_aggregates", []) if c["month"] == month],
        key=lambda x: -x["total_amount"],
    )
