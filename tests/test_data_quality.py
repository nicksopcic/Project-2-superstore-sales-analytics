"""Data-quality checks run as tests, so a regression in the source data fails the build."""

from __future__ import annotations

import pytest

from src.data_quality import (
    check_completeness,
    check_exact_duplicate_lines,
    check_measure_ranges,
    check_order_product_pairs,
    check_referential_integrity,
    check_ship_date_not_before_order_date,
    check_unique_row_id,
    loss_making_profile,
)

# Checks that must pass outright. The exact-duplicate check is deliberately excluded:
# it reports a known condition in the source data and is asserted separately below.
BLOCKING_CHECKS = (
    check_unique_row_id,
    check_ship_date_not_before_order_date,
    check_referential_integrity,
    check_measure_ranges,
    check_completeness,
    check_order_product_pairs,
)


@pytest.mark.parametrize("check", BLOCKING_CHECKS, ids=lambda c: c.__name__)
def test_blocking_check_passes(con, check):
    result = check(con)
    assert result.passed, f"{result.name}: {result.detail}"


def test_no_duplicate_row_ids(con):
    assert check_unique_row_id(con).exceptions.empty


def test_every_ship_date_is_on_or_after_its_order_date(con):
    violations = check_ship_date_not_before_order_date(con).exceptions
    assert violations.empty, f"{len(violations)} rows ship before they are ordered"


def test_postal_code_is_the_only_missing_attribute(con):
    result = check_completeness(con)
    missing = con.execute(
        """
        SELECT count(*) FROM fact_sales f
        JOIN dim_geography g USING (geography_key)
        WHERE g.postal_code IS NULL
        """
    ).fetchone()[0]
    assert missing == 11
    assert result.passed


def test_known_exact_duplicate_is_still_present_and_flagged(con):
    """Row 3406 and 3407 are byte-identical. If that changes, the report needs revisiting."""
    result = check_exact_duplicate_lines(con)
    assert not result.passed
    assert len(result.exceptions) == 1
    assert result.exceptions.iloc[0]["order_id"] == "US-2017-150119"
    assert sorted(result.exceptions.iloc[0]["row_ids"]) == [3406, 3407]


def test_split_order_lines_are_not_treated_as_duplicates(con):
    """8 pairs share (order_id, product_key). Only one of them is a true duplicate."""
    repeats = check_order_product_pairs(con).exceptions
    assert len(repeats) == 8
    assert (repeats["lines"] == 2).all()


def test_loss_making_profile_matches_the_source(con):
    profile = loss_making_profile(con)
    assert int(profile["total_lines"]) == 9994
    assert int(profile["loss_lines"]) == 1871
    assert profile["pct_lines"] == pytest.approx(18.72, abs=0.01)
    assert profile["total_sales"] == pytest.approx(2_297_200.86, abs=0.01)
    assert profile["total_profit"] == pytest.approx(286_397.02, abs=0.01)


def test_is_loss_making_agrees_with_profit(con):
    disagreements = con.execute(
        "SELECT count(*) FROM fact_sales WHERE is_loss_making <> (profit < 0)"
    ).fetchone()[0]
    assert disagreements == 0
