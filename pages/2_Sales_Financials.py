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
section_title("💵 Sales & Financials", "Profitability deep-dive — promotions, payment health & conversion engine")

# ── LOAD DATA ──
exec_df   = load_insight(sk, "executive_summary_kpis")
promo_df  = load_insight(sk, "promotion_roi")
pay_df    = load_insight(sk, "payment_method_friction")
funnel_df = load_insight(sk, "funnel_and_conversion")
sales_df  = load_insight(sk, "sales_performance")
prod_df   = load_insight(sk, "product_profitability")

# ── FILTERS ──
with st.container():
    st.markdown('<div style="background:#161929;border:1px solid #2A2F4A;border-radius:12px;padding:14px 20px;margin-bottom:20px">', unsafe_allow_html=True)
    fa, fb, fc, fd = st.columns([2, 2, 2, 3])
    dtype_opts = ["All"]
    if promo_df is not None and "discount_type" in promo_df.columns:
        dtype_opts += sorted(promo_df["discount_type"].dropna().unique().tolist())
    sel_dtype = fa.selectbox("🏷 Discount Type", dtype_opts, key="sf_dtype")
    plat_opts = ["All"]
    if promo_df is not None and "marketing_platform" in promo_df.columns:
        plat_opts += sorted(promo_df["marketing_platform"].dropna().unique().tolist())
    sel_plat = fb.selectbox("📡 Platform", plat_opts, key="sf_plat")
    gw_opts = ["All"]
    if pay_df is not None and "payment_gateway" in pay_df.columns:
        gw_opts += sorted(pay_df["payment_gateway"].dropna().unique().tolist())
    sel_gw = fc.selectbox("💳 Gateway", gw_opts, key="sf_gw")
    fd.markdown('<p style="font-size:0.78rem;color:#8890B5;margin-top:28px">Promo filters are independent from payment gateway filter.</p>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ── POWER KPI ROW ──
kpi_metrics = []
if exec_df is not None:
    row = exec_df.iloc[0]
    kpi_metrics.extend([
        {"label": "Net Revenue",         "value": f"${float(row['net_revenue']):,.0f}"},
        {"label": "AOV",                 "value": f"${float(row['average_order_value']):.2f}"},
        {"label": "Operating Margin",    "value": f"{float(row['operating_margin_pct']):.1f}%"},
    ])
if promo_df is not None:
    df_p = promo_df.copy()
    if sel_dtype != "All": df_p = df_p[df_p["discount_type"] == sel_dtype]
    if sel_plat  != "All": df_p = df_p[df_p["marketing_platform"] == sel_plat]
    best_roi = df_p.loc[df_p["efficiency_multiplier"].idxmax(), "promo_campaign_name"] if not df_p.empty else "—"
    kpi_metrics.extend([
        {"label": "Promo Orders",        "value": f"{int(df_p['attributed_orders'].sum()):,}"},
        {"label": "Margin Surrendered",  "value": f"${df_p['margin_surrendered'].sum():,.0f}"},
        {"label": "Avg Efficiency",      "value": f"{df_p['efficiency_multiplier'].mean():.2f}×"},
        {"label": "Best Campaign ROI",   "value": str(best_roi)[:20]},
    ])
if pay_df is not None:
    df_pay = pay_df.copy()
    if sel_gw != "All": df_pay = df_pay[df_pay["payment_gateway"] == sel_gw]
    success_rows = df_pay[df_pay["processing_status"].str.lower().isin(["success", "completed"])]
    failed_rows  = df_pay[df_pay["processing_status"].str.lower().isin(["failed", "declined"])]
    total_txn = df_pay["transaction_attempts"].sum()
    success_txn = success_rows["transaction_attempts"].sum()
    pay_success_rate = (success_txn / total_txn * 100) if total_txn > 0 else 0
    kpi_metrics.extend([
        {"label": "Payment Success Rate", "value": f"{pay_success_rate:.1f}%",
         "delta": "▲ healthy" if pay_success_rate >= 90 else "▼ friction detected"},
    ])
if kpi_metrics:
    render_kpi_row(kpi_metrics, num_cols=4)

st.markdown("---")

# ── ROW 1: Promo Campaign ROI + Payment Friction Heatmap ──
c1, c2 = st.columns(2)

with c1:
    insight_badge("Campaign ROI — Revenue vs Cost")
    if promo_df is not None:
        df = promo_df.copy()
        if sel_dtype != "All": df = df[df["discount_type"] == sel_dtype]
        if sel_plat  != "All": df = df[df["marketing_platform"] == sel_plat]
        df = df.sort_values("efficiency_multiplier", ascending=False)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df["promo_campaign_name"], y=df["resulting_net_revenue"], name="Net Revenue",
                             marker=dict(color=df["efficiency_multiplier"],
                                         colorscale=[[0, COLORS["danger"]], [0.5, COLORS["warning"]], [1, COLORS["accent"]]],
                                         showscale=True,
                                         colorbar=dict(title=dict(text="ROI ×", font=dict(color=COLORS["text_muted"])),
                                                       tickfont=dict(color=COLORS["text_muted"]), len=0.55)),
                             hovertemplate="<b>%{x}</b><br>Revenue: $%{y:,.0f}<br>ROI: %{marker.color:.2f}×<extra></extra>"))
        fig.add_trace(go.Scatter(x=df["promo_campaign_name"], y=df["margin_surrendered"], name="Margin Cost",
                                 mode="markers", marker=dict(color=COLORS["accent2"], size=11, symbol="diamond"),
                                 yaxis="y2", hovertemplate="Cost: $%{y:,.0f}<extra></extra>"))
        fig.update_layout(**{**CHART_LAYOUT, "title": "Campaign Revenue (color=ROI) vs Margin Cost",
                             "height": CHART_HEIGHT, "xaxis_tickangle": -40,
                             "yaxis2": dict(overlaying="y", side="right", showgrid=False,
                                            tickfont=dict(color=COLORS["accent2"]),
                                            title=dict(text="Margin Cost $", font=dict(color=COLORS["accent2"]))),
                             "legend": {**CHART_LAYOUT["legend"], "orientation": "h", "y": 1.06}})
        st.plotly_chart(fig, width="stretch")
    else:
        empty_state("No promotion data available")

with c2:
    insight_badge("Payment Gateway — Success vs Failure")
    if pay_df is not None:
        df = pay_df.copy()
        if sel_gw != "All": df = df[df["payment_gateway"] == sel_gw]
        status_colors = {"success": COLORS["success"], "completed": COLORS["success"],
                         "failed": COLORS["danger"], "declined": COLORS["accent2"], "pending": COLORS["warning"]}
        color_map = {s: status_colors.get(s.lower(), COLORS["primary"]) for s in df["processing_status"].unique()}

        # Stacked bar showing success vs failure by gateway
        pivot = df.pivot_table(index="payment_gateway", columns="processing_status",
                               values="transaction_attempts", aggfunc="sum", fill_value=0).reset_index()
        fig = go.Figure()
        for col in [c for c in pivot.columns if c != "payment_gateway"]:
            fig.add_trace(go.Bar(name=col, x=pivot["payment_gateway"], y=pivot[col],
                                 marker_color=status_colors.get(col.lower(), COLORS["primary"]),
                                 text=pivot[col], texttemplate="%{text:,}", textposition="inside",
                                 textfont=dict(color="white", size=10),
                                 hovertemplate=f"<b>%{{x}}</b><br>{col}: %{{y:,}}<extra></extra>"))
        fig.update_layout(**{**CHART_LAYOUT, "title": "Payment Gateway Status — Stacked View",
                             "height": CHART_HEIGHT, "barmode": "stack",
                             "legend": {**CHART_LAYOUT["legend"], "orientation": "h", "y": 1.06}})
        st.plotly_chart(fig, width="stretch")
    else:
        empty_state("No payment friction data available")

# ── ROW 2: Conversion Funnel + Product Efficiency Quadrant ──
c3, c4 = st.columns(2)

with c3:
    insight_badge("Conversion Funnel")
    if funnel_df is not None:
        total_views  = int(funnel_df["detail_page_views"].sum())
        total_carts  = int(funnel_df["cart_additions"].sum())
        total_orders = int(funnel_df["successful_orders"].sum())
        cart_rate    = (total_carts  / total_views * 100) if total_views else 0
        order_rate   = (total_orders / total_carts * 100) if total_carts else 0
        overall_cvr  = (total_orders / total_views * 100) if total_views else 0

        fig = go.Figure(go.Funnel(
            y=["Product Views", "Cart Additions", "Orders Placed"],
            x=[total_views, total_carts, total_orders],
            textinfo="value+percent initial",
            textfont=dict(color=COLORS["text_primary"], size=13),
            marker=dict(color=[COLORS["primary"], COLORS["accent"], COLORS["success"]]),
            connector=dict(line=dict(color=COLORS["border"], width=2)),
        ))
        fig.update_layout(**{**CHART_LAYOUT, "title": "Full Purchase Conversion Funnel", "height": CHART_HEIGHT})
        st.plotly_chart(fig, width="stretch")
        st.markdown(
            f'<div style="display:flex;gap:10px;margin-top:-8px">'
            f'<div style="flex:1;background:#161929;border:1px solid #2A2F4A;border-radius:8px;padding:10px;text-align:center">'
            f'<div style="font-size:0.7rem;color:#8890B5;text-transform:uppercase">View→Cart</div>'
            f'<div style="font-size:1.2rem;font-weight:700;color:{COLORS["accent"]}">{cart_rate:.1f}%</div></div>'
            f'<div style="flex:1;background:#161929;border:1px solid #2A2F4A;border-radius:8px;padding:10px;text-align:center">'
            f'<div style="font-size:0.7rem;color:#8890B5;text-transform:uppercase">Cart→Order</div>'
            f'<div style="font-size:1.2rem;font-weight:700;color:{COLORS["success"]}">{order_rate:.1f}%</div></div>'
            f'<div style="flex:1;background:#161929;border:1px solid #2A2F4A;border-radius:8px;padding:10px;text-align:center">'
            f'<div style="font-size:0.7rem;color:#8890B5;text-transform:uppercase">Overall CVR</div>'
            f'<div style="font-size:1.2rem;font-weight:700;color:{COLORS["primary"]}">{overall_cvr:.2f}%</div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        empty_state("No funnel data available")

with c4:
    insight_badge("Product Conversion Quadrant")
    if funnel_df is not None:
        df = funnel_df.nlargest(20, "detail_page_views").copy()
        med_x = df["detail_page_views"].median()
        med_y = df["view_to_purchase_conversion_rate"].median()
        # Quadrant labels
        def safe_quadrant(r):
            views = r["detail_page_views"]
            cvr = r["view_to_purchase_conversion_rate"]
            if pd.isna(views) or pd.isna(cvr):
                return "⚠️ Underperform"
            return (
                "🌟 Star" if views >= med_x and cvr >= med_y
                else "🔧 Optimize" if views >= med_x and cvr < med_y
                else "💎 Hidden Gem" if views < med_x and cvr >= med_y
                else "⚠️ Underperform"
            )
        df["quadrant"] = df.apply(safe_quadrant, axis=1)
        color_map_q = {"🌟 Star": COLORS["accent"], "🔧 Optimize": COLORS["warning"],
                       "💎 Hidden Gem": COLORS["primary"], "⚠️ Underperform": COLORS["danger"]}
        fig = px.scatter(df, x="detail_page_views", y="view_to_purchase_conversion_rate",
                         size="successful_orders", color="quadrant",
                         color_discrete_map=color_map_q, hover_name="product_name",
                         labels={"detail_page_views": "Page Views", "view_to_purchase_conversion_rate": "CVR %"},
                         size_max=45)
        fig.add_vline(x=med_x, line_dash="dash", line_color=COLORS["border"], opacity=0.6)
        fig.add_hline(y=med_y, line_dash="dash", line_color=COLORS["border"], opacity=0.6)
        fig.update_layout(**{**CHART_LAYOUT, "title": "Views vs CVR% — 4-Quadrant Analysis",
                             "height": CHART_HEIGHT,
                             "legend": {**CHART_LAYOUT["legend"], "orientation": "h", "y": 1.08}})
        st.plotly_chart(fig, width="stretch")
    else:
        empty_state("No conversion data available")

# ── ROW 3: Platform ROI Summary + Monthly Discount Trend ──
c5, c6 = st.columns(2)

with c5:
    insight_badge("Platform Promo Efficiency")
    if promo_df is not None and "marketing_platform" in promo_df.columns:
        df = promo_df.copy()
        if sel_dtype != "All": df = df[df["discount_type"] == sel_dtype]
        plat = (df.groupby("marketing_platform")
                .agg(revenue=("resulting_net_revenue", "sum"), cost=("margin_surrendered", "sum"),
                     efficiency=("efficiency_multiplier", "mean"), campaigns=("promo_campaign_name", "count"))
                .reset_index().sort_values("efficiency", ascending=False))
        plat["revenue"] = plat["revenue"].astype(float)
        plat["cost"] = plat["cost"].astype(float)
        plat["efficiency"] = plat["efficiency"].astype(float)
        plat["roi_color"] = plat["efficiency"].apply(
            lambda v: COLORS["success"] if v >= 5 else COLORS["warning"] if v >= 2 else COLORS["danger"])
        fig = go.Figure()
        fig.add_trace(go.Bar(x=plat["marketing_platform"], y=plat["efficiency"],
                             marker_color=plat["roi_color"],
                             text=plat["efficiency"].apply(lambda v: f"{v:.2f}×"),
                             textposition="outside", textfont_color=COLORS["text_primary"],
                             hovertemplate="<b>%{x}</b><br>Efficiency: %{y:.2f}×<br>Revenue: $%{customdata:,.0f}",
                             customdata=plat["revenue"]))
        fig.add_hline(y=1.0, line_dash="dot", line_color=COLORS["danger"], opacity=0.6,
                      annotation_text="Break-even (1×)", annotation_font_color=COLORS["danger"])
        fig.add_hline(y=3.0, line_dash="dot", line_color=COLORS["success"], opacity=0.5,
                      annotation_text="Good threshold (3×)", annotation_font_color=COLORS["success"])
        fig.update_layout(**{**CHART_LAYOUT, "title": "Avg ROI Efficiency by Marketing Platform",
                             "height": CHART_HEIGHT, "yaxis_title": "Revenue / Margin Cost"})
        st.plotly_chart(fig, width="stretch")
    else:
        empty_state("No platform data available")

with c6:
    insight_badge("Monthly Discount Spend vs Net Revenue")
    if sales_df is not None and "total_discounts_given" in sales_df.columns:
        df = sales_df.copy().sort_values(["year", "month_name"] if "month_name" in sales_df.columns else ["year"])
        df["period"] = df["year"].astype(str) + " " + df.get("month_name", pd.Series(range(len(df)))).astype(str)
        df["discount_pct"] = (df["total_discounts_given"].astype(float) / df["gross_revenue"].astype(float) * 100).round(2)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df["period"], y=df["total_discounts_given"], name="Discounts Given",
                             marker=dict(color=COLORS["danger"], opacity=0.7),
                             hovertemplate="<b>%{x}</b><br>Discounts: $%{y:,.0f}<extra></extra>"))
        fig.add_trace(go.Scatter(x=df["period"], y=df["discount_pct"], name="Discount %",
                                 mode="lines+markers", line=dict(color=COLORS["accent3"], width=2.5),
                                 yaxis="y2", hovertemplate="Discount %: %{y:.1f}%<extra></extra>"))
        fig.update_layout(**{**CHART_LAYOUT, "title": "Monthly Discount Spend & % of Gross",
                             "height": CHART_HEIGHT, "xaxis_tickangle": -35,
                             "yaxis2": dict(overlaying="y", side="right", showgrid=False,
                                            ticksuffix="%", tickfont=dict(color=COLORS["accent3"])),
                             "legend": {**CHART_LAYOUT["legend"], "orientation": "h", "y": 1.08}})
        st.plotly_chart(fig, width="stretch")
    else:
        empty_state("Monthly discount trend not available — requires sales_performance data")

# ── PRODUCT PROFITABILITY TABLE ──
if prod_df is not None:
    st.markdown("---")
    insight_badge("Top 20 Products — Profitability Breakdown")
    df = prod_df.head(20).copy()
    df["commission_impact"] = df["net_marketplace_sales"] - df["estimated_seller_takehome"]
    df["takehome_pct"] = (df["estimated_seller_takehome"] / df["net_marketplace_sales"] * 100).round(1)
    fig = go.Figure(data=[go.Table(
        header=dict(values=["Product", "Category", "Units Sold", "Net Sales $", "Est. Takehome $", "Commission $", "Takehome %"],
                    fill_color=COLORS["bg_card2"], line_color=COLORS["border"],
                    font=dict(color=COLORS["text_primary"], size=12), align="left", height=36),
        cells=dict(values=[df["product_name"].str[:30], df["category_name"],
                            df["units_sold"], df["net_marketplace_sales"].round(0),
                            df["estimated_seller_takehome"].round(0),
                            df["commission_impact"].round(0), df["takehome_pct"]],
                   fill_color=[[COLORS["bg_card"] if i % 2 == 0 else COLORS["bg_dark"] for i in range(len(df))]],
                   line_color=COLORS["border"],
                   font=dict(color=COLORS["text_muted"], size=11), align=["left", "left"] + ["right"] * 5, height=30,
                   format=[None, None, ",d", ",.0f", ",.0f", ",.0f", ".1f"]),
    )])
    fig.update_layout(**{**CHART_LAYOUT, "title": "Product Profitability Ledger",
                         "height": 420, "margin": dict(l=0, r=0, t=48, b=0)})
    st.plotly_chart(fig, width="stretch")