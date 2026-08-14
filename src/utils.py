"""Shared paths, database helpers, and Markdown rendering used across the pipeline.

Data-quality checks live in src/data_quality.py. SQL report execution lives in
src/run_sql_report.py. This module holds only what more than one of them needs.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = PROJECT_ROOT / "data" / "raw" / "Sample_Superstore.csv"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DB_PATH = PROJECT_ROOT / "db" / "superstore.duckdb"
SQL_DIR = PROJECT_ROOT / "sql"
REPORTS_DIR = PROJECT_ROOT / "reports"

DIMENSION_TABLES = ("dim_customer", "dim_product", "dim_geography", "dim_date")
FACT_TABLE = "fact_sales"
EXPORT_TABLES = (FACT_TABLE, *DIMENSION_TABLES)


def connect(db_path: Path | None = None, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Open a project database, creating its parent directory on first use."""
    target = Path(db_path) if db_path is not None else DB_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(target), read_only=read_only)


def table_exists(con: duckdb.DuckDBPyConnection, name: str) -> bool:
    return con.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_name = ?", [name]
    ).fetchone()[0] > 0


def row_count(con: duckdb.DuckDBPyConnection, name: str) -> int:
    return con.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0]


def require_star_schema(con: duckdb.DuckDBPyConnection) -> None:
    """Fail with a useful message rather than a bare SQL error on a missing table."""
    missing = [t for t in EXPORT_TABLES if not table_exists(con, t)]
    if missing:
        raise RuntimeError(
            f"Missing {', '.join(missing)}. Run python -m src.ingest then "
            "python -m src.transform_star_schema first."
        )


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


# Counts read better with thousands separators, but years and identifiers do not: a year
# rendered as "2,017" is just wrong. Columns named here, or ending in _key or _id, print raw.
UNSEPARATED_COLUMNS = frozenset(
    {"year", "month", "quarter", "day_of_month", "day_of_week", "postal_code", "date_key"}
)


def _prints_raw(column: str | None) -> bool:
    return column is not None and (
        column in UNSEPARATED_COLUMNS or column.endswith(("_key", "_id"))
    )


def format_cell(value: object, column: str | None = None) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return pd.Timestamp(value).strftime("%Y-%m-%d")
    if isinstance(value, (list, tuple, np.ndarray)):
        # Identifiers, so no thousands separators.
        return ", ".join(str(v) for v in value)
    if isinstance(value, (bool, np.bool_)):
        return "yes" if value else "no"
    if isinstance(value, (float, np.floating)):
        if value == 0:
            return "0"
        # Rates and proportions live below 1, where two decimals would erase the detail
        # the query rounded to. Trailing zeros are stripped so 0.70 reads as 0.7.
        if abs(value) < 1:
            return f"{value:.4f}".rstrip("0")
        return f"{value:,.2f}"
    if isinstance(value, (int, np.integer)):
        return str(value) if _prints_raw(column) else f"{value:,}"
    return str(value).replace("|", "\\|")


def markdown_table(df: pd.DataFrame, limit: int = 12) -> str:
    """Render a DataFrame as a Markdown table. Hand-rolled to avoid a tabulate dependency."""
    if df.empty:
        return "_No rows._\n"

    shown = df.head(limit)
    columns = [str(c) for c in shown.columns]
    numeric = {c for c in shown.columns if pd.api.types.is_numeric_dtype(shown[c])}
    header = "| " + " | ".join(columns) + " |"
    rule = "| " + " | ".join("---:" if c in numeric else "---" for c in shown.columns) + " |"
    rows = [
        "| " + " | ".join(format_cell(v, c) for c, v in zip(columns, record)) + " |"
        for record in shown.itertuples(index=False, name=None)
    ]
    body = "\n".join([header, rule, *rows])
    if len(df) > limit:
        body += f"\n\n_Showing {limit} of {len(df):,} rows._"
    return body + "\n"
