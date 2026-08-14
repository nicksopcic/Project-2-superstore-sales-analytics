# Fundamental SQL results

Generated from [`sql/02_fundamental_queries.sql`](../sql/02_fundamental_queries.sql) by `python -m src.run_sql_report`. Each section shows the business question, the result, and the SQL that produced it.

13 queries.

## Contents

1. [Sales profit margin by region](#sales-profit-margin-by-region)
2. [Sales profit margin by segment](#sales-profit-margin-by-segment)
3. [Sales profit margin by category](#sales-profit-margin-by-category)
4. [Margin by region and category](#margin-by-region-and-category)
5. [Top 10 sub categories by profit](#top-10-sub-categories-by-profit)
6. [Bottom 10 sub categories by profit](#bottom-10-sub-categories-by-profit)
7. [Sales profit by year](#sales-profit-by-year)
8. [Sales profit by month](#sales-profit-by-month)
9. [Seasonality by calendar month](#seasonality-by-calendar-month)
10. [Avg discount by category](#avg-discount-by-category)
11. [Avg discount by sub category](#avg-discount-by-sub-category)
12. [Margin by discount band](#margin-by-discount-band)
13. [Ship mode mix](#ship-mode-mix)

## Sales profit margin by region

<a id="sales-profit-margin-by-region"></a>

**Which regions carry the business, and which convert revenue into profit efficiently? The West and the East are the volume leaders. Central is the margin problem.**

| region | order_lines | orders | sales | profit | margin_pct | avg_discount | pct_lines_loss_making |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| West | 3,203 | 1,611 | 725,457.82 | 108,418.45 | 14.94 | 0.1093 | 9.90 |
| East | 2,848 | 1,401 | 678,781.24 | 91,522.78 | 13.48 | 0.1454 | 19.40 |
| South | 1,620 | 822 | 391,721.91 | 46,749.43 | 11.93 | 0.1473 | 16.00 |
| Central | 2,323 | 1,175 | 501,239.89 | 39,706.36 | 7.92 | 0.2404 | 31.90 |


<details><summary>SQL</summary>

```sql
SELECT
    g.region,
    count(*)                                            AS order_lines,
    count(DISTINCT f.order_id)                          AS orders,
    round(sum(f.sales), 2)                              AS sales,
    round(sum(f.profit), 2)                             AS profit,
    round(100.0 * sum(f.profit) / sum(f.sales), 2)      AS margin_pct,
    round(avg(f.discount), 4)                           AS avg_discount,
    round(100.0 * sum(f.is_loss_making::INT) / count(*), 1) AS pct_lines_loss_making
FROM fact_sales f
JOIN dim_geography g USING (geography_key)
GROUP BY g.region
ORDER BY profit DESC, g.region
```

</details>

## Sales profit margin by segment

<a id="sales-profit-margin-by-segment"></a>

**Do any customer segments buy at materially worse margin than the others?**

| segment | customers | orders | sales | profit | margin_pct | avg_order_value | avg_discount |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Consumer | 409 | 2,586 | 1,161,401.34 | 134,119.21 | 11.55 | 449.11 | 0.1581 |
| Corporate | 236 | 1,514 | 706,146.37 | 91,979.13 | 13.03 | 466.41 | 0.1582 |
| Home Office | 148 | 909 | 429,653.15 | 60,298.68 | 14.03 | 472.67 | 0.1471 |


<details><summary>SQL</summary>

```sql
SELECT
    c.segment,
    count(DISTINCT c.customer_key)                      AS customers,
    count(DISTINCT f.order_id)                          AS orders,
    round(sum(f.sales), 2)                              AS sales,
    round(sum(f.profit), 2)                             AS profit,
    round(100.0 * sum(f.profit) / sum(f.sales), 2)      AS margin_pct,
    round(sum(f.sales) / count(DISTINCT f.order_id), 2) AS avg_order_value,
    round(avg(f.discount), 4)                           AS avg_discount
FROM fact_sales f
JOIN dim_customer c USING (customer_key)
GROUP BY c.segment
ORDER BY profit DESC, c.segment
```

</details>

## Sales profit margin by category

<a id="sales-profit-margin-by-category"></a>

**Which of the three categories actually earns its shelf space?**

| category | order_lines | sales | pct_of_sales | profit | pct_of_profit | margin_pct |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Technology | 1,847 | 836,154.03 | 36.40 | 145,454.95 | 50.80 | 17.40 |
| Office Supplies | 6,026 | 719,047.03 | 31.30 | 122,490.80 | 42.80 | 17.04 |
| Furniture | 2,121 | 741,999.80 | 32.30 | 18,451.27 | 6.40 | 2.49 |


<details><summary>SQL</summary>

```sql
SELECT
    p.category,
    count(*)                                            AS order_lines,
    round(sum(f.sales), 2)                              AS sales,
    round(100.0 * sum(f.sales) / sum(sum(f.sales)) OVER (), 1) AS pct_of_sales,
    round(sum(f.profit), 2)                             AS profit,
    round(100.0 * sum(f.profit) / sum(sum(f.profit)) OVER (), 1) AS pct_of_profit,
    round(100.0 * sum(f.profit) / sum(f.sales), 2)      AS margin_pct
FROM fact_sales f
JOIN dim_product p USING (product_key)
GROUP BY p.category
ORDER BY profit DESC, p.category
```

</details>

## Margin by region and category

<a id="margin-by-region-and-category"></a>

**Where does a specific category go wrong in a specific region? This is the cell-level view the regional managers need, rather than either margin averaged on its own.**

| region | category | sales | profit | margin_pct | avg_discount |
| --- | --- | ---: | ---: | ---: | ---: |
| Central | Furniture | 163,797.16 | -2,871.05 | -1.75 | 0.2974 |
| East | Furniture | 208,291.20 | 3,046.17 | 1.46 | 0.1541 |
| West | Furniture | 252,612.74 | 11,504.95 | 4.55 | 0.1314 |
| Central | Office Supplies | 167,026.42 | 8,879.98 | 5.32 | 0.2527 |
| South | Furniture | 117,298.68 | 6,771.21 | 5.77 | 0.1215 |
| South | Technology | 148,771.91 | 19,991.83 | 13.44 | 0.1078 |
| South | Office Supplies | 125,651.31 | 19,986.39 | 15.91 | 0.1674 |
| West | Technology | 251,991.83 | 44,303.65 | 17.58 | 0.1339 |
| East | Technology | 264,973.98 | 47,462.04 | 17.91 | 0.1434 |
| Central | Technology | 170,416.31 | 33,697.43 | 19.77 | 0.1331 |
| East | Office Supplies | 205,516.05 | 41,014.58 | 19.96 | 0.1429 |
| West | Office Supplies | 220,853.25 | 52,609.85 | 23.82 | 0.0934 |


<details><summary>SQL</summary>

```sql
SELECT
    g.region,
    p.category,
    round(sum(f.sales), 2)                              AS sales,
    round(sum(f.profit), 2)                             AS profit,
    round(100.0 * sum(f.profit) / sum(f.sales), 2)      AS margin_pct,
    round(avg(f.discount), 4)                           AS avg_discount
FROM fact_sales f
JOIN dim_geography g USING (geography_key)
JOIN dim_product p USING (product_key)
GROUP BY g.region, p.category
ORDER BY margin_pct, g.region, p.category
```

</details>

## Top 10 sub categories by profit

<a id="top-10-sub-categories-by-profit"></a>

**Where is the profit actually made? These are the lines to protect from discounting.**

| sub_category | category | sales | profit | margin_pct | avg_discount |
| --- | --- | ---: | ---: | ---: | ---: |
| Copiers | Technology | 149,528.03 | 55,617.82 | 37.20 | 0.1618 |
| Phones | Technology | 330,007.05 | 44,515.73 | 13.49 | 0.1546 |
| Accessories | Technology | 167,380.32 | 41,936.64 | 25.05 | 0.0785 |
| Paper | Office Supplies | 78,479.21 | 34,053.57 | 43.39 | 0.0749 |
| Binders | Office Supplies | 203,412.73 | 30,221.76 | 14.86 | 0.3723 |
| Chairs | Furniture | 328,449.10 | 26,590.17 | 8.10 | 0.1702 |
| Storage | Office Supplies | 223,843.61 | 21,278.83 | 9.51 | 0.0747 |
| Appliances | Office Supplies | 107,532.16 | 18,138.01 | 16.87 | 0.1665 |
| Furnishings | Furniture | 91,705.16 | 13,059.14 | 14.24 | 0.1383 |
| Envelopes | Office Supplies | 16,476.40 | 6,964.18 | 42.27 | 0.0803 |


<details><summary>SQL</summary>

```sql
SELECT
    p.sub_category,
    p.category,
    round(sum(f.sales), 2)                              AS sales,
    round(sum(f.profit), 2)                             AS profit,
    round(100.0 * sum(f.profit) / sum(f.sales), 2)      AS margin_pct,
    round(avg(f.discount), 4)                           AS avg_discount
FROM fact_sales f
JOIN dim_product p USING (product_key)
GROUP BY p.sub_category, p.category
ORDER BY profit DESC, p.sub_category
LIMIT 10
```

</details>

## Bottom 10 sub categories by profit

<a id="bottom-10-sub-categories-by-profit"></a>

**Which sub-categories destroy profit? Tables and Bookcases are net-negative outright, and both sell in volume, so this is a pricing problem rather than a demand problem.**

| sub_category | category | sales | profit | margin_pct | avg_discount | pct_lines_loss_making |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Tables | Furniture | 206,965.53 | -17,725.48 | -8.56 | 0.2613 | 63.60 |
| Bookcases | Furniture | 114,880.00 | -3,472.56 | -3.02 | 0.2111 | 47.80 |
| Supplies | Office Supplies | 46,673.54 | -1,189.10 | -2.55 | 0.0768 | 17.40 |
| Fasteners | Office Supplies | 3,024.28 | 949.52 | 31.40 | 0.082 | 5.50 |
| Machines | Technology | 189,238.63 | 3,384.76 | 1.79 | 0.3061 | 38.30 |
| Labels | Office Supplies | 12,486.31 | 5,546.25 | 44.42 | 0.0687 | 0 |
| Art | Office Supplies | 27,118.79 | 6,527.79 | 24.07 | 0.0749 | 0 |
| Envelopes | Office Supplies | 16,476.40 | 6,964.18 | 42.27 | 0.0803 | 0 |
| Furnishings | Furniture | 91,705.16 | 13,059.14 | 14.24 | 0.1383 | 17.50 |
| Appliances | Office Supplies | 107,532.16 | 18,138.01 | 16.87 | 0.1665 | 14.40 |


<details><summary>SQL</summary>

```sql
SELECT
    p.sub_category,
    p.category,
    round(sum(f.sales), 2)                              AS sales,
    round(sum(f.profit), 2)                             AS profit,
    round(100.0 * sum(f.profit) / sum(f.sales), 2)      AS margin_pct,
    round(avg(f.discount), 4)                           AS avg_discount,
    round(100.0 * sum(f.is_loss_making::INT) / count(*), 1) AS pct_lines_loss_making
FROM fact_sales f
JOIN dim_product p USING (product_key)
GROUP BY p.sub_category, p.category
ORDER BY profit, p.sub_category
LIMIT 10
```

</details>

## Sales profit by year

<a id="sales-profit-by-year"></a>

**Is the business growing, and is profit growing with it?**

| year | orders | sales | profit | margin_pct | avg_discount |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 2017 | 969 | 484,247.50 | 49,543.97 | 10.23 | 0.1583 |
| 2018 | 1,038 | 470,532.51 | 61,618.60 | 13.10 | 0.1556 |
| 2019 | 1,315 | 609,205.60 | 81,795.17 | 13.43 | 0.1547 |
| 2020 | 1,687 | 733,215.26 | 93,439.27 | 12.74 | 0.1565 |


<details><summary>SQL</summary>

```sql
SELECT
    d.year,
    count(DISTINCT f.order_id)                          AS orders,
    round(sum(f.sales), 2)                              AS sales,
    round(sum(f.profit), 2)                             AS profit,
    round(100.0 * sum(f.profit) / sum(f.sales), 2)      AS margin_pct,
    round(avg(f.discount), 4)                           AS avg_discount
FROM fact_sales f
JOIN dim_date d ON f.order_date_key = d.date_key
GROUP BY d.year
ORDER BY d.year
```

</details>

## Sales profit by month

<a id="sales-profit-by-month"></a>

**What does the monthly trend look like, including the seasonal shape ops plans against?**

| year_month | year | month | orders | sales | profit | margin_pct |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2017-01 | 2017 | 1 | 32 | 14,236.89 | 2,450.19 | 17.21 |
| 2017-02 | 2017 | 2 | 28 | 4,519.89 | 862.31 | 19.08 |
| 2017-03 | 2017 | 3 | 71 | 55,691.01 | 498.73 | 0.90 |
| 2017-04 | 2017 | 4 | 66 | 28,295.34 | 3,488.84 | 12.33 |
| 2017-05 | 2017 | 5 | 69 | 23,648.29 | 2,738.71 | 11.58 |
| 2017-06 | 2017 | 6 | 66 | 34,595.13 | 4,976.52 | 14.39 |
| 2017-07 | 2017 | 7 | 65 | 33,946.39 | -841.48 | -2.48 |
| 2017-08 | 2017 | 8 | 72 | 27,909.47 | 5,318.11 | 19.05 |
| 2017-09 | 2017 | 9 | 130 | 81,777.35 | 8,328.10 | 10.18 |
| 2017-10 | 2017 | 10 | 78 | 31,453.39 | 3,448.26 | 10.96 |
| 2017-11 | 2017 | 11 | 151 | 78,628.72 | 9,292.13 | 11.82 |
| 2017-12 | 2017 | 12 | 141 | 69,545.62 | 8,983.57 | 12.92 |
| 2018-01 | 2018 | 1 | 29 | 18,174.08 | -3,281.01 | -18.05 |
| 2018-02 | 2018 | 2 | 36 | 11,951.41 | 2,813.85 | 23.54 |
| 2018-03 | 2018 | 3 | 79 | 38,726.25 | 9,732.10 | 25.13 |
| 2018-04 | 2018 | 4 | 72 | 34,195.21 | 4,187.50 | 12.25 |
| 2018-05 | 2018 | 5 | 74 | 30,131.69 | 4,667.87 | 15.49 |
| 2018-06 | 2018 | 6 | 68 | 24,797.29 | 3,335.56 | 13.45 |
| 2018-07 | 2018 | 7 | 66 | 28,765.32 | 3,288.65 | 11.43 |
| 2018-08 | 2018 | 8 | 68 | 36,898.33 | 5,355.81 | 14.52 |

_Showing 20 of 48 rows._


<details><summary>SQL</summary>

```sql
SELECT
    d.year_month,
    d.year,
    d.month,
    count(DISTINCT f.order_id)                          AS orders,
    round(sum(f.sales), 2)                              AS sales,
    round(sum(f.profit), 2)                             AS profit,
    round(100.0 * sum(f.profit) / sum(f.sales), 2)      AS margin_pct
FROM fact_sales f
JOIN dim_date d ON f.order_date_key = d.date_key
GROUP BY d.year_month, d.year, d.month
ORDER BY d.year_month
```

</details>

## Seasonality by calendar month

<a id="seasonality-by-calendar-month"></a>

**Which months carry the year, averaged across all four years? Q4 concentration matters for the capacity and staffing side of sales ops.**

| month | month_name | sales | avg_sales_per_year | profit | pct_of_annual_sales |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | January | 94,924.84 | 23,731.21 | 9,134.45 | 4.10 |
| 2 | February | 59,751.25 | 14,937.81 | 10,294.61 | 2.60 |
| 3 | March | 205,005.49 | 51,251.37 | 28,594.69 | 8.90 |
| 4 | April | 137,762.13 | 34,440.53 | 11,587.44 | 6.00 |
| 5 | May | 155,028.81 | 38,757.20 | 22,411.31 | 6.70 |
| 6 | June | 152,718.68 | 38,179.67 | 21,285.80 | 6.60 |
| 7 | July | 147,238.10 | 36,809.52 | 13,832.66 | 6.40 |
| 8 | August | 159,044.06 | 39,761.02 | 21,776.94 | 6.90 |
| 9 | September | 307,649.95 | 76,912.49 | 36,857.48 | 13.40 |
| 10 | October | 200,322.98 | 50,080.75 | 31,784.04 | 8.70 |
| 11 | November | 352,461.07 | 88,115.27 | 35,468.43 | 15.30 |
| 12 | December | 325,293.50 | 81,323.38 | 43,369.19 | 14.20 |


<details><summary>SQL</summary>

```sql
SELECT
    d.month,
    d.month_name,
    round(sum(f.sales), 2)                              AS sales,
    round(sum(f.sales) / count(DISTINCT d.year), 2)     AS avg_sales_per_year,
    round(sum(f.profit), 2)                             AS profit,
    round(100.0 * sum(f.sales) / sum(sum(f.sales)) OVER (), 1) AS pct_of_annual_sales
FROM fact_sales f
JOIN dim_date d ON f.order_date_key = d.date_key
GROUP BY d.month, d.month_name
ORDER BY d.month
```

</details>

## Avg discount by category

<a id="avg-discount-by-category"></a>

**How aggressively is each category discounted, and what does it cost?**

| category | avg_discount | sales_weighted_discount | max_discount | pct_lines_discounted | margin_pct |
| --- | ---: | ---: | ---: | ---: | ---: |
| Furniture | 0.1739 | 0.1665 | 0.7 | 60.60 | 2.49 |
| Office Supplies | 0.1573 | 0.1063 | 0.8 | 48.10 | 17.04 |
| Technology | 0.1323 | 0.1467 | 0.7 | 54.90 | 17.40 |


<details><summary>SQL</summary>

```sql
SELECT
    p.category,
    round(avg(f.discount), 4)                           AS avg_discount,
    round(sum(f.discount * f.sales) / sum(f.sales), 4)  AS sales_weighted_discount,
    max(f.discount)                                     AS max_discount,
    round(100.0 * sum(CASE WHEN f.discount > 0 THEN 1 ELSE 0 END) / count(*), 1)
                                                        AS pct_lines_discounted,
    round(100.0 * sum(f.profit) / sum(f.sales), 2)      AS margin_pct
FROM fact_sales f
JOIN dim_product p USING (product_key)
GROUP BY p.category
ORDER BY avg_discount DESC, p.category
```

</details>

## Avg discount by sub category

<a id="avg-discount-by-sub-category"></a>

**The same question one level down. Ordering by average discount puts the sub-categories with the deepest cuts at the top, next to the margin those cuts leave behind.**

| sub_category | category | order_lines | avg_discount | max_discount | pct_lines_discounted | profit | margin_pct |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Binders | Office Supplies | 1,523 | 0.3723 | 0.8 | 77.90 | 30,221.76 | 14.86 |
| Machines | Technology | 115 | 0.3061 | 0.7 | 74.80 | 3,384.76 | 1.79 |
| Tables | Furniture | 319 | 0.2613 | 0.5 | 77.40 | -17,725.48 | -8.56 |
| Bookcases | Furniture | 228 | 0.2111 | 0.7 | 73.70 | -3,472.56 | -3.02 |
| Chairs | Furniture | 617 | 0.1702 | 0.3 | 78.40 | 26,590.17 | 8.10 |
| Appliances | Office Supplies | 466 | 0.1665 | 0.8 | 41.80 | 18,138.01 | 16.87 |
| Copiers | Technology | 68 | 0.1618 | 0.4 | 67.60 | 55,617.82 | 37.20 |
| Phones | Technology | 889 | 0.1546 | 0.4 | 65.00 | 44,515.73 | 13.49 |
| Furnishings | Furniture | 957 | 0.1383 | 0.6 | 40.30 | 13,059.14 | 14.24 |
| Fasteners | Office Supplies | 217 | 0.082 | 0.2 | 41.00 | 949.52 | 31.40 |
| Envelopes | Office Supplies | 254 | 0.0803 | 0.2 | 40.20 | 6,964.18 | 42.27 |
| Accessories | Technology | 775 | 0.0785 | 0.2 | 39.20 | 41,936.64 | 25.05 |
| Supplies | Office Supplies | 190 | 0.0768 | 0.2 | 38.40 | -1,189.10 | -2.55 |
| Art | Office Supplies | 796 | 0.0749 | 0.2 | 37.40 | 6,527.79 | 24.07 |
| Paper | Office Supplies | 1,370 | 0.0749 | 0.2 | 37.40 | 34,053.57 | 43.39 |
| Storage | Office Supplies | 846 | 0.0747 | 0.2 | 37.40 | 21,278.83 | 9.51 |
| Labels | Office Supplies | 364 | 0.0687 | 0.2 | 34.30 | 5,546.25 | 44.42 |


<details><summary>SQL</summary>

```sql
SELECT
    p.sub_category,
    p.category,
    count(*)                                            AS order_lines,
    round(avg(f.discount), 4)                           AS avg_discount,
    max(f.discount)                                     AS max_discount,
    round(100.0 * sum(CASE WHEN f.discount > 0 THEN 1 ELSE 0 END) / count(*), 1)
                                                        AS pct_lines_discounted,
    round(sum(f.profit), 2)                             AS profit,
    round(100.0 * sum(f.profit) / sum(f.sales), 2)      AS margin_pct
FROM fact_sales f
JOIN dim_product p USING (product_key)
GROUP BY p.sub_category, p.category
ORDER BY avg_discount DESC, p.sub_category
```

</details>

## Margin by discount band

<a id="margin-by-discount-band"></a>

**The headline relationship of the whole project: what happens to margin as discount rises? Banding the discount rate makes the tipping point visible without a regression.**

| discount_band | order_lines | sales | profit | margin_pct | pct_lines_loss_making |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0% | 4,798 | 1,087,908.47 | 320,987.60 | 29.51 | 0 |
| 1-10% | 94 | 54,369.35 | 9,029.18 | 16.61 | 4.30 |
| 11-20% | 3,709 | 792,152.89 | 91,756.30 | 11.58 | 14.00 |
| 21-30% | 227 | 103,226.65 | -10,369.28 | -10.05 | 91.60 |
| 31-40% | 233 | 130,911.24 | -25,448.19 | -19.44 | 88.80 |
| 41%+ | 933 | 128,632.25 | -99,558.59 | -77.40 | 100.00 |


<details><summary>SQL</summary>

```sql
SELECT
    CASE
        WHEN f.discount = 0                        THEN '0%'
        WHEN f.discount <= 0.10                    THEN '1-10%'
        WHEN f.discount <= 0.20                    THEN '11-20%'
        WHEN f.discount <= 0.30                    THEN '21-30%'
        WHEN f.discount <= 0.40                    THEN '31-40%'
        ELSE '41%+'
    END                                                 AS discount_band,
    count(*)                                            AS order_lines,
    round(sum(f.sales), 2)                              AS sales,
    round(sum(f.profit), 2)                             AS profit,
    round(100.0 * sum(f.profit) / sum(f.sales), 2)      AS margin_pct,
    round(100.0 * sum(f.is_loss_making::INT) / count(*), 1) AS pct_lines_loss_making
FROM fact_sales f
GROUP BY discount_band
ORDER BY min(f.discount)
```

</details>

## Ship mode mix

<a id="ship-mode-mix"></a>

**Does the fulfilment mix differ by segment in a way that costs margin?**

| ship_mode | order_lines | pct_of_lines | avg_days_to_ship | sales | margin_pct |
| --- | ---: | ---: | ---: | ---: | ---: |
| Standard Class | 5,968 | 59.70 | 5.01 | 1,358,215.74 | 12.08 |
| Second Class | 1,945 | 19.50 | 3.24 | 459,193.57 | 12.51 |
| First Class | 1,538 | 15.40 | 2.18 | 351,428.42 | 13.93 |
| Same Day | 543 | 5.40 | 0.04 | 128,363.13 | 12.38 |


<details><summary>SQL</summary>

```sql
SELECT
    f.ship_mode,
    count(*)                                            AS order_lines,
    round(100.0 * count(*) / sum(count(*)) OVER (), 1)  AS pct_of_lines,
    round(avg(date_diff('day', f.order_date, f.ship_date)), 2) AS avg_days_to_ship,
    round(sum(f.sales), 2)                              AS sales,
    round(100.0 * sum(f.profit) / sum(f.sales), 2)      AS margin_pct
FROM fact_sales f
GROUP BY f.ship_mode
ORDER BY order_lines DESC, f.ship_mode
```

</details>
