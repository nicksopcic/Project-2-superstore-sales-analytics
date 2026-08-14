"""Tests for the SQL suites and the runner that executes them.

Every tagged query is run against the star schema, so a syntax error or a renamed column
fails the build instead of surfacing as a broken report.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.run_sql_report import SUITES, Query, build_report, parse_queries, run_query
from src.utils import SQL_DIR

FUNDAMENTAL_SQL = SQL_DIR / SUITES["fundamental"][0]
ADVANCED_SQL = SQL_DIR / SUITES["advanced"][0]
MINIMUM_FUNDAMENTAL_QUERIES = 8


def queries_in(path) -> list[Query]:
    return parse_queries(path.read_text(encoding="utf-8"))


def fundamental_queries() -> list[Query]:
    return queries_in(FUNDAMENTAL_SQL)


def advanced_queries() -> list[Query]:
    return queries_in(ADVANCED_SQL)


def advanced_by_name() -> dict[str, Query]:
    return {q.name: q for q in advanced_queries()}


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


@pytest.mark.parametrize(
    "query", fundamental_queries() + advanced_queries(), ids=lambda q: q.name
)
def test_query_runs_and_returns_rows(con, query):
    result = run_query(con, query)
    assert not result.empty, f"{query.name} returned no rows"


# ---------------------------------------------------------------------------
# Advanced suite
# ---------------------------------------------------------------------------


def test_advanced_suite_covers_the_four_planned_queries():
    """Phase 4 asks for running YTD by region, sub-category rank within region,
    month-over-month growth, and a customer lifetime CTE."""
    names = set(advanced_by_name())
    for required in (
        "running_ytd_sales_by_region",
        "sub_category_profit_rank_by_region",
        "month_over_month_sales_growth",
        "month_over_month_sales_growth_by_region",
        "customer_lifetime_value",
    ):
        assert required in names


def test_every_advanced_query_has_a_business_question():
    missing = [q.name for q in advanced_queries() if not q.question]
    assert not missing, f"queries without a stated business question: {missing}"


def test_ytd_sales_accumulate_within_each_region_and_year(con):
    ytd = run_query(con, advanced_by_name()["running_ytd_sales_by_region"])
    ytd["year"] = ytd["year_month"].str.slice(0, 4)

    for (region, year), group in ytd.groupby(["region", "year"]):
        running = group.sort_values("year_month")["ytd_sales"]
        assert running.is_monotonic_increasing, f"{region} {year} YTD is not monotonic"
        assert running.iloc[-1] == pytest.approx(
            group["month_sales"].sum(), abs=0.05
        ), f"{region} {year} YTD does not close on the sum of its months"


def test_ytd_resets_each_january(con):
    ytd = run_query(con, advanced_by_name()["running_ytd_sales_by_region"])
    januaries = ytd[ytd["year_month"].str.endswith("-01")]
    assert not januaries.empty
    for row in januaries.itertuples():
        assert row.ytd_sales == pytest.approx(row.month_sales, abs=0.05)


def test_sub_category_rank_runs_one_to_seventeen_in_every_region(con):
    ranked = run_query(con, advanced_by_name()["sub_category_profit_rank_by_region"])
    for region, group in ranked.groupby("region"):
        assert sorted(group["profit_rank"]) == list(range(1, 18))
        best = group.loc[group["profit_rank"] == 1, "profit"].iloc[0]
        assert best == group["profit"].max()


def test_month_over_month_growth_has_no_prior_month_on_the_first_row(con):
    growth = run_query(con, advanced_by_name()["month_over_month_sales_growth"])
    first = growth.sort_values("year_month").iloc[0]
    assert pd.isna(first["prior_month_sales"])
    assert pd.isna(first["sales_growth_pct"])


def test_month_over_month_growth_matches_a_hand_calculation(con):
    growth = run_query(con, advanced_by_name()["month_over_month_sales_growth"]).sort_values(
        "year_month"
    )
    second = growth.iloc[1]
    expected = 100.0 * (second["sales"] - growth.iloc[0]["sales"]) / growth.iloc[0]["sales"]
    assert second["sales_growth_pct"] == pytest.approx(expected, abs=0.1)


def test_customer_lifetime_covers_every_customer(con):
    lifetime = run_query(con, advanced_by_name()["customer_lifetime_value"])
    assert len(lifetime) == 793
    assert lifetime["lifetime_profit"].sum() == pytest.approx(286_397.02, abs=0.5)
    assert lifetime["orders"].sum() == con.execute(
        "SELECT count(DISTINCT order_id || '|' || customer_key) FROM fact_sales"
    ).fetchone()[0]


def test_pareto_closes_on_one_hundred_percent(con):
    pareto = run_query(con, advanced_by_name()["customer_profit_pareto"])
    last = pareto.sort_values("profit_rank").iloc[-1]
    assert last["pct_of_customers"] == pytest.approx(100.0, abs=0.1)
    assert last["pct_of_total_profit"] == pytest.approx(100.0, abs=0.1)


def test_profit_is_concentrated_in_a_minority_of_customers(con):
    """The Pareto claim the findings will make. Top fifth of customers, four fifths of profit."""
    pareto = run_query(con, advanced_by_name()["customer_profit_pareto"])
    top_fifth = pareto[pareto["pct_of_customers"] <= 20].tail(1).iloc[0]
    assert top_fifth["pct_of_total_profit"] > 75


def test_loss_making_customers_all_have_negative_lifetime_profit(con):
    losers = run_query(con, advanced_by_name()["loss_making_customers"])
    assert (losers["lifetime_profit"] < 0).all()
    assert len(losers) == 155


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
