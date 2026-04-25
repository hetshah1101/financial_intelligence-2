import streamlit as st

from api import api_upload, api_months
from config import COLORS
from formatters import fmt_month


def render_data() -> None:
    col_initial, col_update = st.columns(2)

    with col_initial:
        st.markdown("#### Initial Load")
        st.caption("Upload your full transaction history")
        file_init = st.file_uploader(
            "", type=["csv", "xlsx"], key="upload_initial",
            label_visibility="collapsed",
        )
        if st.button("Load Dataset →", key="btn_initial") and file_init:
            with st.spinner("Processing..."):
                result = api_upload("/upload", file_init)
                if result:
                    st.success(result["message"])
                    st.cache_data.clear()

    with col_update:
        st.markdown("#### Monthly Update")
        st.caption("Append new month data safely")
        file_upd = st.file_uploader(
            "", type=["csv", "xlsx"], key="upload_update",
            label_visibility="collapsed",
        )
        if st.button("Update →", key="btn_update") and file_upd:
            with st.spinner("Updating..."):
                result = api_upload("/update", file_upd)
                if result:
                    st.success(result["message"])
                    st.cache_data.clear()

    st.markdown(f"""
    <div style="background:{COLORS['bg_card']};border:1px solid {COLORS['border']};
                border-radius:10px;padding:16px 20px;margin-top:16px">
      <div style="font-size:11px;letter-spacing:.1em;color:{COLORS['text_tertiary']};
                  text-transform:uppercase;margin-bottom:10px">
        Supported Column Formats
      </div>
      <div style="font-size:12px;color:{COLORS['text_secondary']};line-height:2">
        <b style="color:{COLORS['text_primary']}">Original:</b>
        <code style="background:{COLORS['bg_elevated']};padding:2px 6px;border-radius:4px;color:{COLORS['purple']}">date</code>
        <code style="background:{COLORS['bg_elevated']};padding:2px 6px;border-radius:4px">account</code>
        <code style="background:{COLORS['bg_elevated']};padding:2px 6px;border-radius:4px">category</code>
        <code style="background:{COLORS['bg_elevated']};padding:2px 6px;border-radius:4px">subcategory</code>
        <code style="background:{COLORS['bg_elevated']};padding:2px 6px;border-radius:4px">description</code>
        <code style="background:{COLORS['bg_elevated']};padding:2px 6px;border-radius:4px">amount</code>
        <code style="background:{COLORS['bg_elevated']};padding:2px 6px;border-radius:4px;color:{COLORS['purple']}">type</code>
        <br>
        <b style="color:{COLORS['text_primary']}">Export format:</b>
        <code style="background:{COLORS['bg_elevated']};padding:2px 6px;border-radius:4px;color:{COLORS['purple']}">Period</code>
        <code style="background:{COLORS['bg_elevated']};padding:2px 6px;border-radius:4px">Accounts</code>
        <code style="background:{COLORS['bg_elevated']};padding:2px 6px;border-radius:4px">Category</code>
        <code style="background:{COLORS['bg_elevated']};padding:2px 6px;border-radius:4px">Subcategory</code>
        <code style="background:{COLORS['bg_elevated']};padding:2px 6px;border-radius:4px">Note</code>
        <code style="background:{COLORS['bg_elevated']};padding:2px 6px;border-radius:4px;color:{COLORS['purple']}">INR</code>
        <code style="background:{COLORS['bg_elevated']};padding:2px 6px;border-radius:4px;color:{COLORS['purple']}">Income/Expense</code>
        <code style="background:{COLORS['bg_elevated']};padding:2px 6px;border-radius:4px">Description</code>
        <code style="background:{COLORS['bg_elevated']};padding:2px 6px;border-radius:4px">Amount</code>
        <code style="background:{COLORS['bg_elevated']};padding:2px 6px;border-radius:4px">Currency</code>
      </div>
    </div>
    """, unsafe_allow_html=True)

    months_status = api_months()
    if months_status:
        range_start = fmt_month(months_status[-1])
        range_end   = fmt_month(months_status[0])
        st.markdown(f"""
        <div style="background:{COLORS['bg_card']};border:1px solid {COLORS['border']};
                    border-radius:10px;padding:16px 20px;margin-top:12px">
          <div style="font-size:11px;letter-spacing:.1em;color:{COLORS['text_tertiary']};
                      text-transform:uppercase;margin-bottom:10px">Database Status</div>
          <div style="display:flex;gap:24px;font-size:13px;color:{COLORS['text_secondary']}">
            <span>Months: <b style="color:{COLORS['text_primary']}">{len(months_status)}</b></span>
            <span>Latest: <b style="color:{COLORS['text_primary']}">{range_end}</b></span>
            <span>Range: <b style="color:{COLORS['text_primary']}">{range_start} – {range_end}</b></span>
          </div>
        </div>
        """, unsafe_allow_html=True)
