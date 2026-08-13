"""Load data/raw/Sample_Superstore.csv into DuckDB as stg_orders.

Staging keeps the source column names and shape untouched so the raw file stays traceable.
Renaming to snake_case happens in the star schema transform.

Run with: python -m src.ingest
"""

from __future__ import annotations

import duckdb

from src.utils import DB_PATH, RAW_CSV, connect, row_count

EXPECTED_ROWS = 9_994

# Declared explicitly rather than left to type inference, so a change in the source file
# fails loudly here instead of shifting a type somewhere downstream. Postal Code is
# INTEGER and nullable: 11 Burlington, Vermont rows have no postal code.
STAGING_COLUMNS = {
    "Row ID": "INTEGER",
    "Order ID": "VARCHAR",
    "Order Date": "DATE",
    "Ship Date": "DATE",
    "Ship Mode": "VARCHAR",
    "Customer ID": "VARCHAR",
    "Customer Name": "VARCHAR",
    "Segment": "VARCHAR",
    "Country": "VARCHAR",
    "City": "VARCHAR",
    "State": "VARCHAR",
    "Postal Code": "INTEGER",
    "Region": "VARCHAR",
    "Product ID": "VARCHAR",
    "Category": "VARCHAR",
    "Sub-Category": "VARCHAR",
    "Product Name": "VARCHAR",
    "Sales": "DOUBLE",
    "Quantity": "INTEGER",
    "Discount": "DOUBLE",
    "Profit": "DOUBLE",
}


def build_staging(con: duckdb.DuckDBPyConnection) -> int:
    """Replace stg_orders from the raw CSV. Returns the row count loaded."""
    if not RAW_CSV.exists():
        raise FileNotFoundError(
            f"Raw dataset not found at {RAW_CSV}. See the Provenance section of the README."
        )

    column_spec = ", ".join(f"'{name}': '{dtype}'" for name, dtype in STAGING_COLUMNS.items())
    con.execute("DROP TABLE IF EXISTS stg_orders")
    con.execute(
        f"""
        CREATE TABLE stg_orders AS
        SELECT * FROM read_csv(
            ?,
            header = true,
            dateformat = '%Y-%m-%d',
            columns = {{{column_spec}}}
        )
        """,
        [str(RAW_CSV)],
    )
    return row_count(con, "stg_orders")


def main() -> None:
    with connect() as con:
        loaded = build_staging(con)
        first, last = con.execute(
            'SELECT min("Order Date"), max("Order Date") FROM stg_orders'
        ).fetchone()

    print(f"stg_orders: {loaded:,} rows loaded into {DB_PATH}")
    print(f"order dates: {first} to {last}")
    if loaded != EXPECTED_ROWS:
        print(f"WARNING: expected {EXPECTED_ROWS:,} rows, the source file may have changed")


if __name__ == "__main__":
    main()
