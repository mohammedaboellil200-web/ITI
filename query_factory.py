import textwrap

class SellerInsightQueryFactory:
    """
    Advanced Query Factory for Databricks SQL. Generates business insights 
    and enterprise-grade KPIs for a specific merchant via their seller_key.
    """

    def __init__(self, seller_key: int, catalog: str = "workspace", schema: str = "tijartek_gold"):
        self.seller_key = seller_key
        self.catalog = catalog
        self.schema = schema
        self.base_path = f"`{catalog}`.`{schema}`"

    @staticmethod
    def list_insight_types():
        """Returns all supported insight type codes."""
        return [
            # Enterprise Core
            'executive_summary_kpis',
            'customer_retention_cohort',
            'inventory_velocity_health',
            'payment_method_friction',
            'market_share_benchmarking',
            'basket_analysis_co_purchase',
            'rfm_customer_segmentation',
            'geospatial_expansion',
            # Legacy / Operational
            'sales_performance',
            'product_profitability',
            'return_rate_analysis',
            'customer_demographics',
            'shipping_efficiency',
            'promotion_roi',
            'funnel_and_conversion',
            'customer_satisfaction_drain',
            # Ratings & Reviews
            'customer_ratings_reviews',
            'review_sentiment_analysis',
        ]

    def get_query(self, insight_type: str) -> str:
        """
        Returns an optimized SQL query for advanced seller dashboard modules.
        """
        insight_type = insight_type.lower().strip()
        sk = self.seller_key

        # ==========================================
        # NEW ENTERPRISE CORE KPI MODULES
        # ==========================================

        if insight_type == 'executive_summary_kpis':
            query = f"""
                SELECT 
                    COUNT(DISTINCT f.order_id) AS total_orders,
                    SUM(f.quantity_sold) AS total_units_sold,
                    SUM(f.gross_revenue) AS gross_revenue,
                    SUM(f.net_revenue) AS net_revenue,
                    ROUND(SUM(f.net_revenue) / COUNT(DISTINCT f.order_id), 2) AS average_order_value,
                    ROUND(SUM(f.quantity_sold) / COUNT(DISTINCT f.order_id), 2) AS units_per_transaction,
                    ROUND((SUM(f.net_revenue) / NULLIF(SUM(f.gross_revenue), 0)) * 100, 2) AS operating_margin_pct
                FROM {self.base_path}.fact_sales f
                WHERE f.seller_key = {sk};
            """

        elif insight_type == 'customer_retention_cohort':
            query = f"""
                WITH CustomerPurchaseSequence AS (
                    SELECT 
                        f.customer_key,
                        f.order_id,
                        d.full_date AS purchase_date,
                        LEAD(d.full_date) OVER(PARTITION BY f.customer_key ORDER BY d.full_date) AS next_purchase_date
                    FROM {self.base_path}.fact_sales f
                    INNER JOIN {self.base_path}.dim_date d ON f.date_key = d.date_key
                    WHERE f.seller_key = {sk}
                ),
                CustomerMetrics AS (
                    SELECT 
                        customer_key,
                        COUNT(DISTINCT order_id) AS lifetime_orders,
                        AVG(DATEDIFF(next_purchase_date, purchase_date)) AS avg_days_between_orders
                    FROM CustomerPurchaseSequence
                    GROUP BY customer_key
                )
                SELECT 
                    COUNT(DISTINCT customer_key) AS total_historical_buyers,
                    SUM(CASE WHEN lifetime_orders > 1 THEN 1 ELSE 0 END) AS repeat_customers_count,
                    ROUND((SUM(CASE WHEN lifetime_orders > 1 THEN 1 ELSE 0 END) / COUNT(DISTINCT customer_key)) * 100, 2) AS repeat_buyer_rate,
                    ROUND(AVG(avg_days_between_orders), 1) AS platform_repurchase_cycle_days
                FROM CustomerMetrics;
            """

        elif insight_type == 'inventory_velocity_health':
            query = f"""
                WITH RecentSales AS (
                    SELECT 
                        product_key,
                        SUM(quantity_sold) AS units_sold_last_90_days,
                        SUM(net_revenue) AS revenue_last_90_days
                    FROM {self.base_path}.fact_sales
                    WHERE seller_key = {sk}
                      AND date_key >= (SELECT MIN(date_key) FROM {self.base_path}.dim_date WHERE full_date >= CURRENT_DATE() - INTERVAL 90 DAYS)
                    GROUP BY product_key
                )
                SELECT 
                    p.product_id,
                    p.name AS product_name,
                    p.category_name,
                    p.price AS current_listed_price,
                    COALESCE(r.units_sold_last_90_days, 0) AS units_sold_90d,
                    ROUND(COALESCE(r.units_sold_last_90_days, 0) / 90.0, 2) AS daily_burn_rate,
                    CASE 
                        WHEN COALESCE(r.units_sold_last_90_days, 0) >= 500 THEN 'HIGH VELOCITY (Restock Risk)'
                        WHEN COALESCE(r.units_sold_last_90_days, 0) BETWEEN 50 AND 499 THEN 'STABLE/NORMAL'
                        ELSE 'SLOW MOVING (Dead Stock/Markdown Target)'
                    END AS inventory_health_status
                FROM {self.base_path}.dim_product p
                LEFT JOIN RecentSales r ON p.product_key = r.product_key
                WHERE p.seller_key = {sk} AND p.is_current = 1
                ORDER BY units_sold_90d DESC;
            """

        elif insight_type == 'payment_method_friction':
            query = f"""
                SELECT 
                    p.method AS payment_gateway,
                    p.status AS processing_status,
                    COUNT(DISTINCT p.order_id) AS transaction_attempts,
                    SUM(p.amount) AS financial_volume,
                    ROUND((COUNT(DISTINCT p.order_id) / SUM(COUNT(DISTINCT p.order_id)) OVER(PARTITION BY p.method)) * 100, 2) AS gateway_status_share
                FROM {self.base_path}.dim_payment p
                INNER JOIN {self.base_path}.fact_sales f ON p.order_id = f.order_id
                WHERE f.seller_key = {sk}
                GROUP BY p.method, p.status
                ORDER BY p.method, transaction_attempts DESC;
            """

        elif insight_type == 'market_share_benchmarking':
            query = f"""
                WITH SellerPerformance AS (
                    SELECT 
                        p.category_name,
                        SUM(f.net_revenue) AS seller_net_revenue,
                        SUM(f.quantity_sold) AS seller_units_sold
                    FROM {self.base_path}.fact_sales f
                    INNER JOIN {self.base_path}.dim_product p ON f.product_key = p.product_key
                    WHERE f.seller_key = {sk}
                    GROUP BY p.category_name
                ),
                GlobalPerformance AS (
                    SELECT 
                        p.category_name,
                        SUM(f.net_revenue) AS total_market_revenue,
                        SUM(f.quantity_sold) AS total_market_units_sold
                    FROM {self.base_path}.fact_sales f
                    INNER JOIN {self.base_path}.dim_product p ON f.product_key = p.product_key
                    GROUP BY p.category_name
                )
                SELECT 
                    s.category_name,
                    s.seller_net_revenue,
                    g.total_market_revenue,
                    ROUND((s.seller_net_revenue / g.total_market_revenue) * 100, 2) AS seller_market_share_revenue_percentage,
                    s.seller_units_sold,
                    g.total_market_units_sold,
                    ROUND((s.seller_units_sold / g.total_market_units_sold) * 100, 2) AS seller_market_share_volume_percentage
                FROM SellerPerformance s
                JOIN GlobalPerformance g ON s.category_name = g.category_name
                ORDER BY seller_net_revenue DESC;
            """

        elif insight_type == 'basket_analysis_co_purchase':
            query = f"""
                WITH SellerOrderBaskets AS (
                    SELECT order_id, product_key 
                    FROM {self.base_path}.fact_sales 
                    WHERE seller_key = {sk}
                )
                SELECT 
                    p1.name AS primary_product,
                    p2.name AS co_purchased_product,
                    COUNT(DISTINCT b1.order_id) AS co_purchase_frequency,
                    DENSE_RANK() OVER (PARTITION BY p1.name ORDER BY COUNT(DISTINCT b1.order_id) DESC) as popularity_rank
                FROM SellerOrderBaskets b1
                JOIN SellerOrderBaskets b2 ON b1.order_id = b2.order_id AND b1.product_key < b2.product_key
                INNER JOIN {self.base_path}.dim_product p1 ON b1.product_key = p1.product_key
                INNER JOIN {self.base_path}.dim_product p2 ON b2.product_key = p2.product_key
                GROUP BY p1.name, p2.name
                QUALIFY popularity_rank <= 5
                ORDER BY co_purchase_frequency DESC;
            """

        elif insight_type == 'rfm_customer_segmentation':
            query = f"""
                WITH BaseRFM AS (
                    SELECT 
                        f.customer_key,
                        DATEDIFF(CURRENT_DATE(), MAX(d.full_date)) AS recency_days,
                        COUNT(DISTINCT f.order_id) AS frequency_count,
                        SUM(f.net_revenue) AS total_monetary_value
                    FROM {self.base_path}.fact_sales f
                    INNER JOIN {self.base_path}.dim_date d ON f.date_key = d.date_key
                    WHERE f.seller_key = {sk}
                    GROUP BY f.customer_key
                ),
                RFMTiles AS (
                    SELECT *,
                        NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,
                        NTILE(5) OVER (ORDER BY frequency_count ASC) AS f_score,
                        NTILE(5) OVER (ORDER BY total_monetary_value ASC) AS m_score
                    FROM BaseRFM
                )
                SELECT 
                    customer_key,
                    recency_days,
                    frequency_count,
                    total_monetary_value,
                    (r_score + f_score + m_score) AS aggregated_rfm_score,
                    CASE 
                        WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions / VIP'
                        WHEN r_score >= 3 AND f_score >= 2 THEN 'Loyal Customer Base'
                        WHEN r_score = 1 THEN 'At Risk / Churned'
                        ELSE 'Standard General Shopper'
                    END AS market_segmentation
                FROM RFMTiles
                ORDER BY total_monetary_value DESC;
            """

        elif insight_type == 'geospatial_expansion':
            query = f"""
                SELECT 
                    loc.country,
                    loc.region,
                    loc.city,
                    COUNT(DISTINCT f.order_id) AS absolute_order_count,
                    SUM(f.net_revenue) AS geographic_net_revenue,
                    ROUND(AVG(f.net_revenue), 2) AS avg_basket_spend_by_city,
                    SUM(f.shipping_fee) AS associated_freight_cost,
                    ROUND((SUM(f.net_revenue) / SUM(SUM(f.net_revenue)) OVER()) * 100, 2) AS geographic_revenue_contribution_pct
                FROM {self.base_path}.fact_sales f
                INNER JOIN {self.base_path}.dim_location loc ON f.location_key = loc.location_key
                WHERE f.seller_key = {sk}
                GROUP BY loc.country, loc.region, loc.city
                ORDER BY geographic_net_revenue DESC;
            """

        elif insight_type == 'customer_ratings_reviews':
            query = f'''
                SELECT 
                    r.review_key,
                    r.review_id,
                    r.customer_key,
                    c.name AS customer_name,
                    p.product_id,
                    p.name AS product_name,
                    p.category_name,
                    r.rating AS star_rating,
                    r.review_text,
                    r.review_date,
                    r.verified_purchase,
                    r.helpful_votes,
                    r.total_votes,
                    DATEDIFF(CURRENT_DATE(), r.review_date) AS days_since_review
                FROM {self.base_path}.dim_review r
                INNER JOIN {self.base_path}.dim_product p ON r.product_key = p.product_key
                LEFT JOIN {self.base_path}.dim_customer c ON r.customer_key = c.customer_key
                WHERE p.seller_key = {sk}
                ORDER BY r.review_date DESC;
            '''

        elif insight_type == 'review_sentiment_analysis':
            query = f'''
                SELECT 
                    p.product_id,
                    p.name AS product_name,
                    p.category_name,
                    r.rating AS star_rating,
                    r.review_text,
                    CASE 
                        WHEN r.rating >= 4 THEN 'Positive'
                        WHEN r.rating = 3 THEN 'Neutral'
                        ELSE 'Negative'
                    END AS sentiment_label,
                    CASE 
                        WHEN r.review_text LIKE '%quality%' OR r.review_text LIKE '%defect%' OR r.review_text LIKE '%broke%' THEN 'Product Quality'
                        WHEN r.review_text LIKE '%shipping%' OR r.review_text LIKE '%delivery%' OR r.review_text LIKE '%late%' THEN 'Logistics'
                        WHEN r.review_text LIKE '%price%' OR r.review_text LIKE '%expensive%' OR r.review_text LIKE '%cheap%' THEN 'Pricing'
                        WHEN r.review_text LIKE '%service%' OR r.review_text LIKE '%support%' OR r.review_text LIKE '%help%' THEN 'Customer Service'
                        ELSE 'General'
                    END AS theme_category,
                    r.helpful_votes,
                    r.total_votes,
                    r.review_date,
                    r.verified_purchase
                FROM {self.base_path}.dim_review r
                INNER JOIN {self.base_path}.dim_product p ON r.product_key = p.product_key
                WHERE p.seller_key = {sk} AND r.review_text IS NOT NULL
                ORDER BY r.review_date DESC;
            '''

        else:
            try:
                return self._get_legacy_query(insight_type, sk)
            except ValueError:
                raise ValueError(f"Insight pattern code '{insight_type}' is unknown. Available types: {self.list_insight_types()}")

        return textwrap.dedent(query).strip()

    def _get_legacy_query(self, insight_type: str, sk: int) -> str:
        """Handles routing for original performance queries."""
        if insight_type == 'sales_performance':
            return textwrap.dedent(f"""
                SELECT d.year, d.month_name, COUNT(DISTINCT f.order_id) AS total_orders,
                       SUM(f.quantity_sold) AS total_units_sold, SUM(f.gross_revenue) AS gross_revenue,
                       SUM(f.discount_amount) AS total_discounts_given, SUM(f.net_revenue) AS net_revenue,
                       ROUND((SUM(f.net_revenue) / SUM(f.gross_revenue)) * 100, 2) AS revenue_realization_rate
                FROM {self.base_path}.fact_sales f INNER JOIN {self.base_path}.dim_date d ON f.date_key = d.date_key
                WHERE f.seller_key = {sk} GROUP BY d.year, d.month, d.month_name ORDER BY d.year DESC, d.month DESC;
            """).strip()
        elif insight_type == 'product_profitability':
            return textwrap.dedent(f"""
                SELECT p.product_id, p.name AS product_name, p.category_name, SUM(f.quantity_sold) AS units_sold,
                       SUM(f.net_revenue) AS net_marketplace_sales, SUM(f.net_revenue * (1 - COALESCE(p.commission_rate, 0.0))) AS estimated_seller_takehome,
                       AVG(f.unit_price) AS avg_selling_price
                FROM {self.base_path}.fact_sales f INNER JOIN {self.base_path}.dim_product p ON f.product_key = p.product_key
                WHERE f.seller_key = {sk} AND f.net_revenue > 0 GROUP BY p.product_id, p.name, p.category_name ORDER BY net_marketplace_sales DESC LIMIT 50;
            """).strip()
        elif insight_type == 'return_rate_analysis':
            return textwrap.dedent(f"""
                SELECT p.product_id, p.name AS product_name, COUNT(DISTINCT f.sales_key) AS total_sales_events, COUNT(DISTINCT r.return_key) AS total_returns,
                       ROUND((COUNT(DISTINCT r.return_key) / COUNT(DISTINCT f.sales_key)) * 100, 2) AS return_rate_percentage,
                       SUM(f.net_revenue) AS theoretical_net_revenue, SUM(r.refund_amount) AS total_refunded_cash, SUM(f.shipping_fee) AS sunk_shipping_costs
                FROM {self.base_path}.fact_sales f INNER JOIN {self.base_path}.dim_product p ON f.product_key = p.product_key
                LEFT JOIN {self.base_path}.fact_returns r ON f.order_id = r.order_item_id AND f.product_key = r.product_key
                WHERE f.seller_key = {sk} GROUP BY p.product_id, p.name ORDER BY return_rate_percentage DESC, total_returns DESC;
            """).strip()
        elif insight_type == 'customer_demographics':
            return textwrap.dedent(f"""
                SELECT c.region AS buyer_region, c.age_band, c.gender, COUNT(DISTINCT f.customer_key) AS unique_buyers,
                       COUNT(DISTINCT f.order_id) AS orders_placed, SUM(f.net_revenue) AS lifetime_value_to_seller
                FROM {self.base_path}.fact_sales f INNER JOIN (
                    SELECT cust.*, loc.region, loc.city FROM {self.base_path}.dim_customer cust JOIN {self.base_path}.dim_location loc ON cust.location_key = loc.location_key
                ) c ON f.customer_key = c.customer_key WHERE f.seller_key = {sk} GROUP BY c.region, c.age_band, c.gender ORDER BY lifetime_value_to_seller DESC;
            """).strip()
        elif insight_type == 'shipping_efficiency':
            return textwrap.dedent(f"""
                SELECT l.city AS destination_city, l.region AS destination_region, COUNT(sh.shipment_key) AS total_shipments, AVG(sh.delivery_days) AS avg_days_to_delivery,
                       SUM(CASE WHEN sh.is_on_time = 1 THEN 1 ELSE 0 END) AS on_time_count, ROUND((SUM(CASE WHEN sh.is_on_time = 1 THEN 1 ELSE 0 END) / COUNT(sh.shipment_key)) * 100, 2) AS SLA_compliance_rate
                FROM {self.base_path}.fact_sales f INNER JOIN {self.base_path}.fact_shipments sh ON f.order_id = sh.order_id INNER JOIN {self.base_path}.dim_location l ON sh.location_key = l.location_key
                WHERE f.seller_key = {sk} GROUP BY l.city, l.region ORDER BY SLA_compliance_rate ASC, total_shipments DESC;
            """).strip()
        elif insight_type == 'promotion_roi':
            return textwrap.dedent(f"""
                SELECT p.name AS promo_campaign_name, p.discount_type, p.platform AS marketing_platform, COUNT(DISTINCT f.order_id) AS attributed_orders,
                       SUM(f.quantity_sold) AS units_moved, SUM(f.discount_amount) AS margin_surrendered, SUM(f.net_revenue) AS resulting_net_revenue,
                       ROUND(SUM(f.net_revenue) / NULLIF(SUM(f.discount_amount), 0), 2) AS efficiency_multiplier
                FROM {self.base_path}.fact_sales f INNER JOIN {self.base_path}.dim_promotion p ON f.promotion_key = p.promotion_key
                WHERE f.seller_key = {sk} AND p.promotion_id != 'NO_PROMO' GROUP BY p.name, p.discount_type, p.platform ORDER BY resulting_net_revenue DESC;
            """).strip()
        elif insight_type == 'funnel_and_conversion':
            return textwrap.dedent(f"""
                WITH SellerTraffic AS (
                    SELECT fe.product_key, SUM(CASE WHEN fe.event_type = 'view' THEN 1 ELSE 0 END) AS total_views, SUM(CASE WHEN fe.event_type = 'add_to_cart' THEN 1 ELSE 0 END) AS total_cart_adds
                    FROM {self.base_path}.fact_events fe INNER JOIN {self.base_path}.dim_product p ON fe.product_key = p.product_key WHERE p.seller_key = {sk} GROUP BY fe.product_key
                ), SellerPurchases AS (
                    SELECT f.product_key, COUNT(DISTINCT f.order_id) AS total_purchases FROM {self.base_path}.fact_sales f WHERE f.seller_key = {sk} GROUP BY f.product_key
                )
                SELECT prod.product_id, prod.name AS product_name, COALESCE(t.total_views, 0) AS detail_page_views, COALESCE(t.total_cart_adds, 0) AS cart_additions, COALESCE(p.total_purchases, 0) AS successful_orders,
                       ROUND((COALESCE(p.total_purchases, 0) / NULLIF(COALESCE(t.total_views, 0), 0)) * 100, 2) AS view_to_purchase_conversion_rate
                FROM {self.base_path}.dim_product prod LEFT JOIN SellerTraffic t ON prod.product_key = t.product_key LEFT JOIN SellerPurchases p ON prod.product_key = p.product_key
                WHERE prod.seller_key = {sk} AND (t.total_views > 0 OR p.total_purchases > 0) ORDER BY detail_page_views DESC;
            """).strip()
        elif insight_type == 'customer_satisfaction_drain':
            return textwrap.dedent(f"""
                SELECT p.product_id, p.name AS product_name, AVG(r.rating) AS average_star_rating, COUNT(r.review_key) AS total_reviews_received,
                       SUM(CASE WHEN r.rating <= 2 THEN 1 ELSE 0 END) AS negative_review_count, AVG(sh.delivery_days) AS avg_delivery_days_for_product
                FROM {self.base_path}.dim_review r INNER JOIN {self.base_path}.dim_product p ON r.product_key = p.product_key
                LEFT JOIN {self.base_path}.fact_sales f ON f.product_key = p.product_key AND f.customer_key = r.customer_key LEFT JOIN {self.base_path}.fact_shipments sh ON f.order_id = sh.order_id
                WHERE p.seller_key = {sk} GROUP BY p.product_id, p.name ORDER BY average_star_rating ASC, negative_review_count DESC;
            """).strip()
        else:
            raise ValueError()