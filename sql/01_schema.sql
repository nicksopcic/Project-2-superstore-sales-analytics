-- 01_schema.sql: star schema keys and constraints.
--
-- The tables themselves are created by src/transform_star_schema.py, which runs the CTAS
-- statements against DuckDB. This file is the reference for what the keys mean and why they
-- are shaped the way they are. The constraints at the bottom are the assertions Phase 2
-- enforces as tests.
--
-- Grain: one row in fact_sales per Row ID, which is one product line on one order.


-- ---------------------------------------------------------------------------
-- Why surrogate keys
-- ---------------------------------------------------------------------------
-- None of the natural keys in this dataset is unique enough to be a primary key:
--
--   Product ID   32 IDs are reused across two different product names (337 rows). For
--                example FUR-BO-10002213 is both "DMI Eclipse Executive Suite Bookcases"
--                and "Sauder Forest Hills Library, Woodland Oak Finish".
--   Postal Code  92024 maps to both San Diego and Encinitas, and 11 rows (Burlington,
--                Vermont) have no postal code at all. A nullable column cannot be a key.
--   Customer ID  Unique in this dataset. Given a surrogate key anyway, so all four
--                dimensions join the same way.
--
-- Each dimension therefore gets an integer surrogate key, and the natural key is kept as a
-- regular attribute so the source records stay traceable.


-- ---------------------------------------------------------------------------
-- dim_customer (793 rows)
-- ---------------------------------------------------------------------------
--   customer_key    PK, surrogate, assigned by ROW_NUMBER() over customer_id
--   customer_id     natural key from the source, unique in this dataset
--   customer_name   VARCHAR
--   segment         Consumer, Corporate, or Home Office


-- ---------------------------------------------------------------------------
-- dim_product (1,894 rows)
-- ---------------------------------------------------------------------------
--   product_key     PK, surrogate, assigned over (product_id, product_name)
--   product_id      natural key, NOT unique, see the note above
--   category        Furniture, Office Supplies, or Technology
--   sub_category    17 values nested under category
--   product_name    VARCHAR
--
-- Row count exceeds the 1,862 distinct Product IDs precisely because of the 32 reused IDs.


-- ---------------------------------------------------------------------------
-- dim_geography (632 rows)
-- ---------------------------------------------------------------------------
--   geography_key   PK, surrogate, assigned over the full location combination
--   country         always "United States" in this dataset
--   city            VARCHAR
--   state           VARCHAR
--   postal_code     INTEGER, nullable, 11 source rows have no value
--   region          Central, East, South, or West
--
-- One row per distinct (country, city, state, postal_code, region). The fact join matches
-- postal_code with IS NOT DISTINCT FROM so null-postal rows join rather than drop out.


-- ---------------------------------------------------------------------------
-- dim_date (1,464 rows)
-- ---------------------------------------------------------------------------
--   date_key        PK, integer in YYYYMMDD form, for example 20170103
--   full_date       DATE
--   year, quarter, month, month_name, year_month
--   day_of_month, day_of_week, day_name, is_weekend
--
-- A contiguous daily calendar from the earliest order date (2017-01-03) to the latest ship
-- date (2021-01-05), not only the 1,236 dates that appear as order dates. The gapless spine
-- keeps the running YTD and month-over-month queries in Phase 4 honest about quiet periods,
-- and it lets ship_date_key resolve against the same dimension as order_date_key.


-- ---------------------------------------------------------------------------
-- fact_sales (9,994 rows)
-- ---------------------------------------------------------------------------
--   row_id           PK, the source Row ID, unique
--   order_id         degenerate dimension, 5,009 distinct orders, NOT unique here
--   order_date       DATE, kept alongside order_date_key for readable ad hoc queries
--   ship_date        DATE
--   ship_mode        degenerate dimension: First Class, Same Day, Second Class, Standard Class
--   customer_key     FK to dim_customer
--   product_key      FK to dim_product
--   geography_key    FK to dim_geography
--   order_date_key   FK to dim_date
--   ship_date_key    FK to dim_date
--   sales            DOUBLE, additive
--   quantity         INTEGER, additive
--   discount         DOUBLE, a rate between 0 and 0.8, NOT additive, average it
--   profit           DOUBLE, additive, negative on 1,871 rows
--
-- (order_id, product_key) is not unique: 8 pairs of rows split the same product across two
-- lines of the same order. Row ID is the only safe grain.


-- ---------------------------------------------------------------------------
-- Constraints asserted in Phase 2
-- ---------------------------------------------------------------------------
-- Written as ALTER statements for documentation. DuckDB accepts primary and foreign key
-- constraints on CREATE TABLE only, so the transform relies on the row count check in
-- build_star_schema() plus the tests in tests/ rather than on these statements.
--
-- ALTER TABLE dim_customer  ADD PRIMARY KEY (customer_key);
-- ALTER TABLE dim_product   ADD PRIMARY KEY (product_key);
-- ALTER TABLE dim_geography ADD PRIMARY KEY (geography_key);
-- ALTER TABLE dim_date      ADD PRIMARY KEY (date_key);
-- ALTER TABLE fact_sales    ADD PRIMARY KEY (row_id);
-- ALTER TABLE fact_sales    ADD FOREIGN KEY (customer_key)   REFERENCES dim_customer  (customer_key);
-- ALTER TABLE fact_sales    ADD FOREIGN KEY (product_key)    REFERENCES dim_product   (product_key);
-- ALTER TABLE fact_sales    ADD FOREIGN KEY (geography_key)  REFERENCES dim_geography (geography_key);
-- ALTER TABLE fact_sales    ADD FOREIGN KEY (order_date_key) REFERENCES dim_date      (date_key);
-- ALTER TABLE fact_sales    ADD FOREIGN KEY (ship_date_key)  REFERENCES dim_date      (date_key);
