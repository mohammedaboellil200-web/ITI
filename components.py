import streamlit as st

CHART_HEIGHT = 520

# ── DESIGN SYSTEM TOKENS ──
COLORS = {
    "primary":      "#6C63FF",
    "primary_dark": "#4B44CC",
    "accent":       "#00E5C3",
    "accent2":      "#FF6B6B",
    "accent3":      "#FFD93D",
    "success":      "#2ECC71",
    "warning":      "#F39C12",
    "danger":       "#E74C3C",
    "bg_dark":      "#0D0F1A",
    "bg_card":      "#161929",
    "bg_card2":     "#1E2237",
    "border":       "#2A2F4A",
    "text_primary": "#F0F2FF",
    "text_muted":   "#8890B5",
}

PLOTLY_PALETTE = [
    "#6C63FF", "#00E5C3", "#FF6B6B", "#FFD93D",
    "#A78BFA", "#34D399", "#FB923C", "#60A5FA",
]

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="'DM Sans', sans-serif", color="#B0B8D8", size=12),
    title_font=dict(family="'Syne', sans-serif", color="#F0F2FF", size=15),
    legend=dict(
        bgcolor="rgba(22,25,41,0.85)",
        bordercolor="#2A2F4A",
        borderwidth=1,
        font=dict(color="#B0B8D8", size=11),
    ),
    xaxis=dict(
        gridcolor="rgba(42,47,74,0.6)",
        linecolor="#2A2F4A",
        tickfont=dict(color="#8890B5"),
    ),
    yaxis=dict(
        gridcolor="rgba(42,47,74,0.6)",
        linecolor="#2A2F4A",
        tickfont=dict(color="#8890B5"),
    ),
    margin=dict(l=16, r=16, t=56, b=16),
    hoverlabel=dict(
        bgcolor="#161929",
        bordercolor="#6C63FF",
        font=dict(color="#F0F2FF", size=12),
    ),
)

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

/* ── BASE RESET ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* ── APP BACKGROUND ── */
.stApp {
    background: #0D0F1A;
    background-image:
        radial-gradient(ellipse 80% 50% at 20% 0%, rgba(108,99,255,0.08) 0%, transparent 60%),
        radial-gradient(ellipse 60% 40% at 80% 100%, rgba(0,229,195,0.06) 0%, transparent 60%);
}

/* ── SIDEBAR ── */
section[data-testid="stSidebar"] {
    background: #0A0C16 !important;
    border-right: 1px solid #1E2237 !important;
}
section[data-testid="stSidebar"] * { color: #B0B8D8 !important; }
section[data-testid="stSidebar"] h1, 
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 { color: #F0F2FF !important; }

/* ── METRIC CARDS ── */
[data-testid="metric-container"] {
    background: #161929 !important;
    border: 1px solid #2A2F4A !important;
    border-radius: 14px !important;
    padding: 20px 24px !important;
    position: relative;
    overflow: hidden;
    transition: border-color 0.2s;
}
[data-testid="metric-container"]:hover {
    border-color: #6C63FF !important;
}
[data-testid="metric-container"]::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #6C63FF, #00E5C3);
    border-radius: 14px 14px 0 0;
}
[data-testid="stMetricLabel"] {
    color: #8890B5 !important;
    font-size: 0.72rem !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
[data-testid="stMetricValue"] {
    color: #F0F2FF !important;
    font-family: 'Syne', sans-serif !important;
    font-size: 1.65rem !important;
    font-weight: 700 !important;
}
[data-testid="stMetricDelta"] { font-size: 0.8rem !important; }

/* ── PLOTLY CHARTS ── */
.js-plotly-plot .plotly { border-radius: 12px; }

/* ── SECTION HEADERS ── */
.tj-section-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 8px 0 4px 0;
}
.tj-section-header h2 {
    font-family: 'Syne', sans-serif;
    font-size: 1.6rem;
    font-weight: 700;
    background: linear-gradient(135deg, #F0F2FF 0%, #8890B5 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0;
}

/* ── FILTER BAR ── */
.tj-filter-bar {
    background: #161929;
    border: 1px solid #2A2F4A;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 20px;
}

/* ── INSIGHT BADGE ── */
.tj-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(108,99,255,0.15);
    border: 1px solid rgba(108,99,255,0.35);
    color: #A78BFA;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    padding: 3px 10px;
    border-radius: 20px;
}

/* ── DIVIDER ── */
hr { border-color: #1E2237 !important; }

/* ── INPUTS ── */
.stTextInput input, .stSelectbox select, .stMultiSelect, .stDateInput input {
    background: #1E2237 !important;
    border-color: #2A2F4A !important;
    color: #F0F2FF !important;
    border-radius: 8px !important;
}
.stButton > button {
    background: linear-gradient(135deg, #6C63FF, #4B44CC) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: opacity 0.2s !important;
}
.stButton > button:hover { opacity: 0.88 !important; }

/* ── EXPANDER ── */
.streamlit-expanderHeader {
    background: #161929 !important;
    border: 1px solid #2A2F4A !important;
    border-radius: 10px !important;
    color: #B0B8D8 !important;
}

/* ── INFO / WARNING / ERROR BOXES ── */
.stAlert { border-radius: 10px !important; }
</style>
"""


def inject_theme():
    """Inject the global CSS design system once."""
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def section_title(title: str, subtitle: str = ""):
    """Premium styled section header with optional subtitle."""
    html = f"""
    <div class="tj-section-header">
        <h2>{title}</h2>
    </div>"""
    if subtitle:
        html += f'<p style="color:#8890B5;font-size:0.85rem;margin:0 0 12px 0;">{subtitle}</p>'
    st.markdown(html, unsafe_allow_html=True)


def render_kpi_row(metrics: list, num_cols: int = 4):
    """Render a row of styled KPI metric cards."""
    cols = st.columns(num_cols)
    for i, m in enumerate(metrics):
        cols[i % num_cols].metric(
            label=m.get("label", "—"),
            value=m.get("value", "—"),
            delta=m.get("delta"),
        )
    st.markdown("<div style='margin-bottom:8px'></div>", unsafe_allow_html=True)


def filter_bar(label: str = "Filters"):
    """Styled container for filter rows."""
    return st.container()


def insight_badge(text: str):
    st.markdown(f'<span class="tj-badge">{text}</span>', unsafe_allow_html=True)


def empty_state(message: str, icon: str = "📭"):
    st.markdown(
        f"""
        <div style='text-align:center;padding:40px 20px;background:#161929;
                    border:1px dashed #2A2F4A;border-radius:14px;margin:8px 0;'>
            <div style='font-size:2rem;margin-bottom:8px'>{icon}</div>
            <p style='color:#8890B5;font-size:0.9rem;margin:0'>{message}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )