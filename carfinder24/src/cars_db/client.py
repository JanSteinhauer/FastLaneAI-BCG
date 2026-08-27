"""SQL client for the used-car dataset shipped in this repo.

`CarsDB` loads data/autoscout24_de.parquet (~46k German AutoScout24 listings,
snapshot 2025-11-08, see scripts/build_dataset.py) into an in-memory DuckDB
table named `ads` and executes whatever SQL it is given — writing the queries
is the caller's job (the MCP tools). One instance is meant to be shared by all
tools; every `query()` call runs on its own cursor.

    db = CarsDB("data/autoscout24_de.parquet")
    db.query("DESCRIBE ads")  # column names and types
    db.query(
        "SELECT * FROM ads WHERE price <= $price AND mileage_km <= $km LIMIT 5",
        {"price": 15_000, "km": 100_000},
    )

The in-memory database is yours to extend: `CREATE MACRO`, `CREATE TABLE ...
AS SELECT`, temp views etc. all work, so tools can set up whatever SQL helpers
they need at startup. Only the filesystem is off-limits — the connection is
cut off from it after loading, so candidate- or LLM-written SQL can only
touch the in-memory data.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Self

import duckdb


class CarsDB:
    """Executes SQL against a used-car listings Parquet file (table `ads`)."""

    def __init__(self, parquet_path: Path | str) -> None:
        path = Path(parquet_path)
        if not path.exists():
            raise FileNotFoundError(
                f"dataset not found at {path} — run scripts/build_dataset.py "
                "to create it"
            )
        self._con = duckdb.connect()
        self._con.execute(
            "CREATE TABLE ads AS SELECT * FROM read_parquet(?)", [str(path)]
        )
        # The data is loaded; cut the connection off from the filesystem so
        # arbitrary (tool-generated) SQL stays sandboxed to the in-memory db.
        self._con.execute("SET disabled_filesystems = 'LocalFileSystem'")
        self._con.execute("SET lock_configuration = true")

    def query(
        self, sql: str, params: dict[str, Any] | list[Any] | None = None
    ) -> list[dict[str, Any]]:
        """Run SQL and return the rows as dicts.

        Use $name (with a params dict) or ? (with a params list) placeholders
        for values — never interpolate user input into the SQL string.
        """
        cursor = self._con.cursor()
        try:
            result = cursor.execute(sql, params)
            columns = [d[0] for d in result.description]
            return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]
        finally:
            cursor.close()

    def close(self) -> None:
        self._con.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
