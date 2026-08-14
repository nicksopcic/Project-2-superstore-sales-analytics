# Discount and profit analysis

Regenerate with `python -m src.profitability`. Every number here is computed from the validated star schema, not copied by hand.

## The question

Does discounting explain the margin damage, and if so, where is the ceiling?

## Regression

Margin on discount, quantity, and category dummies, over 9,994 order lines with HC3 robust standard errors. Adjusted R-squared **0.751**.

| term | coefficient | std_error | t | p_value | ci_low | ci_high |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Intercept | 37.67 | 0.63 | 60.01 | 0 | 36.44 | 38.90 |
| C(category)[T.Office Supplies] | 6.68 | 0.51 | 13.05 | 0 | 5.67 | 7.68 |
| C(category)[T.Technology] | 3.62 | 0.56 | 6.44 | 0 | 2.52 | 4.72 |
| discount | -195.17 | 2.31 | -84.61 | 0 | -199.69 | -190.65 |
| quantity | 0.04 | 0.10 | 0.39 | 0.6937 | -0.16 | 0.24 |


The discount coefficient is **-195.2**, meaning each additional 10 points of discount is associated with a **19.5 point** fall in margin, holding quantity and category constant (p = 0.00e+00).

Discount alone accounts for nearly all of the explained variance. Quantity contributes a coefficient of 0.040 (p = 0.694), which is negligible next to the discount effect.

### The same model against dollar profit

The plan asks for profit as the response, so it is reported here too. It is the weaker specification, because dollar profit mixes pricing quality with order size.

| term | coefficient | std_error | t | p_value | ci_low | ci_high |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Intercept | 23.69 | 5.84 | 4.05 | 0.0001 | 12.24 | 35.14 |
| C(category)[T.Office Supplies] | 7.46 | 3.39 | 2.20 | 0.0278 | 0.81 | 14.10 |
| C(category)[T.Technology] | 60.12 | 10.23 | 5.88 | 0 | 40.07 | 80.18 |
| discount | -243.61 | 16.82 | -14.48 | 0 | -276.59 | -210.64 |
| quantity | 7.23 | 1.32 | 5.49 | 0 | 4.65 | 9.81 |


Each additional 10 points of discount is associated with **$24.36 lower profit per line item**, controlling for quantity and category (p = 1.63e-47). Adjusted R-squared is only 0.061, against 0.751 for the margin model.

## Do the discount tiers actually differ?

| discount_tier | order_lines | sales | profit | mean_margin_pct | median_margin_pct | pct_loss_making |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0% | 4,798 | 1,087,908.47 | 320,987.60 | 34.02 | 34.00 | 0 |
| 1-10% | 94 | 54,369.35 | 9,029.18 | 15.58 | 16.67 | 4.26 |
| 11-20% | 3,709 | 792,152.89 | 91,756.30 | 17.48 | 16.25 | 13.99 |
| 21-30% | 227 | 103,226.65 | -10,369.28 | -11.55 | -8.57 | 91.63 |
| 30%+ | 1,166 | 259,543.49 | -125,006.78 | -91.47 | -73.33 | 97.77 |


**ANOVA**: F = 5,590.1, p = 0.00e+00. **Kruskal-Wallis**: H = 4,672.2, p = 0.00e+00.

Levene's test rejects equal variances (p = 0.00e+00), which is expected given how much wider margin spreads at high discounts. That violates an ANOVA assumption, which is exactly why the non-parametric Kruskal-Wallis is reported alongside it. Both reject the null at any conventional threshold, so the tier differences are not an artefact of the assumption failure.

## Break-even discount by sub-category

A per-sub-category regression of margin on discount, solved for the point where fitted margin crosses zero. This is the discount ceiling each line's own history implies.

| sub_category | category | order_lines | avg_discount | max_discount | margin_pct | r_squared | breakeven_discount | note | headroom | over_discounted |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| Appliances | Office Supplies | 466 | 0.1665 | 0.8 | 16.87 | 0.9384 | 0.1215 | within observed range | -0.045 | yes |
| Bookcases | Furniture | 228 | 0.2111 | 0.7 | -3.02 | 0.8207 | 0.154 | within observed range | -0.0571 | yes |
| Storage | Office Supplies | 846 | 0.0747 | 0.2 | 9.51 | 0.4278 | 0.1555 | within observed range | 0.0808 | no |
| Tables | Furniture | 319 | 0.2613 | 0.5 | -8.56 | 0.8641 | 0.1639 | within observed range | -0.0974 | yes |
| Supplies | Office Supplies | 190 | 0.0768 | 0.2 | -2.55 | 0.4428 | 0.1681 | within observed range | 0.0912 | no |
| Chairs | Furniture | 617 | 0.1702 | 0.3 | 8.10 | 0.6389 | 0.2085 | within observed range | 0.0383 | no |
| Furnishings | Furniture | 957 | 0.1383 | 0.6 | 14.24 | 0.8042 | 0.2225 | within observed range | 0.0842 | no |
| Phones | Technology | 889 | 0.1546 | 0.4 | 13.49 | 0.5692 | 0.2667 | within observed range | 0.1121 | no |
| Machines | Technology | 115 | 0.3061 | 0.7 | 1.79 | 0.8129 | 0.2699 | within observed range | -0.0362 | yes |
| Binders | Office Supplies | 1,523 | 0.3723 | 0.8 | 14.86 | 0.9045 | 0.2879 | within observed range | -0.0844 | yes |
| Accessories | Technology | 775 | 0.0785 | 0.2 | 25.05 | 0.3018 | 0.3201 | beyond the 20% ever offered | 0.2416 | no |
| Art | Office Supplies | 796 | 0.0749 | 0.2 | 24.07 | 0.5729 | 0.3767 | beyond the 20% ever offered | 0.3018 | no |
| Fasteners | Office Supplies | 217 | 0.082 | 0.2 | 31.40 | 0.099 | 0.5708 | beyond the 20% ever offered | 0.4888 | no |
| Copiers | Technology | 68 | 0.1618 | 0.4 | 37.20 | 0.6566 | 0.5825 | beyond the 40% ever offered | 0.4207 | no |
| Labels | Office Supplies | 364 | 0.0687 | 0.2 | 44.42 | 0.9549 | 0.7175 | beyond the 20% ever offered | 0.6488 | no |
| Paper | Office Supplies | 1,370 | 0.0749 | 0.2 | 43.39 | 0.9438 | 0.7249 | beyond the 20% ever offered | 0.6501 | no |
| Envelopes | Office Supplies | 254 | 0.0803 | 0.2 | 42.27 | 0.9314 | 0.7406 | beyond the 20% ever offered | 0.6603 | no |


10 sub-categories have a break-even point inside the range of discounts actually offered, which makes them the actionable list. Where the note says the crossing sits beyond the maximum discount ever offered, the line has not yet been discounted hard enough to lose money on average.

### Already past the ceiling

`headroom` is the break-even discount minus the discount currently being given. Where it is negative, the line is routinely sold below the point its own history says it stops paying. These are the discount caps to set.

| sub_category | category | order_lines | avg_discount | breakeven_discount | headroom | margin_pct |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Tables | Furniture | 319 | 0.2613 | 0.1639 | -0.0974 | -8.56 |
| Binders | Office Supplies | 1,523 | 0.3723 | 0.2879 | -0.0844 | 14.86 |
| Bookcases | Furniture | 228 | 0.2111 | 0.154 | -0.0571 | -3.02 |
| Appliances | Office Supplies | 466 | 0.1665 | 0.1215 | -0.045 | 16.87 |
| Machines | Technology | 115 | 0.3061 | 0.2699 | -0.0362 | 1.79 |


Tables is the clearest case: it breaks even at 16.4% and is sold at 26.1% on average, 9.7% past its own ceiling, for a -8.6% margin across 319 lines.
