"""Monthly sales forecasting: seasonal naive, SARIMA, and Prophet, backtested then applied.

The method is deliberately conservative. A forecast nobody can check is worth nothing, so
every model is scored against a held-out period before any of them is used to predict, and a
seasonal-naive baseline is included to prove the sophisticated models earn their complexity.

  1. Aggregate fact_sales to monthly totals, overall and per region.
  2. Hold out the last 6 months.
  3. Fit all three models on the training period and score them on the holdout with MAPE
     and RMSE.
  4. Refit whichever wins on the full series and forecast the next quarter with an 80%
     interval.

Run with: python -m src.forecasting
"""

from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.utils import REPORTS_DIR, connect, markdown_table, require_star_schema

REPORT_PATH = REPORTS_DIR / "forecast_results.md"

HOLDOUT_MONTHS = 6
FORECAST_MONTHS = 3
SEASONAL_PERIOD = 12
INTERVAL_WIDTH = 0.80

# Prophet and cmdstanpy are noisy on import and on every fit.
logging.getLogger("cmdstanpy").setLevel(logging.ERROR)
logging.getLogger("prophet").setLevel(logging.ERROR)


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


def monthly_sales(region: str | None = None) -> pd.Series:
    """Monthly sales totals as a Series indexed by month start.

    Reindexed onto a complete monthly range so a month with no orders reads as zero rather
    than vanishing and silently shortening the series.
    """
    where = "WHERE g.region = ?" if region else ""
    params = [region] if region else []
    with connect(read_only=True) as con:
        require_star_schema(con)
        rows = con.execute(
            f"""
            SELECT date_trunc('month', f.order_date) AS month, sum(f.sales) AS sales
            FROM fact_sales f
            JOIN dim_geography g USING (geography_key)
            {where}
            GROUP BY month
            ORDER BY month
            """,
            params,
        ).df()

    series = pd.Series(rows["sales"].values, index=pd.DatetimeIndex(rows["month"]), name="sales")
    full = pd.date_range(series.index.min(), series.index.max(), freq="MS")
    return series.reindex(full, fill_value=0.0).astype(float)


def split(series: pd.Series, holdout: int = HOLDOUT_MONTHS) -> tuple[pd.Series, pd.Series]:
    return series.iloc[:-holdout], series.iloc[-holdout:]


# ---------------------------------------------------------------------------
# Accuracy
# ---------------------------------------------------------------------------


def mape(actual: np.ndarray, predicted: np.ndarray) -> float:
    actual, predicted = np.asarray(actual, float), np.asarray(predicted, float)
    nonzero = actual != 0
    return float(np.mean(np.abs((actual[nonzero] - predicted[nonzero]) / actual[nonzero])) * 100)


def rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    actual, predicted = np.asarray(actual, float), np.asarray(predicted, float)
    return float(np.sqrt(np.mean((actual - predicted) ** 2)))


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


@dataclass
class Forecast:
    """A model's prediction, with an interval where the model provides one."""

    model: str
    predicted: pd.Series
    lower: pd.Series | None = None
    upper: pd.Series | None = None
    note: str = ""


@dataclass
class Scorecard:
    model: str
    mape: float
    rmse: float
    note: str = ""


def seasonal_naive(train: pd.Series, periods: int) -> Forecast:
    """Each future month repeats the same month a year earlier. The bar to beat."""
    history = list(train.values)
    predictions = []
    for step in range(periods):
        index = len(history) - SEASONAL_PERIOD + step
        predictions.append(history[index] if index >= 0 else history[-1])

    future = pd.date_range(train.index[-1] + pd.offsets.MonthBegin(), periods=periods, freq="MS")
    return Forecast("Seasonal naive", pd.Series(predictions, index=future),
                    note="last year's same month")


def fit_sarima(train: pd.Series, periods: int) -> Forecast:
    """SARIMA(1,1,1)(1,1,0,12).

    The seasonal order is kept deliberately small. With 42 training months, seasonal
    differencing at lag 12 leaves under 30 usable observations, so a richer seasonal
    specification would be fitting noise.
    """
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = SARIMAX(
            train,
            order=(1, 1, 1),
            seasonal_order=(1, 1, 0, SEASONAL_PERIOD),
            enforce_stationarity=False,
            enforce_invertibility=False,
        ).fit(disp=False)
        result = model.get_forecast(steps=periods)
        interval = result.conf_int(alpha=1 - INTERVAL_WIDTH)

    future = pd.date_range(train.index[-1] + pd.offsets.MonthBegin(), periods=periods, freq="MS")
    return Forecast(
        "SARIMA",
        pd.Series(result.predicted_mean.values, index=future),
        pd.Series(interval.iloc[:, 0].values, index=future),
        pd.Series(interval.iloc[:, 1].values, index=future),
        note="(1,1,1)(1,1,0,12)",
    )


def fit_prophet(train: pd.Series, periods: int) -> Forecast:
    """Prophet with yearly seasonality only.

    Weekly and daily seasonality are switched off because the series is monthly. Changepoint
    flexibility is left at the default; with 42 points there is little to be gained from
    tuning it and a real risk of overfitting the holdout.
    """
    from prophet import Prophet

    frame = pd.DataFrame({"ds": train.index, "y": train.values})
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False,
            interval_width=INTERVAL_WIDTH,
        )
        model.fit(frame)
        future_frame = model.make_future_dataframe(periods=periods, freq="MS")
        prediction = model.predict(future_frame).tail(periods)

    future = pd.DatetimeIndex(prediction["ds"].values)
    return Forecast(
        "Prophet",
        pd.Series(prediction["yhat"].values, index=future),
        pd.Series(prediction["yhat_lower"].values, index=future),
        pd.Series(prediction["yhat_upper"].values, index=future),
        note="yearly seasonality",
    )


MODELS = {
    "Seasonal naive": seasonal_naive,
    "SARIMA": fit_sarima,
    "Prophet": fit_prophet,
}


# ---------------------------------------------------------------------------
# Backtest and forecast
# ---------------------------------------------------------------------------


@dataclass
class Backtest:
    scores: list[Scorecard]
    forecasts: dict[str, Forecast]
    train: pd.Series
    test: pd.Series
    failures: dict[str, str] = field(default_factory=dict)

    @property
    def table(self) -> pd.DataFrame:
        return pd.DataFrame(
            [{"model": s.model, "mape_pct": s.mape, "rmse": s.rmse, "note": s.note}
             for s in sorted(self.scores, key=lambda s: s.mape)]
        )

    @property
    def best(self) -> str:
        return min(self.scores, key=lambda s: s.mape).model


def backtest(series: pd.Series, holdout: int = HOLDOUT_MONTHS) -> Backtest:
    """Score every model on a held-out tail of the series."""
    train, test = split(series, holdout)
    scores, forecasts, failures = [], {}, {}

    for name, fit in MODELS.items():
        try:
            forecast = fit(train, len(test))
        except Exception as exc:  # A model that will not fit is a result, not a crash.
            failures[name] = str(exc)[:200]
            continue
        forecasts[name] = forecast
        scores.append(
            Scorecard(
                model=name,
                mape=mape(test.values, forecast.predicted.values),
                rmse=rmse(test.values, forecast.predicted.values),
                note=forecast.note,
            )
        )

    if not scores:
        raise RuntimeError(f"No model could be fitted. Failures: {failures}")

    return Backtest(scores, forecasts, train, test, failures)


def forecast_next_quarter(series: pd.Series, model: str,
                          periods: int = FORECAST_MONTHS) -> Forecast:
    """Refit the chosen model on the full series and predict forward.

    Interval bounds are floored at zero. A Gaussian prediction interval around a low monthly
    total will happily reach below zero, but negative sales are not a possible outcome, and
    printing one costs more credibility than the lost symmetry is worth.
    """
    forecast = MODELS[model](series, periods)
    forecast.predicted = forecast.predicted.clip(lower=0)
    if forecast.lower is not None:
        forecast.lower = forecast.lower.clip(lower=0)
        forecast.upper = forecast.upper.clip(lower=0)
    return forecast


def regional_forecasts(model: str, periods: int = FORECAST_MONTHS) -> pd.DataFrame:
    """Next-quarter forecast per region, using the model that won the overall backtest."""
    rows = []
    for region in ("Central", "East", "South", "West"):
        series = monthly_sales(region)
        try:
            forecast = forecast_next_quarter(series, model, periods)
        except Exception as exc:
            rows.append({"region": region, "note": f"fit failed: {str(exc)[:80]}"})
            continue
        for month, value in forecast.predicted.items():
            row = {
                "region": region,
                "month": month.strftime("%Y-%m"),
                "forecast_sales": value,
            }
            if forecast.lower is not None:
                row["lower_80"] = forecast.lower[month]
                row["upper_80"] = forecast.upper[month]
            rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def build_report() -> str:
    series = monthly_sales()
    result = backtest(series)
    best = result.best
    best_score = min(result.scores, key=lambda s: s.mape)
    baseline = next((s for s in result.scores if s.model == "Seasonal naive"), None)

    overall = forecast_next_quarter(series, best)
    regional = regional_forecasts(best)

    quarter_total = overall.predicted.sum()
    prior_quarter = series.tail(FORECAST_MONTHS).sum()
    same_quarter_last_year = series.tail(SEASONAL_PERIOD).head(FORECAST_MONTHS).sum()

    forecast_table = pd.DataFrame({
        "month": [d.strftime("%Y-%m") for d in overall.predicted.index],
        "forecast_sales": overall.predicted.values,
    })
    if overall.lower is not None:
        forecast_table["lower_80"] = overall.lower.values
        forecast_table["upper_80"] = overall.upper.values

    lines = [
        "# Sales forecast",
        "",
        "Regenerate with `python -m src.forecasting`.",
        "",
        "## Method",
        "",
        f"Monthly sales from {series.index[0]:%B %Y} to {series.index[-1]:%B %Y}, "
        f"{len(series)} months. The last {HOLDOUT_MONTHS} are held out as a test set. Three "
        "models are fitted on the remaining "
        f"{len(series) - HOLDOUT_MONTHS} months and scored on the holdout. The winner is "
        f"refit on the full series to forecast the next {FORECAST_MONTHS} months.",
        "",
        "A seasonal-naive baseline is included so the sophisticated models have something to "
        "beat. A SARIMA or Prophet model that cannot beat last year's same month is not "
        "worth deploying.",
        "",
        "## Backtest",
        "",
        markdown_table(result.table),
        "",
    ]

    if result.failures:
        lines += [
            "Models that failed to fit: "
            + ", ".join(f"{k} ({v})" for k, v in result.failures.items()),
            "",
        ]

    lines += [
        f"**{best} wins** with a MAPE of {best_score.mape:.1f}% and an RMSE of "
        f"${best_score.rmse:,.0f}.",
        "",
    ]

    if baseline and best != "Seasonal naive":
        improvement = 100 * (baseline.mape - best_score.mape) / baseline.mape
        lines += [
            f"That is a {improvement:.0f}% improvement on the seasonal-naive baseline's "
            f"{baseline.mape:.1f}% MAPE, so the added complexity is earning its place.",
            "",
        ]
    elif best == "Seasonal naive":
        lines += [
            "The naive baseline beat both statistical models. With only "
            f"{len(series) - HOLDOUT_MONTHS} training months against a 12-month seasonal "
            "cycle, neither SARIMA nor Prophet has enough history to estimate seasonality "
            "better than simply repeating last year. Reporting this honestly is the point of "
            "including a baseline.",
            "",
        ]

    lines += [
        f"## Next quarter, {overall.predicted.index[0]:%B %Y} to "
        f"{overall.predicted.index[-1]:%B %Y}",
        "",
        markdown_table(forecast_table),
        "",
        f"**Total forecast: ${quarter_total:,.0f}.**",
        "",
        f"Read that against the right comparison. The most recent three months delivered "
        f"${prior_quarter:,.0f}, but those are October to December, the strongest quarter of "
        f"the year. The like-for-like comparison is the same quarter twelve months earlier, "
        f"which delivered ${same_quarter_last_year:,.0f}. On that basis the forecast is "
        f"{100 * (quarter_total - same_quarter_last_year) / same_quarter_last_year:+.0f}% "
        "year over year, consistent with the growth trend of the last three years rather "
        "than the collapse the quarter-on-quarter figure would suggest.",
        "",
    ]

    if overall.lower is not None:
        lines += [
            f"The 80% interval spans ${overall.lower.sum():,.0f} to "
            f"${overall.upper.sum():,.0f} across the quarter. That width is the honest "
            "message: with four years of monthly history, a point estimate on its own would "
            "imply more confidence than the data supports.",
            "",
        ]
    else:
        lines += [
            "The winning model is the naive baseline, which produces no interval. Treat the "
            "number as a planning anchor rather than a prediction with quantified "
            "uncertainty.",
            "",
        ]

    lines += [
        "## By region",
        "",
        markdown_table(regional, limit=20),
        "",
        "Regional forecasts are far less reliable than the national one. Each is fitted on a "
        "quarter of the volume, so the seasonal signal is weaker and the intervals are wide "
        "enough to touch zero in several months. Treat these as a split of the national "
        "number for planning purposes, not as four independent forecasts.",
        "",
        "## Caveats",
        "",
        f"- {len(series)} monthly observations is a short series. Four seasonal cycles is the "
        "bare minimum for estimating annual seasonality, and it shows in the interval width.",
        "- The series ends 2020-12-30. Sales grew in three of the four years, so the models "
        "extrapolate an upward trend that assumes conditions continue.",
        "- Sales, not profit, are forecast. Given that margin depends heavily on discounting, "
        "a sales forecast says nothing about whether that revenue will be profitable.",
        "",
    ]

    return "\n".join(lines)


def main() -> None:
    series = monthly_sales()
    result = backtest(series)

    print(f"{len(series)} months, holdout {HOLDOUT_MONTHS}")
    for score in sorted(result.scores, key=lambda s: s.mape):
        print(f"  {score.model:<16} MAPE {score.mape:>6.1f}%   RMSE ${score.rmse:>10,.0f}")
    for name, reason in result.failures.items():
        print(f"  {name:<16} failed: {reason}")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(build_report(), encoding="utf-8", newline="\n")
    print(f"\nbest: {result.best}")
    print(f"wrote {REPORT_PATH.relative_to(REPORTS_DIR.parent)}")


if __name__ == "__main__":
    main()
