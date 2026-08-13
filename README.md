# US Superstore Sales & Sales Operations Analytics

A sales-operations analytics and reporting layer built on the Sample Superstore dataset:
a DuckDB star schema, a SQL analysis suite, Python profitability and forecasting modules,
and a Streamlit dashboard.

**Guiding business question:** Which regions, segments, and product categories are profitable
to discount, and where is discounting quietly destroying margin?

## Dataset

`data/raw/Sample_Superstore.csv` — a single flat table of ~9,994 US retail order-line records
covering customer, product, geography, sales, quantity, discount, and profit fields.

| Field group | Columns |
| --- | --- |
| Order | Row ID, Order ID, Order Date, Ship Date, Ship Mode |
| Customer | Customer ID, Customer Name, Segment |
| Geography | Country, City, State, Postal Code, Region |
| Product | Product ID, Category, Sub-Category, Product Name |
| Measures | Sales, Quantity, Discount, Profit |

This is the widely-distributed Tableau/community "Sample - Superstore" dataset, used here for
demonstration and portfolio purposes. It is **not** proprietary company data, and no finding in
this repository describes a real business.

## How to run

> Placeholder — expanded as each phase lands.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Then (once the pipeline exists):

```bash
python -m src.ingest                  # load the raw CSV into db/superstore.duckdb
python -m src.transform_star_schema   # build fact_sales + dimension tables
pytest -q                             # data-quality and pipeline checks
streamlit run app/streamlit_app.py    # dashboard
```

## Data model

> Placeholder — a Mermaid ERD of `fact_sales` and the four dimensions is added in Phase 1.

## Key findings

> Placeholder — populated with real numbers once the analysis runs.

## Repository layout

| Path | Contents |
| --- | --- |
| `data/raw/` | Source CSV (committed) |
| `data/processed/` | Cleaned star-schema Parquet outputs (gitignored) |
| `db/` | Local DuckDB database (gitignored) |
| `sql/` | Schema, fundamental queries, advanced queries, views |
| `src/` | Ingest, transform, profitability, forecasting, utilities |
| `notebooks/` | EDA, discount/profit, Pareto/CLV, forecasting |
| `app/` | Streamlit dashboard |
| `tests/` | Data-quality and pipeline tests |
| `reports/` | Findings write-up and figures |
