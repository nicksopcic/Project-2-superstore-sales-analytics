"""Shared fixtures. The star schema is built once per session into a temporary database.

Tests never touch db/superstore.duckdb, so a broken local database cannot make the suite pass
and a test run cannot corrupt work in progress. The raw CSV is committed, so this also means
CI can run the full pipeline with nothing but a checkout.
"""

from __future__ import annotations

import duckdb
import pytest

from src.ingest import build_staging
from src.transform_star_schema import build_star_schema
from src.utils import connect


@pytest.fixture(scope="session")
def con(tmp_path_factory) -> duckdb.DuckDBPyConnection:
    db_path = tmp_path_factory.mktemp("duckdb") / "test_superstore.duckdb"
    with connect(db_path) as connection:
        build_staging(connection)
        build_star_schema(connection)
        yield connection
