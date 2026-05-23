import streamlit as st
from query_factory import SellerInsightQueryFactory

@st.cache_data(ttl=300, show_spinner="Querying Databricks warehouse...")
def fetch_insight(seller_key: int, insight_type: str, catalog: str = "workspace", schema: str = "tijartek_gold"):
    """
    Fetches a specific insight using the cached executor context from state.
    Results are cached for 5 minutes to mitigate pipeline overhead.
    """
    if "db_executor" not in st.session_state:
        from db_layer import DatabricksConnectionManager, DatabricksQueryExecutor
        conn_mgr = DatabricksConnectionManager()
        executor = DatabricksQueryExecutor(conn_mgr)
    else:
        executor = st.session_state.db_executor

    factory = SellerInsightQueryFactory(seller_key, catalog, schema)
    query = factory.get_query(insight_type)
    return executor.execute_to_dataframe(query)