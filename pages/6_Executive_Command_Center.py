import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
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
section_title("🎯 Executive Command Center", "Single-screen intelligence — all KPIs, alerts & strategic signals in one view")

# ── LOAD ALL DATA ──
exec_df   = load_insight(sk, "executive_summary_kpis")
sales_df  = load_insight(sk, "sales_performance")
rfm_df    = load_insight(sk, "rfm_customer_segmentation")
ret_df    = load_insight(sk, "customer_retention_cohort")
inv_df    = load_insight(sk, "inventory_velocity_health")
ship_df   = load_insight(sk, "shipping_efficiency")
promo_df  = load_insight(sk, "promotion_roi")
pay_df    = load_insight(sk, "payment_method_friction")
funnel_df = load_insight(sk, "funnel_and_conversion")
geo_df    = load_insight(sk, "geospatial_expansion")
prod_df   = load_insight(sk, "product_profitability")
return_df = load_insight(sk, "return_rate_analysis")
sat_df    = load_insight(sk, "customer_satisfaction_drain")

# ── HEALTH SCORE COMPUTATION ──
def pct_score(val, good=90, bad=50):
    if val is None or (isinstance(val, float) and np.isnan(val)): return 50
    if val >= good: return 100
    if val <= bad:  return 0
    return int((val - bad) / (good - bad) * 100)

scores = {}
if exec_df is not None:
    row = exec_df.iloc[0]
    scores["Revenue Margin"]    = pct_score(float(row["operating_margin_pct"]), good=35, bad=10)
    scores["AOV Efficiency"]    = min(100, int(float(row["average_order_value"]) / 2))
if sales_df is not None and "revenue_realization_rate" in sales_df.columns:
    scores["Revenue Realization"] = pct_score(sales_df["revenue_realization_rate"].mean(), good=92, bad=70)
if ret_df is not None and not ret_df.empty:
    scores["Repeat Rate"]       = pct_score(float(ret_df.iloc[0].get("repeat_buyer_rate", 0)), good=50, bad=15)
if ship_df is not None:
    scores["Shipping SLA"]      = pct_score(ship_df["SLA_compliance_rate"].mean(), good=93, bad=70)
if pay_df is not None:
    s_rows = pay_df[pay_df["processing_status"].str.lower().isin(["success","completed"])]
    total  = pay_df["transaction_attempts"].sum()
    scores["Payment Health"]    = pct_score((s_rows["transaction_attempts"].sum() / total * 100) if total else 0, good=95, bad=70)
if return_df is not None:
    avg_ret = return_df["return_rate_percentage"].mean()
    scores["Return Quality"]    = pct_score(100 - avg_ret, good=90, bad=60)
if sat_df is not None:
    scores["Customer Satisfaction"] = pct_score(sat_df["average_star_rating"].mean() * 20, good=85, bad=55)
if funnel_df is not None:
    tot_v = funnel_df["detail_page_views"].sum()
    tot_o = funnel_df["successful_orders"].sum()
    scores["Conversion Rate"]   = pct_score((tot_o / tot_v * 100) if tot_v > 0 else 0, good=8, bad=1)

overall_health = int(np.mean(list(scores.values()))) if scores else 0

# ── HEALTH SCORE BANNER ──
health_color = COLORS["success"] if overall_health >= 75 else COLORS["warning"] if overall_health >= 50 else COLORS["danger"]
health_label = "HEALTHY" if overall_health >= 75 else "WATCH" if overall_health >= 50 else "CRITICAL"
st.markdown(f"""
<div style='background:linear-gradient(135deg,{health_color}15,{health_color}05);
            border:1px solid {health_color}40;border-radius:14px;
            padding:18px 24px;margin-bottom:20px;display:flex;align-items:center;gap:20px'>
    <div style='text-align:center;min-width:80px'>
        <div style='font-family:Syne,sans-serif;font-size:2.5rem;font-weight:800;color:{health_color}'>{overall_health}</div>
        <div style='font-size:0.65rem;color:{health_color};text-transform:uppercase;letter-spacing:0.1em'>Health Score</div>
    </div>
    <div style='width:1px;height:50px;background:{health_color}30'></div>
    <div>
        <div style='font-family:Syne,sans-serif;font-size:1.1rem;font-weight:700;color:{health_color}'>{health_label}</div>
        <div style='font-size:0.8rem;color:#8890B5;margin-top:4px'>
            Composite across {len(scores)} business dimensions. Score ≥75 = Healthy | 50-74 = Watch | &lt;50 = Critical
        </div>
    </div>
    <div style='margin-left:auto;display:flex;gap:8px;flex-wrap:wrap'>
        {"".join([
            f'<span style="background:{(COLORS["success"] if v>=75 else COLORS["warning"] if v>=50 else COLORS["danger"])}20;'
            f'border:1px solid {(COLORS["success"] if v>=75 else COLORS["warning"] if v>=50 else COLORS["danger"])}40;'
            f'color:{(COLORS["success"] if v>=75 else COLORS["warning"] if v>=50 else COLORS["danger"])};'
            f'font-size:0.65rem;padding:3px 8px;border-radius:12px;white-space:nowrap">{k}: {v}</span>'
            for k, v in scores.items()
        ])}
    </div>
</div>
""", unsafe_allow_html=True)

# ── MASTER KPI ROW ──
master_kpis = []
if exec_df is not None:
    row = exec_df.iloc[0]
    master_kpis.extend([
        {"label": "Total Orders",       "value": f"{int(row['total_orders']):,}"},
        {"label": "Net Revenue",        "value": f"${float(row['net_revenue']):,.0f}"},
        {"label": "Gross Revenue",      "value": f"${float(row['gross_revenue']):,.0f}"},
        {"label": "AOV",                "value": f"${float(row['average_order_value']):.2f}"},
        {"label": "Operating Margin",   "value": f"{float(row['operating_margin_pct']):.1f}%"},
        {"label": "Units / Order",      "value": f"{float(row['units_per_transaction']):.1f}"},
    ])
if ret_df is not None and not ret_df.empty:
    r2 = ret_df.iloc[0]
    master_kpis.extend([
        {"label": "Total Buyers",       "value": f"{int(r2.get('total_historical_buyers', 0)):,}"},
        {"label": "Repeat Rate",        "value": f"{float(r2.get('repeat_buyer_rate', 0)):.1f}%"},
    ])
if master_kpis:
    render_kpi_row(master_kpis, num_cols=4)

st.markdown("---")

# ── COMMAND ROW 1: Revenue Trend + Customer Segment Pie ──
c1, c2 = st.columns([3, 2])

with c1:
    insight_badge("Revenue Trend — Gross vs Net")
    if sales_df is not None:
        df = sales_df.sort_values(["year", "month_name"] if "month_name" in sales_df.columns else ["year"]).copy()
        df["period"] = df["year"].astype(str) + " " + df.get("month_name", pd.Series(range(len(df)))).astype(str)
        df["net_rolling"] = df["net_revenue"].rolling(3, min_periods=1).mean()
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df["period"], y=df["gross_revenue"], name="Gross",
                             marker=dict(color=COLORS["primary"], opacity=0.5),
                             hovertemplate="Gross: $%{y:,.0f}<extra></extra>"))
        fig.add_trace(go.Bar(x=df["period"], y=df["net_revenue"], name="Net",
                             marker=dict(color=COLORS["accent"], opacity=0.8),
                             hovertemplate="Net: $%{y:,.0f}<extra></extra>"))
        fig.add_trace(go.Scatter(x=df["period"], y=df["net_rolling"], name="3M Net Avg",
                                 mode="lines", line=dict(color=COLORS["accent3"], width=2, dash="dot")))
        fig.update_layout(**{**CHART_LAYOUT, "title": "Monthly Revenue — Gross vs Net + 3M Rolling",
                             "height": 360, "barmode": "overlay", "xaxis_tickangle": -30,
                             "legend": {**CHART_LAYOUT["legend"], "orientation": "h", "y": 1.08}})
        st.plotly_chart(fig, width="stretch")
    else:
        empty_state("No revenue trend data available")

with c2:
    insight_badge("Customer Value Segments")
    if rfm_df is not None:
        seg_agg = (rfm_df.groupby("market_segmentation")
                   .agg(customers=("customer_key", "count"), spend=("total_monetary_value", "sum"))
                   .reset_index())
        seg_color = {"Champions / VIP": COLORS["accent"], "Loyal Customer Base": COLORS["primary"],
                     "Standard General Shopper": COLORS["warning"], "At Risk / Churned": COLORS["danger"]}
        colors = [seg_color.get(s, COLORS["text_muted"]) for s in seg_agg["market_segmentation"]]
        fig = go.Figure(go.Pie(
            labels=seg_agg["market_segmentation"], values=seg_agg["spend"],
            hole=0.55, marker=dict(colors=colors, line=dict(color=COLORS["bg_dark"], width=2)),
            textinfo="percent+label", textfont=dict(color=COLORS["text_primary"], size=11),
            hovertemplate="<b>%{label}</b><br>Spend: $%{value:,.0f}<br>Share: %{percent}<extra></extra>",
        ))
        total_spend = seg_agg["spend"].sum()
        champ_spend = seg_agg[seg_agg["market_segmentation"].str.contains("Champions", na=False)]["spend"].sum()
        champ_pct = champ_spend / total_spend * 100 if total_spend > 0 else 0
        fig.update_layout(**{**CHART_LAYOUT,
                             "title": f"Revenue by Customer Segment<br><span style='font-size:11px;color:#8890B5'>Champions = {champ_pct:.1f}% of revenue</span>",
                             "height": 360, "showlegend": False,
                             "annotations": [dict(text=f"${total_spend:,.0f}", x=0.5, y=0.5,
                                                  font=dict(size=14, color=COLORS["text_primary"], family="Syne"),
                                                  showarrow=False)]})
        st.plotly_chart(fig, width="stretch")
    else:
        empty_state("No RFM data available")

# ── COMMAND ROW 2: Category Market Share + Top 5 Products ──
c3, c4 = st.columns([2, 3])

with c3:
    insight_badge("Market Share by Category")
    if load_insight(sk, "market_share_benchmarking") is not None:
        mkt_df = load_insight(sk, "market_share_benchmarking")
        fig = px.bar(mkt_df.sort_values("seller_market_share_revenue_percentage", ascending=True),
                     x="seller_market_share_revenue_percentage", y="category_name", orientation="h",
                     color="seller_market_share_revenue_percentage",
                     color_continuous_scale=[[0, COLORS["primary_dark"]], [1, COLORS["accent"]]],
                     text="seller_market_share_revenue_percentage",
                     labels={"seller_market_share_revenue_percentage": "Share %", "category_name": "Category"})
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside",
                          textfont_color=COLORS["text_primary"])
        fig.update_layout(**{**CHART_LAYOUT, "title": "Revenue Market Share", "height": 360,
                             "coloraxis_showscale": False,
                             "yaxis": {**CHART_LAYOUT["yaxis"], "categoryorder": "total ascending"}})
        st.plotly_chart(fig, width="stretch")
    else:
        empty_state("No market share data")

with c4:
    insight_badge("Top 10 SKUs — Revenue & Takehome")
    if prod_df is not None:
        df_top = prod_df.head(10).copy()
        df_top["label"] = df_top["product_name"].str[:28]
        df_top["commission"] = df_top["net_marketplace_sales"] - df_top["estimated_seller_takehome"]
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Takehome", x=df_top["label"], y=df_top["estimated_seller_takehome"],
                             marker_color=COLORS["accent"], opacity=0.9,
                             hovertemplate="<b>%{x}</b><br>Takehome: $%{y:,.0f}<extra></extra>"))
        fig.add_trace(go.Bar(name="Commission", x=df_top["label"], y=df_top["commission"],
                             marker_color=COLORS["danger"], opacity=0.75,
                             hovertemplate="Commission: $%{y:,.0f}<extra></extra>"))
        fig.update_layout(**{**CHART_LAYOUT, "title": "Top 10 SKUs — Takehome vs Commission Split",
                             "height": 360, "barmode": "stack", "xaxis_tickangle": -35,
                             "legend": {**CHART_LAYOUT["legend"], "orientation": "h", "y": 1.08}})
        st.plotly_chart(fig, width="stretch")
    else:
        empty_state("No product data available")

# ── ALERTS SECTION ──
st.markdown("---")
st.markdown('<p style="font-family:Syne,sans-serif;font-size:1.1rem;font-weight:700;color:#F0F2FF;margin-bottom:12px">⚡ Active Business Alerts</p>', unsafe_allow_html=True)

alerts = []
if inv_df is not None:
    restock_risk = inv_df[inv_df["inventory_health_status"].str.contains("HIGH", na=False)].shape[0]
    slow_skus    = inv_df[inv_df["inventory_health_status"].str.contains("SLOW", na=False)].shape[0]
    if restock_risk > 0:
        alerts.append(("🔴", "Restock Risk", f"{restock_risk} SKU(s) are HIGH VELOCITY and may go out of stock soon.", COLORS["danger"]))
    if slow_skus > 3:
        alerts.append(("🟡", "Dead Stock", f"{slow_skus} SKU(s) are SLOW MOVING — consider markdowns or bundles.", COLORS["warning"]))
if ship_df is not None:
    breach = ship_df[ship_df["SLA_compliance_rate"] < 80]
    if not breach.empty:
        cities = ", ".join(breach["destination_city"].head(3).tolist())
        alerts.append(("🔴", "SLA Breach", f"{len(breach)} cities below 80% SLA: {cities}", COLORS["danger"]))
if return_df is not None:
    high_ret = return_df[return_df["return_rate_percentage"] > 20]
    if not high_ret.empty:
        alerts.append(("🟡", "High Returns", f"{len(high_ret)} product(s) with >20% return rate — quality review needed.", COLORS["warning"]))
if sat_df is not None:
    low_sat = sat_df[sat_df["average_star_rating"] < 3]
    if not low_sat.empty:
        alerts.append(("🔴", "Low Satisfaction", f"{len(low_sat)} product(s) rated below 3★ — urgent review required.", COLORS["danger"]))
if pay_df is not None:
    fail_rows = pay_df[pay_df["processing_status"].str.lower().isin(["failed", "declined"])]
    total_txn = pay_df["transaction_attempts"].sum()
    fail_pct  = (fail_rows["transaction_attempts"].sum() / total_txn * 100) if total_txn > 0 else 0
    if fail_pct > 10:
        alerts.append(("🟡", "Payment Friction", f"{fail_pct:.1f}% of transactions failing — gateway issue suspected.", COLORS["warning"]))
if rfm_df is not None:
    at_risk = rfm_df[rfm_df["market_segmentation"].str.contains("At Risk", na=False)]
    if not at_risk.empty:
        lost_rev = at_risk["total_monetary_value"].sum()
        alerts.append(("🟡", "Churn Risk", f"{len(at_risk)} customers at-risk of churning — ${lost_rev:,.0f} in revenue at stake.", COLORS["warning"]))

if not alerts:
    st.markdown('<div style="background:#161929;border:1px dashed #2A2F4A;border-radius:10px;padding:16px 20px;color:#00E5C3;font-size:0.88rem">✅ No active alerts — all business dimensions are performing within normal parameters.</div>', unsafe_allow_html=True)
else:
    alert_cols = st.columns(min(len(alerts), 3))
    for i, (icon, title, msg, color) in enumerate(alerts):
        alert_cols[i % 3].markdown(
            f'<div style="background:{color}10;border:1px solid {color}30;border-radius:10px;'
            f'padding:14px 16px;margin-bottom:8px">'
            f'<div style="font-size:1.1rem;margin-bottom:4px">{icon} <span style="font-weight:700;color:{color};font-size:0.85rem">{title}</span></div>'
            f'<div style="font-size:0.78rem;color:#8890B5;line-height:1.5">{msg}</div></div>',
            unsafe_allow_html=True,
        )

# ── SPIDER / RADAR CHART ──
st.markdown("---")
insight_badge("Business Dimension Radar")
if scores:
    categories = list(scores.keys())
    values = list(scores.values()) + [list(scores.values())[0]]  # Close loop
    cats_loop = categories + [categories[0]]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values, theta=cats_loop, fill="toself",
        fillcolor=f"rgba(108,99,255,0.15)", line=dict(color=COLORS["primary"], width=2.5),
        name="Current Score", hovertemplate="%{theta}: %{r}/100<extra></extra>",
    ))
    fig.add_trace(go.Scatterpolar(
        r=[75] * (len(categories) + 1), theta=cats_loop, fill="toself",
        fillcolor="rgba(0,229,195,0.05)", line=dict(color=COLORS["accent"], width=1.5, dash="dot"),
        name="Healthy Threshold (75)", hoverinfo="skip",
    ))
    fig.update_layout(**{**CHART_LAYOUT, "title": "Business Health Radar (0-100 per dimension)",
                         "height": 450,
                         "polar": dict(
                             bgcolor=COLORS["bg_card"],
                             angularaxis=dict(tickfont=dict(color=COLORS["text_primary"], size=11),
                                              gridcolor=COLORS["border"]),
                             radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(color=COLORS["text_muted"], size=9),
                                             gridcolor=COLORS["border"]),
                         ),
                         "legend": {**CHART_LAYOUT["legend"], "orientation": "h", "y": -0.1}})
    st.plotly_chart(fig, width="stretch")
else:
    empty_state("Not enough data to render radar chart")
