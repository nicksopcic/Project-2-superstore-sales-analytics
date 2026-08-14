"""Tests for the SQL suites and the runner that executes them.

Every tagged query is run against the star schema, so a syntax error or a renamed column
fails the build instead of surfacing as a broken report.
"""

from __future__ import annotations

import pytest

from src.run_sql_report import SUITES, Query, build_report, parse_queries, run_query
from src.utils import SQL_DIR

FUNDAMENTAL_SQL = SQL_DIR / SUITES["fundamental"][0]
MINIMUM_FUNDAMENTAL_QUERIES = 8


def fundamental_queries() -> list[Query]:
    return parse_queries(FUNDAMENTAL_SQL.read_text(encoding="utf-8"))


def test_suite_meets_the_minimum_query_count():
    assert len(fundamental_queries()) >= MINIMUM_FUNDAMENTAL_QUERIES


def test_every_query_has_a_business_question():
    missing = [q.name for q in fundamental_queries() if not q.question]
    assert not missing, f"queries without a stated business question: {missing}"


def test_query_names_are_unique():
    names = [q.name for q in fundamental_queries()]
    assert len(names) == len(set(names))


def test_the_four_planned_topics_are_covered():
    """Phase 3 asks for region, segment and category rollups, top and bottom sub-categories,
    a year and month trend, and average discount by category and sub-category."""
    names = {q.name for q in fundamental_queries()}
    for required in (
        "sales_profit_margin_by_region",
        "sales_profit_margin_by_segment",
        "sales_profit_margin_by_category",
        "top_10_sub_categories_by_profit",
        "bottom_10_sub_categories_by_profit",
        "sales_profit_by_year",
        "sales_profit_by_month",
        "avg_discount_by_category",
        "avg_discount_by_sub_category",
    ):
        assert required in names


@pytest.mark.parametrize("query", fundamental_queries(), ids=lambda q: q.name)
def test_query_runs_and_returns_rows(con, query):
    result = run_query(con, query)
    assert not result.empty, f"{query.name} returned no rows"


def test_top_and_bottom_sub_category_queries_return_ten_rows(con):
    by_name = {q.name: q for q in fundamental_queries()}
    for name in ("top_10_sub_categories_by_profit", "bottom_10_sub_categories_by_profit"):
        assert len(run_query(con, by_name[name])) == 10


def test_region_totals_reconcile_with_the_fact_table(con):
    by_name = {q.name: q for q in fundamental_queries()}
    regions = run_query(con, by_name["sales_profit_margin_by_region"])
    fact_total = con.execute("SELECT sum(sales), sum(profit) FROM fact_sales").fetchone()

    assert regions["sales"].sum() == pytest.approx(fact_total[0], abs=0.05)
    assert regions["profit"].sum() == pytest.approx(fact_total[1], abs=0.05)


def test_discount_bands_cover_every_line(con):
    by_name = {q.name: q for q in fundamental_queries()}
    bands = run_query(con, by_name["margin_by_discount_band"])
    assert bands["order_lines"].sum() == 9994


def test_margin_turns_negative_above_a_twenty_percent_discount(con):
    """The central finding of the project. If this stops holding, the narrative changes."""
    by_name = {q.name: q for q in fundamental_queries()}
    bands = run_query(con, by_name["margin_by_discount_band"]).set_index("discount_band")

    assert bands.loc["0%", "margin_pct"] > 0
    assert bands.loc["11-20%", "margin_pct"] > 0
    assert bands.loc["21-30%", "margin_pct"] < 0
    assert bands.loc["41%+", "margin_pct"] < 0


def test_parser_ignores_the_file_preamble():
    parsed = parse_queries(
        """
        -- A file header that is not a query.
        -- Another preamble line.

        -- name: first
        -- The question.
        SELECT 1 AS a;

        -- name: second
        -- Another question.
        SELECT 2 AS b;
        """
    )
    assert [q.name for q in parsed] == ["first", "second"]
    assert parsed[0].question == "The question."
    assert parsed[0].sql == "SELECT 1 AS a"


def test_parser_keeps_inline_comments_inside_the_statement():
    parsed = parse_queries(
        """
        -- name: only
        -- The question.
        SELECT
            1 AS a,  -- an inline note
            2 AS b;
        """
    )
    assert parsed[0].question == "The question."
    assert "an inline note" in parsed[0].sql


def test_report_renders_every_query(con, tmp_path, monkeypatch):
    monkeypatch.setattr("src.run_sql_report.REPORTS_DIR", tmp_path)
    queries = fundamental_queries()
    report = build_report(con, queries, "Test title", "02_fundamental_queries.sql")

    assert report.startswith("# Test title")
    for query in queries:
        assert f"## {query.title}" in report
        assert query.sql in report
