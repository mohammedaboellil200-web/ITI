import streamlit as st
from db_layer import DatabricksConnectionManager, DatabricksQueryExecutor

st.set_page_config(
    page_title="Tijartek Seller Insights Pro",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── INJECT GLOBAL THEME ──
from components import inject_theme, COLORS
inject_theme()

# ── SESSION STATE INITIALIZATION ──
for key, default in [
    ("seller_key", None),
    ("seller_label", None),
    ("search_results", None),
    ("db_connected", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── DATABASE INITIALIZATION ──
@st.cache_resource
def init_executor():
    conn_mgr = DatabricksConnectionManager()
    return DatabricksQueryExecutor(conn_mgr)

try:
    executor = init_executor()
    st.session_state.db_executor = executor
    st.session_state.db_connected = True
except Exception as e:
    st.session_state.db_connected = False
    st.session_state.db_error = str(e)

# ── SIDEBAR ──
st.sidebar.markdown("""
<div style='padding:8px 0 16px 0'>
    <div style='font-family:Syne,sans-serif;font-size:1.3rem;font-weight:800;
                background:linear-gradient(135deg,#6C63FF,#00E5C3);
                -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                background-clip:text;'>
        Tijartek Pro
    </div>
    <div style='font-size:0.72rem;color:#8890B5;letter-spacing:0.08em;text-transform:uppercase;margin-top:2px'>
        Enterprise Seller Analytics
    </div>
</div>
""", unsafe_allow_html=True)

if not st.session_state.db_connected:
    st.sidebar.error("⚡ Connection Error")
    st.sidebar.caption(st.session_state.get("db_error", "Unknown error."))
    st.error("Configure `.env` with valid Databricks credentials to continue.")
    st.stop()

st.sidebar.markdown("---")
st.sidebar.markdown(
    '<p style="font-size:0.72rem;text-transform:uppercase;letter-spacing:0.08em;'
    'color:#6C63FF;font-weight:600;margin-bottom:8px">Merchant Lookup</p>',
    unsafe_allow_html=True,
)
st.sidebar.caption("Search by name, ID, or both.")

with st.sidebar.form(key="seller_search_form", clear_on_submit=False):
    name_input = st.text_input("Seller Name", placeholder="e.g. Acme Corp", key="search_name")
    id_input   = st.text_input("Seller ID",   placeholder="e.g. SELL_12345", key="search_id")
    search_btn = st.form_submit_button("Search Merchants", use_container_width=True)

# ── SEARCH LOGIC ──
if search_btn:
    name_val = name_input.strip()
    id_val   = id_input.strip()
    if not name_val and not id_val:
        st.sidebar.warning("Enter at least a name or ID.")
        st.session_state.search_results = None
    else:
        try:
            with st.sidebar.status("Querying warehouse...", expanded=False) as status:
                if id_val and name_val:
                    results = st.session_state.db_executor.lookup_seller_combined(name_val, id_val)
                elif id_val:
                    results = st.session_state.db_executor.lookup_seller_by_id(id_val)
                else:
                    results = st.session_state.db_executor.lookup_seller_by_name(name_val)
                status.update(label="Done", state="complete")
            st.session_state.search_results = results
            if results is None or results.empty:
                st.sidebar.warning("No merchants matched.")
                st.session_state.seller_key   = None
                st.session_state.seller_label = None
            else:
                st.sidebar.success(f"{len(results)} result(s) found")
        except Exception as e:
            st.sidebar.error(f"Error: {e}")

# ── MERCHANT SELECTOR ──
if st.session_state.get("search_results") is not None:
    results = st.session_state.search_results
    if not results.empty:
        options = {
            f"{row['name']}  ·  {row['seller_id']}  ·  {row['seller_tier']}": row["seller_key"]
            for _, row in results.iterrows()
        }
        selected_label = st.sidebar.selectbox("Active Profile", list(options.keys()), key="seller_profile_selector")
        new_key = options[selected_label]
        if st.session_state.seller_key != new_key:
            st.session_state.seller_key   = new_key
            st.session_state.seller_label = selected_label
            st.rerun()

# ── STATUS FOOTER ──
st.sidebar.markdown("---")
if st.session_state.get("seller_key"):
    st.sidebar.markdown(
        f'<div style="background:rgba(0,229,195,0.1);border:1px solid rgba(0,229,195,0.25);'
        f'border-radius:8px;padding:10px 12px;font-size:0.8rem;color:#00E5C3;">'
        f'✓ Active: <strong>{st.session_state.seller_label}</strong></div>',
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)
    if st.sidebar.button("↩ Change Merchant", use_container_width=True):
        st.session_state.seller_key   = None
        st.session_state.seller_label = None
        st.session_state.search_results = None
        st.rerun()
else:
    st.sidebar.info("Search for a merchant to begin.")

st.sidebar.markdown(
    '<p style="font-size:0.68rem;color:#3A3F5C;text-align:center;margin-top:16px">'
    '© 2026 Tijartek Analytics · Databricks SQL</p>',
    unsafe_allow_html=True,
)

# ── LANDING PAGE ──
if not st.session_state.get("seller_key"):
    st.markdown("""
    <div style='padding:60px 0 40px 0;text-align:center'>
        <div style='font-family:Syne,sans-serif;font-size:3rem;font-weight:800;
                    background:linear-gradient(135deg,#F0F2FF 0%,#6C63FF 50%,#00E5C3 100%);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                    background-clip:text;line-height:1.15;margin-bottom:16px'>
            Tijartek Seller Insights Pro
        </div>
        <p style='color:#8890B5;font-size:1.05rem;max-width:540px;margin:0 auto 40px auto;line-height:1.6'>
            Enterprise-grade seller analytics powered by Databricks SQL Warehouse.
            Search a merchant in the sidebar to unlock all modules.
        </p>
    </div>
    """, unsafe_allow_html=True)

    cols = st.columns(4)
    tiles = [
        ("📈", "Store Overview",        "Executive KPIs, revenue trends, market share, basket analysis"),
        ("💵", "Sales & Financials",    "Promo ROI, payment friction, conversion funnel"),
        ("📦", "Inventory & Logistics", "Stock velocity, SLA compliance, returns, satisfaction"),
        ("👥", "Customer Insights",     "RFM segmentation, demographics, retention, geo expansion"),
        ("⭐", "Ratings & Reviews",     "Sentiment analysis, rating distribution, review intelligence"),
        ("🎯", "Executive Command",     "Single-screen health score, alerts, strategic radar"),
    ]
    for col, (icon, title, desc) in zip(cols, tiles):
        col.markdown(
            f"""<div style='background:#161929;border:1px solid #2A2F4A;border-radius:14px;
                            padding:24px 20px;height:100%;position:relative;overflow:hidden'>
                <div style='font-size:1.8rem;margin-bottom:12px'>{icon}</div>
                <div style='font-family:Syne,sans-serif;font-size:0.95rem;font-weight:700;
                            color:#F0F2FF;margin-bottom:8px'>{title}</div>
                <div style='font-size:0.8rem;color:#8890B5;line-height:1.5'>{desc}</div>
                <div style='position:absolute;bottom:0;left:0;right:0;height:2px;
                            background:linear-gradient(90deg,#6C63FF,#00E5C3)'></div>
            </div>""",
            unsafe_allow_html=True,
        )
else:
    st.markdown(
        f"""
        <div style='display:flex;align-items:center;gap:16px;padding:24px 0 8px 0'>
            <div>
                <div style='font-family:Syne,sans-serif;font-size:1.8rem;font-weight:800;color:#F0F2FF'>
                    Seller Workspace
                </div>
                <div style='color:#8890B5;font-size:0.88rem;margin-top:4px'>
                    {st.session_state.seller_label}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="background:rgba(108,99,255,0.08);border:1px solid rgba(108,99,255,0.2);'
        'border-radius:10px;padding:12px 16px;color:#A78BFA;font-size:0.85rem">'
        '👈 Navigate between analytics modules using the sidebar pages.</div>',
        unsafe_allow_html=True,
    )