# Findings

The full write-up behind the summary in the README. Every figure here comes from a generated
report in this directory or from a query in `sql/`, and can be reproduced with the four
commands in the README's "How to run".

Period covered: 2017-01-03 to 2020-12-30. 9,994 order lines, 5,009 orders, 793 customers.

## Headline

The business turned **$2,297,201 of sales into $286,397 of profit**, a 12.47% margin. That
number is the net of two very different books of business:

- 8,123 order lines earned **$442,528**.
- 1,871 order lines, 18.7% of the total, lost **$156,131**.

Just over a third of the gross profit is destroyed before it reaches the bottom line, and
almost all of that destruction traces to a single controllable variable.

## 1. Discounting past 20% is where the margin goes

Banding every line by its discount rate locates the failure precisely.

| Discount | Lines | Sales | Profit | Margin | Loss-making lines |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0% | 4,798 | $1,087,908 | $320,988 | 29.51% | 0.0% |
| 1-10% | 94 | $54,369 | $9,029 | 16.61% | 4.3% |
| 11-20% | 3,709 | $792,153 | $91,756 | 11.58% | 14.0% |
| 21-30% | 227 | $103,227 | -$10,369 | -10.05% | 91.6% |
| 31-40% | 233 | $130,911 | -$25,448 | -19.44% | 88.8% |
| 41%+ | 933 | $128,632 | -$99,559 | -77.40% | 100.0% |

There is no gradual decline. Margin goes from +11.58% to -10.05% across one step, and the share
of loss-making lines goes from 14% to 92% across the same step. Above 40%, the failure rate is
100%: not one of those 933 lines made money.

This is what makes a policy cap workable. A gently sloping relationship would force a judgement
about where to draw the line. This one draws it for us.

## 2. Discount explains three quarters of the variation in margin

An OLS regression of margin on discount, quantity, and category dummies, with HC3 robust
standard errors, over all 9,994 lines:

- **Adjusted R-squared: 0.751.**
- **Discount coefficient: -195.2** (p far below any threshold worth naming). Every 10 points of
  discount costs 19.5 points of margin, holding quantity and category constant.
- Quantity contributes essentially nothing. Volume is not buying anything.

Since the average full-price line earns about 34 points of margin, roughly 17 points of
discount is enough to erase it entirely.

Robust standard errors are used rather than the default because margin variance widens sharply
as discount rises, which is visible in the scatter and confirmed by Levene's test.

**The same model against dollar profit gives -$24.36 per 10 points of discount, but an adjusted
R-squared of only 0.061.** The relationship is identical; the response variable is worse. Dollar
profit mixes pricing quality with order size, so a large discounted order can out-earn a small
full-price one and dilute the signal. This is why margin is the variable to manage and to
report.

Both tests of the tier structure reject the null overwhelmingly: **ANOVA F = 5,590.1** and
**Kruskal-Wallis H = 4,672.2**. Both are reported because Levene's test rejects equal variances,
which violates an ANOVA assumption. The non-parametric test agrees, so the conclusion does not
depend on the broken assumption.

## 3. Five sub-categories are sold past their own break-even discount

Regressing margin on discount within each sub-category and solving for zero gives the ceiling
each line's own trading history implies. Comparing that to what is actually charged:

| Sub-category | Lines | Breaks even at | Sold at | Past the ceiling by | Margin | Fit R-sq |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Tables | 319 | 16.4% | 26.1% | 9.7 points | -8.56% | 0.86 |
| Binders | 1,523 | 28.8% | 37.2% | 8.4 points | 14.86% | 0.90 |
| Bookcases | 228 | 15.4% | 21.1% | 5.7 points | -3.02% | 0.82 |
| Appliances | 466 | 12.2% | 16.7% | 4.5 points | 16.87% | 0.94 |
| Machines | 115 | 27.0% | 30.6% | 3.6 points | 1.79% | 0.81 |

**Tables is the clearest case**: 63.6% of its lines lose money and it returns -8.56% overall on
$206,966 of sales, which puts it in the top third of sub-categories by revenue. This is a
pricing problem, not a demand problem.

**Binders is the largest by volume** and the most easily missed. It still shows a positive
14.86% margin overall, because its full-price sales are highly profitable, so the damage is
hidden inside the average rather than absent. 613 of its lines sit above the break-even
discount and lose $38,511 between them.

**Machines is the quiet one.** A 1.79% margin on $189,239 of sales means it is one policy change
away from joining Tables and Bookcases below zero.

At the other end, **Paper, Labels, and Envelopes break even only past a 70% discount** and are
never discounted beyond 20%. They have real promotional headroom.

## 4. Profit is concentrated, and the bottom fifth of customers give a quarter of it back

| Share of customers | Share of profit |
| --- | ---: |
| Top 5% | 39.0% |
| Top 10% | 57.3% |
| Top 20% | 81.4% |
| Top 30% | 97.1% |

**19.2% of customers generate 80% of profit.** The top 20 customers, 2.5% of the book, generate
26.0%.

The Pareto curve does something worth understanding: it climbs past 100%, **peaking at 124.9% at
the 638th of 793 customers**, then falls back to 100%. The overshoot is real. The profitable
customers generate roughly a quarter more profit than the business keeps, and **155 customers
hand $71,224 of it back**.

Those 155 are not a distinct type of buyer. **Their average discount is 23.8% against 15.6%
overall**, which puts them on the wrong side of the same cliff identified in section 1. The
customer problem and the pricing problem are the same problem, reached from two directions.

**Segment explains almost nothing.** Home Office carries the best margin at 14.03% and Consumer
the worst at 11.55%, a spread of under 2.5 points, with average order values between $449 and
$473. The share of loss-making lines runs 17.5% to 19.3% across all three. Segmenting discount
policy by customer type would be solving the wrong variable.

One nuance for account planning: the top 20 skews Corporate. 8 of 20 are Corporate accounts
against 29.8% of the customer base, and 9 are Consumer against 51.6%.

## 5. Regional performance diverges, and Central is going the wrong way

| Region | Sales | Profit | Margin | Loss-making lines | Worst sub-category |
| --- | ---: | ---: | ---: | ---: | --- |
| West | $725,458 | $108,418 | 14.94% | 9.9% | Bookcases |
| East | $678,781 | $91,523 | 13.48% | 19.4% | Tables |
| South | $391,722 | $46,749 | 11.93% | 16.0% | Tables |
| Central | $501,240 | $39,706 | 7.92% | 31.9% | Furnishings |

**Central runs at roughly half the West's margin with three times the failure rate.** Its margin
fell from 13.50% in 2019 to 5.13% in 2020 while sales stayed flat, so the trend is worsening.

The West grew sales 33.9% in 2019 and 33.4% in 2020 while improving margin to 17.51%. Whatever
it is doing differently is worth understanding before the next planning cycle.

## 6. Next quarter forecasts at $159,264, up 29% year over year

Three models were fitted on 42 months and scored against a six-month holdout:

| Model | MAPE | RMSE |
| --- | ---: | ---: |
| SARIMA (1,1,1)(1,1,0,12) | 18.0% | $17,960 |
| Prophet | 18.6% | $20,763 |
| Seasonal naive | 25.4% | $23,430 |

SARIMA wins and beats the naive baseline by 29%, so the added complexity is justified. An 18%
MAPE is honest but not precise: on a $50,000 month it implies a typical miss around $9,000. It
should be quoted alongside the forecast every time.

**Q1 2021: $159,264, with an 80% interval from $101,846 to $216,682.**

The comparison that matters is the same quarter a year earlier, $123,145, making this **+29%
year over year**. The preceding quarter delivered $280,054, but that is October to December, the
seasonal peak. Comparing against it would suggest a collapse where there is none.

Two limits worth stating. The series has only 48 monthly observations, four seasonal cycles,
which is the bare minimum for estimating annual seasonality and is why the interval is wide.
And this forecasts **revenue, not profit**. Growing sales into the current discount practices
would grow the losses along with them.

## What to do

1. **Cap discounts at the break-even rate for the five sub-categories in section 3.** Lines
   already above their cap carry $121,494 of losses, 42% of total company profit. That figure
   assumes volume holds at the lower discount, so treat it as the size of the prize rather than
   a committed recovery, and pilot on Tables first.
2. **Require named approval above 20%** rather than banning deep discounts. 4,798 lines already
   sell at full price at a 29.51% margin, so the demand is not universally discount-dependent.
3. **Review Central region pricing**, which is the weakest on every measure and deteriorating.
4. **Assign owners to the top 20 accounts**, which carry 26.0% of profit between them.
5. **Use Paper, Labels, and Envelopes for promotion** when promotion is needed. They have
   genuine headroom and are currently under-used for it.

## Caveats

- **Discounts cluster at 0% and 20%** rather than spreading evenly, and the 1-10% band holds
  only 94 lines. The cliff between 11-20% and 21-30% is well evidenced; the shape in between is
  not, and the break-even estimates interpolate across a lumpy distribution.
- **This is observational data.** Discount is not randomly assigned, so the regression measures
  association. It is plausible that hard-to-sell items attract both deep discounts and thin
  margins for a common reason. The recommendation to cap is a hypothesis worth piloting, not a
  proven causal claim.
- **11 rows have no postal code** and one pair of rows is an exact duplicate. Both are
  documented in the [data quality report](data_quality_report.md) and left in place.
- **The dataset is a public sample**, not real company data. The method is the deliverable here,
  not the business conclusion.
