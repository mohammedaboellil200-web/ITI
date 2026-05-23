import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from utils import load_insight
from components import (
    inject_theme, render_kpi_row, section_title,
    CHART_HEIGHT, CHART_LAYOUT, COLORS, PLOTLY_PALETTE,
    insight_badge, empty_state,
)

inject_theme()

if not st.session_state.get("seller_key"):
    st.warning("Please select a seller from the main page sidebar.")
    st.stop()

sk = st.session_state.seller_key
section_title("📈 Store Overview", "Executive pulse check — revenue, market share, velocity & expansion")

# ── LOAD CORE DATA ──
exec_df   = load_insight(sk, "executive_summary_kpis")
sales_df  = load_insight(sk, "sales_performance")
market_df = load_insight(sk, "market_share_benchmarking")
basket_df = load_insight(sk, "basket_analysis_co_purchase")
geo_df    = load_insight(sk, "geospatial_expansion")
prod_df   = load_insight(sk, "product_profitability")

# ── FILTER BAR ──
with st.container():
    st.markdown('<div style="background:#161929;border:1px solid #2A2F4A;border-radius:12px;padding:14px 20px;margin-bottom:20px">', unsafe_allow_html=True)
    fc1, fc2, fc3 = st.columns([2, 2, 3])
    year_options = ["All"]
    if sales_df is not None and "year" in sales_df.columns:
        year_options += sorted(sales_df["year"].dropna().unique().astype(str).tolist(), reverse=True)
    selected_year = fc1.selectbox("📅 Year", year_options, key="ov_year")
    cat_options = ["All"]
    if market_df is not None and "category_name" in market_df.columns:
        cat_options += sorted(market_df["category_name"].dropna().unique().tolist())
    selected_cat = fc2.selectbox("🏷 Category", cat_options, key="ov_cat")
    fc3.markdown('<p style="font-size:0.78rem;color:#8890B5;margin-top:28px">Filters apply to charts. KPIs reflect all-time totals.</p>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ── ENHANCED KPI ROW (8 metrics) ──
if exec_df is not None:
    row = exec_df.iloc[0]
    margin = float(row["operating_margin_pct"])
    realization = round((float(row["net_revenue"]) / float(row["gross_revenue"])) * 100, 1) if float(row["gross_revenue"]) > 0 else 0
    discount_leakage = float(row["gross_revenue"]) - float(row["net_revenue"])
    metrics = [
        {"label": "Total Orders",         "value": f"{int(row['total_orders']):,}"},
        {"label": "Units Sold",            "value": f"{int(row['total_units_sold']):,}"},
        {"label": "Gross Revenue",         "value": f"${float(row['gross_revenue']):,.0f}"},
        {"label": "Net Revenue",           "value": f"${float(row['net_revenue']):,.0f}"},
        {"label": "Avg Order Value",       "value": f"${float(row['average_order_value']):.2f}"},
        {"label": "Units / Transaction",   "value": f"{float(row['units_per_transaction']):.1f}"},
        {"label": "Operating Margin",      "value": f"{margin:.1f}%",       "delta": "▲ healthy" if margin >= 30 else "▼ watch"},
        {"label": "Revenue Realization",   "value": f"{realization:.1f}%",  "delta": f"-${discount_leakage:,.0f} leakage"},
    ]
    render_kpi_row(metrics, num_cols=4)
    # Second row — derived power metrics
    if sales_df is not None and not sales_df.empty:
        total_months = len(sales_df)
        avg_monthly_rev = float(row['net_revenue']) / total_months if total_months > 0 else 0
        peak_row = sales_df.loc[sales_df["gross_revenue"].idxmax()] if "gross_revenue" in sales_df.columns else None
        peak_label = f"{peak_row['month_name']} {peak_row['year']}" if peak_row is not None else "—"
        metrics2 = [
            {"label": "Avg Monthly Revenue",  "value": f"${avg_monthly_rev:,.0f}"},
            {"label": "Peak Revenue Period",  "value": str(peak_label)},
            {"label": "Discount Leakage",     "value": f"${discount_leakage:,.0f}", "delta": f"{100-realization:.1f}% of gross"},
        ]
        render_kpi_row(metrics2, num_cols=3)

st.markdown("---")

# ── ROW 1: Revenue Waterfall + Market Share Treemap ──
c1, c2 = st.columns(2)

with c1:
    insight_badge("Revenue Waterfall — Gross to Net")
    if exec_df is not None:
        row = exec_df.iloc[0]
        gross = float(row["gross_revenue"])
        net = float(row["net_revenue"])
        leakage = gross - net
        fig = go.Figure(go.Waterfall(
            orientation="v",
            measure=["absolute", "relative", "total"],
            x=["Gross Revenue", "Discount & Fees", "Net Revenue"],
            y=[gross, -leakage, 0],
            text=[f"${gross:,.0f}", f"-${leakage:,.0f}", f"${net:,.0f}"],
            textposition="outside",
            textfont=dict(color=COLORS["text_primary"], size=12),
            connector=dict(line=dict(color=COLORS["border"], width=1.5, dash="solid")),
            increasing=dict(marker=dict(color=COLORS["success"])),
            decreasing=dict(marker=dict(color=COLORS["danger"])),
            totals=dict(marker=dict(color=COLORS["accent"])),
        ))
        fig.update_layout(**{**CHART_LAYOUT, "title": "Revenue Waterfall: Gross → Net", "height": CHART_HEIGHT})
        st.plotly_chart(fig, width="stretch")
    else:
        empty_state("No KPI data available")

with c2:
    insight_badge("Category Market Share")
    if market_df is not None:
        df = market_df.copy()
        if selected_cat != "All":
            df = df[df["category_name"] == selected_cat]
        fig = px.treemap(
            df,
            path=["category_name"],
            values="seller_market_share_revenue_percentage",
            color="seller_market_share_revenue_percentage",
            color_continuous_scale=[[0, COLORS["primary_dark"]], [0.5, COLORS["primary"]], [1, COLORS["accent"]]],
            custom_data=["category_name", "seller_market_share_revenue_percentage"],
        )
        fig.update_traces(
            texttemplate="<b>%{label}</b><br>%{value:.1f}%",
            textfont_size=13,
            hovertemplate="<b>%{customdata[0]}</b><br>Market Share: %{customdata[1]:.2f}%<extra></extra>",
        )
        fig.update_layout(**{**CHART_LAYOUT, "title": "Market Share Treemap by Category",
                             "height": CHART_HEIGHT, "coloraxis_showscale": False,
                             "margin": dict(l=8, r=8, t=56, b=8)})
        st.plotly_chart(fig, width="stretch")
    else:
        empty_state("No market share data available")

# ── ROW 2: Monthly Revenue (enhanced dual-axis) + Top Products Bubble ──
c3, c4 = st.columns(2)

with c3:
    insight_badge("Monthly Revenue Trend")
    if sales_df is not None:
        df = sales_df.copy()
        if selected_year != "All":
            df = df[df["year"].astype(str) == selected_year]
        df = df.sort_values(["year", "month_name"] if "month_name" in df.columns else ["year"])
        df["period"] = df["year"].astype(str) + " " + df.get("month_name", pd.Series(range(len(df)))).astype(str)
        df["rolling_net"] = df["net_revenue"].rolling(3, min_periods=1).mean()

        fig = go.Figure()
        fig.add_trace(go.Bar(x=df["period"], y=df["gross_revenue"], name="Gross",
                             marker=dict(color=COLORS["primary"], opacity=0.6),
                             hovertemplate="<b>%{x}</b><br>Gross: $%{y:,.0f}<extra></extra>"))
        fig.add_trace(go.Bar(x=df["period"], y=df["net_revenue"], name="Net",
                             marker=dict(color=COLORS["accent"], opacity=0.85),
                             hovertemplate="Net: $%{y:,.0f}<extra></extra>"))
        fig.add_trace(go.Scatter(x=df["period"], y=df["rolling_net"], name="3M Avg Net",
                                 mode="lines", line=dict(color=COLORS["accent3"], width=2, dash="dot"),
                                 hovertemplate="3M Avg: $%{y:,.0f}<extra></extra>"))
        if "total_orders" in df.columns:
            fig.add_trace(go.Scatter(x=df["period"], y=df["total_orders"], name="Orders",
                                     mode="lines+markers", line=dict(color=COLORS["accent2"], width=1.5),
                                     marker=dict(size=6), yaxis="y2",
                                     hovertemplate="Orders: %{y:,}<extra></extra>"))
            fig.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False,
                                          tickfont=dict(color=COLORS["accent2"])))
        fig.update_layout(**{**CHART_LAYOUT, "title": "Monthly Gross vs Net Revenue + 3M Rolling Avg",
                             "height": CHART_HEIGHT, "barmode": "overlay",
                             "legend": {**CHART_LAYOUT["legend"], "orientation": "h", "y": 1.08},
                             "xaxis_tickangle": -35})
        st.plotly_chart(fig, width="stretch")
    else:
        empty_state("No sales trend data available")

with c4:
    insight_badge("Top Products Revenue vs Profitability")
    if prod_df is not None:
        df = prod_df.head(20).copy()
        fig = px.scatter(
            df, x="net_marketplace_sales", y="estimated_seller_takehome",
            size="units_sold", color="category_name",
            color_discrete_sequence=PLOTLY_PALETTE,
            hover_name="product_name",
            labels={"net_marketplace_sales": "Net Sales $", "estimated_seller_takehome": "Est. Takehome $"},
            size_max=45,
        )
        # Diagonal = 100% takehome reference line
        max_val = df["net_marketplace_sales"].max()
        fig.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val,
                      line=dict(color=COLORS["text_muted"], width=1, dash="dot"))
        fig.update_layout(**{**CHART_LAYOUT, "title": "Revenue vs Takehome (size=units sold)",
                             "height": CHART_HEIGHT,
                             "legend": {**CHART_LAYOUT["legend"], "orientation": "h", "y": 1.08}})
        st.plotly_chart(fig, width="stretch")
    else:
        empty_state("No product profitability data available")

# ── ROW 3: Basket Co-purchase + Geo Bubble Map ──
c5, c6 = st.columns(2)

with c5:
    insight_badge("Co-purchase Affinity (Top 15)")
    if basket_df is not None:
        top = basket_df.head(15).copy()
        top["label"] = top["primary_product"].str[:30]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=top["co_purchase_frequency"], y=top["label"],
            orientation="h",
            marker=dict(color=top["co_purchase_frequency"],
                        colorscale=[[0, COLORS["bg_card2"]], [1, COLORS["primary"]]],
                        showscale=False),
            text=top["co_purchase_frequency"].apply(lambda v: f"{v:,}"),
            textposition="outside", textfont_color=COLORS["text_primary"],
            hovertemplate="<b>%{y}</b><br>Co-buys: %{x:,}<extra></extra>",
        ))
        fig.update_layout(**{**CHART_LAYOUT, "title": "Top Bundle Co-purchase Frequency",
                             "height": CHART_HEIGHT,
                             "yaxis": {**CHART_LAYOUT["yaxis"], "categoryorder": "total ascending"}})
        st.plotly_chart(fig, width="stretch")
    else:
        empty_state("No basket analysis data available")

with c6:
    insight_badge("Geographic Revenue Contribution")
    if geo_df is not None:
        df = geo_df.head(15).copy()
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df["geographic_net_revenue"], y=df["city"],
            orientation="h",
            marker=dict(color=df["geographic_revenue_contribution_pct"],
                        colorscale=[[0, COLORS["primary_dark"]], [1, COLORS["accent"]]],
                        showscale=True,
                        colorbar=dict(title=dict(text="Share %", font=dict(color=COLORS["text_muted"])),
                                      tickfont=dict(color=COLORS["text_muted"]), ticksuffix="%", len=0.6)),
            text=df["geographic_revenue_contribution_pct"].apply(lambda v: f"{v:.1f}%"),
            textposition="outside", textfont_color=COLORS["text_primary"],
            customdata=df["avg_basket_spend_by_city"],
            hovertemplate="<b>%{y}</b><br>Revenue: $%{x:,.0f}<br>Avg Basket: $%{customdata:,.0f}<extra></extra>",
        ))
        fig.update_layout(**{**CHART_LAYOUT, "title": "Top Cities — Revenue & Share",
                             "height": CHART_HEIGHT,
                             "yaxis": {**CHART_LAYOUT["yaxis"], "categoryorder": "total ascending"}})
        st.plotly_chart(fig, width="stretch")
    else:
        empty_state("No geographic data available")

# ── REVENUE REALIZATION DEEP-DIVE ──
if sales_df is not None and "revenue_realization_rate" in sales_df.columns:
    st.markdown("---")
    insight_badge("Revenue Realization Rate — Monthly Trend")
    df = sales_df.copy()
    if selected_year != "All":
        df = df[df["year"].astype(str) == selected_year]
    df = df.sort_values(["year", "month_name"] if "month_name" in df.columns else ["year"])
    df["period"] = df["year"].astype(str) + " " + df.get("month_name", pd.Series(range(len(df)))).astype(str)
    df["total_discounts"] = df["gross_revenue"] - df["net_revenue"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["period"], y=df["revenue_realization_rate"],
                             mode="lines+markers+text", name="Realization %",
                             line=dict(color=COLORS["accent3"], width=2.5),
                             marker=dict(size=8, color=COLORS["accent3"]),
                             fill="tozeroy", fillcolor="rgba(255,217,61,0.06)",
                             text=df["revenue_realization_rate"].apply(lambda v: f"{v:.1f}%"),
                             textposition="top center", textfont=dict(color=COLORS["text_muted"], size=10)))
    fig.add_trace(go.Bar(x=df["period"], y=df["total_discounts"], name="Discount Given",
                         marker=dict(color=COLORS["danger"], opacity=0.45), yaxis="y2",
                         hovertemplate="Discounts: $%{y:,.0f}<extra></extra>"))
    fig.update_layout(**{**CHART_LAYOUT, "title": "Revenue Realization Rate vs Discount Volume",
                         "height": 320, "yaxis_ticksuffix": "%",
                         "yaxis_range": [max(0, df["revenue_realization_rate"].min() - 5), 105],
                         "yaxis2": dict(overlaying="y", side="right", showgrid=False,
                                        tickfont=dict(color=COLORS["danger"]),
                                        title=dict(text="Discount $", font=dict(color=COLORS["danger"]))),
                         "xaxis_tickangle": -35,
                         "legend": {**CHART_LAYOUT["legend"], "orientation": "h", "y": 1.08}})
    st.plotly_chart(fig, width="stretch")