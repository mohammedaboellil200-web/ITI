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
section_title("⭐ Customer Ratings & Reviews", "Voice of the customer — rating distribution, quality trends & sentiment signals")

# ── LOAD DATA ──
reviews_df = load_insight(sk, "customer_ratings_reviews")
sentiment_df = load_insight(sk, "review_sentiment_analysis")

# ── FILTER BAR ──
st.markdown(
    '<div style="background:#161929;border:1px solid #2A2F4A;border-radius:12px;padding:14px 20px;margin-bottom:20px">',
    unsafe_allow_html=True,
)
fa, fb, fc = st.columns([2, 2, 3])

star_opts = ["All", "5★", "4★", "3★", "2★", "1★"]
sel_star = fa.selectbox("⭐ Rating", star_opts, key="rr_star")

cat_opts = ["All"]
if reviews_df is not None and "category_name" in reviews_df.columns:
    cat_opts += sorted(reviews_df["category_name"].dropna().unique().tolist())
sel_cat = fb.selectbox("🏷 Category", cat_opts, key="rr_cat")

fc.markdown(
    '<p style="font-size:0.78rem;color:#8890B5;margin-top:28px">Filters apply to all charts. Reviews load most recent first.</p>',
    unsafe_allow_html=True,
)
st.markdown("</div>", unsafe_allow_html=True)

# ── APPLY FILTERS ──
df_rev = None
df_sent = None
if reviews_df is not None:
    df_rev = reviews_df.copy()
    if sel_star != "All":
        star_map = {"5★": 5, "4★": 4, "3★": 3, "2★": 2, "1★": 1}
        df_rev = df_rev[df_rev["star_rating"] == star_map[sel_star]]
    if sel_cat != "All":
        df_rev = df_rev[df_rev["category_name"] == sel_cat]
    # Decimal safety
    for col in ["star_rating", "days_since_review"]:
        if col in df_rev.columns:
            df_rev[col] = df_rev[col].astype(float)

if sentiment_df is not None:
    df_sent = sentiment_df.copy()
    if sel_star != "All":
        star_map = {"5★": 5, "4★": 4, "3★": 3, "2★": 2, "1★": 1}
        df_sent = df_sent[df_sent["star_rating"] == star_map[sel_star]]
    if sel_cat != "All":
        df_sent = df_sent[df_sent["category_name"] == sel_cat]
    for col in ["star_rating"]:
        if col in df_sent.columns:
            df_sent[col] = df_sent[col].astype(float)

# ── POWER KPI ROW ──
kpi_metrics = []
if df_rev is not None and not df_rev.empty:
    total_reviews = len(df_rev)
    avg_rating = df_rev["star_rating"].mean()

    # Sentiment breakdown from star ratings
    pos_pct = (df_rev["star_rating"] >= 4).sum() / len(df_rev) * 100
    neg_pct = (df_rev["star_rating"] <= 2).sum() / len(df_rev) * 100
    neu_pct = 100 - pos_pct - neg_pct

    # Recent activity (last 30 days)
    recent_count = df_rev[df_rev["days_since_review"].fillna(999) <= 30].shape[0] if "days_since_review" in df_rev.columns else 0

    kpi_metrics.extend([
        {"label": "Total Reviews",        "value": f"{int(total_reviews):,}"},
        {"label": "Avg Star Rating",      "value": f"{avg_rating:.2f}★", "delta": "▲ good" if avg_rating >= 4 else "▼ watch"},
        {"label": "Positive Sentiment",   "value": f"{pos_pct:.1f}%"},
        {"label": "Neutral",              "value": f"{neu_pct:.1f}%"},
        {"label": "Negative Sentiment",   "value": f"{neg_pct:.1f}%", "delta": "⚠️ action" if neg_pct > 15 else "✓ healthy"},
        {"label": "Reviews (Last 30d)",   "value": f"{int(recent_count):,}"},
    ])
elif reviews_df is not None and reviews_df.empty:
    kpi_metrics.append({"label": "Reviews", "value": "No reviews found"})

if kpi_metrics:
    render_kpi_row(kpi_metrics, num_cols=3)

st.markdown("---")

# ══════════════════════════════════════════════════════
# ── ROW 1: Rating Distribution Donut + Sentiment by Category ──
# ══════════════════════════════════════════════════════
c1, c2 = st.columns(2)

with c1:
    insight_badge("Star Rating Distribution")
    if df_rev is not None and not df_rev.empty:
        rating_counts = df_rev["star_rating"].value_counts().sort_index().reset_index()
        rating_counts.columns = ["rating", "count"]
        # Ensure all 5 stars are represented
        for r in range(1, 6):
            if r not in rating_counts["rating"].values:
                rating_counts = pd.concat([rating_counts, pd.DataFrame({"rating": [float(r)], "count": [0]})], ignore_index=True)
        rating_counts = rating_counts.sort_values("rating")

        star_colors = [COLORS["danger"], COLORS["accent2"], COLORS["warning"], "#A78BFA", COLORS["accent"]]
        fig = go.Figure(go.Pie(
            labels=[f"{int(r)}★" for r in rating_counts["rating"]],
            values=rating_counts["count"],
            hole=0.55,
            marker=dict(colors=star_colors, line=dict(color=COLORS["bg_dark"], width=2)),
            textinfo="label+percent",
            textfont=dict(color=COLORS["text_primary"], size=12),
            hovertemplate="<b>%{label}</b><br>Reviews: %{value:,}<br>Share: %{percent}<extra></extra>",
        ))
        fig.update_layout(**{
            **CHART_LAYOUT,
            "title": "Rating Breakdown",
            "height": CHART_HEIGHT,
            "showlegend": False,
            "annotations": [dict(
                text=f"{avg_rating:.2f}<br><span style='font-size:10px'>avg</span>",
                x=0.5, y=0.5,
                font=dict(size=18, color=COLORS["text_primary"], family="Syne"),
                showarrow=False
            )]
        })
        st.plotly_chart(fig, width="stretch")
    else:
        empty_state("No rating data available")

with c2:
    insight_badge("Sentiment by Product Category")
    if df_sent is not None and not df_sent.empty:
        cat_sent = df_sent.groupby(["category_name", "sentiment_label"], as_index=False, observed=True).size().reset_index()
        # The size() column is named 0 in older pandas, or size in newer versions
        count_col = 0 if 0 in cat_sent.columns else ("size" if "size" in cat_sent.columns else None)
        if count_col is not None:
            cat_sent = cat_sent.rename(columns={count_col: "count"})
        # Pivot for stacked bar
        cat_pivot = cat_sent.pivot(index="category_name", columns="sentiment_label", values="count").fillna(0)
        for col in ["Positive", "Neutral", "Negative"]:
            if col not in cat_pivot.columns:
                cat_pivot[col] = 0
        cat_pivot = cat_pivot[["Positive", "Neutral", "Negative"]]
        cat_pivot = cat_pivot.sort_values("Negative", ascending=True)

        fig = go.Figure()
        sentiment_colors = {"Positive": COLORS["success"], "Neutral": COLORS["warning"], "Negative": COLORS["danger"]}
        for sent in ["Positive", "Neutral", "Negative"]:
            fig.add_trace(go.Bar(
                name=sent,
                y=cat_pivot.index,
                x=cat_pivot[sent],
                orientation="h",
                marker_color=sentiment_colors[sent],
                text=cat_pivot[sent].apply(lambda v: f"{int(v)}"),
                textposition="inside",
                textfont=dict(color="white", size=10),
                hovertemplate=f"<b>%{{y}}</b><br>{sent}: %{{x:,}}<extra></extra>",
            ))
        fig.update_layout(**{
            **CHART_LAYOUT,
            "title": "Sentiment Stack by Category",
            "height": CHART_HEIGHT,
            "barmode": "stack",
            "yaxis": {**CHART_LAYOUT["yaxis"], "categoryorder": "total ascending"},
            "legend": {**CHART_LAYOUT["legend"], "orientation": "h", "y": 1.08},
        })
        st.plotly_chart(fig, width="stretch")
    else:
        empty_state("No sentiment data available")

# ══════════════════════════════════════════════════════
# ── ROW 2: Monthly Review Trend + Category Rating Comparison ──
# ══════════════════════════════════════════════════════
st.markdown("---")
c3, c4 = st.columns(2)

with c3:
    insight_badge("Monthly Review Volume & Avg Rating")
    if df_rev is not None and not df_rev.empty and "review_date" in df_rev.columns:
        df_rev["review_date"] = pd.to_datetime(df_rev["review_date"], errors="coerce")
        df_monthly = df_rev.dropna(subset=["review_date"]).copy()
        df_monthly["year_month"] = df_monthly["review_date"].dt.to_period("M").astype(str)

        monthly_agg = df_monthly.groupby("year_month", as_index=False, observed=True).agg(
            review_count=("review_key", "count"),
            avg_rating=("star_rating", "mean"),
        ).sort_values("year_month").tail(12)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=monthly_agg["year_month"],
            y=monthly_agg["review_count"],
            name="Review Count",
            marker=dict(color=COLORS["primary"], opacity=0.6),
            hovertemplate="<b>%{x}</b><br>Reviews: %{y:,}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=monthly_agg["year_month"],
            y=monthly_agg["avg_rating"],
            name="Avg Rating",
            mode="lines+markers",
            line=dict(color=COLORS["accent3"], width=2.5),
            marker=dict(size=8),
            yaxis="y2",
            hovertemplate="Avg Rating: %{y:.2f}★<extra></extra>",
        ))
        fig.add_hline(y=4.0, line_dash="dot", line_color=COLORS["success"], opacity=0.5,
                      annotation_text="4★ Target", annotation_font_color=COLORS["success"])
        fig.update_layout(**{
            **CHART_LAYOUT,
            "title": "Review Volume & Quality Trend (Last 12M)",
            "height": CHART_HEIGHT,
            "yaxis2": dict(
                overlaying="y", side="right", showgrid=False,
                range=[0, 5.5], tickfont=dict(color=COLORS["accent3"]),
                title=dict(text="Avg Rating", font=dict(color=COLORS["accent3"])),
            ),
            "legend": {**CHART_LAYOUT["legend"], "orientation": "h", "y": 1.08},
            "xaxis_tickangle": -35,
        })
        st.plotly_chart(fig, width="stretch")
    else:
        empty_state("No date data for trend")

with c4:
    insight_badge("Category Rating Comparison")
    if df_rev is not None and not df_rev.empty and "category_name" in df_rev.columns:
        cat_ratings = df_rev.dropna(subset=["star_rating"]).groupby("category_name", as_index=False, observed=True).agg(
            avg_rating=("star_rating", "mean"),
            review_count=("review_key", "count"),
        ).sort_values("avg_rating", ascending=True)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=cat_ratings["avg_rating"],
            y=cat_ratings["category_name"],
            orientation="h",
            marker=dict(
                color=cat_ratings["avg_rating"],
                colorscale=[[0, COLORS["danger"]], [0.5, COLORS["warning"]], [1, COLORS["accent"]]],
                showscale=True,
                colorbar=dict(
                    title=dict(text="Avg ★", font=dict(color=COLORS["text_muted"])),
                    tickfont=dict(color=COLORS["text_muted"]),
                    len=0.6,
                ),
            ),
            text=cat_ratings["avg_rating"].apply(lambda v: f"{v:.2f}★"),
            textposition="outside",
            textfont_color=COLORS["text_primary"],
            customdata=cat_ratings["review_count"].values,
            hovertemplate="<b>%{y}</b><br>Avg: %{x:.2f}★<br>Reviews: %{customdata:,}<extra></extra>",
        ))
        fig.add_vline(x=4.0, line_dash="dot", line_color=COLORS["success"], opacity=0.6,
                      annotation_text="4★ Target", annotation_font_color=COLORS["success"])
        fig.update_layout(**{
            **CHART_LAYOUT,
            "title": "Category Quality Score (color = avg rating)",
            "height": CHART_HEIGHT,
            "yaxis": {**CHART_LAYOUT["yaxis"], "categoryorder": "total ascending"},
        })
        st.plotly_chart(fig, width="stretch")
    else:
        empty_state("No category data available")

# ══════════════════════════════════════════════════════
# ── ROW 3: Product Rating Heatmap + Rating Velocity ──
# ══════════════════════════════════════════════════════
st.markdown("---")
c5, c6 = st.columns(2)

with c5:
    insight_badge("Product Rating Heatmap — Top 20 SKUs")
    if df_rev is not None and not df_rev.empty:
        prod_ratings = df_rev.dropna(subset=["star_rating"]).groupby("product_name", as_index=False, observed=True).agg(
            avg_rating=("star_rating", "mean"),
            review_count=("review_key", "count"),
        ).sort_values("review_count", ascending=False).head(20)

        prod_ratings["label"] = prod_ratings["product_name"].str[:28]
        prod_ratings = prod_ratings.sort_values("avg_rating", ascending=True)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=prod_ratings["avg_rating"],
            y=prod_ratings["label"],
            orientation="h",
            marker=dict(
                color=prod_ratings["avg_rating"],
                colorscale=[[0, COLORS["danger"]], [0.5, COLORS["warning"]], [1, COLORS["accent"]]],
                showscale=True,
                colorbar=dict(
                    title=dict(text="Avg ★", font=dict(color=COLORS["text_muted"])),
                    tickfont=dict(color=COLORS["text_muted"]),
                    len=0.6,
                ),
            ),
            text=prod_ratings["avg_rating"].apply(lambda v: f"{v:.2f}★"),
            textposition="outside",
            textfont_color=COLORS["text_primary"],
            customdata=prod_ratings["review_count"].values,
            hovertemplate="<b>%{y}</b><br>Avg: %{x:.2f}★<br>Reviews: %{customdata:,}<extra></extra>",
        ))
        fig.add_vline(x=4.0, line_dash="dot", line_color=COLORS["success"], opacity=0.6,
                      annotation_text="4★ Target", annotation_font_color=COLORS["success"])
        fig.update_layout(**{
            **CHART_LAYOUT,
            "title": "Product Quality Score (color = avg rating)",
            "height": CHART_HEIGHT,
            "yaxis": {**CHART_LAYOUT["yaxis"], "categoryorder": "total ascending"},
        })
        st.plotly_chart(fig, width="stretch")
    else:
        empty_state("No product rating data")

with c6:
    insight_badge("Rating Velocity — Reviews per Day")
    if df_rev is not None and not df_rev.empty and "days_since_review" in df_rev.columns:
        df_vel = df_rev.dropna(subset=["days_since_review"]).copy()
        df_vel["period"] = pd.cut(df_vel["days_since_review"], 
                                   bins=[0, 7, 30, 90, 180, 365, 9999],
                                   labels=["0-7d", "8-30d", "31-90d", "91-180d", "181-365d", "365d+"])
        vel_agg = df_vel.groupby("period", as_index=False, observed=True).agg(
            review_count=("review_key", "count"),
            avg_rating=("star_rating", "mean"),
        )

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=vel_agg["period"],
            y=vel_agg["review_count"],
            name="Review Count",
            marker=dict(color=COLORS["primary"], opacity=0.7),
            text=vel_agg["review_count"].apply(lambda v: f"{int(v)}"),
            textposition="outside",
            textfont_color=COLORS["text_primary"],
            hovertemplate="<b>%{x}</b><br>Reviews: %{y:,}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=vel_agg["period"],
            y=vel_agg["avg_rating"],
            name="Avg Rating",
            mode="lines+markers",
            line=dict(color=COLORS["accent3"], width=2.5),
            marker=dict(size=8),
            yaxis="y2",
            hovertemplate="Avg: %{y:.2f}★<extra></extra>",
        ))
        fig.add_hline(y=4.0, line_dash="dot", line_color=COLORS["success"], opacity=0.5,
                      annotation_text="4★ Target", annotation_font_color=COLORS["success"])
        fig.update_layout(**{
            **CHART_LAYOUT,
            "title": "Review Recency & Quality",
            "height": CHART_HEIGHT,
            "yaxis2": dict(
                overlaying="y", side="right", showgrid=False,
                range=[0, 5.5], tickfont=dict(color=COLORS["accent3"]),
                title=dict(text="Avg Rating", font=dict(color=COLORS["accent3"])),
            ),
            "legend": {**CHART_LAYOUT["legend"], "orientation": "h", "y": 1.08},
        })
        st.plotly_chart(fig, width="stretch")
    else:
        empty_state("No recency data available")

# ══════════════════════════════════════════════════════
# ── ALERTS: Negative Review Flags ──
# ══════════════════════════════════════════════════════
st.markdown("---")
st.markdown(
    '<p style="font-family:Syne,sans-serif;font-size:1.1rem;font-weight:700;color:#F0F2FF;margin-bottom:12px">⚡ Review Quality Alerts</p>',
    unsafe_allow_html=True,
)

alerts = []
if df_rev is not None and not df_rev.empty:
    # Recent 1-star reviews
    recent_bad = df_rev[(df_rev["star_rating"] == 1) & (df_rev["days_since_review"].fillna(999) <= 30)] if "days_since_review" in df_rev.columns else pd.DataFrame()
    if not recent_bad.empty:
        alerts.append(("🔴", "Recent 1★ Reviews", f"{len(recent_bad)} one-star review(s) in the last 30 days — immediate response needed.", COLORS["danger"]))

    # Products with avg < 3
    low_prod = df_rev.dropna(subset=["star_rating"]).groupby("product_name")["star_rating"].mean().reset_index()
    low_prod = low_prod[low_prod["star_rating"] < 3]
    if not low_prod.empty:
        prod_names = ", ".join(low_prod["product_name"].head(3).str[:20].tolist())
        alerts.append(("🔴", "Low-Rated Products", f"{len(low_prod)} product(s) below 3★: {prod_names}...", COLORS["danger"]))

    # Rating decline trend
    if "review_date" in df_rev.columns and len(df_rev) > 10:
        df_rev["review_date"] = pd.to_datetime(df_rev["review_date"], errors="coerce")
        df_trend = df_rev.dropna(subset=["review_date"]).copy()
        df_trend["month"] = df_trend["review_date"].dt.to_period("M")
        monthly_avg = df_trend.groupby("month")["star_rating"].mean()
        if len(monthly_avg) >= 2:
            latest = monthly_avg.iloc[-1]
            prev = monthly_avg.iloc[-2]
            if latest < prev - 0.5:
                alerts.append(("🟡", "Rating Decline", f"Avg rating dropped from {prev:.2f}★ to {latest:.2f}★ this month.", COLORS["warning"]))

if df_sent is not None and not df_sent.empty:
    # Negative sentiment by category
    neg_cats = df_sent[df_sent["sentiment_label"] == "Negative"]["category_name"].value_counts().head(1)
    if not neg_cats.empty:
        top_cat = neg_cats.index[0]
        alerts.append(("🟡", f"Problem Category: {top_cat}", f"Most negative ratings are in {top_cat} — investigate quality.", COLORS["warning"]))

if not alerts:
    st.markdown(
        '<div style="background:#161929;border:1px dashed #2A2F4A;border-radius:10px;padding:16px 20px;color:#00E5C3;font-size:0.88rem">✅ No active review alerts — customer sentiment is healthy.</div>',
        unsafe_allow_html=True,
    )
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

# ══════════════════════════════════════════════════════
# ── REVIEW TABLE: Latest Reviews ──
# ══════════════════════════════════════════════════════
st.markdown("---")
insight_badge("Latest Reviews — Product Breakdown")

if df_rev is not None and not df_rev.empty:
    display_df = df_rev.head(20).copy()
    display_df["review_date_fmt"] = pd.to_datetime(display_df["review_date"], errors="coerce").dt.strftime("%Y-%m-%d").fillna("—")

    fig = go.Figure(data=[go.Table(
        header=dict(
            values=["Product", "Category", "Rating", "Date", "Days Ago"],
            fill_color=COLORS["bg_card2"],
            line_color=COLORS["border"],
            font=dict(color=COLORS["text_primary"], size=12, family="DM Sans"),
            align="left", height=38,
        ),
        cells=dict(
            values=[
                display_df["product_name"].str[:30],
                display_df["category_name"],
                display_df["star_rating"].apply(lambda v: f"{int(v)}★"),
                display_df["review_date_fmt"],
                display_df["days_since_review"].apply(lambda v: f"{int(v)}d" if pd.notna(v) else "—"),
            ],
            fill_color=[[COLORS["bg_card"] if i % 2 == 0 else COLORS["bg_dark"] for i in range(len(display_df))]],
            line_color=COLORS["border"],
            font=dict(color=COLORS["text_muted"], size=11, family="DM Mono"),
            align=["left", "left", "center", "center", "center"],
            height=34,
        ),
    )])
    fig.update_layout(**{
        **CHART_LAYOUT,
        "title": "Recent Reviews by Product",
        "height": min(520, 120 + len(display_df) * 36),
        "margin": dict(l=0, r=0, t=48, b=0),
    })
    st.plotly_chart(fig, width="stretch")
else:
    empty_state("No review data available")

# ══════════════════════════════════════════════════════
# ── SENTIMENT RADAR: Product-Level ──
# ══════════════════════════════════════════════════════
st.markdown("---")
insight_badge("Product Sentiment Radar — Top 10 by Review Volume")

if df_sent is not None and not df_sent.empty:
    top_prods = df_sent["product_name"].value_counts().head(10).index.tolist()
    radar_data = []
    for prod in top_prods:
        prod_df = df_sent[(df_sent["product_name"] == prod) & df_sent["sentiment_label"].notna()]
        counts = prod_df["sentiment_label"].value_counts()
        total = len(prod_df)
        pos = counts.get("Positive", 0) / total * 100 if total > 0 else 0
        neu = counts.get("Neutral", 0) / total * 100 if total > 0 else 0
        neg = counts.get("Negative", 0) / total * 100 if total > 0 else 0
        radar_data.append({
            "product": prod[:22],
            "Positive": pos,
            "Neutral": neu,
            "Negative": neg,
            "volume": total,
        })

    radar_df = pd.DataFrame(radar_data)
    categories = ["Positive", "Neutral", "Negative"]

    fig = go.Figure()
    colors_radar = [COLORS["primary"], COLORS["accent"], COLORS["accent2"], COLORS["warning"], "#A78BFA", "#34D399", "#FB923C", "#60A5FA", COLORS["success"], COLORS["danger"]]

    for i, row in radar_df.iterrows():
        values = [row[c] for c in categories] + [row[categories[0]]]  # close loop
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories + [categories[0]],
            name=f"{row['product']} ({int(row['volume'])})",
            line=dict(color=colors_radar[i % len(colors_radar)], width=1.5),
            fill="toself",
            fillcolor=f"rgba{tuple(int(colors_radar[i % len(colors_radar)].lstrip('#')[j:j+2], 16) for j in (0, 2, 4)) + (0.08,)}",
            hovertemplate="<b>%{theta}</b>: %{r:.1f}%<extra></extra>",
        ))

    fig.update_layout(**{
        **CHART_LAYOUT,
        "title": "Sentiment Profile per Product (% of reviews)",
        "height": 500,
        "polar": dict(
            bgcolor=COLORS["bg_card"],
            angularaxis=dict(tickfont=dict(color=COLORS["text_primary"], size=11), gridcolor=COLORS["border"]),
            radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(color=COLORS["text_muted"], size=9), gridcolor=COLORS["border"]),
        ),
        "legend": {**CHART_LAYOUT["legend"], "orientation": "h", "y": -0.12},
    })
    st.plotly_chart(fig, width="stretch")
else:
    empty_state("Not enough data for sentiment radar")