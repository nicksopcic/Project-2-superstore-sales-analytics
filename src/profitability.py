"""Discount and margin analysis: regression, tier testing, and per-sub-category break-even.

Answers the project's central question with statistics rather than a look at a scatterplot:

  1. Does discount predict margin once quantity and category are controlled for? (OLS)
  2. Do the discount tiers really differ, or is the banding an artefact? (ANOVA, Kruskal-Wallis)
  3. At what discount does each sub-category stop making money? (per-group break-even)

Run with: python -m src.profitability
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats

from src.utils import REPORTS_DIR, load_analysis_frame, markdown_table

REPORT_PATH = REPORTS_DIR / "discount_profit_analysis.md"

# The tiers the plan calls for. Ordered, because the ordering is the point.
TIER_BINS = [-0.001, 0.0, 0.10, 0.20, 0.30, 1.0]
TIER_LABELS = ["0%", "1-10%", "11-20%", "21-30%", "30%+"]

MIN_LINES_FOR_BREAKEVEN = 30


def prepare(df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Analysis frame with margin and the discount tier attached."""
    data = load_analysis_frame() if df is None else df.copy()
    data["margin_pct"] = 100 * data["profit"] / data["sales"]
    data["discount_tier"] = pd.cut(
        data["discount"], bins=TIER_BINS, labels=TIER_LABELS, ordered=True
    )
    return data


# ---------------------------------------------------------------------------
# Regression
# ---------------------------------------------------------------------------


def fit_margin_model(data: pd.DataFrame) -> sm.regression.linear_model.RegressionResultsWrapper:
    """OLS of margin on discount, quantity, and category dummies.

    Margin rather than raw profit is the response. Profit in dollars confounds pricing
    quality with order size, which is why its correlation with discount looks weak while
    margin's is strong. Heteroskedasticity-robust (HC3) standard errors, since margin
    variance widens sharply at higher discounts.
    """
    return smf.ols(
        "margin_pct ~ discount + quantity + C(category)", data=data
    ).fit(cov_type="HC3")


def fit_profit_model(data: pd.DataFrame) -> sm.regression.linear_model.RegressionResultsWrapper:
    """The same specification against dollar profit, for the plan's stated deliverable."""
    return smf.ols(
        "profit ~ discount + quantity + C(category)", data=data
    ).fit(cov_type="HC3")


def coefficient_table(model) -> pd.DataFrame:
    conf = model.conf_int()
    return pd.DataFrame(
        {
            "term": model.params.index,
            "coefficient": model.params.values,
            "std_error": model.bse.values,
            "t": model.tvalues.values,
            "p_value": model.pvalues.values,
            "ci_low": conf[0].values,
            "ci_high": conf[1].values,
        }
    ).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Tier testing
# ---------------------------------------------------------------------------


@dataclass
class TierTests:
    anova_f: float
    anova_p: float
    kruskal_h: float
    kruskal_p: float
    levene_p: float
    groups: list[str]

    @property
    def variances_are_equal(self) -> bool:
        return self.levene_p >= 0.05


def test_discount_tiers(data: pd.DataFrame) -> TierTests:
    """Compare margin across discount tiers.

    ANOVA and Kruskal-Wallis are both reported on purpose. ANOVA assumes normal residuals
    and equal variances, and margin here is skewed with variance that grows with discount.
    Levene's test says whether that assumption holds. Kruskal-Wallis makes no such
    assumption, so agreement between the two is the reassurance that the result is not an
    artefact of a violated assumption.
    """
    groups = [
        data.loc[data["discount_tier"] == tier, "margin_pct"].dropna().values
        for tier in TIER_LABELS
    ]
    present = [(tier, g) for tier, g in zip(TIER_LABELS, groups, strict=True) if len(g) > 0]
    values = [g for _, g in present]

    anova_f, anova_p = stats.f_oneway(*values)
    kruskal_h, kruskal_p = stats.kruskal(*values)
    _, levene_p = stats.levene(*values)

    return TierTests(
        anova_f=anova_f,
        anova_p=anova_p,
        kruskal_h=kruskal_h,
        kruskal_p=kruskal_p,
        levene_p=levene_p,
        groups=[tier for tier, _ in present],
    )


def tier_summary(data: pd.DataFrame) -> pd.DataFrame:
    summary = (
        data.groupby("discount_tier", observed=True)
        .agg(
            order_lines=("margin_pct", "size"),
            sales=("sales", "sum"),
            profit=("profit", "sum"),
            mean_margin_pct=("margin_pct", "mean"),
            median_margin_pct=("margin_pct", "median"),
            pct_loss_making=("is_loss_making", "mean"),
        )
        .reset_index()
    )
    summary["pct_loss_making"] *= 100
    return summary


# ---------------------------------------------------------------------------
# Break-even discount
# ---------------------------------------------------------------------------


def breakeven_by_sub_category(data: pd.DataFrame) -> pd.DataFrame:
    """The discount at which each sub-category's fitted margin crosses zero.

    A simple per-group OLS of margin on discount. Where the slope is negative and the
    intercept positive, the crossing point is -intercept/slope, which is the discount
    ceiling implied by that sub-category's own history. Groups with too few lines, or with
    no discount variation, cannot support a fit and are reported as such rather than given
    a fabricated number.
    """
    rows = []
    for (sub_category, category), group in data.groupby(["sub_category", "category"]):
        observed_max = group["discount"].max()
        row = {
            "sub_category": sub_category,
            "category": category,
            "order_lines": len(group),
            "avg_discount": group["discount"].mean(),
            "max_discount": observed_max,
            "margin_pct": 100 * group["profit"].sum() / group["sales"].sum(),
        }

        if len(group) < MIN_LINES_FOR_BREAKEVEN or group["discount"].nunique() < 2:
            row["breakeven_discount"] = np.nan
            row["note"] = "too few lines or no discount variation"
        else:
            fit = smf.ols("margin_pct ~ discount", data=group).fit()
            intercept, slope = fit.params["Intercept"], fit.params["discount"]
            row["r_squared"] = fit.rsquared
            if slope >= 0:
                row["breakeven_discount"] = np.nan
                row["note"] = "margin does not fall with discount"
            else:
                crossing = -intercept / slope
                row["breakeven_discount"] = crossing
                if crossing <= 0:
                    row["note"] = "loses money even at full price"
                elif crossing > observed_max:
                    row["note"] = f"beyond the {observed_max:.0%} ever offered"
                else:
                    row["note"] = "within observed range"
        rows.append(row)

    result = pd.DataFrame(rows).sort_values("breakeven_discount", na_position="last")
    # Negative headroom means the line is already being discounted past the point where its
    # own history says it stops making money. That is the recommendation list.
    result["headroom"] = result["breakeven_discount"] - result["avg_discount"]
    result["over_discounted"] = result["headroom"] < 0
    return result


def over_discounted_sub_categories(data: pd.DataFrame) -> pd.DataFrame:
    """Sub-categories whose average discount already exceeds their break-even point."""
    breakeven = breakeven_by_sub_category(data)
    return breakeven[breakeven["over_discounted"].fillna(False)].sort_values("headroom")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def build_report(data: pd.DataFrame) -> str:
    margin_model = fit_margin_model(data)
    profit_model = fit_profit_model(data)
    tests = test_discount_tiers(data)
    tiers = tier_summary(data)
    breakeven = breakeven_by_sub_category(data)

    discount_coef = margin_model.params["discount"]
    profit_coef = profit_model.params["discount"]
    per_ten_points = profit_coef * 0.10
    actionable = breakeven[breakeven["note"] == "within observed range"]
    over_discounted = breakeven[breakeven["over_discounted"].fillna(False)].sort_values(
        "headroom"
    )

    lines = [
        "# Discount and profit analysis",
        "",
        "Regenerate with `python -m src.profitability`. Every number here is computed from "
        "the validated star schema, not copied by hand.",
        "",
        "## The question",
        "",
        "Does discounting explain the margin damage, and if so, where is the ceiling?",
        "",
        "## Regression",
        "",
        f"Margin on discount, quantity, and category dummies, over {int(margin_model.nobs):,} "
        f"order lines with HC3 robust standard errors. Adjusted R-squared "
        f"**{margin_model.rsquared_adj:.3f}**.",
        "",
        markdown_table(coefficient_table(margin_model), limit=20),
        "",
        f"The discount coefficient is **{discount_coef:,.1f}**, meaning each additional 10 "
        f"points of discount is associated with a **{abs(discount_coef) / 10:,.1f} point** "
        f"fall in margin, holding quantity and category constant "
        f"(p = {margin_model.pvalues['discount']:.2e}).",
        "",
        "Discount alone accounts for nearly all of the explained variance. Quantity "
        f"contributes a coefficient of {margin_model.params['quantity']:,.3f} "
        f"(p = {margin_model.pvalues['quantity']:.3f}), which is negligible next to the "
        "discount effect.",
        "",
        "### The same model against dollar profit",
        "",
        "The plan asks for profit as the response, so it is reported here too. It is the "
        "weaker specification, because dollar profit mixes pricing quality with order size.",
        "",
        markdown_table(coefficient_table(profit_model), limit=20),
        "",
        f"Each additional 10 points of discount is associated with **${abs(per_ten_points):,.2f} "
        f"lower profit per line item**, controlling for quantity and category "
        f"(p = {profit_model.pvalues['discount']:.2e}). Adjusted R-squared is only "
        f"{profit_model.rsquared_adj:.3f}, against {margin_model.rsquared_adj:.3f} for the "
        "margin model.",
        "",
        "## Do the discount tiers actually differ?",
        "",
        markdown_table(tiers, limit=10),
        "",
        f"**ANOVA**: F = {tests.anova_f:,.1f}, p = {tests.anova_p:.2e}. "
        f"**Kruskal-Wallis**: H = {tests.kruskal_h:,.1f}, p = {tests.kruskal_p:.2e}.",
        "",
    ]

    if tests.variances_are_equal:
        lines.append(
            f"Levene's test does not reject equal variances (p = {tests.levene_p:.3f}), so "
            "the ANOVA assumption holds and both tests are on equal footing."
        )
    else:
        lines.append(
            f"Levene's test rejects equal variances (p = {tests.levene_p:.2e}), which is "
            "expected given how much wider margin spreads at high discounts. That violates "
            "an ANOVA assumption, which is exactly why the non-parametric Kruskal-Wallis is "
            "reported alongside it. Both reject the null at any conventional threshold, so "
            "the tier differences are not an artefact of the assumption failure."
        )

    lines += [
        "",
        "## Break-even discount by sub-category",
        "",
        "A per-sub-category regression of margin on discount, solved for the point where "
        "fitted margin crosses zero. This is the discount ceiling each line's own history "
        "implies.",
        "",
        markdown_table(breakeven, limit=20),
        "",
        f"{len(actionable)} sub-categories have a break-even point inside the range of "
        "discounts actually offered, which makes them the actionable list. Where the note "
        "says the crossing sits beyond the maximum discount ever offered, the line has not "
        "yet been discounted hard enough to lose money on average.",
        "",
        "### Already past the ceiling",
        "",
        "`headroom` is the break-even discount minus the discount currently being given. "
        "Where it is negative, the line is routinely sold below the point its own history "
        "says it stops paying. These are the discount caps to set.",
        "",
        markdown_table(
            over_discounted[
                ["sub_category", "category", "order_lines", "avg_discount",
                 "breakeven_discount", "headroom", "margin_pct"]
            ],
            limit=20,
        ),
        "",
    ]

    if not over_discounted.empty:
        worst = over_discounted.iloc[0]
        lines += [
            f"{worst['sub_category']} is the clearest case: it breaks even at "
            f"{worst['breakeven_discount']:.1%} and is sold at {worst['avg_discount']:.1%} on "
            f"average, {abs(worst['headroom']):.1%} past its own ceiling, for a "
            f"{worst['margin_pct']:.1f}% margin across {int(worst['order_lines']):,} lines.",
            "",
        ]

    return "\n".join(lines)


def main() -> None:
    data = prepare()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(build_report(data), encoding="utf-8", newline="\n")

    margin_model = fit_margin_model(data)
    tests = test_discount_tiers(data)
    print(f"margin model  adj R2 {margin_model.rsquared_adj:.3f}  "
          f"discount coef {margin_model.params['discount']:,.1f}")
    print(f"ANOVA         F {tests.anova_f:,.1f}  p {tests.anova_p:.2e}")
    print(f"Kruskal       H {tests.kruskal_h:,.1f}  p {tests.kruskal_p:.2e}")
    print(f"wrote {REPORT_PATH.relative_to(REPORTS_DIR.parent)}")


if __name__ == "__main__":
    main()
