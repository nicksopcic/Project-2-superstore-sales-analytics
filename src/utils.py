"""Shared paths and connection helpers. Data-quality checks are added in Phase 2."""

from __future__ import annotations

from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = PROJECT_ROOT / "data" / "raw" / "Sample_Superstore.csv"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DB_PATH = PROJECT_ROOT / "db" / "superstore.duckdb"

DIMENSION_TABLES = ("dim_customer", "dim_product", "dim_geography", "dim_date")
FACT_TABLE = "fact_sales"


def connect(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Open the project database, creating db/ on first use."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(DB_PATH), read_only=read_only)


def table_exists(con: duckdb.DuckDBPyConnection, name: str) -> bool:
    return con.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_name = ?", [name]
    ).fetchone()[0] > 0


def row_count(con: duckdb.DuckDBPyConnection, name: str) -> int:
    return con.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0]
