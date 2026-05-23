import streamlit as st
from data_manager import fetch_insight

def load_insight(seller_key: int, insight_type: str):
    """
    Safely fetch an insight with error handling and empty-state messaging.
    Returns a DataFrame or None if unavailable.
    """
    try:
        with st.spinner(f"Loading {insight_type.replace('_', ' ').title()}..."):
            df = fetch_insight(seller_key, insight_type)
        if df is None or df.empty:
            st.info(f"ℹ️ No active record entries found for type **{insight_type.replace('_', ' ').title()}**.")
            return None
        return df
    except Exception as e:
        st.error(f"❌ Error loading {insight_type}: {str(e)}")
        return None