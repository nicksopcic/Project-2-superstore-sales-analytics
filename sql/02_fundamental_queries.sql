-- 02_fundamental_queries.sql: core aggregations against the star schema.
--
-- Each query is preceded by a "-- name:" tag and the business question it answers.
-- src/run_sql_report.py splits this file on those tags, runs each statement, and writes the
-- results to reports/sql_fundamental_results.md. Keep one statement per tag.
--
-- Margin % is profit divided by sales, not profit divided by cost. Discount is a rate, so it
-- is averaged rather than summed, and weighted by sales where the weighting matters.


-- name: sales_profit_margin_by_region
-- Which regions carry the business, and which convert revenue into profit efficiently?
-- The West and the East are the volume leaders. Central is the margin problem.
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
ORDER BY profit DESC;


-- name: sales_profit_margin_by_segment
-- Do any customer segments buy at materially worse margin than the others?
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
ORDER BY profit DESC;


-- name: sales_profit_margin_by_category
-- Which of the three categories actually earns its shelf space?
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
ORDER BY profit DESC;


-- name: margin_by_region_and_category
-- Where does a specific category go wrong in a specific region? This is the cell-level view
-- the regional managers need, rather than either margin averaged on its own.
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
ORDER BY margin_pct;


-- name: top_10_sub_categories_by_profit
-- Where is the profit actually made? These are the lines to protect from discounting.
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
ORDER BY profit DESC
LIMIT 10;


-- name: bottom_10_sub_categories_by_profit
-- Which sub-categories destroy profit? Tables and Bookcases are net-negative outright, and
-- both sell in volume, so this is a pricing problem rather than a demand problem.
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
ORDER BY profit
LIMIT 10;


-- name: sales_profit_by_year
-- Is the business growing, and is profit growing with it?
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
ORDER BY d.year;


-- name: sales_profit_by_month
-- What does the monthly trend look like, including the seasonal shape ops plans against?
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
ORDER BY d.year_month;


-- name: seasonality_by_calendar_month
-- Which months carry the year, averaged across all four years? Q4 concentration matters for
-- the capacity and staffing side of sales ops.
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
ORDER BY d.month;


-- name: avg_discount_by_category
-- How aggressively is each category discounted, and what does it cost?
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
ORDER BY avg_discount DESC;


-- name: avg_discount_by_sub_category
-- The same question one level down. Ordering by average discount puts the sub-categories
-- with the deepest cuts at the top, next to the margin those cuts leave behind.
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
ORDER BY avg_discount DESC;


-- name: margin_by_discount_band
-- The headline relationship of the whole project: what happens to margin as discount rises?
-- Banding the discount rate makes the tipping point visible without a regression.
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
ORDER BY min(f.discount);


-- name: ship_mode_mix
-- Does the fulfilment mix differ by segment in a way that costs margin?
SELECT
    f.ship_mode,
    count(*)                                            AS order_lines,
    round(100.0 * count(*) / sum(count(*)) OVER (), 1)  AS pct_of_lines,
    round(avg(date_diff('day', f.order_date, f.ship_date)), 2) AS avg_days_to_ship,
    round(sum(f.sales), 2)                              AS sales,
    round(100.0 * sum(f.profit) / sum(f.sales), 2)      AS margin_pct
FROM fact_sales f
GROUP BY f.ship_mode
ORDER BY order_lines DESC;
