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
section_title("📦 Inventory & Logistics", "Supply chain velocity, SLA compliance, returns & quality signals")

# ── LOAD DATA ──
inv_df  = load_insight(sk, "inventory_velocity_health")
ship_df = load_insight(sk, "shipping_efficiency")
ret_df  = load_insight(sk, "return_rate_analysis")
sat_df  = load_insight(sk, "customer_satisfaction_drain")

# ── FILTER BAR ──
st.markdown('<div style="background:#161929;border:1px solid #2A2F4A;border-radius:12px;padding:14px 20px;margin-bottom:20px">', unsafe_allow_html=True)
fa, fb, fc = st.columns([2, 2, 3])
health_opts = ["All"]
if inv_df is not None and "inventory_health_status" in inv_df.columns:
    health_opts += sorted(inv_df["inventory_health_status"].dropna().unique().tolist())
sel_health = fa.selectbox("📊 Health Status", health_opts, key="il_health")
region_opts = ["All"]
if ship_df is not None and "destination_region" in ship_df.columns:
    region_opts += sorted(ship_df["destination_region"].dropna().unique().tolist())
sel_region = fb.selectbox("🌍 Region", region_opts, key="il_region")
fc.markdown('<p style="font-size:0.78rem;color:#8890B5;margin-top:28px">Health → inventory charts. Region → shipping charts.</p>', unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ── POWER KPI ROW ──
kpi_metrics = []
if inv_df is not None:
    df = inv_df.copy()
    if sel_health != "All": df = df[df["inventory_health_status"] == sel_health]
    high = df[df["inventory_health_status"].str.contains("HIGH", na=False)].shape[0]
    slow = df[df["inventory_health_status"].str.contains("SLOW", na=False)].shape[0]
    total = df.shape[0]
    avg_burn = df["daily_burn_rate"].astype(float).mean() if "daily_burn_rate" in df.columns else None
    kpi_metrics.extend([
        {"label": "High Velocity SKUs",   "value": str(high),   "delta": f"of {total} total"},
        {"label": "Slow Moving SKUs",     "value": str(slow),   "delta": f"of {total} total"},
        {"label": "Avg Daily Burn Rate",  "value": f"{avg_burn:.1f}/day" if avg_burn and pd.notna(avg_burn) else "—"},
    ])
if ship_df is not None:
    df_s = ship_df.copy()
    if sel_region != "All": df_s = df_s[df_s["destination_region"] == sel_region]
    avg_sla  = df_s["SLA_compliance_rate"].astype(float).mean()
    avg_days = df_s["avg_days_to_delivery"].astype(float).mean()
    breach_cities = (df_s["SLA_compliance_rate"].astype(float) < 80).sum()
    kpi_metrics.extend([
        {"label": "Avg SLA Compliance",  "value": f"{avg_sla:.1f}%" if pd.notna(avg_sla) else "—",
         "delta": "▲ on target" if avg_sla >= 90 else "▼ below target"},
        {"label": "Avg Delivery Days",   "value": f"{avg_days:.1f}d" if pd.notna(avg_days) else "—"},
        {"label": "Cities < 80% SLA",    "value": str(breach_cities), "delta": "⚠️ action needed" if breach_cities > 0 else "✓ clean"},
    ])
if ret_df is not None:
    avg_ret = ret_df["return_rate_percentage"].astype(float).mean()
    total_refunds = ret_df["total_refunded_cash"].astype(float).sum() if "total_refunded_cash" in ret_df.columns else None
    kpi_metrics.extend([
        {"label": "Avg Return Rate",     "value": f"{avg_ret:.2f}%" if pd.notna(avg_ret) else "—"},
        {"label": "Total Refunded",      "value": f"${total_refunds:,.0f}" if total_refunds and pd.notna(total_refunds) else "—"},
    ])
if sat_df is not None:
    avg_star = sat_df["average_star_rating"].mean()
    neg_pct = (sat_df["negative_review_count"].sum() / sat_df["total_reviews_received"].sum() * 100) if sat_df["total_reviews_received"].sum() > 0 else 0
    kpi_metrics.extend([
        {"label": "Avg Star Rating",     "value": f"{avg_star:.2f}★" if pd.notna(avg_star) else "—"},
        {"label": "Negative Review %",   "value": f"{neg_pct:.1f}%", "delta": "▼ risk" if neg_pct > 15 else "✓ healthy"},
    ])
if kpi_metrics:
    render_kpi_row(kpi_metrics, num_cols=4)

st.markdown("---")

# ── ROW 1: Inventory Treemap + SLA Gauge ──
c1, c2 = st.columns(2)

with c1:
    insight_badge("Inventory Health — Category Treemap")
    if inv_df is not None:
        df = inv_df.copy()
        if sel_health != "All": df = df[df["inventory_health_status"] == sel_health]
        if "category_name" in df.columns:
            cat_agg = df.groupby(["category_name", "inventory_health_status"], as_index=False).agg(
                units=("units_sold_90d", "sum"), skus=("product_name", "count"))
            health_color_map = {
                "HIGH VELOCITY (Restock Risk)":             COLORS["danger"],
                "STABLE/NORMAL":                            COLORS["success"],
                "SLOW MOVING (Dead Stock/Markdown Target)": COLORS["warning"],
            }
            fig = px.treemap(cat_agg, path=["category_name", "inventory_health_status"],
                             values="units", color="inventory_health_status",
                             color_discrete_map=health_color_map,
                             custom_data=["skus"])
            fig.update_traces(texttemplate="<b>%{label}</b><br>%{value:,} units",
                              hovertemplate="<b>%{label}</b><br>Units: %{value:,}<br>SKUs: %{customdata[0]}<extra></extra>")
            fig.update_layout(**{**CHART_LAYOUT, "title": "Inventory by Category & Health",
                                 "height": CHART_HEIGHT, "margin": dict(l=8, r=8, t=56, b=8)})
            st.plotly_chart(fig, width="stretch")
        else:
            # Fallback: horizontal bar
            df2 = df.head(20).copy()
            color_map_h = {"HIGH VELOCITY (Restock Risk)": COLORS["danger"],
                           "STABLE/NORMAL": COLORS["success"],
                           "SLOW MOVING (Dead Stock/Markdown Target)": COLORS["warning"]}
            fig = px.bar(df2, x="units_sold_90d", y="product_name", orientation="h",
                         color="inventory_health_status", color_discrete_map=color_map_h,
                         labels={"units_sold_90d": "Units (90d)", "product_name": "Product"})
            fig.update_layout(**{**CHART_LAYOUT, "title": "Inventory Velocity Top 20",
                                 "height": CHART_HEIGHT,
                                 "yaxis": {**CHART_LAYOUT["yaxis"], "categoryorder": "total ascending"}})
            st.plotly_chart(fig, width="stretch")
    else:
        empty_state("No inventory data available")

with c2:
    insight_badge("SLA Compliance by City")
    if ship_df is not None:
        df = ship_df.dropna(subset=["avg_days_to_delivery", "SLA_compliance_rate", "total_shipments"]).copy()
        df["avg_days_to_delivery"] = df["avg_days_to_delivery"].astype(float)
        df["SLA_compliance_rate"] = df["SLA_compliance_rate"].astype(float)
        df["total_shipments"] = df["total_shipments"].astype(float)
        if sel_region != "All": df = df[df["destination_region"] == sel_region]
        if df.empty:
            empty_state("No shipping data for selected region")
        else:
            df_sorted = df.sort_values("SLA_compliance_rate", ascending=True).head(20)
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df_sorted["SLA_compliance_rate"], y=df_sorted["destination_city"],
                orientation="h",
                marker=dict(color=df_sorted["SLA_compliance_rate"],
                            colorscale=[[0, COLORS["danger"]], [0.6, COLORS["warning"]], [1, COLORS["success"]]],
                            showscale=True,
                            colorbar=dict(title=dict(text="SLA %", font=dict(color=COLORS["text_muted"])),
                                          tickfont=dict(color=COLORS["text_muted"]), ticksuffix="%", len=0.6)),
                text=df_sorted["SLA_compliance_rate"].apply(lambda v: f"{v:.1f}%"),
                textposition="outside", textfont_color=COLORS["text_primary"],
                customdata=df_sorted[["avg_days_to_delivery", "total_shipments"]].values,
                hovertemplate="<b>%{y}</b><br>SLA: %{x:.1f}%<br>Avg Days: %{customdata[0]:.1f}d<br>Shipments: %{customdata[1]:,}<extra></extra>",
            ))
            fig.add_vline(x=90, line_dash="dot", line_color=COLORS["success"], opacity=0.6,
                          annotation_text="90% Target", annotation_font_color=COLORS["success"])
            fig.add_vline(x=80, line_dash="dot", line_color=COLORS["danger"], opacity=0.5,
                          annotation_text="Critical (80%)", annotation_font_color=COLORS["danger"])
            fig.update_layout(**{**CHART_LAYOUT, "title": "City-level SLA Compliance Rate",
                                 "height": CHART_HEIGHT,
                                 "yaxis": {**CHART_LAYOUT["yaxis"], "categoryorder": "total ascending"}})
            st.plotly_chart(fig, width="stretch")
    else:
        empty_state("No shipping data available")

# ── ROW 2: Returns Pareto + Satisfaction Scatter ──
c3, c4 = st.columns(2)

with c3:
    insight_badge("Returns — Pareto Analysis")
    if ret_df is not None:
        df = ret_df.dropna(subset=["return_rate_percentage"]).copy()
        df["return_rate_percentage"] = df["return_rate_percentage"].astype(float)
        if "total_returns" in df.columns:
            df["total_returns"] = df["total_returns"].astype(float)
        df = df.sort_values("return_rate_percentage", ascending=False).head(15)
        df["cumulative_returns"] = df["total_returns"].cumsum() if "total_returns" in df.columns else None
        df["cum_pct"] = (df["total_returns"].cumsum() / df["total_returns"].sum() * 100) if "total_returns" in df.columns else None

        fig = go.Figure()
        fig.add_trace(go.Bar(x=df["product_name"].str[:25], y=df["return_rate_percentage"],
                             name="Return Rate %",
                             marker=dict(color=df["return_rate_percentage"],
                                         colorscale=[[0, COLORS["warning"]], [0.5, COLORS["accent2"]], [1, COLORS["danger"]]],
                                         showscale=False),
                             text=df["return_rate_percentage"].apply(lambda v: f"{v:.1f}%"),
                             textposition="outside", textfont_color=COLORS["text_primary"],
                             hovertemplate="<b>%{x}</b><br>Return Rate: %{y:.1f}%<extra></extra>"))
        if df["cum_pct"] is not None:
            fig.add_trace(go.Scatter(x=df["product_name"].str[:25], y=df["cum_pct"],
                                     name="Cumulative %", mode="lines+markers",
                                     line=dict(color=COLORS["primary"], width=2.5), yaxis="y2",
                                     hovertemplate="Cumul: %{y:.1f}%<extra></extra>"))
            fig.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False,
                                          range=[0, 110], ticksuffix="%",
                                          tickfont=dict(color=COLORS["primary"])))
        fig.add_hline(y=10, line_dash="dot", line_color=COLORS["warning"], opacity=0.6,
                      annotation_text="Watch (10%)", annotation_font_color=COLORS["warning"])
        fig.update_layout(**{**CHART_LAYOUT, "title": "Highest Return Rate Products — Pareto",
                             "height": CHART_HEIGHT, "xaxis_tickangle": -35,
                             "legend": {**CHART_LAYOUT["legend"], "orientation": "h", "y": 1.08}})
        st.plotly_chart(fig, width="stretch")
    else:
        empty_state("No returns data available")

with c4:
    insight_badge("Satisfaction vs Delivery Days — Risk Matrix")
    if sat_df is not None:
        df = sat_df.dropna(subset=["average_star_rating"]).copy()
        def safe_risk_label(r):
            rating = r["average_star_rating"]
            days = r.get("avg_delivery_days_for_product")
            if pd.isna(rating):
                return "⚠️ Underperform"
            if rating < 3 and pd.notna(days) and days > 5:
                return "🔴 High Risk"
            if rating < 4:
                return "🟡 Watch"
            return "🟢 Healthy"
        df["risk_label"] = df.apply(safe_risk_label, axis=1)
        risk_color = {"🔴 High Risk": COLORS["danger"], "🟡 Watch": COLORS["warning"], "🟢 Healthy": COLORS["success"]}
        fig = px.scatter(df, x="avg_delivery_days_for_product", y="average_star_rating",
                         size="total_reviews_received", color="risk_label",
                         color_discrete_map=risk_color, hover_name="product_name",
                         labels={"avg_delivery_days_for_product": "Avg Delivery Days", "average_star_rating": "Star Rating"},
                         size_max=40)
        fig.add_hline(y=4.0, line_dash="dot", line_color=COLORS["success"], opacity=0.5,
                      annotation_text="4★ Threshold", annotation_font_color=COLORS["success"])
        fig.add_vline(x=5.0, line_dash="dot", line_color=COLORS["warning"], opacity=0.5,
                      annotation_text="5-day SLA", annotation_font_color=COLORS["warning"])
        fig.update_layout(**{**CHART_LAYOUT, "title": "Product Satisfaction vs Delivery Days (size=reviews)",
                             "height": CHART_HEIGHT,
                             "yaxis": {**CHART_LAYOUT["yaxis"], "range": [0, 5.4]},
                             "legend": {**CHART_LAYOUT["legend"], "orientation": "h", "y": 1.08}})
        st.plotly_chart(fig, width="stretch")
    else:
        empty_state("No satisfaction data available")

# ── ROW 3: Burn Rate + Refund Cost Bar ──
c5, c6 = st.columns(2)

with c5:
    insight_badge("Daily Burn Rate — Restock Priority")
    if inv_df is not None and "daily_burn_rate" in inv_df.columns:
        df = inv_df.dropna(subset=["daily_burn_rate"]).copy()
        df["daily_burn_rate"] = df["daily_burn_rate"].astype(float)
        if sel_health != "All": df = df[df["inventory_health_status"] == sel_health]
        df = df.sort_values("daily_burn_rate", ascending=False).head(15)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df["product_name"].str[:25], y=df["daily_burn_rate"],
            marker=dict(color=df["daily_burn_rate"],
                        colorscale=[[0, COLORS["warning"]], [1, COLORS["danger"]]],
                        showscale=False),
            text=df["daily_burn_rate"].apply(lambda v: f"{v:.1f}/d"),
            textposition="outside", textfont_color=COLORS["text_primary"],
            hovertemplate="<b>%{x}</b><br>Burn: %{y:.2f} units/day<extra></extra>",
        ))
        fig.update_layout(**{**CHART_LAYOUT, "title": "Daily Unit Burn Rate — Restock Priority",
                             "height": CHART_HEIGHT, "xaxis_tickangle": -35,
                             "yaxis_title": "Units / Day"})
        st.plotly_chart(fig, width="stretch")
    else:
        empty_state("No burn rate data available")

with c6:
    insight_badge("Refund Cost vs Shipping Sink")
    if ret_df is not None and "total_refunded_cash" in ret_df.columns:
        df = ret_df.dropna(subset=["total_refunded_cash"]).copy()
        df["total_refunded_cash"] = df["total_refunded_cash"].astype(float)
        df = df.nlargest(15, "total_refunded_cash").copy()
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Refunds $", x=df["product_name"].str[:25], y=df["total_refunded_cash"],
                             marker_color=COLORS["danger"], opacity=0.8,
                             hovertemplate="Refunds: $%{y:,.0f}<extra></extra>"))
        if "sunk_shipping_costs" in df.columns:
            df["sunk_shipping_costs"] = df["sunk_shipping_costs"].astype(float)
            fig.add_trace(go.Bar(name="Sunk Shipping $", x=df["product_name"].str[:25], y=df["sunk_shipping_costs"],
                                 marker_color=COLORS["warning"], opacity=0.8,
                                 hovertemplate="Shipping sink: $%{y:,.0f}<extra></extra>"))
        fig.update_layout(**{**CHART_LAYOUT, "title": "Refund Cost + Sunk Shipping per Product",
                             "height": CHART_HEIGHT, "barmode": "stack", "xaxis_tickangle": -35,
                             "legend": {**CHART_LAYOUT["legend"], "orientation": "h", "y": 1.08}})
        st.plotly_chart(fig, width="stretch")
    else:
        empty_state("No refund cost data available")

# ── WORST QUALITY PRODUCTS TABLE ──
if sat_df is not None and ret_df is not None:
    st.markdown("---")
    insight_badge("Quality Risk Table — Worst Products by Rating & Returns")
    merged = pd.merge(
        sat_df[["product_name", "average_star_rating", "total_reviews_received", "negative_review_count"]],
        ret_df[["product_name", "return_rate_percentage", "total_returns"]].rename(columns={"total_returns": "returns_count"}),
        on="product_name", how="outer"
    ).fillna(0).sort_values("average_star_rating", ascending=True).head(15)
    merged["risk_score"] = ((5 - merged["average_star_rating"]) * merged["return_rate_percentage"]).round(2)
    fig = go.Figure(data=[go.Table(
        header=dict(values=["Product", "Avg Rating", "Neg Reviews", "Return Rate %", "Risk Score"],
                    fill_color=COLORS["bg_card2"], line_color=COLORS["border"],
                    font=dict(color=COLORS["text_primary"], size=12), align="left", height=36),
        cells=dict(values=[merged["product_name"].str[:35],
                            merged["average_star_rating"].round(2),
                            merged["negative_review_count"].astype(int),
                            merged["return_rate_percentage"].round(2),
                            merged["risk_score"]],
                   fill_color=[[COLORS["bg_card"] if i % 2 == 0 else COLORS["bg_dark"] for i in range(len(merged))]],
                   line_color=COLORS["border"],
                   font=dict(color=COLORS["text_muted"], size=11), align=["left"] + ["right"] * 4, height=30,
                   format=[None, ".2f", ",d", ".2f", ".2f"]),
    )])
    fig.update_layout(**{**CHART_LAYOUT, "title": "Product Quality Risk Index",
                         "height": 380, "margin": dict(l=0, r=0, t=48, b=0)})
    st.plotly_chart(fig, width="stretch")