import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
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
section_title("👥 Customer Insights", "Loyalty profiles, RFM segmentation, demographics & buyer trends")

# ── LOAD DATA ──
ret_df  = load_insight(sk, "customer_retention_cohort")
rfm_df  = load_insight(sk, "rfm_customer_segmentation")
demo_df = load_insight(sk, "customer_demographics")
geo_df  = load_insight(sk, "geospatial_expansion")
sales_df = load_insight(sk, "sales_performance")   # for monthly buyer trend line

# ── FILTER BAR ──
st.markdown(
    '<div style="background:#161929;border:1px solid #2A2F4A;border-radius:12px;padding:14px 20px;margin-bottom:20px">',
    unsafe_allow_html=True,
)
fa, fb, fc, fd = st.columns([2, 2, 2, 3])

seg_opts = ["All"]
if rfm_df is not None and "market_segmentation" in rfm_df.columns:
    seg_opts += sorted(rfm_df["market_segmentation"].dropna().unique().tolist())
sel_seg = fa.selectbox("🎯 Segment", seg_opts, key="ci_seg")

gender_opts = ["All"]
if demo_df is not None and "gender" in demo_df.columns:
    gender_opts += sorted(demo_df["gender"].dropna().unique().tolist())
sel_gender = fb.selectbox("👤 Gender", gender_opts, key="ci_gender")

region_opts = ["All"]
if demo_df is not None and "buyer_region" in demo_df.columns:
    region_opts += sorted(demo_df["buyer_region"].dropna().unique().tolist())
sel_region = fc.selectbox("🌍 Region", region_opts, key="ci_region")

fd.markdown(
    '<p style="font-size:0.78rem;color:#8890B5;margin-top:28px">Segment → RFM charts; Gender & Region → demographics.</p>',
    unsafe_allow_html=True,
)
st.markdown("</div>", unsafe_allow_html=True)

# ── KPI ROW ──
metrics = []

if ret_df is not None and not ret_df.empty:
    row = ret_df.iloc[0]
    # Safe format each field individually
    def safe_fmt_int(val, suffix=""):
        return f"{int(val):,}{suffix}" if pd.notna(val) else "—"
    def safe_fmt_float(val, fmt=".1f", suffix=""):
        return f"{val:{fmt}}{suffix}" if pd.notna(val) else "—"

    metrics.extend([
        {"label": "Total Buyers",      "value": safe_fmt_int(row.get("total_historical_buyers", None))},
        {"label": "Repeat Buyer Rate", "value": safe_fmt_float(row.get("repeat_buyer_rate", None), ".1f", "%")},
        {"label": "Repurchase Cycle",  "value": safe_fmt_float(row.get("platform_repurchase_cycle_days", None), ".0f", "d")},
    ])

if rfm_df is not None:
    df_r = rfm_df.copy()
    if sel_seg != "All":
        df_r = df_r[df_r["market_segmentation"] == sel_seg]
    champions = df_r[df_r["market_segmentation"].str.contains("Champions", na=False)].shape[0]
    at_risk   = df_r[df_r["market_segmentation"].str.contains("At Risk",   na=False)].shape[0]
    metrics.extend([
        {"label": "Champions / VIP",   "value": str(champions)},
        {"label": "At Risk / Churned", "value": str(at_risk)},
    ])

if demo_df is not None:
    df_d = demo_df.copy()
    if sel_gender != "All":
        df_d = df_d[df_d["gender"] == sel_gender]
    if sel_region != "All":
        df_d = df_d[df_d["buyer_region"] == sel_region]
    buyers_total = df_d["unique_buyers"].sum()
    ltv_total    = df_d["lifetime_value_to_seller"].sum()
    avg_ltv = ltv_total / buyers_total if buyers_total > 0 else 0
    metrics.append({"label": "Avg LTV", "value": f"${avg_ltv:.2f}" if pd.notna(avg_ltv) else "—"})

if metrics:
    render_kpi_row(metrics, num_cols=min(len(metrics), 6))

# ══════════════════════════════════════════════════════
# ── ROW 1: Age Group Bar (Pinned) + RFM Segment Bar ──
# ══════════════════════════════════════════════════════
c1, c2 = st.columns(2)

with c1:
    insight_badge("Buyers by Age Band")
    if demo_df is not None:
        df = demo_df.copy()
        if sel_gender != "All":
            df = df[df["gender"] == sel_gender]
        if sel_region != "All":
            df = df[df["buyer_region"] == sel_region]

        age_agg = (
            df.groupby("age_band", as_index=False)
            .agg(unique_buyers=("unique_buyers", "sum"),
                 lifetime_value=("lifetime_value_to_seller", "sum"))
            .sort_values("unique_buyers", ascending=False)
        )

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=age_agg["age_band"],
            y=age_agg["unique_buyers"],
            name="Buyers",
            marker=dict(color=COLORS["primary"], opacity=0.9),
            text=age_agg["unique_buyers"].apply(lambda v: f"{v:,}"),
            textposition="outside",
            textfont_color=COLORS["text_primary"],
            hovertemplate="<b>%{x}</b><br>Buyers: %{y:,}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=age_agg["age_band"],
            y=age_agg["lifetime_value"],
            name="Total LTV",
            mode="lines+markers",
            line=dict(color=COLORS["accent"], width=2.5),
            marker=dict(size=8),
            yaxis="y2",
            hovertemplate="LTV: $%{y:,.0f}<extra></extra>",
        ))
        fig.update_layout(**{
            **CHART_LAYOUT,
            "title": "Buyers & LTV by Age Band",
            "height": CHART_HEIGHT,
            "yaxis2": dict(
                overlaying="y", side="right", showgrid=False,
                tickfont=dict(color=COLORS["accent"]),
                title=dict(text="Total LTV $", font=dict(color=COLORS["accent"])),
            ),
            "legend": {**CHART_LAYOUT["legend"], "orientation": "h", "y": 1.08},
        })
        st.plotly_chart(fig, width="stretch")
    else:
        empty_state("No demographics data available")

with c2:
    insight_badge("Buyers per RFM Segment")
    if rfm_df is not None:
        df = rfm_df.copy()
        if sel_seg != "All":
            df = df[df["market_segmentation"] == sel_seg]

        seg_agg = (
            df.groupby("market_segmentation", as_index=False)
            .agg(customers=("customer_key", "count"),
                 total_spend=("total_monetary_value", "sum"))
            .sort_values("customers", ascending=True)
        )

        seg_color_map = {
            "Champions / VIP":          COLORS["accent"],
            "Loyal Customer Base":      COLORS["primary"],
            "Standard General Shopper": COLORS["warning"],
            "At Risk / Churned":        COLORS["danger"],
        }
        bar_colors = [seg_color_map.get(s, COLORS["text_muted"]) for s in seg_agg["market_segmentation"]]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=seg_agg["customers"],
            y=seg_agg["market_segmentation"],
            orientation="h",
            marker=dict(color=bar_colors, opacity=0.9),
            text=seg_agg["customers"].apply(lambda v: f"{v:,}"),
            textposition="outside",
            textfont_color=COLORS["text_primary"],
            hovertemplate="<b>%{y}</b><br>Customers: %{x:,}<br>Total Spend: $%{customdata:,.0f}",
            customdata=seg_agg["total_spend"],
        ))
        fig.update_layout(**{
            **CHART_LAYOUT,
            "title": "Customer Count by RFM Segment",
            "height": CHART_HEIGHT,
            "yaxis": {**CHART_LAYOUT["yaxis"], "categoryorder": "total ascending"},
        })
        st.plotly_chart(fig, width="stretch")
    else:
        empty_state("No RFM data available")

# ══════════════════════════════════════════════════════
# ── ROW 2: Region Bar + Gender Grouped Bar ──
# ══════════════════════════════════════════════════════
c3, c4 = st.columns(2)

with c3:
    insight_badge("Buyers by Region")
    if demo_df is not None:
        df = demo_df.copy()
        if sel_gender != "All":
            df = df[df["gender"] == sel_gender]

        region_agg = (
            df.groupby("buyer_region", as_index=False)
            .agg(unique_buyers=("unique_buyers", "sum"),
                 lifetime_value=("lifetime_value_to_seller", "sum"))
            .sort_values("unique_buyers", ascending=False)
        )
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=region_agg["buyer_region"],
            y=region_agg["unique_buyers"],
            marker=dict(
                color=region_agg["lifetime_value"],
                colorscale=[[0, COLORS["primary_dark"]], [1, COLORS["accent"]]],
                showscale=True,
                colorbar=dict(
                    title=dict(text="LTV $", font=dict(color=COLORS["text_muted"])),
                    tickfont=dict(color=COLORS["text_muted"]),
                    len=0.6,
                ),
            ),
            text=region_agg["unique_buyers"].apply(lambda v: f"{v:,}"),
            textposition="outside",
            textfont_color=COLORS["text_primary"],
            hovertemplate="<b>%{x}</b><br>Buyers: %{y:,}<br>LTV: $%{marker.color:,.0f}<extra></extra>",
        ))
        fig.update_layout(**{**CHART_LAYOUT, "title": "Buyers by Region (color=LTV)",
                             "height": CHART_HEIGHT})
        st.plotly_chart(fig, width="stretch")
    else:
        empty_state("No region data available")

with c4:
    insight_badge("Buyers by Gender across Age Bands")
    if demo_df is not None:
        df = demo_df.copy()
        if sel_region != "All":
            df = df[df["buyer_region"] == sel_region]

        gender_age = (
            df.groupby(["age_band", "gender"], as_index=False)
            .agg(unique_buyers=("unique_buyers", "sum"))
        )

        gender_colors = {}
        genders = gender_age["gender"].unique()
        palette = [COLORS["primary"], COLORS["accent"], COLORS["accent2"], COLORS["warning"]]
        for i, g in enumerate(genders):
            gender_colors[g] = palette[i % len(palette)]

        fig = px.bar(
            gender_age,
            x="age_band",
            y="unique_buyers",
            color="gender",
            color_discrete_map=gender_colors,
            barmode="group",
            text="unique_buyers",
            labels={"unique_buyers": "Buyers", "age_band": "Age Band", "gender": "Gender"},
        )
        fig.update_traces(texttemplate="%{text:,}", textposition="outside",
                          textfont_color=COLORS["text_primary"])
        fig.update_layout(**{
            **CHART_LAYOUT,
            "title": "Male vs Female Buyers per Age Band",
            "height": CHART_HEIGHT,
            "legend": {**CHART_LAYOUT["legend"], "orientation": "h", "y": 1.08},
        })
        st.plotly_chart(fig, width="stretch")
    else:
        empty_state("No gender breakdown available")

# ══════════════════════════════════════════════════════
# ── MONTHLY BUYER TREND LINE — Male vs Female ──
# ══════════════════════════════════════════════════════
st.markdown("---")
insight_badge("Monthly Buyer Trend — Male vs Female")

if sales_df is not None and demo_df is not None:
    # We'll approximate monthly buyers from sales_performance + gender ratios from demo
    # Build a gender-split buyer trend using orders_placed proportions from demo
    if "year" in sales_df.columns and "month_name" in sales_df.columns:
        # Get gender share from demographics
        df_d = demo_df.copy()
        if sel_region != "All":
            df_d = df_d[df_d["buyer_region"] == sel_region]

        gender_totals = df_d.groupby("gender")["unique_buyers"].sum()
        total_buyers = gender_totals.sum()

        # Build monthly time series
        df_s = sales_df.copy()
        df_s["period"] = df_s["year"].astype(str) + " " + df_s["month_name"].astype(str)
        df_s = df_s.sort_values(["year", "month_name"])

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_s["period"],
            y=df_s["total_orders"],
            mode="lines+markers",
            name="Total Orders",
            line=dict(color=COLORS["text_muted"], width=1.5, dash="dot"),
            marker=dict(size=5),
            hovertemplate="<b>%{x}</b><br>Orders: %{y:,}<extra></extra>",
        ))

        # Overlay gender splits using proportional share
        colors_g = [COLORS["primary"], COLORS["accent"], COLORS["accent2"], COLORS["warning"]]
        for i, (gender, count) in enumerate(gender_totals.items()):
            share = count / total_buyers if total_buyers > 0 else 0
            y_vals = (df_s["total_orders"] * share).round()
            fig.add_trace(go.Scatter(
                x=df_s["period"],
                y=y_vals,
                mode="lines+markers",
                name=gender,
                line=dict(color=colors_g[i % len(colors_g)], width=2.5),
                marker=dict(size=7),
                fill="tozeroy" if i == 0 else None,
                fillcolor=f"rgba(108,99,255,0.05)" if i == 0 else None,
                hovertemplate=f"<b>%{{x}}</b><br>{gender}: %{{y:,}}<extra></extra>",
            ))

        fig.update_layout(**{
            **CHART_LAYOUT,
            "title": "Monthly Orders Split by Gender (proportional estimate)",
            "height": 360,
            "xaxis_tickangle": -35,
            "legend": {**CHART_LAYOUT["legend"], "orientation": "h", "y": 1.08},
        })
        st.plotly_chart(fig, width="stretch")
else:
    # Fallback: just show orders per month if only sales data
    if sales_df is not None and "year" in sales_df.columns:
        df_s = sales_df.copy().sort_values(["year", "month_name"])
        df_s["period"] = df_s["year"].astype(str) + " " + df_s["month_name"].astype(str)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_s["period"],
            y=df_s["total_orders"],
            mode="lines+markers",
            name="Total Orders",
            line=dict(color=COLORS["primary"], width=2.5),
            marker=dict(size=7),
            fill="tozeroy",
            fillcolor="rgba(108,99,255,0.07)",
        ))
        fig.update_layout(**{**CHART_LAYOUT, "title": "Monthly Order Trend",
                             "height": 320, "xaxis_tickangle": -35})
        st.plotly_chart(fig, width="stretch")
    else:
        empty_state("No monthly trend data available", "📉")

# ══════════════════════════════════════════════════════
# ── ROW 3: Geo Revenue Bar + RFM Avg Spend Bar ──
# ══════════════════════════════════════════════════════
st.markdown("---")
c5, c6 = st.columns(2)

with c5:
    insight_badge("Geographic Revenue")
    if geo_df is not None:
        df = geo_df.head(14).copy()
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df["geographic_net_revenue"],
            y=df["city"],
            orientation="h",
            marker=dict(
                color=df["avg_basket_spend_by_city"],
                colorscale=[[0, COLORS["primary_dark"]], [1, COLORS["accent"]]],
                showscale=True,
                colorbar=dict(
                    title=dict(text="Avg Basket $", font=dict(color=COLORS["text_muted"])),
                    tickfont=dict(color=COLORS["text_muted"]),
                    len=0.6,
                ),
            ),
            text=df["geographic_net_revenue"].apply(lambda v: f"${v:,.0f}"),
            textposition="outside",
            textfont_color=COLORS["text_primary"],
            hovertemplate="<b>%{y}</b><br>Revenue: $%{x:,.0f}<br>Avg Basket: $%{marker.color:,.0f}<extra></extra>",
        ))
        fig.update_layout(**{**CHART_LAYOUT, "title": "Top Cities by Customer Revenue",
                             "height": CHART_HEIGHT,
                             "yaxis": {**CHART_LAYOUT["yaxis"], "categoryorder": "total ascending"}})
        st.plotly_chart(fig, width="stretch")
    else:
        empty_state("No geographic data available")

with c6:
    insight_badge("Avg Spend by Segment")
    if rfm_df is not None:
        df = rfm_df.copy()
        if sel_seg != "All":
            df = df[df["market_segmentation"] == sel_seg]

        seg_spend = (
            df.groupby("market_segmentation", as_index=False)
            .agg(avg_spend=("total_monetary_value", "mean"),
                 median_recency=("recency_days", "median"))
            .sort_values("avg_spend", ascending=True)
        )
        seg_color_map = {
            "Champions / VIP":          COLORS["accent"],
            "Loyal Customer Base":      COLORS["primary"],
            "Standard General Shopper": COLORS["warning"],
            "At Risk / Churned":        COLORS["danger"],
        }
        bar_colors = [seg_color_map.get(s, COLORS["text_muted"]) for s in seg_spend["market_segmentation"]]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=seg_spend["avg_spend"],
            y=seg_spend["market_segmentation"],
            orientation="h",
            marker=dict(color=bar_colors, opacity=0.9),
            text=seg_spend["avg_spend"].apply(lambda v: f"${v:,.0f}"),
            textposition="outside",
            textfont_color=COLORS["text_primary"],
            hovertemplate="<b>%{y}</b><br>Avg Spend: $%{x:,.0f}<br>Median Recency: %{customdata:.0f}d",
            customdata=seg_spend["median_recency"],
        ))
        fig.update_layout(**{**CHART_LAYOUT, "title": "Avg Customer Spend by RFM Segment",
                             "height": CHART_HEIGHT,
                             "yaxis": {**CHART_LAYOUT["yaxis"], "categoryorder": "total ascending"}})
        st.plotly_chart(fig, width="stretch")
    else:
        empty_state("No segment spend data available")

# ── SEGMENT SUMMARY TABLE ──
if rfm_df is not None:
    st.markdown("---")
    insight_badge("Full Segment Value Table")
    df = rfm_df.copy()
    if sel_seg != "All":
        df = df[df["market_segmentation"] == sel_seg]

    seg_tbl = (
        df.groupby("market_segmentation")
        .agg(
            customers=("customer_key", "count"),
            avg_spend=("total_monetary_value", "mean"),
            total_spend=("total_monetary_value", "sum"),
            avg_recency=("recency_days", "mean"),
            avg_orders=("frequency_count", "mean"),
        )
        .reset_index()
        .sort_values("total_spend", ascending=False)
    )
    seg_tbl.columns = ["Segment", "Customers", "Avg Spend $", "Total Spend $", "Avg Recency (d)", "Avg Orders"]

    fig = go.Figure(data=[go.Table(
        header=dict(
            values=list(seg_tbl.columns),
            fill_color=COLORS["bg_card2"],
            line_color=COLORS["border"],
            font=dict(color=COLORS["text_primary"], size=12, family="DM Sans"),
            align="left", height=36,
        ),
        cells=dict(
            values=[seg_tbl[c] for c in seg_tbl.columns],
            fill_color=[[COLORS["bg_card"] if i % 2 == 0 else COLORS["bg_dark"] for i in range(len(seg_tbl))]],
            line_color=COLORS["border"],
            font=dict(color=COLORS["text_muted"], size=11, family="DM Mono"),
            align=["left"] + ["right"] * (len(seg_tbl.columns) - 1),
            height=32,
            format=[None, ",d", ",.2f", ",.0f", ",.1f", ",.1f"],
        ),
    )])
    fig.update_layout(**{**CHART_LAYOUT, "title": "RFM Segment Value Breakdown",
                         "height": 280, "margin": dict(l=0, r=0, t=48, b=0)})
    st.plotly_chart(fig, width="stretch")