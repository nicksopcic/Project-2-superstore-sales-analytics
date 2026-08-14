# Sales forecast

Regenerate with `python -m src.forecasting`.

## Method

Monthly sales from January 2017 to December 2020, 48 months. The last 6 are held out as a test set. Three models are fitted on the remaining 42 months and scored on the holdout. The winner is refit on the full series to forecast the next 3 months.

A seasonal-naive baseline is included so the sophisticated models have something to beat. A SARIMA or Prophet model that cannot beat last year's same month is not worth deploying.

## Backtest

| model | mape_pct | rmse | note |
| --- | ---: | ---: | --- |
| SARIMA | 18.02 | 17,960.11 | (1,1,1)(1,1,0,12) |
| Prophet | 18.55 | 20,762.50 | yearly seasonality |
| Seasonal naive | 25.39 | 23,430.16 | last year's same month |


**SARIMA wins** with a MAPE of 18.0% and an RMSE of $17,960.

That is a 29% improvement on the seasonal-naive baseline's 25.4% MAPE, so the added complexity is earning its place.

## Next quarter, January 2021 to March 2021

| month | forecast_sales | lower_80 | upper_80 |
| --- | ---: | ---: | ---: |
| 2021-01 | 52,929.03 | 33,805.68 | 72,052.39 |
| 2021-02 | 35,122.09 | 15,998.81 | 54,245.37 |
| 2021-03 | 71,212.84 | 52,041.64 | 90,384.05 |


**Total forecast: $159,264.**

Read that against the right comparison. The most recent three months delivered $280,054, but those are October to December, the strongest quarter of the year. The like-for-like comparison is the same quarter twelve months earlier, which delivered $123,145. On that basis the forecast is +29% year over year, consistent with the growth trend of the last three years rather than the collapse the quarter-on-quarter figure would suggest.

The 80% interval spans $101,846 to $216,682 across the quarter. That width is the honest message: with four years of monthly history, a point estimate on its own would imply more confidence than the data supports.

## By region

| region | month | forecast_sales | lower_80 | upper_80 |
| --- | --- | ---: | ---: | ---: |
| Central | 2021-01 | 14,566.12 | 3,087.23 | 26,045.02 |
| Central | 2021-02 | 379.92 | 0 | 11,933.12 |
| Central | 2021-03 | 12,588.45 | 506.43 | 24,670.47 |
| East | 2021-01 | 14,463.34 | 2,923.04 | 26,003.63 |
| East | 2021-02 | 9,410.60 | 0 | 21,158.97 |
| East | 2021-03 | 22,893.01 | 10,333.23 | 35,452.80 |
| South | 2021-01 | 7,991.16 | 0 | 17,147.20 |
| South | 2021-02 | 7,054.18 | 0 | 16,231.13 |
| South | 2021-03 | 9,897.86 | 644.15 | 19,151.58 |
| West | 2021-01 | 14,448.58 | 6,468.05 | 22,429.11 |
| West | 2021-02 | 12,893.06 | 4,894.98 | 20,891.14 |
| West | 2021-03 | 30,064.99 | 22,047.90 | 38,082.08 |


Regional forecasts are far less reliable than the national one. Each is fitted on a quarter of the volume, so the seasonal signal is weaker and the intervals are wide enough to touch zero in several months. Treat these as a split of the national number for planning purposes, not as four independent forecasts.

## Caveats

- 48 monthly observations is a short series. Four seasonal cycles is the bare minimum for estimating annual seasonality, and it shows in the interval width.
- The series ends 2020-12-30. Sales grew in three of the four years, so the models extrapolate an upward trend that assumes conditions continue.
- Sales, not profit, are forecast. Given that margin depends heavily on discounting, a sales forecast says nothing about whether that revenue will be profitable.
