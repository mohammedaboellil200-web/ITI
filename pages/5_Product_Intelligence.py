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
section_title("🧠 Product Intelligence", "Revenue attribution, price efficiency, margin by SKU & portfolio analysis")

# ── LOAD DATA ──
prod_df   = load_insight(sk, "product_profitability")
funnel_df = load_insight(sk, "funnel_and_conversion")
inv_df    = load_insight(sk, "inventory_velocity_health")
ret_df    = load_insight(sk, "return_rate_analysis")
sat_df    = load_insight(sk, "customer_satisfaction_drain")
basket_df = load_insight(sk, "basket_analysis_co_purchase")

# ── FILTER BAR ──
st.markdown('<div style="background:#161929;border:1px solid #2A2F4A;border-radius:12px;padding:14px 20px;margin-bottom:20px">', unsafe_allow_html=True)
fa, fb, fc = st.columns([2, 2, 3])
cat_opts = ["All"]
if prod_df is not None and "category_name" in prod_df.columns:
    cat_opts += sorted(prod_df["category_name"].dropna().unique().tolist())
sel_cat = fa.selectbox("🏷 Category", cat_opts, key="pi_cat")
top_n = fb.selectbox("📊 Show Top N", [10, 20, 30, 50], index=1, key="pi_topn")
fc.markdown('<p style="font-size:0.78rem;color:#8890B5;margin-top:28px">All charts reflect the filtered category & top N products.</p>', unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ── KPI ROW ──
kpi_metrics = []
if prod_df is not None:
    df_p = prod_df.copy()
    if sel_cat != "All": df_p = df_p[df_p["category_name"] == sel_cat]
    df_p = df_p.head(top_n)
    for col in ["net_marketplace_sales", "estimated_seller_takehome", "units_sold", "avg_selling_price"]:
        if col in df_p.columns:
            df_p[col] = df_p[col].astype(float)
    total_rev   = df_p["net_marketplace_sales"].sum()
    total_take  = df_p["estimated_seller_takehome"].sum()
    total_units = df_p["units_sold"].sum()
    avg_price   = df_p["avg_selling_price"].mean() if "avg_selling_price" in df_p.columns else None
    commission  = total_rev - total_take
    margin_rate = (total_take / total_rev * 100) if total_rev > 0 else 0
    top_sku     = df_p.loc[df_p["net_marketplace_sales"].idxmax(), "product_name"] if not df_p.empty else "—"
    kpi_metrics.extend([
        {"label": "Portfolio Net Revenue",   "value": f"${total_rev:,.0f}"},
        {"label": "Est. Seller Takehome",    "value": f"${total_take:,.0f}"},
        {"label": "Platform Commission",     "value": f"${commission:,.0f}", "delta": f"{100-margin_rate:.1f}% rate"},
        {"label": "Units Sold",              "value": f"{int(total_units):,}"},
        {"label": "Avg Selling Price",       "value": f"${avg_price:.2f}" if avg_price and pd.notna(avg_price) else "—"},
        {"label": "Top Revenue SKU",         "value": str(top_sku)[:22]},
    ])
if kpi_metrics:
    render_kpi_row(kpi_metrics, num_cols=3)

st.markdown("---")

# ── ROW 1: Revenue Pareto + Takehome Scatter ──
c1, c2 = st.columns(2)

with c1:
    insight_badge("Revenue Pareto — Top SKUs")
    if prod_df is not None:
        df = prod_df.copy()
        if sel_cat != "All": df = df[df["category_name"] == sel_cat]
        df = df.head(top_n)
        for col in ["net_marketplace_sales", "estimated_seller_takehome", "units_sold", "avg_selling_price"]:
            if col in df.columns:
                df[col] = df[col].astype(float)
        df = df.sort_values("net_marketplace_sales", ascending=False)
        df["cum_rev"] = df["net_marketplace_sales"].cumsum()
        df["cum_pct"] = df["cum_rev"] / df["net_marketplace_sales"].sum() * 100
        df["label"]   = df["product_name"].str[:22]

        fig = go.Figure()
        fig.add_trace(go.Bar(x=df["label"], y=df["net_marketplace_sales"],
                             name="Net Revenue",
                             marker=dict(color=df["net_marketplace_sales"],
                                         colorscale=[[0, COLORS["primary_dark"]], [1, COLORS["accent"]]],
                                         showscale=False),
                             hovertemplate="<b>%{x}</b><br>$%{y:,.0f}<extra></extra>"))
        fig.add_trace(go.Scatter(x=df["label"], y=df["cum_pct"], name="Cumulative %",
                                 mode="lines+markers", line=dict(color=COLORS["accent3"], width=2.5),
                                 marker=dict(size=7), yaxis="y2",
                                 hovertemplate="Cumul: %{y:.1f}%<extra></extra>"))
        fig.add_hline(y=80, line_dash="dot", line_color=COLORS["warning"], opacity=0.6,
                      yref="y2", annotation_text="80% threshold", annotation_font_color=COLORS["warning"])
        fig.update_layout(**{**CHART_LAYOUT, "title": "Revenue Pareto — Identify Power SKUs",
                             "height": CHART_HEIGHT, "xaxis_tickangle": -40,
                             "yaxis2": dict(overlaying="y", side="right", showgrid=False,
                                            range=[0, 110], ticksuffix="%",
                                            tickfont=dict(color=COLORS["accent3"])),
                             "legend": {**CHART_LAYOUT["legend"], "orientation": "h", "y": 1.08}})
        st.plotly_chart(fig, width="stretch")
    else:
        empty_state("No product profitability data available")

with c2:
    insight_badge("Selling Price vs Takehome Margin")
    if prod_df is not None:
        df = prod_df.copy()
        if sel_cat != "All": df = df[df["category_name"] == sel_cat]
        df = df.head(top_n).copy()
        for col in ["net_marketplace_sales", "estimated_seller_takehome", "units_sold", "avg_selling_price"]:
            if col in df.columns:
                df[col] = df[col].astype(float)
        df["commission_rate"] = ((df["net_marketplace_sales"] - df["estimated_seller_takehome"]) / df["net_marketplace_sales"] * 100).round(1)
        fig = px.scatter(df, x="avg_selling_price", y="estimated_seller_takehome",
                         size="units_sold", color="commission_rate",
                         color_continuous_scale=[[0, COLORS["success"]], [0.5, COLORS["warning"]], [1, COLORS["danger"]]],
                         hover_name="product_name",
                         labels={"avg_selling_price": "Avg Selling Price $",
                                 "estimated_seller_takehome": "Est. Takehome $",
                                 "commission_rate": "Commission %"},
                         size_max=45)
        fig.update_layout(**{**CHART_LAYOUT, "title": "Price vs Takehome (color=Commission%, size=Units)",
                             "height": CHART_HEIGHT,
                             "coloraxis_colorbar": dict(title=dict(text="Commission %"),
                                                         tickfont=dict(color=COLORS["text_muted"]), ticksuffix="%")})
        st.plotly_chart(fig, width="stretch")
    else:
        empty_state("No pricing data available")

# ── ROW 2: BCG Matrix + Conversion vs Satisfaction ──
c3, c4 = st.columns(2)

with c3:
    insight_badge("BCG-style Portfolio Matrix")
    if prod_df is not None and funnel_df is not None:
        df_p = prod_df.copy()
        if sel_cat != "All": df_p = df_p[df_p["category_name"] == sel_cat]
        df_p = df_p.head(top_n)
        for col in ["net_marketplace_sales", "units_sold"]:
            if col in df_p.columns:
                df_p[col] = df_p[col].astype(float)
        funnel_df_f = funnel_df.copy()
        for col in ["view_to_purchase_conversion_rate", "detail_page_views", "successful_orders", "cart_additions"]:
            if col in funnel_df_f.columns:
                funnel_df_f[col] = funnel_df_f[col].astype(float)
        merged = pd.merge(df_p[["product_name", "net_marketplace_sales", "units_sold", "category_name"]],
                          funnel_df_f[["product_name", "view_to_purchase_conversion_rate", "detail_page_views"]],
                          on="product_name", how="inner")
        med_rev = merged["net_marketplace_sales"].median()
        med_cvr = merged["view_to_purchase_conversion_rate"].median()
        def safe_bcg(r):
            rev = r["net_marketplace_sales"]
            cvr = r["view_to_purchase_conversion_rate"]
            if pd.isna(rev) or pd.isna(cvr):
                return "🐶 Dog"
            return (
                "⭐ Star" if rev >= med_rev and cvr >= med_cvr
                else "❓ Question Mark" if rev < med_rev and cvr >= med_cvr
                else "🐄 Cash Cow" if rev >= med_rev and cvr < med_cvr
                else "🐶 Dog"
            )
        merged["bcg_label"] = merged.apply(safe_bcg, axis=1)
        bcg_color = {"⭐ Star": COLORS["accent"], "❓ Question Mark": COLORS["warning"],
                     "🐄 Cash Cow": COLORS["success"], "🐶 Dog": COLORS["danger"]}
        fig = px.scatter(merged, x="view_to_purchase_conversion_rate", y="net_marketplace_sales",
                         size="units_sold", color="bcg_label", color_discrete_map=bcg_color,
                         hover_name="product_name",
                         labels={"view_to_purchase_conversion_rate": "CVR %", "net_marketplace_sales": "Net Revenue $"},
                         size_max=50)
        fig.add_vline(x=med_cvr, line_dash="dash", line_color=COLORS["border"], opacity=0.5)
        fig.add_hline(y=med_rev, line_dash="dash", line_color=COLORS["border"], opacity=0.5)
        fig.update_layout(**{**CHART_LAYOUT, "title": "BCG Matrix: CVR% vs Revenue (size=Units)",
                             "height": CHART_HEIGHT,
                             "legend": {**CHART_LAYOUT["legend"], "orientation": "h", "y": 1.08}})
        st.plotly_chart(fig, width="stretch")
    elif prod_df is not None:
        # Fallback: category breakdown
        df_p = prod_df.copy()
        cat_agg = df_p.groupby("category_name", as_index=False).agg(
            revenue=("net_marketplace_sales", "sum"), units=("units_sold", "sum"))
        fig = px.bar(cat_agg.sort_values("revenue", ascending=False), x="category_name", y="revenue",
                     color="revenue", color_continuous_scale=[[0, COLORS["primary_dark"]], [1, COLORS["accent"]]],
                     text="revenue", labels={"category_name": "Category", "revenue": "Net Revenue $"})
        fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
        fig.update_layout(**{**CHART_LAYOUT, "title": "Revenue by Category", "height": CHART_HEIGHT,
                             "coloraxis_showscale": False})
        st.plotly_chart(fig, width="stretch")
    else:
        empty_state("No BCG data available")

with c4:
    insight_badge("Quality Score — CVR × Satisfaction")
    if funnel_df is not None and sat_df is not None:
        funnel_df_f = funnel_df.copy()
        for col in ["view_to_purchase_conversion_rate", "successful_orders"]:
            if col in funnel_df_f.columns:
                funnel_df_f[col] = funnel_df_f[col].astype(float)
        sat_df_f = sat_df.copy()
        for col in ["average_star_rating", "negative_review_count", "total_reviews_received", "avg_delivery_days_for_product"]:
            if col in sat_df_f.columns:
                sat_df_f[col] = sat_df_f[col].astype(float)
        merged_qs = pd.merge(
            funnel_df_f[["product_name", "view_to_purchase_conversion_rate", "successful_orders"]],
            sat_df_f[["product_name", "average_star_rating", "negative_review_count", "total_reviews_received"]],
            on="product_name", how="inner").head(top_n)
        merged_qs["quality_score"] = (merged_qs["view_to_purchase_conversion_rate"] *
                                       merged_qs["average_star_rating"] / 5).round(2)
        fig = px.scatter(merged_qs, x="average_star_rating", y="view_to_purchase_conversion_rate",
                         size="successful_orders", color="quality_score",
                         color_continuous_scale=[[0, COLORS["danger"]], [0.5, COLORS["warning"]], [1, COLORS["accent"]]],
                         hover_name="product_name",
                         labels={"average_star_rating": "Avg Star Rating", "view_to_purchase_conversion_rate": "CVR %"},
                         size_max=45)
        fig.add_vline(x=4.0, line_dash="dot", line_color=COLORS["success"], opacity=0.5,
                      annotation_text="4★ Min", annotation_font_color=COLORS["success"])
        fig.add_hline(y=5.0, line_dash="dot", line_color=COLORS["primary"], opacity=0.5,
                      annotation_text="5% CVR target", annotation_font_color=COLORS["primary"])
        fig.update_layout(**{**CHART_LAYOUT, "title": "CVR% vs Star Rating — Product Quality Score",
                             "height": CHART_HEIGHT,
                             "coloraxis_colorbar": dict(title=dict(text="Quality Score"),
                                                         tickfont=dict(color=COLORS["text_muted"]))})
        st.plotly_chart(fig, width="stretch")
    else:
        empty_state("Requires both funnel and satisfaction data")

# ── ROW 3: Top Products Full Table ──
st.markdown("---")
insight_badge("Full Product Performance Ledger")
if prod_df is not None:
    df_t = prod_df.copy()
    if sel_cat != "All": df_t = df_t[df_t["category_name"] == sel_cat]
    df_t = df_t.head(top_n).copy()
    for col in ["net_marketplace_sales", "estimated_seller_takehome", "units_sold", "avg_selling_price"]:
        if col in df_t.columns:
            df_t[col] = df_t[col].astype(float)
    df_t["commission_$"] = df_t["net_marketplace_sales"] - df_t["estimated_seller_takehome"]
    df_t["margin_%"] = (df_t["estimated_seller_takehome"] / df_t["net_marketplace_sales"] * 100).round(1)
    df_t["rank"] = range(1, len(df_t) + 1)

    # Merge in return rate and CVR if available
    if ret_df is not None:
        df_t = df_t.merge(ret_df[["product_name", "return_rate_percentage"]], on="product_name", how="left")
    else:
        df_t["return_rate_percentage"] = np.nan
    if funnel_df is not None:
        df_t = df_t.merge(funnel_df[["product_name", "view_to_purchase_conversion_rate"]], on="product_name", how="left")
    else:
        df_t["view_to_purchase_conversion_rate"] = np.nan

    cols_show = ["rank", "product_name", "category_name", "units_sold", "net_marketplace_sales",
                 "estimated_seller_takehome", "commission_$", "margin_%", "return_rate_percentage",
                 "view_to_purchase_conversion_rate"]
    header_names = ["#", "Product", "Category", "Units", "Net Sales $", "Takehome $", "Commission $", "Margin %", "Return %", "CVR %"]
    df_display = df_t[cols_show]
    fig = go.Figure(data=[go.Table(
        header=dict(values=header_names, fill_color=COLORS["bg_card2"], line_color=COLORS["border"],
                    font=dict(color=COLORS["text_primary"], size=11), align="left", height=34),
        cells=dict(
            values=[df_display[c] for c in cols_show],
            fill_color=[[COLORS["bg_card"] if i % 2 == 0 else COLORS["bg_dark"] for i in range(len(df_display))]],
            line_color=COLORS["border"],
            font=dict(color=COLORS["text_muted"], size=10), align=["right", "left", "left"] + ["right"] * 7, height=28,
            format=[None, None, None, ",d", ",.0f", ",.0f", ",.0f", ".1f", ".2f", ".2f"],
        ),
    )])
    fig.update_layout(**{**CHART_LAYOUT, "title": f"Top {top_n} Products — Full Metrics",
                         "height": min(600, 120 + len(df_display) * 30), "margin": dict(l=0, r=0, t=48, b=0)})
    st.plotly_chart(fig, width="stretch")
else:
    empty_state("No product data available")