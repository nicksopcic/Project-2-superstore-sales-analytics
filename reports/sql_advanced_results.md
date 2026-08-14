# Advanced SQL results

Generated from [`sql/03_advanced_queries.sql`](../sql/03_advanced_queries.sql) by `python -m src.run_sql_report`. Each section shows the business question, the result, and the SQL that produced it.

9 queries.

## Contents

1. [Running ytd sales by region](#running-ytd-sales-by-region)
2. [Sub category profit rank by region](#sub-category-profit-rank-by-region)
3. [Worst sub category per region](#worst-sub-category-per-region)
4. [Month over month sales growth](#month-over-month-sales-growth)
5. [Month over month sales growth by region](#month-over-month-sales-growth-by-region)
6. [Year over year growth by region](#year-over-year-growth-by-region)
7. [Customer lifetime value](#customer-lifetime-value)
8. [Customer profit pareto](#customer-profit-pareto)
9. [Loss making customers](#loss-making-customers)

## Running ytd sales by region

<a id="running-ytd-sales-by-region"></a>

**How is each region tracking against its own year, month by month? A running total resets every January, which is what a sales-ops YTD number means in practice.**

| region | year_month | month_sales | ytd_sales | ytd_profit |
| --- | --- | ---: | ---: | ---: |
| Central | 2017-01 | 1,539.91 | 1,539.91 | 118.49 |
| Central | 2017-02 | 1,233.17 | 2,773.08 | 413.30 |
| Central | 2017-03 | 5,827.60 | 8,600.68 | 139.25 |
| Central | 2017-04 | 3,712.34 | 12,313.02 | 368.63 |
| Central | 2017-05 | 4,048.51 | 16,361.53 | -137.39 |
| Central | 2017-06 | 9,646.30 | 26,007.83 | 1,108.73 |
| Central | 2017-07 | 6,740.57 | 32,748.40 | -2,946.60 |
| Central | 2017-08 | 3,022.18 | 35,770.58 | -2,318.17 |
| Central | 2017-09 | 34,408.69 | 70,179.27 | -895.38 |
| Central | 2017-10 | 8,965.76 | 79,145.03 | 445.87 |
| Central | 2017-11 | 14,057.57 | 93,202.60 | -348.29 |
| Central | 2017-12 | 10,635.57 | 103,838.16 | 539.55 |
| Central | 2018-01 | 2,510.51 | 2,510.51 | -602.85 |
| Central | 2018-02 | 2,527.59 | 5,038.10 | -271.87 |
| Central | 2018-03 | 6,730.27 | 11,768.37 | -220.46 |
| Central | 2018-04 | 11,642.06 | 23,410.42 | 771.60 |
| Central | 2018-05 | 8,623.90 | 32,034.32 | 1,735.53 |
| Central | 2018-06 | 3,713.19 | 35,747.51 | 1,314.86 |
| Central | 2018-07 | 7,605.57 | 43,353.08 | 1,620.12 |
| Central | 2018-08 | 9,301.45 | 52,654.53 | 2,651.70 |

_Showing 20 of 192 rows._


<details><summary>SQL</summary>

```sql
WITH monthly AS (
    SELECT
        g.region,
        d.year,
        d.month,
        d.year_month,
        sum(f.sales)  AS month_sales,
        sum(f.profit) AS month_profit
    FROM fact_sales f
    JOIN dim_geography g USING (geography_key)
    JOIN dim_date d ON f.order_date_key = d.date_key
    GROUP BY g.region, d.year, d.month, d.year_month
)
SELECT
    region,
    year_month,
    round(month_sales, 2) AS month_sales,
    round(sum(month_sales) OVER (
        PARTITION BY region, year
        ORDER BY month
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ), 2) AS ytd_sales,
    round(sum(month_profit) OVER (
        PARTITION BY region, year
        ORDER BY month
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ), 2) AS ytd_profit
FROM monthly
ORDER BY region, year_month
```

</details>

## Sub category profit rank by region

<a id="sub-category-profit-rank-by-region"></a>

**Within each region, which sub-categories earn and which bleed? Ranking inside the region rather than nationally is what lets a regional manager act on the list.**

| region | sub_category | sales | profit | margin_pct | profit_rank | loss_rank |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Central | Copiers | 37,259.57 | 15,608.84 | 41.89 | 1 | 17 |
| Central | Phones | 72,403.28 | 12,323.03 | 17.02 | 2 | 16 |
| Central | Accessories | 33,956.08 | 7,251.63 | 21.36 | 3 | 15 |
| Central | Paper | 17,491.90 | 6,971.90 | 39.86 | 4 | 14 |
| Central | Chairs | 85,230.65 | 6,592.72 | 7.74 | 5 | 13 |
| Central | Storage | 45,930.11 | 1,969.84 | 4.29 | 6 | 12 |
| Central | Envelopes | 4,636.87 | 1,777.53 | 38.33 | 7 | 11 |
| Central | Art | 5,765.34 | 1,195.16 | 20.73 | 8 | 10 |
| Central | Labels | 2,451.47 | 1,073.08 | 43.77 | 9 | 9 |
| Central | Fasteners | 778.03 | 236.62 | 30.41 | 10 | 8 |
| Central | Supplies | 9,467.37 | -661.89 | -6.99 | 11 | 7 |
| Central | Binders | 56,923.28 | -1,043.64 | -1.83 | 12 | 6 |
| Central | Machines | 26,797.38 | -1,486.07 | -5.55 | 13 | 5 |
| Central | Bookcases | 24,157.18 | -1,997.90 | -8.27 | 14 | 4 |
| Central | Appliances | 23,582.03 | -2,638.62 | -11.19 | 15 | 3 |
| Central | Tables | 39,154.97 | -3,559.65 | -9.09 | 16 | 2 |
| Central | Furnishings | 15,254.37 | -3,906.22 | -25.61 | 17 | 1 |
| East | Copiers | 53,219.46 | 17,022.84 | 31.99 | 1 | 17 |
| East | Phones | 100,614.98 | 12,314.69 | 12.24 | 2 | 16 |
| East | Binders | 53,498.00 | 11,267.93 | 21.06 | 3 | 15 |

_Showing 20 of 68 rows._


<details><summary>SQL</summary>

```sql
SELECT
    g.region,
    p.sub_category,
    round(sum(f.sales), 2)  AS sales,
    round(sum(f.profit), 2) AS profit,
    round(100.0 * sum(f.profit) / sum(f.sales), 2) AS margin_pct,
    RANK() OVER (PARTITION BY g.region ORDER BY sum(f.profit) DESC) AS profit_rank,
    RANK() OVER (PARTITION BY g.region ORDER BY sum(f.profit)) AS loss_rank
FROM fact_sales f
JOIN dim_geography g USING (geography_key)
JOIN dim_product p USING (product_key)
GROUP BY g.region, p.sub_category
ORDER BY g.region, profit_rank, p.sub_category
```

</details>

## Worst sub category per region

<a id="worst-sub-category-per-region"></a>

**The single worst sub-category in each region, pulled out of the ranking above. This is the shortlist for a discount policy change.**

| region | sub_category | sales | profit | margin_pct |
| --- | --- | ---: | ---: | ---: |
| East | Tables | 39,139.81 | -11,025.38 | -28.17 |
| South | Tables | 43,916.19 | -4,623.06 | -10.53 |
| Central | Furnishings | 15,254.37 | -3,906.22 | -25.61 |
| West | Bookcases | 36,004.12 | -1,646.51 | -4.57 |


<details><summary>SQL</summary>

```sql
WITH ranked AS (
    SELECT
        g.region,
        p.sub_category,
        sum(f.sales)  AS sales,
        sum(f.profit) AS profit,
        RANK() OVER (PARTITION BY g.region ORDER BY sum(f.profit)) AS loss_rank
    FROM fact_sales f
    JOIN dim_geography g USING (geography_key)
    JOIN dim_product p USING (product_key)
    GROUP BY g.region, p.sub_category
)
SELECT
    region,
    sub_category,
    round(sales, 2)  AS sales,
    round(profit, 2) AS profit,
    round(100.0 * profit / sales, 2) AS margin_pct
FROM ranked
WHERE loss_rank = 1
ORDER BY profit, region
```

</details>

## Month over month sales growth

<a id="month-over-month-sales-growth"></a>

**Is the business accelerating or decelerating? LAG() against the previous calendar month, across the whole book.**

| year_month | sales | prior_month_sales | sales_growth_pct | profit | profit_growth_pct |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2017-01 | 14,236.89 |  |  | 2,450.19 |  |
| 2017-02 | 4,519.89 | 14,236.89 | -68.30 | 862.31 | -64.80 |
| 2017-03 | 55,691.01 | 4,519.89 | 1,132.10 | 498.73 | -42.20 |
| 2017-04 | 28,295.34 | 55,691.01 | -49.20 | 3,488.84 | 599.50 |
| 2017-05 | 23,648.29 | 28,295.34 | -16.40 | 2,738.71 | -21.50 |
| 2017-06 | 34,595.13 | 23,648.29 | 46.30 | 4,976.52 | 81.70 |
| 2017-07 | 33,946.39 | 34,595.13 | -1.90 | -841.48 | -116.90 |
| 2017-08 | 27,909.47 | 33,946.39 | -17.80 | 5,318.11 | 732.00 |
| 2017-09 | 81,777.35 | 27,909.47 | 193.00 | 8,328.10 | 56.60 |
| 2017-10 | 31,453.39 | 81,777.35 | -61.50 | 3,448.26 | -58.60 |
| 2017-11 | 78,628.72 | 31,453.39 | 150.00 | 9,292.13 | 169.50 |
| 2017-12 | 69,545.62 | 78,628.72 | -11.60 | 8,983.57 | -3.30 |
| 2018-01 | 18,174.08 | 69,545.62 | -73.90 | -3,281.01 | -136.50 |
| 2018-02 | 11,951.41 | 18,174.08 | -34.20 | 2,813.85 | 185.80 |
| 2018-03 | 38,726.25 | 11,951.41 | 224.00 | 9,732.10 | 245.90 |
| 2018-04 | 34,195.21 | 38,726.25 | -11.70 | 4,187.50 | -57.00 |
| 2018-05 | 30,131.69 | 34,195.21 | -11.90 | 4,667.87 | 11.50 |
| 2018-06 | 24,797.29 | 30,131.69 | -17.70 | 3,335.56 | -28.50 |
| 2018-07 | 28,765.32 | 24,797.29 | 16.00 | 3,288.65 | -1.40 |
| 2018-08 | 36,898.33 | 28,765.32 | 28.30 | 5,355.81 | 62.90 |

_Showing 20 of 48 rows._


<details><summary>SQL</summary>

```sql
WITH monthly AS (
    SELECT
        d.year_month,
        sum(f.sales)  AS sales,
        sum(f.profit) AS profit
    FROM fact_sales f
    JOIN dim_date d ON f.order_date_key = d.date_key
    GROUP BY d.year_month
)
SELECT
    year_month,
    round(sales, 2) AS sales,
    round(LAG(sales) OVER (ORDER BY year_month), 2) AS prior_month_sales,
    round(100.0 * (sales - LAG(sales) OVER (ORDER BY year_month))
          / LAG(sales) OVER (ORDER BY year_month), 1) AS sales_growth_pct,
    round(profit, 2) AS profit,
    round(100.0 * (profit - LAG(profit) OVER (ORDER BY year_month))
          / nullif(abs(LAG(profit) OVER (ORDER BY year_month)), 0), 1) AS profit_growth_pct
FROM monthly
ORDER BY year_month
```

</details>

## Month over month sales growth by region

<a id="month-over-month-sales-growth-by-region"></a>

**The same comparison held inside each region, so a national swing does not hide a regional one moving the other way.**

| region | year_month | sales | prior_month_sales | sales_growth_pct |
| --- | --- | ---: | ---: | ---: |
| Central | 2017-01 | 1,539.91 |  |  |
| Central | 2017-02 | 1,233.17 | 1,539.91 | -19.90 |
| Central | 2017-03 | 5,827.60 | 1,233.17 | 372.60 |
| Central | 2017-04 | 3,712.34 | 5,827.60 | -36.30 |
| Central | 2017-05 | 4,048.51 | 3,712.34 | 9.10 |
| Central | 2017-06 | 9,646.30 | 4,048.51 | 138.30 |
| Central | 2017-07 | 6,740.57 | 9,646.30 | -30.10 |
| Central | 2017-08 | 3,022.18 | 6,740.57 | -55.20 |
| Central | 2017-09 | 34,408.69 | 3,022.18 | 1,038.50 |
| Central | 2017-10 | 8,965.76 | 34,408.69 | -73.90 |
| Central | 2017-11 | 14,057.57 | 8,965.76 | 56.80 |
| Central | 2017-12 | 10,635.57 | 14,057.57 | -24.30 |
| Central | 2018-01 | 2,510.51 | 10,635.57 | -76.40 |
| Central | 2018-02 | 2,527.59 | 2,510.51 | 0.70 |
| Central | 2018-03 | 6,730.27 | 2,527.59 | 166.30 |
| Central | 2018-04 | 11,642.06 | 6,730.27 | 73.00 |
| Central | 2018-05 | 8,623.90 | 11,642.06 | -25.90 |
| Central | 2018-06 | 3,713.19 | 8,623.90 | -56.90 |
| Central | 2018-07 | 7,605.57 | 3,713.19 | 104.80 |
| Central | 2018-08 | 9,301.45 | 7,605.57 | 22.30 |

_Showing 20 of 192 rows._


<details><summary>SQL</summary>

```sql
WITH monthly AS (
    SELECT
        g.region,
        d.year_month,
        sum(f.sales) AS sales
    FROM fact_sales f
    JOIN dim_geography g USING (geography_key)
    JOIN dim_date d ON f.order_date_key = d.date_key
    GROUP BY g.region, d.year_month
)
SELECT
    region,
    year_month,
    round(sales, 2) AS sales,
    round(LAG(sales) OVER (PARTITION BY region ORDER BY year_month), 2) AS prior_month_sales,
    round(100.0 * (sales - LAG(sales) OVER (PARTITION BY region ORDER BY year_month))
          / LAG(sales) OVER (PARTITION BY region ORDER BY year_month), 1) AS sales_growth_pct
FROM monthly
ORDER BY region, year_month
```

</details>

## Year over year growth by region

<a id="year-over-year-growth-by-region"></a>

**The comparison that survives seasonality. Month over month is noisy in a business with a Q4 peak, so the annual view is the one to quote in a QBR.**

| region | year | sales | sales_growth_pct | profit | margin_pct |
| --- | ---: | ---: | ---: | ---: | ---: |
| Central | 2017 | 103,838.16 |  | 539.55 | 0.52 |
| Central | 2018 | 102,874.22 | -0.90 | 11,716.80 | 11.39 |
| Central | 2019 | 147,429.38 | 43.30 | 19,899.16 | 13.50 |
| Central | 2020 | 147,098.13 | -0.20 | 7,550.84 | 5.13 |
| East | 2017 | 128,680.46 |  | 17,059.61 | 13.26 |
| East | 2018 | 156,332.06 | 21.50 | 21,091.01 | 13.49 |
| East | 2019 | 180,685.82 | 15.60 | 20,141.60 | 11.15 |
| East | 2020 | 213,082.90 | 17.90 | 33,230.56 | 15.60 |
| South | 2017 | 103,845.84 |  | 11,879.12 | 11.44 |
| South | 2018 | 71,359.98 | -31.30 | 8,318.59 | 11.66 |
| South | 2019 | 93,610.22 | 31.20 | 17,702.81 | 18.91 |
| South | 2020 | 122,905.86 | 31.30 | 8,848.91 | 7.20 |
| West | 2017 | 147,883.03 |  | 20,065.69 | 13.57 |
| West | 2018 | 139,966.25 | -5.40 | 20,492.19 | 14.64 |
| West | 2019 | 187,480.18 | 33.90 | 24,051.61 | 12.83 |
| West | 2020 | 250,128.37 | 33.40 | 43,808.96 | 17.51 |


<details><summary>SQL</summary>

```sql
WITH yearly AS (
    SELECT
        g.region,
        d.year,
        sum(f.sales)  AS sales,
        sum(f.profit) AS profit
    FROM fact_sales f
    JOIN dim_geography g USING (geography_key)
    JOIN dim_date d ON f.order_date_key = d.date_key
    GROUP BY g.region, d.year
)
SELECT
    region,
    year,
    round(sales, 2) AS sales,
    round(100.0 * (sales - LAG(sales) OVER (PARTITION BY region ORDER BY year))
          / LAG(sales) OVER (PARTITION BY region ORDER BY year), 1) AS sales_growth_pct,
    round(profit, 2) AS profit,
    round(100.0 * profit / sales, 2) AS margin_pct
FROM yearly
ORDER BY region, year
```

</details>

## Customer lifetime value

<a id="customer-lifetime-value"></a>

**What is each customer worth over the whole period? Sales, profit, and order count per customer, which Phase 6 turns into the Pareto and CLV work.**

| customer_id | customer_name | segment | orders | order_lines | lifetime_sales | lifetime_profit | margin_pct | avg_order_value | first_order | last_order | days_active |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: |
| TC-20980 | Tamara Chand | Corporate | 5 | 12 | 19,052.22 | 8,981.32 | 47.14 | 3,810.44 | 2017-11-07 | 2019-11-26 | 749 |
| RB-19360 | Raymond Buch | Consumer | 6 | 18 | 15,117.34 | 6,976.10 | 46.15 | 2,519.56 | 2019-04-01 | 2020-09-25 | 543 |
| SC-20095 | Sanjit Chand | Consumer | 9 | 22 | 14,142.33 | 5,757.41 | 40.71 | 1,571.37 | 2017-02-12 | 2020-01-15 | 1,067 |
| HL-15040 | Hunter Lopez | Consumer | 6 | 11 | 12,873.30 | 5,622.43 | 43.68 | 2,145.55 | 2017-01-20 | 2020-11-17 | 1,397 |
| AB-10105 | Adrian Barton | Consumer | 10 | 20 | 14,473.57 | 5,444.81 | 37.62 | 1,447.36 | 2017-12-20 | 2020-11-19 | 1,065 |
| TA-21385 | Tom Ashbrook | Home Office | 4 | 10 | 14,595.62 | 4,703.79 | 32.23 | 3,648.91 | 2017-09-12 | 2020-10-22 | 1,136 |
| CM-12385 | Christopher Martinez | Consumer | 4 | 10 | 8,954.02 | 3,899.89 | 43.55 | 2,238.51 | 2018-03-16 | 2020-11-23 | 983 |
| KD-16495 | Keith Dawkins | Corporate | 12 | 28 | 8,181.26 | 3,038.63 | 37.14 | 681.77 | 2017-09-28 | 2020-09-09 | 1,077 |
| AR-10540 | Andy Reiter | Consumer | 6 | 9 | 6,608.45 | 2,884.62 | 43.65 | 1,101.41 | 2017-11-25 | 2020-12-24 | 1,125 |
| DR-12940 | Daniel Raglin | Home Office | 8 | 13 | 8,350.87 | 2,869.08 | 34.36 | 1,043.86 | 2017-03-28 | 2020-11-10 | 1,323 |
| TB-21400 | Tom Boeckenhauer | Consumer | 7 | 17 | 9,133.99 | 2,798.37 | 30.64 | 1,304.86 | 2017-01-21 | 2020-06-11 | 1,237 |
| NM-18445 | Nathan Mautz | Home Office | 7 | 14 | 6,459.34 | 2,751.68 | 42.60 | 922.76 | 2017-02-08 | 2020-07-23 | 1,261 |
| SE-20110 | Sanjit Engle | Consumer | 11 | 19 | 12,209.44 | 2,650.68 | 21.71 | 1,109.95 | 2017-04-11 | 2020-12-21 | 1,350 |
| BS-11365 | Bill Shonely | Corporate | 5 | 9 | 10,501.65 | 2,616.06 | 24.91 | 2,100.33 | 2017-05-04 | 2019-06-20 | 777 |
| HM-14860 | Harry Marie | Corporate | 10 | 20 | 8,236.76 | 2,437.98 | 29.60 | 823.68 | 2017-07-21 | 2020-12-28 | 1,256 |
| TS-21370 | Todd Sumrall | Corporate | 6 | 15 | 11,891.75 | 2,371.71 | 19.94 | 1,981.96 | 2017-10-28 | 2020-11-24 | 1,123 |
| BM-11650 | Brian Moss | Corporate | 11 | 29 | 7,294.19 | 2,199.28 | 30.15 | 663.11 | 2017-07-09 | 2020-11-27 | 1,237 |
| CC-12370 | Christopher Conant | Consumer | 5 | 11 | 12,129.07 | 2,177.05 | 17.95 | 2,425.81 | 2019-05-23 | 2020-11-17 | 544 |
| JW-15220 | Jane Waco | Corporate | 6 | 14 | 7,721.71 | 2,173.71 | 28.15 | 1,286.95 | 2018-04-30 | 2020-11-18 | 933 |
| HW-14935 | Helen Wasserman | Corporate | 8 | 20 | 9,300.25 | 2,164.16 | 23.27 | 1,162.53 | 2018-09-27 | 2020-09-04 | 708 |

_Showing 20 of 793 rows._


<details><summary>SQL</summary>

```sql
WITH customer_lifetime AS (
    SELECT
        c.customer_id,
        c.customer_name,
        c.segment,
        count(DISTINCT f.order_id) AS orders,
        count(*)                   AS order_lines,
        sum(f.sales)               AS lifetime_sales,
        sum(f.profit)              AS lifetime_profit,
        min(f.order_date)          AS first_order,
        max(f.order_date)          AS last_order
    FROM fact_sales f
    JOIN dim_customer c USING (customer_key)
    GROUP BY c.customer_id, c.customer_name, c.segment
)
SELECT
    customer_id,
    customer_name,
    segment,
    orders,
    order_lines,
    round(lifetime_sales, 2)  AS lifetime_sales,
    round(lifetime_profit, 2) AS lifetime_profit,
    round(100.0 * lifetime_profit / lifetime_sales, 2) AS margin_pct,
    round(lifetime_sales / orders, 2) AS avg_order_value,
    first_order,
    last_order,
    date_diff('day', first_order, last_order) AS days_active
FROM customer_lifetime
ORDER BY lifetime_profit DESC, customer_id
```

</details>

## Customer profit pareto

<a id="customer-profit-pareto"></a>

**Do a small share of customers carry the profit? Cumulative profit share, ordered from the most profitable customer down. Read the cumulative share carefully. Loss-making customers subtract, so the running share climbs above 100% and then falls back to 100% at the last row. The peak is the real concentration: it is how much profit the profitable customers generate before the rest give some of it back.**

| profit_rank | customer_id | customer_name | segment | orders | lifetime_sales | lifetime_profit | cumulative_profit | pct_of_customers | pct_of_total_profit |
| ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | TC-20980 | Tamara Chand | Corporate | 5 | 19,052.22 | 8,981.32 | 8,981.32 | 0.10 | 3.10 |
| 2 | RB-19360 | Raymond Buch | Consumer | 6 | 15,117.34 | 6,976.10 | 15,957.42 | 0.30 | 5.60 |
| 3 | SC-20095 | Sanjit Chand | Consumer | 9 | 14,142.33 | 5,757.41 | 21,714.83 | 0.40 | 7.60 |
| 4 | HL-15040 | Hunter Lopez | Consumer | 6 | 12,873.30 | 5,622.43 | 27,337.26 | 0.50 | 9.50 |
| 5 | AB-10105 | Adrian Barton | Consumer | 10 | 14,473.57 | 5,444.81 | 32,782.07 | 0.60 | 11.40 |
| 6 | TA-21385 | Tom Ashbrook | Home Office | 4 | 14,595.62 | 4,703.79 | 37,485.85 | 0.80 | 13.10 |
| 7 | CM-12385 | Christopher Martinez | Consumer | 4 | 8,954.02 | 3,899.89 | 41,385.75 | 0.90 | 14.50 |
| 8 | KD-16495 | Keith Dawkins | Corporate | 12 | 8,181.26 | 3,038.63 | 44,424.37 | 1.00 | 15.50 |
| 9 | AR-10540 | Andy Reiter | Consumer | 6 | 6,608.45 | 2,884.62 | 47,308.99 | 1.10 | 16.50 |
| 10 | DR-12940 | Daniel Raglin | Home Office | 8 | 8,350.87 | 2,869.08 | 50,178.07 | 1.30 | 17.50 |
| 11 | TB-21400 | Tom Boeckenhauer | Consumer | 7 | 9,133.99 | 2,798.37 | 52,976.44 | 1.40 | 18.50 |
| 12 | NM-18445 | Nathan Mautz | Home Office | 7 | 6,459.34 | 2,751.68 | 55,728.12 | 1.50 | 19.50 |
| 13 | SE-20110 | Sanjit Engle | Consumer | 11 | 12,209.44 | 2,650.68 | 58,378.80 | 1.60 | 20.40 |
| 14 | BS-11365 | Bill Shonely | Corporate | 5 | 10,501.65 | 2,616.06 | 60,994.86 | 1.80 | 21.30 |
| 15 | HM-14860 | Harry Marie | Corporate | 10 | 8,236.76 | 2,437.98 | 63,432.85 | 1.90 | 22.10 |
| 16 | TS-21370 | Todd Sumrall | Corporate | 6 | 11,891.75 | 2,371.71 | 65,804.56 | 2.00 | 23.00 |
| 17 | BM-11650 | Brian Moss | Corporate | 11 | 7,294.19 | 2,199.28 | 68,003.84 | 2.10 | 23.70 |
| 18 | CC-12370 | Christopher Conant | Consumer | 5 | 12,129.07 | 2,177.05 | 70,180.89 | 2.30 | 24.50 |
| 19 | JW-15220 | Jane Waco | Corporate | 6 | 7,721.71 | 2,173.71 | 72,354.60 | 2.40 | 25.30 |
| 20 | HW-14935 | Helen Wasserman | Corporate | 8 | 9,300.25 | 2,164.16 | 74,518.76 | 2.50 | 26.00 |

_Showing 20 of 793 rows._


<details><summary>SQL</summary>

```sql
WITH customer_lifetime AS (
    SELECT
        c.customer_id,
        c.customer_name,
        c.segment,
        count(DISTINCT f.order_id) AS orders,
        sum(f.sales)               AS lifetime_sales,
        sum(f.profit)              AS lifetime_profit
    FROM fact_sales f
    JOIN dim_customer c USING (customer_key)
    GROUP BY c.customer_id, c.customer_name, c.segment
),
ranked AS (
    SELECT
        customer_id,
        customer_name,
        segment,
        orders,
        lifetime_sales,
        lifetime_profit,
        ROW_NUMBER() OVER (ORDER BY lifetime_profit DESC, customer_id) AS profit_rank,
        count(*) OVER ()                                  AS total_customers,
        sum(lifetime_profit) OVER ()                      AS total_profit,
        sum(lifetime_profit) OVER (
            ORDER BY lifetime_profit DESC, customer_id
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_profit
    FROM customer_lifetime
)
SELECT
    profit_rank,
    customer_id,
    customer_name,
    segment,
    orders,
    round(lifetime_sales, 2)   AS lifetime_sales,
    round(lifetime_profit, 2)  AS lifetime_profit,
    round(cumulative_profit, 2) AS cumulative_profit,
    round(100.0 * profit_rank / total_customers, 1)     AS pct_of_customers,
    round(100.0 * cumulative_profit / total_profit, 1)  AS pct_of_total_profit
FROM ranked
ORDER BY profit_rank
```

</details>

## Loss making customers

<a id="loss-making-customers"></a>

**Which customers cost money overall? A customer can order steadily and still be worth less than nothing once discounts are counted.**

| customer_id | customer_name | segment | orders | lifetime_sales | lifetime_profit | avg_discount |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| CS-12505 | Cindy Stewart | Consumer | 6 | 5,690.06 | -6,626.39 | 0.2 |
| GT-14635 | Grant Thornton | Corporate | 3 | 9,351.21 | -4,108.66 | 0.25 |
| LF-17185 | Luke Foster | Consumer | 7 | 3,930.51 | -3,583.98 | 0.3188 |
| SR-20425 | Sharelle Roach | Home Office | 5 | 3,233.48 | -3,333.91 | 0.3667 |
| HG-14965 | Henry Goldwyn | Corporate | 12 | 3,247.64 | -2,797.96 | 0.1706 |
| NC-18415 | Nathan Cano | Consumer | 6 | 2,218.99 | -2,204.81 | 0.2643 |
| SB-20290 | Sean Braxton | Corporate | 7 | 8,057.89 | -2,082.75 | 0.2412 |
| SM-20320 | Sean Miller | Home Office | 5 | 25,043.05 | -1,980.74 | 0.2467 |
| CP-12340 | Christine Phan | Corporate | 8 | 5,888.28 | -1,850.30 | 0.2133 |
| NF-18385 | Natalie Fritzler | Consumer | 7 | 8,322.83 | -1,695.97 | 0.25 |
| BM-11140 | Becky Martin | Consumer | 4 | 11,789.63 | -1,659.96 | 0.1688 |
| TB-21520 | Tracy Blumstein | Consumer | 9 | 4,737.49 | -1,603.05 | 0.265 |
| DC-12850 | Dan Campbell | Consumer | 9 | 3,336.17 | -1,441.63 | 0.2111 |
| DB-13120 | David Bremer | Corporate | 7 | 2,973.09 | -1,421.77 | 0.1429 |
| RO-19780 | Rose O'Brian | Consumer | 7 | 3,815.48 | -1,262.57 | 0.2917 |
| TP-21415 | Tom Prescott | Consumer | 5 | 5,329.00 | -1,087.39 | 0.462 |
| ZC-21910 | Zuschuss Carroll | Consumer | 13 | 8,025.71 | -1,032.15 | 0.2548 |
| VP-21760 | Victoria Pisteka | Corporate | 7 | 3,360.53 | -1,018.78 | 0.1714 |
| SS-20410 | Shahid Shariari | Consumer | 6 | 3,056.81 | -1,010.97 | 0.2583 |
| OT-18730 | Olvera Toch | Consumer | 5 | 3,818.62 | -925.12 | 0.16 |

_Showing 20 of 155 rows._


<details><summary>SQL</summary>

```sql
WITH customer_lifetime AS (
    SELECT
        c.customer_id,
        c.customer_name,
        c.segment,
        count(DISTINCT f.order_id) AS orders,
        sum(f.sales)               AS lifetime_sales,
        sum(f.profit)              AS lifetime_profit,
        avg(f.discount)            AS avg_discount
    FROM fact_sales f
    JOIN dim_customer c USING (customer_key)
    GROUP BY c.customer_id, c.customer_name, c.segment
)
SELECT
    customer_id,
    customer_name,
    segment,
    orders,
    round(lifetime_sales, 2)  AS lifetime_sales,
    round(lifetime_profit, 2) AS lifetime_profit,
    round(avg_discount, 4)    AS avg_discount
FROM customer_lifetime
WHERE lifetime_profit < 0
ORDER BY lifetime_profit, customer_id
```

</details>
