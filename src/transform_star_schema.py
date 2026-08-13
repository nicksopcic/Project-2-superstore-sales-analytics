"""Build the star schema from stg_orders: four dimensions and fact_sales.

Every dimension uses an integer surrogate key rather than its natural key, because none of
the three candidate natural keys in this dataset is actually unique:

  Product ID     32 IDs are reused for two different product names (337 rows).
  Postal Code    92024 covers both San Diego and Encinitas, and 11 rows have no postal code.
  Customer ID    unique here, given a surrogate key for consistency with the other dimensions.

dim_date is a contiguous daily calendar spanning the earliest order date to the latest ship
date, not just the 1,236 dates that appear as order dates. A gapless spine keeps the running
YTD and month-over-month queries in Phase 4 honest about periods with no orders.

Run with: python -m src.transform_star_schema (after python -m src.ingest)
"""

from __future__ import annotations

import duckdb

from src.utils import DIMENSION_TABLES, FACT_TABLE, connect, row_count, table_exists

DIM_CUSTOMER = """
CREATE OR REPLACE TABLE dim_customer AS
SELECT
    ROW_NUMBER() OVER (ORDER BY customer_id) AS customer_key,
    customer_id,
    customer_name,
    segment
FROM (
    SELECT DISTINCT
        "Customer ID"   AS customer_id,
        "Customer Name" AS customer_name,
        "Segment"       AS segment
    FROM stg_orders
)
"""

DIM_PRODUCT = """
CREATE OR REPLACE TABLE dim_product AS
SELECT
    ROW_NUMBER() OVER (ORDER BY product_id, product_name) AS product_key,
    product_id,
    category,
    sub_category,
    product_name
FROM (
    SELECT DISTINCT
        "Product ID"   AS product_id,
        "Category"     AS category,
        "Sub-Category" AS sub_category,
        "Product Name" AS product_name
    FROM stg_orders
)
"""

DIM_GEOGRAPHY = """
CREATE OR REPLACE TABLE dim_geography AS
SELECT
    ROW_NUMBER() OVER (ORDER BY country, state, city, postal_code NULLS LAST) AS geography_key,
    country,
    city,
    state,
    postal_code,
    region
FROM (
    SELECT DISTINCT
        "Country"     AS country,
        "City"        AS city,
        "State"       AS state,
        "Postal Code" AS postal_code,
        "Region"      AS region
    FROM stg_orders
)
"""

DIM_DATE = """
CREATE OR REPLACE TABLE dim_date AS
WITH bounds AS (
    SELECT min("Order Date") AS first_day, max("Ship Date") AS last_day FROM stg_orders
),
calendar AS (
    SELECT CAST(UNNEST(generate_series(first_day, last_day, INTERVAL 1 DAY)) AS DATE) AS full_date
    FROM bounds
)
SELECT
    CAST(strftime(full_date, '%Y%m%d') AS INTEGER) AS date_key,
    full_date,
    YEAR(full_date)                    AS year,
    QUARTER(full_date)                 AS quarter,
    MONTH(full_date)                   AS month,
    monthname(full_date)               AS month_name,
    CAST(strftime(full_date, '%Y-%m') AS VARCHAR) AS year_month,
    DAY(full_date)                     AS day_of_month,
    dayofweek(full_date)               AS day_of_week,
    dayname(full_date)                 AS day_name,
    dayofweek(full_date) IN (0, 6)     AS is_weekend
FROM calendar
"""

# The joins are inner joins on purpose. Every dimension is derived from stg_orders itself,
# so an unmatched row would mean the transform is wrong, and the row count check below
# turns that into a failure rather than a silently short fact table. Postal Code is matched
# with IS NOT DISTINCT FROM so the 11 null-postal-code rows join instead of dropping out.
FACT_SALES = """
CREATE OR REPLACE TABLE fact_sales AS
SELECT
    s."Row ID"    AS row_id,
    s."Order ID"  AS order_id,
    s."Order Date" AS order_date,
    s."Ship Date"  AS ship_date,
    s."Ship Mode"  AS ship_mode,
    c.customer_key,
    p.product_key,
    g.geography_key,
    od.date_key   AS order_date_key,
    sd.date_key   AS ship_date_key,
    s."Sales"     AS sales,
    s."Quantity"  AS quantity,
    s."Discount"  AS discount,
    s."Profit"    AS profit
FROM stg_orders s
JOIN dim_customer c
    ON s."Customer ID" = c.customer_id
JOIN dim_product p
    ON s."Product ID" = p.product_id
   AND s."Product Name" = p.product_name
JOIN dim_geography g
    ON s."Country" = g.country
   AND s."City" = g.city
   AND s."State" = g.state
   AND s."Postal Code" IS NOT DISTINCT FROM g.postal_code
   AND s."Region" = g.region
JOIN dim_date od
    ON s."Order Date" = od.full_date
JOIN dim_date sd
    ON s."Ship Date" = sd.full_date
"""


def build_star_schema(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    """Rebuild all dimensions and the fact table. Returns row counts by table."""
    if not table_exists(con, "stg_orders"):
        raise RuntimeError("stg_orders is missing. Run python -m src.ingest first.")

    for statement in (DIM_CUSTOMER, DIM_PRODUCT, DIM_GEOGRAPHY, DIM_DATE, FACT_SALES):
        con.execute(statement)

    staged = row_count(con, "stg_orders")
    fact = row_count(con, FACT_TABLE)
    if fact != staged:
        raise RuntimeError(
            f"fact_sales has {fact:,} rows against {staged:,} staged rows. "
            "A dimension join is either dropping rows or fanning them out."
        )

    return {name: row_count(con, name) for name in (*DIMENSION_TABLES, FACT_TABLE)}


def main() -> None:
    with connect() as con:
        counts = build_star_schema(con)
        measures = con.execute(
            "SELECT sum(sales), sum(profit), sum(quantity) FROM fact_sales"
        ).fetchone()

    for name, count in counts.items():
        print(f"{name:<15} {count:>7,} rows")
    print(f"\nfact_sales totals: sales {measures[0]:,.2f}, profit {measures[1]:,.2f}, "
          f"quantity {measures[2]:,}")


if __name__ == "__main__":
    main()
