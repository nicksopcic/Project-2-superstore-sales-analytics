"""Run a commented SQL suite against the star schema and write the results to Markdown.

The SQL files are the deliverable, not this module. Queries are annotated with a header of
the form:

    -- name: some_query_name
    -- One or more comment lines stating the business question.
    SELECT ...;

This module splits on those headers, runs each statement, and renders the result as a
Markdown table under its question. Keeping the SQL in .sql files means it stays runnable in
any DuckDB client rather than being trapped inside Python strings.

Run with: python -m src.run_sql_report [suite ...]
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

import duckdb
import pandas as pd

from src.utils import (
    REPORTS_DIR,
    SQL_DIR,
    connect,
    markdown_table,
    require_star_schema,
)

# suite name -> (sql file, report file, report title)
SUITES = {
    "fundamental": (
        "02_fundamental_queries.sql",
        "sql_fundamental_results.md",
        "Fundamental SQL results",
    ),
    "advanced": (
        "03_advanced_queries.sql",
        "sql_advanced_results.md",
        "Advanced SQL results",
    ),
}

NAME_TAG = "-- name:"
MAX_ROWS_IN_REPORT = 20


@dataclass
class Query:
    """One named query: its question, the SQL to run, and where it came from."""

    name: str
    question: str
    sql: str

    @property
    def title(self) -> str:
        return self.name.replace("_", " ").capitalize()


def parse_queries(sql_text: str) -> list[Query]:
    """Split a suite file into named queries on its `-- name:` tags."""
    queries: list[Query] = []
    name: str | None = None
    question: list[str] = []
    body: list[str] = []

    def flush() -> None:
        if name is None:
            return
        statement = "\n".join(body).strip().rstrip(";").strip()
        if statement:
            queries.append(Query(name, " ".join(question).strip(), statement))

    for line in sql_text.splitlines():
        stripped = line.strip()
        if stripped.startswith(NAME_TAG):
            flush()
            name = stripped[len(NAME_TAG):].strip()
            question, body = [], []
        elif name is None:
            continue  # File-level preamble before the first query.
        elif stripped.startswith("--"):
            comment = stripped.lstrip("-").strip()
            if comment and not body:
                question.append(comment)
            elif comment:
                body.append(line)
        else:
            body.append(line)

    flush()
    return queries


def run_query(con: duckdb.DuckDBPyConnection, query: Query) -> pd.DataFrame:
    try:
        return con.execute(query.sql).df()
    except duckdb.Error as exc:
        raise RuntimeError(f"Query '{query.name}' failed: {exc}") from exc


def build_report(
    con: duckdb.DuckDBPyConnection, queries: list[Query], title: str, source_file: str
) -> str:
    lines = [
        f"# {title}",
        "",
        f"Generated from [`sql/{source_file}`](../sql/{source_file}) by "
        "`python -m src.run_sql_report`. Each section shows the business question, the result, "
        "and the SQL that produced it.",
        "",
        f"{len(queries)} queries.",
        "",
        "## Contents",
        "",
    ]
    lines += [f"{i}. [{q.title}](#{q.name.replace('_', '-')})" for i, q in enumerate(queries, 1)]
    lines.append("")

    for query in queries:
        result = run_query(con, query)
        lines += [
            f"## {query.title}",
            "",
            f"<a id=\"{query.name.replace('_', '-')}\"></a>",
            "",
            f"**{query.question}**" if query.question else "",
            "",
            markdown_table(result, limit=MAX_ROWS_IN_REPORT),
            "",
            "<details><summary>SQL</summary>",
            "",
            "```sql",
            query.sql,
            "```",
            "",
            "</details>",
            "",
        ]

    return "\n".join(lines)


def run_suite(con: duckdb.DuckDBPyConnection, suite: str) -> tuple[int, str]:
    """Run one suite and write its report. Returns the query count and the report path."""
    if suite not in SUITES:
        raise KeyError(f"Unknown suite '{suite}'. Choose from {', '.join(SUITES)}.")

    sql_file, report_file, title = SUITES[suite]
    sql_path = SQL_DIR / sql_file
    if not sql_path.exists():
        raise FileNotFoundError(f"{sql_path} does not exist yet.")

    queries = parse_queries(sql_path.read_text(encoding="utf-8"))
    if not queries:
        raise RuntimeError(f"No '{NAME_TAG}' tagged queries found in {sql_path.name}.")

    report = build_report(con, queries, title, sql_file)
    report_path = REPORTS_DIR / report_file
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8", newline="\n")
    return len(queries), str(report_path.relative_to(REPORTS_DIR.parent))


def has_queries(suite: str) -> bool:
    """True when the suite file exists and holds at least one tagged query."""
    path = SQL_DIR / SUITES[suite][0]
    return path.exists() and NAME_TAG in path.read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    # With no arguments, run whichever suites are written. Later phases fill in the rest,
    # and a stub file with no tagged queries is skipped rather than treated as an error.
    requested = argv if argv else [s for s in SUITES if has_queries(s)]
    if not requested:
        print("No SQL suites are populated yet.")
        return

    with connect(read_only=True) as con:
        require_star_schema(con)
        for suite in requested:
            count, path = run_suite(con, suite)
            print(f"{suite:<12} {count:>2} queries -> {path}")


if __name__ == "__main__":
    main(sys.argv[1:])
