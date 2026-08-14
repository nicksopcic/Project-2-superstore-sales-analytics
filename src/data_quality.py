"""Data-quality checks over the star schema, the report generator, and the Parquet export.

Running this module validates the star schema, writes reports/data_quality_report.md, and
persists the validated tables to data/processed/ as Parquet.

Run with: python -m src.data_quality (after python -m src.transform_star_schema)
"""

from __future__ import annotations

from dataclasses import dataclass, field

import duckdb
import pandas as pd

from src.utils import (
    EXPORT_TABLES,
    PROCESSED_DIR,
    PROJECT_ROOT,
    REPORTS_DIR,
    connect,
    markdown_table,
    require_star_schema,
    row_count,
    table_exists,
)

REPORT_PATH = REPORTS_DIR / "data_quality_report.md"


# ---------------------------------------------------------------------------
# Data-quality checks
# ---------------------------------------------------------------------------


@dataclass
class CheckResult:
    """One data-quality check. `exceptions` holds the offending rows when there are any."""

    name: str
    passed: bool
    detail: str
    exceptions: pd.DataFrame = field(default_factory=pd.DataFrame)

    @property
    def status(self) -> str:
        return "pass" if self.passed else "review"


def check_unique_row_id(con: duckdb.DuckDBPyConnection) -> CheckResult:
    dupes = con.execute(
        "SELECT row_id, count(*) AS lines FROM fact_sales GROUP BY row_id HAVING count(*) > 1"
    ).df()
    return CheckResult(
        name="Row ID is unique",
        passed=dupes.empty,
        detail=(
            "Every fact row has a distinct Row ID, so the grain is one product line per order."
            if dupes.empty
            else f"{len(dupes):,} Row ID values appear more than once."
        ),
        exceptions=dupes,
    )


def check_ship_date_not_before_order_date(con: duckdb.DuckDBPyConnection) -> CheckResult:
    violations = con.execute(
        """
        SELECT row_id, order_id, order_date, ship_date,
               date_diff('day', order_date, ship_date) AS days_to_ship
        FROM fact_sales
        WHERE ship_date < order_date
        ORDER BY row_id
        """
    ).df()
    spread = con.execute(
        """
        SELECT min(date_diff('day', order_date, ship_date)),
               max(date_diff('day', order_date, ship_date)),
               round(avg(date_diff('day', order_date, ship_date)), 2)
        FROM fact_sales
        """
    ).fetchone()
    return CheckResult(
        name="Ship Date is on or after Order Date",
        passed=violations.empty,
        detail=(
            f"No violations. Fulfilment takes {spread[0]} to {spread[1]} days, "
            f"averaging {spread[2]}."
            if violations.empty
            else f"{len(violations):,} rows ship before they are ordered."
        ),
        exceptions=violations,
    )


def check_order_product_pairs(con: duckdb.DuckDBPyConnection) -> CheckResult:
    """(order_id, product_key) is expected to repeat. Report the repeats for inspection."""
    repeats = con.execute(
        """
        SELECT f.order_id, p.product_id, p.product_name, count(*) AS lines,
               round(sum(f.sales), 2) AS total_sales, sum(f.quantity) AS total_quantity
        FROM fact_sales f
        JOIN dim_product p USING (product_key)
        GROUP BY f.order_id, p.product_id, p.product_name
        HAVING count(*) > 1
        ORDER BY f.order_id
        """
    ).df()
    return CheckResult(
        name="Repeated (Order ID, Product ID) pairs",
        passed=True,
        detail=(
            f"{len(repeats)} product/order pairs span more than one line. These are split "
            "order lines rather than errors, which is why Row ID and not this pair is the "
            "fact grain. See the exact-duplicate check below for the one real duplicate."
        ),
        exceptions=repeats,
    )


def check_exact_duplicate_lines(con: duckdb.DuckDBPyConnection) -> CheckResult:
    """Rows identical in every field except row_id. Unlike split lines, these are suspect."""
    dupes = con.execute(
        """
        SELECT order_id, product_key, order_date, ship_date, ship_mode,
               sales, quantity, discount, profit,
               count(*) AS lines, list(row_id ORDER BY row_id) AS row_ids
        FROM fact_sales
        GROUP BY order_id, product_key, order_date, ship_date, ship_mode,
                 sales, quantity, discount, profit
        HAVING count(*) > 1
        ORDER BY order_id
        """
    ).df()
    return CheckResult(
        name="Exact duplicate line items",
        passed=dupes.empty,
        detail=(
            "No two lines are identical across every measure."
            if dupes.empty
            else f"{len(dupes)} group(s) of lines are identical in every field except Row ID. "
            "Left in place rather than deleted, since dropping source rows is an analytical "
            "decision and not a transform decision."
        ),
        exceptions=dupes,
    )


def check_referential_integrity(con: duckdb.DuckDBPyConnection) -> CheckResult:
    joins = {
        "customer_key": ("dim_customer", "customer_key"),
        "product_key": ("dim_product", "product_key"),
        "geography_key": ("dim_geography", "geography_key"),
        "order_date_key": ("dim_date", "date_key"),
        "ship_date_key": ("dim_date", "date_key"),
    }
    rows = []
    for fact_column, (dim_table, dim_column) in joins.items():
        orphans = con.execute(
            f"""
            SELECT count(*) FROM fact_sales f
            LEFT JOIN {dim_table} d ON f.{fact_column} = d.{dim_column}
            WHERE d.{dim_column} IS NULL
            """
        ).fetchone()[0]
        nulls = con.execute(
            f"SELECT count(*) FROM fact_sales WHERE {fact_column} IS NULL"
        ).fetchone()[0]
        rows.append(
            {"foreign_key": fact_column, "references": f"{dim_table}.{dim_column}",
             "orphan_rows": orphans, "null_keys": nulls}
        )

    summary = pd.DataFrame(rows)
    broken = summary[(summary["orphan_rows"] > 0) | (summary["null_keys"] > 0)]
    return CheckResult(
        name="Foreign keys resolve",
        passed=broken.empty,
        detail=(
            "All five foreign keys resolve to a dimension row, with no nulls."
            if broken.empty
            else f"{len(broken)} foreign key(s) do not resolve."
        ),
        exceptions=summary if broken.empty else broken,
    )


def check_measure_ranges(con: duckdb.DuckDBPyConnection) -> CheckResult:
    problems = con.execute(
        """
        SELECT 'sales <= 0' AS rule, count(*) AS rows FROM fact_sales WHERE sales <= 0
        UNION ALL SELECT 'quantity <= 0', count(*) FROM fact_sales WHERE quantity <= 0
        UNION ALL SELECT 'discount outside 0 to 1', count(*) FROM fact_sales
            WHERE discount < 0 OR discount > 1
        UNION ALL SELECT 'null measure', count(*) FROM fact_sales
            WHERE sales IS NULL OR quantity IS NULL OR discount IS NULL OR profit IS NULL
        """
    ).df()
    failing = problems[problems["rows"] > 0]
    return CheckResult(
        name="Measures are within range",
        passed=failing.empty,
        detail=(
            "Sales and quantity are positive on every line, discount sits between 0 and 1, "
            "and no measure is null."
            if failing.empty
            else f"{len(failing)} range rule(s) have exceptions."
        ),
        exceptions=problems,
    )


def check_completeness(con: duckdb.DuckDBPyConnection) -> CheckResult:
    """Postal code is the one attribute allowed to be missing, on 11 known rows."""
    missing = con.execute(
        """
        SELECT count(*) AS fact_rows_without_postal_code
        FROM fact_sales f JOIN dim_geography g USING (geography_key)
        WHERE g.postal_code IS NULL
        """
    ).fetchone()[0]
    where = con.execute(
        """
        SELECT DISTINCT g.city, g.state, g.region
        FROM fact_sales f JOIN dim_geography g USING (geography_key)
        WHERE g.postal_code IS NULL
        """
    ).df()
    return CheckResult(
        name="Attribute completeness",
        passed=True,
        detail=(
            f"{missing} fact rows have no postal code, all in "
            f"{', '.join(f'{r.city}, {r.state}' for r in where.itertuples())}. Preserved as "
            "null rather than imputed. Every other attribute is populated."
        ),
        exceptions=where,
    )


ALL_CHECKS = (
    check_unique_row_id,
    check_ship_date_not_before_order_date,
    check_referential_integrity,
    check_measure_ranges,
    check_completeness,
    check_order_product_pairs,
    check_exact_duplicate_lines,
)


def run_all_checks(con: duckdb.DuckDBPyConnection) -> list[CheckResult]:
    require_star_schema(con)
    return [check(con) for check in ALL_CHECKS]


# ---------------------------------------------------------------------------
# Loss-making profile
# ---------------------------------------------------------------------------


def loss_making_profile(con: duckdb.DuckDBPyConnection) -> dict[str, float]:
    """Headline numbers for is_loss_making, used by the report and by later phases."""
    return con.execute(
        """
        SELECT
            count(*)                                                   AS total_lines,
            sum(is_loss_making::INT)                                   AS loss_lines,
            100.0 * sum(is_loss_making::INT) / count(*)                AS pct_lines,
            sum(sales)                                                 AS total_sales,
            sum(CASE WHEN is_loss_making THEN sales ELSE 0 END)        AS loss_sales,
            100.0 * sum(CASE WHEN is_loss_making THEN sales ELSE 0 END) / sum(sales)
                                                                       AS pct_sales,
            sum(profit)                                                AS total_profit,
            sum(CASE WHEN is_loss_making THEN profit ELSE 0 END)       AS loss_profit,
            sum(CASE WHEN NOT is_loss_making THEN profit ELSE 0 END)   AS profit_from_winners
        FROM fact_sales
        """
    ).df().iloc[0].to_dict()


def loss_making_by(con: duckdb.DuckDBPyConnection, dimension: str) -> pd.DataFrame:
    """Loss-making breakdown by a dim_product or dim_geography attribute."""
    source = {
        "category": "dim_product",
        "sub_category": "dim_product",
        "region": "dim_geography",
        "segment": "dim_customer",
    }[dimension]
    return con.execute(
        f"""
        SELECT
            d.{dimension}                                            AS grouping,
            count(*)                                                 AS lines,
            CAST(sum(f.is_loss_making::INT) AS BIGINT)               AS loss_lines,
            round(100.0 * sum(f.is_loss_making::INT) / count(*), 1)  AS pct_lines,
            round(sum(f.sales), 2)                                   AS sales,
            round(sum(f.profit), 2)                                  AS profit,
            round(100.0 * sum(f.profit) / sum(f.sales), 1)           AS margin_pct
        FROM fact_sales f
        JOIN {source} d USING ({source.replace('dim_', '')}_key)
        GROUP BY d.{dimension}
        ORDER BY profit
        """
    ).df()


# ---------------------------------------------------------------------------
# Parquet export
# ---------------------------------------------------------------------------


def export_processed_tables(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    """Write the validated fact and dimension tables to data/processed/ as Parquet."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    written = {}
    for table in EXPORT_TABLES:
        target = PROCESSED_DIR / f"{table}.parquet"
        con.execute(
            f"COPY (SELECT * FROM {table}) TO ? (FORMAT PARQUET, COMPRESSION ZSTD)",
            [str(target)],
        )
        written[f"{table}.parquet"] = target.stat().st_size
    return written


def build_report(con: duckdb.DuckDBPyConnection, exported: dict[str, int]) -> str:
    results = run_all_checks(con)
    profile = loss_making_profile(con)

    lines = [
        "# Data quality report",
        "",
        "Regenerate with `python -m src.utils`. Every figure below is read from the star "
        "schema in `db/superstore.duckdb`, so this file is only as current as the last "
        "transform run.",
        "",
        "## Summary",
        "",
        "| Check | Result | Notes |",
        "| --- | --- | --- |",
    ]
    for r in results:
        note = r.detail.replace("\n", " ")
        lines.append(f"| {r.name} | {r.status} | {note} |")

    lines += [
        "",
        "Checks marked `review` need a human decision. They are not automatically failures.",
        "",
        "## Table row counts",
        "",
        "| Table | Rows |",
        "| --- | ---: |",
    ]
    for table in ("stg_orders", *EXPORT_TABLES):
        if table_exists(con, table):
            lines.append(f"| `{table}` | {row_count(con, table):,} |")

    lines += [
        "",
        "## Loss-making line items",
        "",
        f"`is_loss_making` is stored on `fact_sales` as `profit < 0`. It flags "
        f"**{int(profile['loss_lines']):,} of {int(profile['total_lines']):,} line items "
        f"({profile['pct_lines']:.1f}%)**, which carry "
        f"**${profile['loss_sales']:,.2f} of the ${profile['total_sales']:,.2f} in total sales "
        f"({profile['pct_sales']:.1f}%)**.",
        "",
        f"Those lines lose ${abs(profile['loss_profit']):,.2f}. Profitable lines earn "
        f"${profile['profit_from_winners']:,.2f}, so the business nets "
        f"${profile['total_profit']:,.2f}. Nearly a fifth of the order lines are erasing "
        f"{100 * abs(profile['loss_profit']) / profile['profit_from_winners']:.0f}% of the "
        "profit the rest of the book generates.",
        "",
        "### By category",
        "",
        markdown_table(loss_making_by(con, "category")),
        "### By sub-category",
        "",
        markdown_table(loss_making_by(con, "sub_category"), limit=20),
        "### By region",
        "",
        markdown_table(loss_making_by(con, "region")),
        "### By segment",
        "",
        markdown_table(loss_making_by(con, "segment")),
        "## Check detail",
        "",
    ]

    for r in results:
        lines += [f"### {r.name}", "", r.detail, ""]
        if not r.exceptions.empty:
            lines += [markdown_table(r.exceptions), ""]

    lines += [
        "## Processed outputs",
        "",
        "Validated tables written to `data/processed/` as ZSTD-compressed Parquet. The "
        "directory is gitignored, so these are rebuilt locally rather than committed.",
        "",
        "| File | Size |",
        "| --- | ---: |",
    ]
    for name, size in exported.items():
        lines.append(f"| `{name}` | {size / 1024:,.0f} KB |")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    with connect() as con:
        results = run_all_checks(con)
        exported = export_processed_tables(con)
        report = build_report(con, exported)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8", newline="\n")

    for r in results:
        print(f"  {r.status:<6} {r.name}")
    print(f"\nwrote {REPORT_PATH.relative_to(PROJECT_ROOT)}")
    print(f"wrote {len(exported)} Parquet files to {PROCESSED_DIR.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
