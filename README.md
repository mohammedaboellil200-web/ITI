# Tijartek Seller Insights Pro

A unified Streamlit dashboard that connects directly to Databricks SQL Warehouse to deliver real-time, enterprise-grade seller analytics.

## Project Structure

```
tijartek_dashboard/
├── app.py                          # Main entry point (sidebar, seller search, landing page)
├── db_layer.py                     # DatabricksConnectionManager + DatabricksQueryExecutor
├── query_factory.py                # SellerInsightQueryFactory (16 insight modules)
├── data_manager.py                 # Caching layer (@st.cache_data) for warehouse queries
├── components.py                   # Reusable UI helpers (KPI cards, section headers)
├── utils.py                        # Safe data fetching with error handling
├── pages/
│   ├── 1_Store_Overview.py         # Executive KPIs, sales trends, market share, basket analysis
│   ├── 2_Sales_Financials.py       # Promotion ROI, payment friction, conversion funnel
│   ├── 3_Inventory_Logistics.py    # Stock velocity, shipping SLA, returns, satisfaction
│   └── 4_Customer_Insights.py      # Demographics, RFM segmentation, retention, geography
├── requirements.txt
└── .env.example
```

## Architecture

| Layer | Responsibility |
|-------|----------------|
| **Presentation** | Streamlit multipage app (`app.py` + `pages/`) |
| **Components** | Shared KPI rows, chart containers, layout helpers |
| **Data Manager** | Cached bridge between UI and DB layer (`@st.cache_data`) |
| **Query Factory** | Type-safe SQL generation for 16 insight patterns |
| **DB Layer** | Connection pooling, parameterized seller lookup, DataFrame conversion |

## Quick Start

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your Databricks credentials
   ```

3. **Launch the app**
   ```bash
   streamlit run app.py
   ```

4. **Search for a seller** in the sidebar, then navigate through the insight modules.

## Key Features

- **Parameterized SQL**: Seller lookup uses `?` placeholders to prevent injection.
- **Smart Caching**: All warehouse queries are cached for 5 minutes via `data_manager.py`.
- **Combined Search**: Supports `Name | ID`, `Name, ID`, or `Name and ID` syntax in seller lookup.
- **16 Insight Modules**: From executive KPIs to RFM segmentation and geospatial expansion.
- **Consistent UX**: Every page follows the same KPI-row → 2×2 chart grid layout from the original `strim.py` design.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABRICKS_SERVER_HOSTNAME` | Databricks workspace host |
| `DATABRICKS_HTTP_PATH` | SQL warehouse HTTP path |
| `DATABRICKS_ACCESS_TOKEN` | Personal access token |
