"""Pipeline tests: the staging load, the star schema shape, and the Parquet export."""

from __future__ import annotations

import pytest

from src.data_quality import export_processed_tables
from src.ingest import EXPECTED_ROWS, STAGING_COLUMNS
from src.transform_star_schema import build_star_schema
from src.utils import DIMENSION_TABLES, FACT_TABLE, row_count

EXPECTED_COUNTS = {
    "dim_customer": 793,
    "dim_product": 1894,
    "dim_geography": 632,
    "dim_date": 1464,
    "fact_sales": 9994,
}


def test_staging_loads_every_source_row(con):
    assert row_count(con, "stg_orders") == EXPECTED_ROWS


def test_staging_keeps_the_source_columns(con):
    columns = [row[0] for row in con.execute("DESCRIBE stg_orders").fetchall()]
    assert columns == list(STAGING_COLUMNS)


def test_staging_parses_dates_as_dates(con):
    types = {row[0]: row[1] for row in con.execute("DESCRIBE stg_orders").fetchall()}
    assert types["Order Date"] == "DATE"
    assert types["Ship Date"] == "DATE"


@pytest.mark.parametrize("table,expected", EXPECTED_COUNTS.items())
def test_table_row_counts(con, table, expected):
    assert row_count(con, table) == expected


def test_fact_grain_matches_staging(con):
    assert row_count(con, FACT_TABLE) == row_count(con, "stg_orders")


@pytest.mark.parametrize("table", DIMENSION_TABLES)
def test_surrogate_keys_are_unique(con, table):
    key = "date_key" if table == "dim_date" else f"{table.removeprefix('dim_')}_key"
    duplicates = con.execute(
        f"SELECT count(*) - count(DISTINCT {key}) FROM {table}"
    ).fetchone()[0]
    assert duplicates == 0


def test_measures_survive_the_transform(con):
    drift = con.execute(
        """
        SELECT round(abs((SELECT sum(sales) FROM fact_sales)
                       - (SELECT sum("Sales") FROM stg_orders)), 6),
               round(abs((SELECT sum(profit) FROM fact_sales)
                       - (SELECT sum("Profit") FROM stg_orders)), 6)
        """
    ).fetchone()
    assert drift == (0, 0)


def test_dim_date_is_a_contiguous_calendar(con):
    gaps = con.execute(
        "SELECT (max(full_date) - min(full_date) + 1) - count(*) FROM dim_date"
    ).fetchone()[0]
    assert gaps == 0


def test_dim_date_covers_every_order_and_ship_date(con):
    unmatched = con.execute(
        """
        SELECT count(*) FROM fact_sales f
        LEFT JOIN dim_date o ON f.order_date_key = o.date_key
        LEFT JOIN dim_date s ON f.ship_date_key = s.date_key
        WHERE o.date_key IS NULL OR s.date_key IS NULL
        """
    ).fetchone()[0]
    assert unmatched == 0


def test_reused_product_ids_get_separate_product_keys(con):
    """32 Product IDs cover two products each, which is why product_key exists."""
    reused = con.execute(
        """
        SELECT count(*) FROM (
            SELECT product_id FROM dim_product
            GROUP BY product_id HAVING count(*) > 1
        )
        """
    ).fetchone()[0]
    assert reused == 32


def test_rows_without_a_postal_code_still_join_to_geography(con):
    matched = con.execute(
        """
        SELECT count(*) FROM fact_sales f
        JOIN dim_geography g USING (geography_key)
        WHERE g.postal_code IS NULL
        """
    ).fetchone()[0]
    assert matched == 11


def test_transform_is_idempotent(con):
    before = {t: row_count(con, t) for t in EXPECTED_COUNTS}
    build_star_schema(con)
    assert {t: row_count(con, t) for t in EXPECTED_COUNTS} == before


def test_parquet_export_round_trips(con, tmp_path, monkeypatch):
    monkeypatch.setattr("src.data_quality.PROCESSED_DIR", tmp_path)
    written = export_processed_tables(con)

    assert set(written) == {f"{t}.parquet" for t in (FACT_TABLE, *DIMENSION_TABLES)}
    for name in written:
        assert (tmp_path / name).stat().st_size > 0

    fact_file = str(tmp_path / "fact_sales.parquet").replace("\\", "/")
    exported_rows = con.execute(f"SELECT count(*) FROM read_parquet('{fact_file}')").fetchone()[0]
    assert exported_rows == EXPECTED_COUNTS["fact_sales"]
