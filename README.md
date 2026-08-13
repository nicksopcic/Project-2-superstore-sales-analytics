# US Superstore Sales & Sales Operations Analytics

A sales-operations analytics and reporting layer built on the Sample Superstore dataset:
a DuckDB star schema, a SQL analysis suite, Python profitability and forecasting modules,
and a Streamlit dashboard.

**Guiding business question:** Which regions, segments, and product categories are profitable
to discount, and where is discounting quietly destroying margin?

## Dataset

`data/raw/Sample_Superstore.csv` — a single flat table of 9,994 US retail order-line records
covering customer, product, geography, sales, quantity, discount, and profit fields.
Orders span **2017-01-03 to 2020-12-30**; ship dates run through 2021-01-05.

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

### Provenance

Extracted from the `Orders` sheet of the Tableau Desktop 2020.4 sample workbook
(`Sample - Superstore.xls`) with `pandas.read_excel`. Two normalizations were applied and nothing
else — measures, dates, and text round-trip exactly against the source:

- `Country/Region` renamed to `Country`, matching the `dim_geography` column naming.
- `Postal Code` written as an integer rather than the float pandas infers from the 11 blank values
  (all Burlington, Vermont). Those 11 blanks are preserved as empty, not imputed.

The workbook's `People` (4 rows: regional manager by region) and `Returns` (800 rows: returned
order IDs) sheets were not exported — no phase of the analysis uses them.

Note that this 2020.4 edition dates orders 2017–2020, whereas the older, more commonly cited
version of Superstore covers 2014–2017. Any comparison to published figures from that version
will differ on absolute dates, though the row count and measures are the same.

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
