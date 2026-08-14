"""Tests for the analysis layer: profitability statistics, forecasting, and the dashboard.

The dashboard is tested through its data functions rather than its widgets. `apply_filters`
and `kpis` are plain pandas, so they can be checked without a Streamlit runtime, and they are
the parts that would silently produce a wrong number.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src import forecasting as fc
from src import profitability as prof
from src.utils import load_analysis_frame

pytest.importorskip("statsmodels")


@pytest.fixture(scope="module")
def frame() -> pd.DataFrame:
    return prof.prepare()


# ---------------------------------------------------------------------------
# Analysis frame
# ---------------------------------------------------------------------------


def test_analysis_frame_does_not_fan_out():
    """Joining the dimensions back on must not multiply rows. The merges assert this too."""
    assert len(load_analysis_frame()) == 9994


def test_analysis_frame_totals_match_the_fact_table():
    flat = load_analysis_frame()
    assert flat["sales"].sum() == pytest.approx(2_297_200.86, abs=0.05)
    assert flat["profit"].sum() == pytest.approx(286_397.02, abs=0.05)


def test_duckdb_and_parquet_sources_agree():
    from_parquet = load_analysis_frame("parquet")
    from_duckdb = load_analysis_frame("duckdb")
    assert len(from_parquet) == len(from_duckdb)
    assert from_parquet["sales"].sum() == pytest.approx(from_duckdb["sales"].sum(), abs=0.01)


# ---------------------------------------------------------------------------
# Profitability
# ---------------------------------------------------------------------------


def test_discount_tiers_cover_every_line(frame):
    assert frame["discount_tier"].notna().all()
    assert frame.groupby("discount_tier", observed=True).size().sum() == 9994


def test_zero_discount_lines_land_in_the_zero_tier(frame):
    zero = frame[frame["discount"] == 0]
    assert (zero["discount_tier"] == "0%").all()


def test_margin_model_finds_a_significant_negative_discount_effect(frame):
    model = prof.fit_margin_model(frame)
    assert model.params["discount"] < 0
    assert model.pvalues["discount"] < 0.001
    assert model.rsquared_adj > 0.5


def test_margin_model_explains_more_than_the_dollar_profit_model(frame):
    """The methodological claim the notebook makes. Margin is the better response variable."""
    margin_model = prof.fit_margin_model(frame)
    profit_model = prof.fit_profit_model(frame)
    assert margin_model.rsquared_adj > profit_model.rsquared_adj


def test_both_tier_tests_reject_the_null(frame):
    tests = prof.test_discount_tiers(frame)
    assert tests.anova_p < 0.001
    assert tests.kruskal_p < 0.001
    assert len(tests.groups) == 5


def test_tier_margins_fall_as_discount_rises(frame):
    """Not strictly monotonic: the 94-line 1-10% tier is noise. The cliff is what matters."""
    tiers = prof.tier_summary(frame).set_index("discount_tier")
    assert tiers.loc["0%", "mean_margin_pct"] > tiers.loc["11-20%", "mean_margin_pct"]
    assert tiers.loc["11-20%", "mean_margin_pct"] > 0
    assert tiers.loc["21-30%", "mean_margin_pct"] < 0
    assert tiers.loc["30%+", "mean_margin_pct"] < tiers.loc["21-30%", "mean_margin_pct"]


def test_breakeven_covers_every_sub_category(frame):
    breakeven = prof.breakeven_by_sub_category(frame)
    assert len(breakeven) == 17
    assert breakeven["note"].notna().all()


def test_over_discounted_lines_are_sold_past_their_breakeven(frame):
    over = prof.over_discounted_sub_categories(frame)
    assert not over.empty
    assert (over["avg_discount"] > over["breakeven_discount"]).all()
    assert "Tables" in set(over["sub_category"])


def test_breakeven_is_a_rate_between_zero_and_one(frame):
    breakeven = prof.breakeven_by_sub_category(frame).dropna(subset=["breakeven_discount"])
    assert breakeven["breakeven_discount"].between(0, 1).all()


# ---------------------------------------------------------------------------
# Forecasting
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def series() -> pd.Series:
    return fc.monthly_sales()


def test_monthly_series_is_a_gapless_monthly_index(series):
    assert len(series) == 48
    assert (series.index == pd.date_range(series.index[0], periods=48, freq="MS")).all()


def test_monthly_series_totals_match_the_fact_table(series):
    assert series.sum() == pytest.approx(2_297_200.86, abs=0.05)


def test_split_holds_out_the_requested_tail(series):
    train, test = fc.split(series, holdout=6)
    assert len(test) == 6
    assert len(train) == len(series) - 6
    assert train.index[-1] < test.index[0]


def test_accuracy_metrics_are_zero_on_a_perfect_forecast():
    actual = [100.0, 200.0, 300.0]
    assert fc.mape(actual, actual) == pytest.approx(0)
    assert fc.rmse(actual, actual) == pytest.approx(0)


def test_seasonal_naive_repeats_the_prior_year(series):
    train, test = fc.split(series)
    forecast = fc.seasonal_naive(train, len(test))
    assert len(forecast.predicted) == len(test)
    assert forecast.predicted.iloc[0] == pytest.approx(train.iloc[-12])


def test_every_model_produces_a_forecast_of_the_right_length(series):
    result = fc.backtest(series)
    assert not result.failures, f"models failed to fit: {result.failures}"
    for name, forecast in result.forecasts.items():
        assert len(forecast.predicted) == 6, name


def test_statistical_models_beat_the_naive_baseline(series):
    """If they cannot, the extra dependencies are not earning their place."""
    result = fc.backtest(series)
    scores = {s.model: s.mape for s in result.scores}
    assert scores["SARIMA"] < scores["Seasonal naive"]
    assert scores["Prophet"] < scores["Seasonal naive"]


def test_forecast_horizon_and_interval_are_sane(series):
    forecast = fc.forecast_next_quarter(series, "SARIMA")
    assert len(forecast.predicted) == 3
    assert (forecast.predicted >= 0).all()
    assert (forecast.lower >= 0).all(), "sales cannot be negative"
    assert (forecast.lower <= forecast.predicted).all()
    assert (forecast.predicted <= forecast.upper).all()


def test_forecast_continues_from_the_end_of_the_series(series):
    forecast = fc.forecast_next_quarter(series, "SARIMA")
    assert forecast.predicted.index[0] == series.index[-1] + pd.offsets.MonthBegin()


def test_regional_forecast_covers_all_four_regions():
    regional = fc.regional_forecasts("SARIMA")
    assert set(regional["region"]) == {"Central", "East", "South", "West"}
    assert len(regional) == 12
    assert (regional["forecast_sales"] >= 0).all()


# ---------------------------------------------------------------------------
# Dashboard data layer
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def dashboard_frame() -> pd.DataFrame:
    flat = load_analysis_frame()
    flat["order_date"] = pd.to_datetime(flat["order_date"])
    return flat


def test_no_filters_returns_everything(dashboard_frame):
    from app.streamlit_app import apply_filters

    assert len(apply_filters(dashboard_frame)) == len(dashboard_frame)


def test_each_filter_narrows_the_frame(dashboard_frame):
    from app.streamlit_app import apply_filters

    west = apply_filters(dashboard_frame, regions=["West"])
    assert set(west["region"]) == {"West"}
    assert 0 < len(west) < len(dashboard_frame)

    consumer = apply_filters(dashboard_frame, segments=["Consumer"])
    assert set(consumer["segment"]) == {"Consumer"}

    tech = apply_filters(dashboard_frame, categories=["Technology"])
    assert set(tech["category"]) == {"Technology"}


def test_filters_combine(dashboard_frame):
    from app.streamlit_app import apply_filters

    both = apply_filters(dashboard_frame, regions=["West"], categories=["Technology"])
    assert set(both["region"]) == {"West"}
    assert set(both["category"]) == {"Technology"}


def test_date_range_filter_bounds_the_frame(dashboard_frame):
    from app.streamlit_app import apply_filters

    filtered = apply_filters(
        dashboard_frame, date_range=(pd.Timestamp("2020-01-01"), pd.Timestamp("2020-12-31"))
    )
    assert filtered["order_date"].dt.year.unique().tolist() == [2020]


def test_kpis_match_the_known_totals(dashboard_frame):
    from app.streamlit_app import kpis

    values = kpis(dashboard_frame)
    assert values["sales"] == pytest.approx(2_297_200.86, abs=0.05)
    assert values["profit"] == pytest.approx(286_397.02, abs=0.05)
    assert values["margin_pct"] == pytest.approx(12.47, abs=0.01)
    assert values["pct_loss_making"] == pytest.approx(18.72, abs=0.01)


def test_kpis_survive_an_empty_frame(dashboard_frame):
    """A filter combination with no rows must not divide by zero."""
    from app.streamlit_app import apply_filters, kpis

    empty = apply_filters(dashboard_frame, regions=["West"], categories=["Technology"],
                          date_range=(pd.Timestamp("2016-01-01"), pd.Timestamp("2016-01-02")))
    assert empty.empty
    assert kpis(empty)["margin_pct"] == 0.0
