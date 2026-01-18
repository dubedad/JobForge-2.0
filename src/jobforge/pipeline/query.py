"""DuckDB query interface for gold layer data."""

from pathlib import Path
from typing import Optional

import duckdb
import polars as pl

from jobforge.pipeline.config import PipelineConfig


class GoldQueryEngine:
    """SQL query interface for gold layer parquet files.

    Provides DuckDB-based querying of gold layer data with
    provenance tracking support.
    """

    def __init__(
        self,
        config: Optional[PipelineConfig] = None,
        db_path: Optional[Path] = None,
    ) -> None:
        """Initialize the query engine.

        Args:
            config: Pipeline configuration for locating gold files.
            db_path: Optional path to persist DuckDB database.
                     If None, uses in-memory database.
        """
        self.config = config or PipelineConfig()
        self._registered_tables: list[str] = []

        if db_path is not None:
            self._conn = duckdb.connect(str(db_path))
        else:
            self._conn = duckdb.connect(":memory:")

    def register_gold_tables(self) -> list[str]:
        """Register all gold layer parquet files as DuckDB views.

        Scans the gold directory and creates a view for each
        parquet file found.

        Returns:
            List of registered table names.
        """
        gold_dir = self.config.gold_path()

        if not gold_dir.exists():
            return []

        registered = []
        for parquet_file in gold_dir.glob("*.parquet"):
            table_name = parquet_file.stem
            # Create view for the parquet file
            self._conn.execute(
                f"CREATE OR REPLACE VIEW {table_name} AS "
                f"SELECT * FROM '{parquet_file}'"
            )
            registered.append(table_name)

        self._registered_tables = registered
        return registered

    def query(self, sql: str) -> pl.DataFrame:
        """Execute SQL query against registered tables.

        Args:
            sql: SQL query string.

        Returns:
            Query result as Polars DataFrame.
        """
        return self._conn.execute(sql).pl()

    def query_with_provenance(self, sql: str) -> pl.DataFrame:
        """Execute SQL query ensuring provenance columns are included.

        Useful for audit queries where lineage tracking is required.

        Args:
            sql: SQL query string.

        Returns:
            Query result as Polars DataFrame with provenance columns.
        """
        # Execute the query
        result = self.query(sql)

        # Verify provenance columns are present
        provenance_cols = ["_source_file", "_batch_id", "_ingested_at"]
        for col in provenance_cols:
            if col not in result.columns:
                raise ValueError(
                    f"Provenance column '{col}' not found in result. "
                    "Ensure your query selects provenance columns or use SELECT *."
                )

        return result

    def get_lineage(self, table_name: str) -> dict:
        """Get provenance summary for a gold table.

        Groups data by source file and provides lineage statistics.

        Args:
            table_name: Name of the registered gold table.

        Returns:
            Dict with lineage information including:
            - source_files: list of source files
            - row_counts: dict of source file to row count
            - ingested_range: min/max ingestion timestamps
        """
        # Query provenance information
        result = self._conn.execute(
            f"""
            SELECT
                _source_file,
                COUNT(*) as row_count,
                MIN(_ingested_at) as first_ingested,
                MAX(_ingested_at) as last_ingested
            FROM {table_name}
            GROUP BY _source_file
            """
        ).pl()

        source_files = result["_source_file"].to_list()
        row_counts = dict(zip(source_files, result["row_count"].to_list()))

        # Get overall range
        all_first = result["first_ingested"].to_list()
        all_last = result["last_ingested"].to_list()

        return {
            "table_name": table_name,
            "source_files": source_files,
            "row_counts": row_counts,
            "total_rows": sum(row_counts.values()),
            "ingested_range": {
                "min": min(all_first) if all_first else None,
                "max": max(all_last) if all_last else None,
            },
        }

    def list_tables(self) -> list[str]:
        """Get list of registered table names.

        Returns:
            List of table names that have been registered.
        """
        return list(self._registered_tables)

    def close(self) -> None:
        """Close the DuckDB connection."""
        self._conn.close()

    def __enter__(self) -> "GoldQueryEngine":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - close connection."""
        self.close()
