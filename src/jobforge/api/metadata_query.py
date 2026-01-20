"""Metadata Query Service wrapping LineageQueryEngine.

Extends the rule-based lineage query engine with additional catalogue patterns
for answering metadata questions about WiQ tables and schemas.
"""

import json
import re
from pathlib import Path
from typing import Callable

import duckdb

from jobforge.governance.graph import LineageGraph
from jobforge.governance.query import LineageQueryEngine
from jobforge.pipeline.config import PipelineConfig


class MetadataQueryService:
    """Service for natural language metadata queries.

    Extends LineageQueryEngine patterns with catalogue-level queries like
    table counts, column listings, and table descriptions from catalog metadata.
    """

    def __init__(self, config: PipelineConfig | None = None) -> None:
        """Initialize the metadata query service.

        Args:
            config: Pipeline configuration for accessing paths.
        """
        self.config = config or PipelineConfig()
        self.graph = LineageGraph(self.config)
        self.lineage_engine = LineageQueryEngine(self.graph)
        self.patterns: list[tuple[re.Pattern, Callable]] = self._build_patterns()

    def _build_patterns(self) -> list[tuple[re.Pattern, Callable]]:
        """Build additional patterns beyond LineageQueryEngine.

        Returns:
            List of (compiled pattern, handler function) tuples.
        """
        return [
            # Catalogue patterns
            (re.compile(r"describe (?:table )?(\w+)", re.I), self._handle_describe),
            (re.compile(r"what columns (?:are )?in (\w+)", re.I), self._handle_columns),
            (re.compile(r"how many (?:gold )?tables", re.I), self._handle_table_count),
            (re.compile(r"list (?:all )?(?:gold )?tables", re.I), self._handle_list_tables),
            # Row count patterns
            (
                re.compile(r"how many rows (?:are )?in (\w+)", re.I),
                self._handle_row_count,
            ),
            # Schema patterns
            (re.compile(r"what (?:is the )?schema (?:of |for )?(\w+)", re.I), self._handle_schema),
        ]

    def query(self, question: str) -> str:
        """Process metadata question, return human-readable answer.

        Tries extended patterns first, then falls back to lineage engine.

        Args:
            question: Natural language question about metadata.

        Returns:
            Human-readable answer.
        """
        # Try extended patterns first
        for pattern, handler in self.patterns:
            match = pattern.search(question)
            if match:
                return handler(*match.groups()) if match.groups() else handler()

        # Fall back to lineage engine
        return self.lineage_engine.query(question)

    def _handle_describe(self, table_name: str) -> str:
        """Describe a table from catalogue metadata.

        Args:
            table_name: Name of the table to describe.

        Returns:
            Table description from catalog metadata.
        """
        table_name = table_name.lower()
        catalog_path = self.config.catalog_tables_path() / f"{table_name}.json"

        if not catalog_path.exists():
            return f"Table '{table_name}' not found in catalog."

        try:
            metadata = json.loads(catalog_path.read_text(encoding="utf-8"))
            name = metadata.get("table_name", table_name)
            description = metadata.get("description", "No description available.")
            row_count = metadata.get("row_count", "Unknown")
            layer = metadata.get("layer", "gold")

            lines = [
                f"Table: {name}",
                f"Layer: {layer}",
                f"Rows: {row_count:,}" if isinstance(row_count, int) else f"Rows: {row_count}",
                f"Description: {description}",
            ]

            # Add column info if available
            columns = metadata.get("columns", [])
            if columns:
                lines.append("")
                lines.append(f"Columns ({len(columns)}):")
                for col in columns[:10]:  # Limit to first 10
                    col_name = col.get("name", col.get("column_name", "?"))
                    col_type = col.get("type", col.get("dtype", "?"))
                    lines.append(f"  - {col_name} ({col_type})")
                if len(columns) > 10:
                    lines.append(f"  ... and {len(columns) - 10} more")

            return "\n".join(lines)
        except Exception as e:
            return f"Error reading catalog metadata: {e}"

    def _handle_columns(self, table_name: str) -> str:
        """List columns in a table.

        Args:
            table_name: Name of the table.

        Returns:
            List of column names and types.
        """
        table_name = table_name.lower()
        catalog_path = self.config.catalog_tables_path() / f"{table_name}.json"

        if not catalog_path.exists():
            # Try to get from parquet schema
            parquet_path = self.config.gold_path() / f"{table_name}.parquet"
            if parquet_path.exists():
                conn = duckdb.connect(":memory:")
                parquet_str = str(parquet_path).replace("\\", "/")
                cols = conn.execute(
                    f"DESCRIBE SELECT * FROM '{parquet_str}'"
                ).fetchall()
                conn.close()

                lines = [f"Columns in {table_name}:"]
                for col in cols:
                    lines.append(f"  - {col[0]} ({col[1]})")
                return "\n".join(lines)

            return f"Table '{table_name}' not found."

        try:
            metadata = json.loads(catalog_path.read_text(encoding="utf-8"))
            columns = metadata.get("columns", [])

            if not columns:
                return f"No column metadata available for '{table_name}'."

            lines = [f"Columns in {table_name} ({len(columns)} total):"]
            for col in columns:
                col_name = col.get("name", col.get("column_name", "?"))
                col_type = col.get("type", col.get("dtype", "?"))
                lines.append(f"  - {col_name} ({col_type})")
            return "\n".join(lines)
        except Exception as e:
            return f"Error reading column metadata: {e}"

    def _handle_table_count(self) -> str:
        """Count gold tables.

        Returns:
            Count of tables in the gold layer.
        """
        gold_path = self.config.gold_path()
        if not gold_path.exists():
            return "Gold layer not found."

        count = len(list(gold_path.glob("*.parquet")))
        return f"There are {count} tables in the gold layer."

    def _handle_list_tables(self) -> str:
        """List all gold tables.

        Returns:
            List of table names in the gold layer.
        """
        gold_path = self.config.gold_path()
        if not gold_path.exists():
            return "Gold layer not found."

        tables = sorted(p.stem for p in gold_path.glob("*.parquet"))
        if not tables:
            return "No tables found in the gold layer."

        lines = ["Gold layer tables:", ""]

        # Group by prefix
        prefixes: dict[str, list[str]] = {}
        for t in tables:
            prefix = t.split("_")[0] if "_" in t else "other"
            if prefix not in prefixes:
                prefixes[prefix] = []
            prefixes[prefix].append(t)

        for prefix in sorted(prefixes.keys()):
            lines.append(f"{prefix.upper()}:")
            for t in prefixes[prefix]:
                lines.append(f"  - {t}")
            lines.append("")

        return "\n".join(lines).strip()

    def _handle_row_count(self, table_name: str) -> str:
        """Get row count for a table.

        Args:
            table_name: Name of the table.

        Returns:
            Row count information.
        """
        table_name = table_name.lower()
        path = self.config.gold_path() / f"{table_name}.parquet"

        if not path.exists():
            return f"Table '{table_name}' not found."

        conn = duckdb.connect(":memory:")
        path_str = str(path).replace("\\", "/")
        count = conn.execute(f"SELECT COUNT(*) FROM '{path_str}'").fetchone()[0]
        conn.close()

        return f"Table '{table_name}' has {count:,} rows."

    def _handle_schema(self, table_name: str) -> str:
        """Get schema for a table.

        Args:
            table_name: Name of the table.

        Returns:
            Schema information in DDL format.
        """
        table_name = table_name.lower()
        path = self.config.gold_path() / f"{table_name}.parquet"

        if not path.exists():
            return f"Table '{table_name}' not found."

        conn = duckdb.connect(":memory:")
        path_str = str(path).replace("\\", "/")
        cols = conn.execute(f"DESCRIBE SELECT * FROM '{path_str}'").fetchall()
        conn.close()

        col_defs = [f"  {col[0]} {col[1]}" for col in cols]
        ddl = f"CREATE TABLE {table_name} (\n" + ",\n".join(col_defs) + "\n);"
        return ddl
