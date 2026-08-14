-- 03_advanced_queries.sql: window functions and CTEs for operational questions.
--
-- Same convention as 02_fundamental_queries.sql. Each query carries a "-- name:" tag and the
-- business question it answers, and src/run_sql_report.py writes the results to
-- reports/sql_advanced_results.md.
--
-- These are the questions that need more than a GROUP BY: running totals, ranking within a
-- partition, period-over-period comparison, and per-customer rollups feeding Phase 6.


-- name: running_ytd_sales_by_region
-- How is each region tracking against its own year, month by month? A running total resets
-- every January, which is what a sales-ops YTD number means in practice.
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
ORDER BY region, year_month;


-- name: sub_category_profit_rank_by_region
-- Within each region, which sub-categories earn and which bleed? Ranking inside the region
-- rather than nationally is what lets a regional manager act on the list.
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
ORDER BY g.region, profit_rank, p.sub_category;


-- name: worst_sub_category_per_region
-- The single worst sub-category in each region, pulled out of the ranking above. This is the
-- shortlist for a discount policy change.
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
ORDER BY profit, region;


-- name: month_over_month_sales_growth
-- Is the business accelerating or decelerating? LAG() against the previous calendar month,
-- across the whole book.
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
ORDER BY year_month;


-- name: month_over_month_sales_growth_by_region
-- The same comparison held inside each region, so a national swing does not hide a regional
-- one moving the other way.
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
ORDER BY region, year_month;


-- name: year_over_year_growth_by_region
-- The comparison that survives seasonality. Month over month is noisy in a business with a
-- Q4 peak, so the annual view is the one to quote in a QBR.
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
ORDER BY region, year;


-- name: customer_lifetime_value
-- What is each customer worth over the whole period? Sales, profit, and order count per
-- customer, which Phase 6 turns into the Pareto and CLV work.
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
ORDER BY lifetime_profit DESC, customer_id;


-- name: customer_profit_pareto
-- Do a small share of customers carry the profit? Cumulative profit share, ordered from the
-- most profitable customer down.
--
-- Read the cumulative share carefully. Loss-making customers subtract, so the running share
-- climbs above 100% and then falls back to 100% at the last row. The peak is the real
-- concentration: it is how much profit the profitable customers generate before the rest
-- give some of it back.
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
ORDER BY profit_rank;


-- name: loss_making_customers
-- Which customers cost money overall? A customer can order steadily and still be worth less
-- than nothing once discounts are counted.
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
ORDER BY lifetime_profit, customer_id;
