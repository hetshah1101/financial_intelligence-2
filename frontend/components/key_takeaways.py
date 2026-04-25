"""
Key Takeaways Component

Renders auto-derived financial insights with visual emphasis.

UX Principles Applied:
- Visual Hierarchy: Insights ranked by importance, prominent placement
- Pre-attentive Processing: Color & icon instantly convey status
- Progressive Disclosure: Expandable explanations for detail
- Cognitive Load: Chunked into small, digestible cards (Miller's Law: 7±2)
"""
import streamlit as st
import pandas as pd


def render_key_takeaways(insights: list) -> None:
    """
    Display insights as scannable cards with color-coded status.

    - Green: Positive (savings, income increase)
    - Red: Warning (high expenses, anomalies)
    - Blue: Neutral info
    """
    if not insights:
        return

    st.markdown("---")

    # Section Header with explanation
    # (Nielsen heuristic: System status visibility - let user know what they're seeing)
    col1, col2 = st.columns([1, 10])
    with col1:
        st.markdown("### 🎯")
    with col2:
        st.markdown("### KEY TAKEAWAYS")
        st.caption("Auto-derived insights to guide your financial decisions")

    st.markdown("---")

    # Color-code palette (Pre-attentive processing)
    # Success → Green, Warning → Orange/Red, Info → Blue
    color_map = {
        "success": "#2ecc71",
        "warning": "#f39c12",
        "info": "#3498db",
    }

    # Render insights as columns for side-by-side scanning
    # (Gestalt principle: Proximity + Similarity for grouping)
    insight_cols = st.columns(min(3, len(insights)))

    for idx, insight in enumerate(insights):
        col = insight_cols[idx % len(insight_cols)]

        with col:
            # Card container with subtle background
            st.markdown(f"""
            <div style="
                padding: 16px;
                border-left: 4px solid {color_map.get(insight['type'], '#95a5a6')};
                background-color: #f8f9fa;
                border-radius: 4px;
                margin-bottom: 12px;
            ">
                <p style="margin: 0; font-size: 12px; color: #7f8c8d; font-weight: 600;">
                    {insight['title'].upper()}
                </p>
                <p style="margin: 4px 0; font-size: 24px; font-weight: 700; color: {color_map.get(insight['type'], '#34495e')};">
                    {insight['value']}
                </p>
                <p style="margin: 0; font-size: 11px; color: #7f8c8d;">
                    {insight['description']}
                </p>
            </div>
            """, unsafe_allow_html=True)

            # Progressive disclosure: expandable explanation
            # (Reduces initial cognitive load, provides detail on demand)
            with st.expander("Why this matters", expanded=False):
                st.caption(insight.get("explanation", ""))

    st.markdown("---")
