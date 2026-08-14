# Data quality report

Regenerate with `python -m src.utils`. Every figure below is read from the star schema in `db/superstore.duckdb`, so this file is only as current as the last transform run.

## Summary

| Check | Result | Notes |
| --- | --- | --- |
| Row ID is unique | pass | Every fact row has a distinct Row ID, so the grain is one product line per order. |
| Ship Date is on or after Order Date | pass | No violations. Fulfilment takes 0 to 8 days, averaging 3.96. |
| Foreign keys resolve | pass | All five foreign keys resolve to a dimension row, with no nulls. |
| Measures are within range | pass | Sales and quantity are positive on every line, discount sits between 0 and 1, and no measure is null. |
| Attribute completeness | pass | 11 fact rows have no postal code, all in Burlington, Vermont. Preserved as null rather than imputed. Every other attribute is populated. |
| Repeated (Order ID, Product ID) pairs | pass | 8 product/order pairs span more than one line. These are split order lines rather than errors, which is why Row ID and not this pair is the fact grain. See the exact-duplicate check below for the one real duplicate. |
| Exact duplicate line items | review | 1 group(s) of lines are identical in every field except Row ID. Left in place rather than deleted, since dropping source rows is an analytical decision and not a transform decision. |

Checks marked `review` need a human decision. They are not automatically failures.

## Table row counts

| Table | Rows |
| --- | ---: |
| `stg_orders` | 9,994 |
| `fact_sales` | 9,994 |
| `dim_customer` | 793 |
| `dim_product` | 1,894 |
| `dim_geography` | 632 |
| `dim_date` | 1,464 |

## Loss-making line items

`is_loss_making` is stored on `fact_sales` as `profit < 0`. It flags **1,871 of 9,994 line items (18.7%)**, which carry **$468,707.15 of the $2,297,200.86 in total sales (20.4%)**.

Those lines lose $156,131.29. Profitable lines earn $442,528.31, so the business nets $286,397.02. Nearly a fifth of the order lines are erasing 35% of the profit the rest of the book generates.

### By category

| grouping | lines | loss_lines | pct_lines | sales | profit | margin_pct |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Furniture | 2,121 | 714 | 33.70 | 741,999.80 | 18,451.27 | 2.50 |
| Office Supplies | 6,026 | 886 | 14.70 | 719,047.03 | 122,490.80 | 17.00 |
| Technology | 1,847 | 271 | 14.70 | 836,154.03 | 145,454.95 | 17.40 |

### By sub-category

| grouping | lines | loss_lines | pct_lines | sales | profit | margin_pct |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Tables | 319 | 203 | 63.60 | 206,965.53 | -17,725.48 | -8.60 |
| Bookcases | 228 | 109 | 47.80 | 114,880.00 | -3,472.56 | -3.00 |
| Supplies | 190 | 33 | 17.40 | 46,673.54 | -1,189.10 | -2.50 |
| Fasteners | 217 | 12 | 5.50 | 3,024.28 | 949.52 | 31.40 |
| Machines | 115 | 44 | 38.30 | 189,238.63 | 3,384.76 | 1.80 |
| Labels | 364 | 0 | 0 | 12,486.31 | 5,546.25 | 44.40 |
| Art | 796 | 0 | 0 | 27,118.79 | 6,527.79 | 24.10 |
| Envelopes | 254 | 0 | 0 | 16,476.40 | 6,964.18 | 42.30 |
| Furnishings | 957 | 167 | 17.50 | 91,705.16 | 13,059.14 | 14.20 |
| Appliances | 466 | 67 | 14.40 | 107,532.16 | 18,138.01 | 16.90 |
| Storage | 846 | 161 | 19.00 | 223,843.61 | 21,278.83 | 9.50 |
| Chairs | 617 | 235 | 38.10 | 328,449.10 | 26,590.17 | 8.10 |
| Binders | 1,523 | 613 | 40.20 | 203,412.73 | 30,221.76 | 14.90 |
| Paper | 1,370 | 0 | 0 | 78,479.21 | 34,053.57 | 43.40 |
| Accessories | 775 | 91 | 11.70 | 167,380.32 | 41,936.64 | 25.10 |
| Phones | 889 | 136 | 15.30 | 330,007.05 | 44,515.73 | 13.50 |
| Copiers | 68 | 0 | 0 | 149,528.03 | 55,617.82 | 37.20 |

### By region

| grouping | lines | loss_lines | pct_lines | sales | profit | margin_pct |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Central | 2,323 | 741 | 31.90 | 501,239.89 | 39,706.36 | 7.90 |
| South | 1,620 | 259 | 16.00 | 391,721.91 | 46,749.43 | 11.90 |
| East | 2,848 | 553 | 19.40 | 678,781.24 | 91,522.78 | 13.50 |
| West | 3,203 | 318 | 9.90 | 725,457.82 | 108,418.45 | 14.90 |

### By segment

| grouping | lines | loss_lines | pct_lines | sales | profit | margin_pct |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Home Office | 1,783 | 312 | 17.50 | 429,653.15 | 60,298.68 | 14.00 |
| Corporate | 3,020 | 556 | 18.40 | 706,146.37 | 91,979.13 | 13.00 |
| Consumer | 5,191 | 1,003 | 19.30 | 1,161,401.34 | 134,119.21 | 11.50 |

## Check detail

### Row ID is unique

Every fact row has a distinct Row ID, so the grain is one product line per order.

### Ship Date is on or after Order Date

No violations. Fulfilment takes 0 to 8 days, averaging 3.96.

### Foreign keys resolve

All five foreign keys resolve to a dimension row, with no nulls.

| foreign_key | references | orphan_rows | null_keys |
| --- | --- | ---: | ---: |
| customer_key | dim_customer.customer_key | 0 | 0 |
| product_key | dim_product.product_key | 0 | 0 |
| geography_key | dim_geography.geography_key | 0 | 0 |
| order_date_key | dim_date.date_key | 0 | 0 |
| ship_date_key | dim_date.date_key | 0 | 0 |


### Measures are within range

Sales and quantity are positive on every line, discount sits between 0 and 1, and no measure is null.

| rule | rows |
| --- | ---: |
| sales <= 0 | 0 |
| quantity <= 0 | 0 |
| discount outside 0 to 1 | 0 |
| null measure | 0 |


### Attribute completeness

11 fact rows have no postal code, all in Burlington, Vermont. Preserved as null rather than imputed. Every other attribute is populated.

| city | state | region |
| --- | --- | --- |
| Burlington | Vermont | East |


### Repeated (Order ID, Product ID) pairs

8 product/order pairs span more than one line. These are split order lines rather than errors, which is why Row ID and not this pair is the fact grain. See the exact-duplicate check below for the one real duplicate.

| order_id | product_id | product_name | lines | total_sales | total_quantity |
| --- | --- | --- | ---: | ---: | ---: |
| CA-2018-103135 | OFF-BI-10000069 | GBC Prepunched Paper, 19-Hole, for Binding Systems, 24-lb | 2 | 225.15 | 15.00 |
| CA-2019-129714 | OFF-PA-10001970 | Xerox 1881 | 2 | 73.68 | 6.00 |
| CA-2019-137043 | FUR-FU-10003664 | Electrix Architect's Clamp-On Swing Arm Lamp, Black | 2 | 859.14 | 9.00 |
| CA-2019-140571 | OFF-PA-10001954 | Xerox 1964 | 2 | 365.44 | 16.00 |
| CA-2020-118017 | TEC-AC-10002006 | Memorex Micro Travel Drive 16 GB | 2 | 179.09 | 14.00 |
| CA-2020-152912 | OFF-ST-10003208 | Adjustable Depth Letter/Legal Cart | 2 | 2,177.52 | 12.00 |
| US-2017-150119 | FUR-CH-10002965 | Global Leather Highback Executive Chair with Pneumatic Height Adjustment, Black | 2 | 562.74 | 4.00 |
| US-2019-123750 | TEC-AC-10004659 | Imation Secure+ Hardware Encrypted USB 2.0 Flash Drive; 16GB | 2 | 700.70 | 12.00 |


### Exact duplicate line items

1 group(s) of lines are identical in every field except Row ID. Left in place rather than deleted, since dropping source rows is an analytical decision and not a transform decision.

| order_id | product_key | order_date | ship_date | ship_mode | sales | quantity | discount | profit | lines | row_ids |
| --- | ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| US-2017-150119 | 102 | 2017-04-23 | 2017-04-27 | Standard Class | 281.37 | 2 | 0.3 | -12.06 | 2 | 3406, 3407 |


## Processed outputs

Validated tables written to `data/processed/` as ZSTD-compressed Parquet. The directory is gitignored, so these are rebuilt locally rather than committed.

| File | Size |
| --- | ---: |
| `fact_sales.parquet` | 266 KB |
| `dim_customer.parquet` | 11 KB |
| `dim_product.parquet` | 37 KB |
| `dim_geography.parquet` | 8 KB |
| `dim_date.parquet` | 10 KB |
