"""Sales operations dashboard for the Superstore analytics project.

Reads the processed Parquet written by `python -m src.data_quality`, falling back to the
DuckDB database if the Parquet is not there. Everything below the filters recomputes from the
filtered frame, so the KPI cards and the charts always agree with each other.

Run with: streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import forecasting as fc  # noqa: E402
from src import plotting as viz  # noqa: E402
from src.utils import load_analysis_frame  # noqa: E402

st.set_page_config(page_title="Superstore sales operations", page_icon="+", layout="wide")

PLOT_LAYOUT = dict(
    paper_bgcolor=viz.SURFACE,
    plot_bgcolor=viz.SURFACE,
    font=dict(color=viz.INK_MUTED, size=12),
    title_font=dict(color=viz.INK, size=15),
    margin=dict(l=10, r=10, t=50, b=10),
    xaxis=dict(gridcolor=viz.GRID, zerolinecolor=viz.GRID),
    yaxis=dict(gridcolor=viz.GRID, zerolinecolor=viz.GRID),
    legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0),
    hovermode="x unified",
)


@st.cache_data(show_spinner="Loading the star schema")
def load_data() -> pd.DataFrame:
    try:
        frame = load_analysis_frame("parquet")
    except FileNotFoundError:
        frame = load_analysis_frame("duckdb")
    frame["order_date"] = pd.to_datetime(frame["order_date"])
    frame["margin_pct"] = 100 * frame["profit"] / frame["sales"]
    return frame


@st.cache_data(show_spinner="Fitting the forecast")
def quarterly_forecast(monthly: pd.Series) -> pd.DataFrame | None:
    """SARIMA forecast for the next quarter, or None when the series cannot support one."""
    if len(monthly) < 24:
        return None
    try:
        forecast = fc.forecast_next_quarter(monthly, "SARIMA")
    except Exception:
        return None
    return pd.DataFrame(
        {
            "month": forecast.predicted.index,
            "forecast": forecast.predicted.values,
            "lower": forecast.lower.values,
            "upper": forecast.upper.values,
        }
    )


def apply_filters(
    frame: pd.DataFrame,
    regions: list[str] | None = None,
    segments: list[str] | None = None,
    categories: list[str] | None = None,
    date_range: tuple | None = None,
) -> pd.DataFrame:
    """Narrow the frame by the sidebar selections. An empty selection means no restriction.

    Kept out of main() so it can be tested without a Streamlit runtime.
    """
    filtered = frame
    if regions:
        filtered = filtered[filtered["region"].isin(regions)]
    if segments:
        filtered = filtered[filtered["segment"].isin(segments)]
    if categories:
        filtered = filtered[filtered["category"].isin(categories)]
    if date_range and len(date_range) == 2:
        start, end = (pd.Timestamp(d) for d in date_range)
        filtered = filtered[filtered["order_date"].between(start, end)]
    return filtered


def kpis(frame: pd.DataFrame) -> dict[str, float]:
    """The five headline numbers, computed from whatever frame is passed in."""
    sales = frame["sales"].sum()
    return {
        "sales": sales,
        "profit": frame["profit"].sum(),
        "margin_pct": 100 * frame["profit"].sum() / sales if sales else 0.0,
        "avg_discount": frame["discount"].mean() if len(frame) else 0.0,
        "pct_loss_making": 100 * frame["is_loss_making"].mean() if len(frame) else 0.0,
    }


def kpi_row(frame: pd.DataFrame) -> None:
    """Five metric cards.

    Values are abbreviated ($2.3M rather than $2,297,201) because a metric card does not wrap
    or shrink its text: at anything narrower than a maximised window with the sidebar closed,
    the full figure silently truncates to "$2,29...", which is worse than useless on a
    headline number. The exact figure goes in the tooltip and the table below the charts.
    """
    values = kpis(frame)

    for column, (label, value, help_text) in zip(
        st.columns(5),
        [
            ("Sales", viz.currency(values["sales"]),
             f"Total sales across the filtered lines: ${values['sales']:,.2f}"),
            ("Profit", viz.currency(values["profit"]),
             f"Total profit across the filtered lines: ${values['profit']:,.2f}"),
            ("Margin", f"{values['margin_pct']:.1f}%",
             "Profit as a share of sales"),
            ("Avg discount", f"{values['avg_discount']:.1%}",
             "Mean discount rate per order line"),
            ("Loss-making", f"{values['pct_loss_making']:.1f}%",
             "Share of order lines with negative profit"),
        ],
        strict=True,
    ):
        column.metric(label, value, help=help_text)


def trend_chart(frame: pd.DataFrame, show_forecast: bool) -> go.Figure:
    monthly = (
        frame.set_index("order_date")["sales"].resample("MS").sum().astype(float)
    )

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=monthly.index, y=monthly.values, name="actual",
            line=dict(color=viz.CATEGORICAL[0], width=2),
            hovertemplate="%{x|%b %Y}<br>$%{y:,.0f}<extra></extra>",
        )
    )

    if show_forecast:
        forecast = quarterly_forecast(monthly)
        if forecast is not None:
            figure.add_trace(
                go.Scatter(
                    x=list(forecast["month"]) + list(forecast["month"])[::-1],
                    y=list(forecast["upper"]) + list(forecast["lower"])[::-1],
                    fill="toself", fillcolor="rgba(235, 104, 52, 0.15)",
                    line=dict(width=0), name="80% interval", hoverinfo="skip",
                )
            )
            figure.add_trace(
                go.Scatter(
                    x=forecast["month"], y=forecast["forecast"], name="SARIMA forecast",
                    line=dict(color=viz.CATEGORICAL[1], width=2.5, dash="dot"),
                    mode="lines+markers",
                    hovertemplate="%{x|%b %Y}<br>forecast $%{y:,.0f}<extra></extra>",
                )
            )
        else:
            st.caption("Not enough filtered history to fit a forecast.")

    figure.update_layout(title="Monthly sales", **PLOT_LAYOUT)
    figure.update_yaxes(tickprefix="$", tickformat=",.0f")
    return figure


def discount_scatter(frame: pd.DataFrame) -> go.Figure:
    # One point per discount level per sub-category keeps the chart readable and still shows
    # the relationship. Ten thousand raw points would be a smear.
    grouped = (
        frame.groupby(["discount", "sub_category"])
        .agg(sales=("sales", "sum"), profit=("profit", "sum"), lines=("sales", "size"))
        .reset_index()
    )
    grouped["margin_pct"] = 100 * grouped["profit"] / grouped["sales"]

    figure = go.Figure(
        go.Scatter(
            x=grouped["discount"], y=grouped["margin_pct"], mode="markers",
            marker=dict(
                size=grouped["lines"].clip(4, 40),
                color=grouped["margin_pct"],
                colorscale=[[0, viz.PROFIT_NEGATIVE], [0.5, viz.NEUTRAL],
                            [1, viz.PROFIT_POSITIVE]],
                cmid=0, line=dict(color=viz.SURFACE, width=1),
            ),
            customdata=grouped[["sub_category", "lines"]],
            hovertemplate=("%{customdata[0]}<br>discount %{x:.0%}<br>"
                           "margin %{y:.1f}%<br>%{customdata[1]} lines<extra></extra>"),
        )
    )
    figure.add_hline(y=0, line=dict(color=viz.INK_MUTED, width=1))
    figure.update_layout(title="Discount against margin", **PLOT_LAYOUT)
    figure.update_layout(hovermode="closest")
    figure.update_xaxes(tickformat=".0%", title="Discount")
    figure.update_yaxes(title="Margin %", range=[-150, 100])
    return figure


def sub_category_chart(frame: pd.DataFrame) -> go.Figure:
    ranking = (
        frame.groupby("sub_category")["profit"].sum().sort_values().reset_index()
    )
    figure = go.Figure(
        go.Bar(
            x=ranking["profit"], y=ranking["sub_category"], orientation="h",
            marker_color=viz.profit_colors(ranking["profit"]),
            hovertemplate="%{y}<br>$%{x:,.0f}<extra></extra>",
        )
    )
    figure.update_layout(title="Profit by sub-category", height=520, **PLOT_LAYOUT)
    figure.update_xaxes(tickprefix="$", tickformat=",.0f")
    return figure


def main() -> None:
    frame = load_data()

    st.title("Superstore sales operations")
    st.caption(
        "Which regions, segments, and categories are profitable to discount, and where is "
        "discounting quietly destroying margin?"
    )

    with st.sidebar:
        st.header("Filters")
        regions = st.multiselect("Region", sorted(frame["region"].unique()))
        segments = st.multiselect("Segment", sorted(frame["segment"].unique()))
        categories = st.multiselect("Category", sorted(frame["category"].unique()))

        earliest, latest = frame["order_date"].min().date(), frame["order_date"].max().date()
        date_range = st.date_input(
            "Order date", value=(earliest, latest), min_value=earliest, max_value=latest
        )
        st.divider()
        st.caption(
            "Charts and KPI cards recompute from the same filtered frame. The forecast "
            "refits on whatever is selected."
        )

    filtered = apply_filters(
        frame,
        regions=regions,
        segments=segments,
        categories=categories,
        date_range=date_range if isinstance(date_range, tuple) else None,
    )

    if filtered.empty:
        st.warning("No order lines match these filters.")
        return

    st.caption(
        f"{len(filtered):,} of {len(frame):,} order lines selected"
        + (" (unfiltered)" if len(filtered) == len(frame) else "")
    )
    kpi_row(filtered)
    st.divider()

    st.plotly_chart(trend_chart(filtered, show_forecast=True), use_container_width=True)

    left, right = st.columns([1, 1])
    left.plotly_chart(discount_scatter(filtered), use_container_width=True)
    right.plotly_chart(sub_category_chart(filtered), use_container_width=True)

    with st.expander("Underlying data"):
        st.dataframe(
            filtered.groupby(["category", "sub_category"])
            .agg(
                lines=("sales", "size"),
                sales=("sales", "sum"),
                profit=("profit", "sum"),
                avg_discount=("discount", "mean"),
            )
            .assign(margin_pct=lambda d: 100 * d["profit"] / d["sales"])
            .round(2),
            use_container_width=True,
        )


if __name__ == "__main__":
    main()
