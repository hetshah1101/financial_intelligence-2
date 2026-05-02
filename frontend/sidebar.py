import requests as _req
import streamlit as st

from api import api_dashboard, api_notes, api_upload
from config import API_BASE, COLORS
from formatters import fmt_month


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown(f"""
        <div style="padding:16px 0 8px">
          <span style="font-size:18px;font-weight:600;color:{COLORS['text_primary']};
                       letter-spacing:-0.02em">₹ Finsight</span>
        </div>
        """, unsafe_allow_html=True)

        _divider()

        with st.expander("Upload Data", expanded=False):
            sidebar_file = st.file_uploader(
                "CSV or XLSX", type=["csv", "xlsx"], key="sidebar_upload",
                label_visibility="collapsed",
            )
            upload_mode = st.radio(
                "Mode", ["Initial Load", "Update"], key="sidebar_mode", horizontal=True,
            )
            if st.button("Upload", key="sidebar_btn") and sidebar_file:
                endpoint = "/upload" if upload_mode == "Initial Load" else "/update"
                with st.spinner("Processing..."):
                    result = api_upload(endpoint, sidebar_file)
                    if result:
                        st.success(result["message"])
                        st.cache_data.clear()
                        st.rerun()

        _divider()

        probe = api_dashboard()
        if probe is not None:
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:6px;font-size:12px;color:{COLORS['green']}">
              <span style="width:6px;height:6px;background:{COLORS['green']};
                           border-radius:50%;display:inline-block"></span>
              API Connected
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:6px;font-size:12px;color:{COLORS['red']}">
              <span style="width:6px;height:6px;background:{COLORS['red']};
                           border-radius:50%;display:inline-block"></span>
              API Offline
            </div>
            """, unsafe_allow_html=True)

        # ── Month note editor ──────────────────────────────────────────────────
        sel_month = st.session_state.get("overview_month")
        if sel_month:
            _divider()
            notes = api_notes()
            existing_note = notes.get(sel_month, "")
            note_text = st.text_area(
                f"Note — {fmt_month(sel_month)}",
                value=existing_note,
                placeholder="e.g. Goa trip, annual insurance, bonus month...",
                key=f"note_{sel_month}",
                height=80,
            )
            if st.button("Save note", key=f"save_note_{sel_month}"):
                try:
                    _req.post(
                        f"{API_BASE}/notes",
                        json={"month": sel_month, "note": note_text},
                        timeout=5,
                    )
                    st.cache_data.clear()
                    st.success("Saved.")
                except Exception as e:
                    st.error(f"Could not save: {e}")


def _divider() -> None:
    st.markdown(
        f'<hr style="border:none;border-top:1px solid {COLORS["border"]};margin:8px 0">',
        unsafe_allow_html=True,
    )
