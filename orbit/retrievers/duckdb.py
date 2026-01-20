"""DuckDB Retriever for Orbit - queries parquet files directly.

This retriever enables Orbit to query DuckDB parquet files using text-to-SQL.
It follows the same pattern as Orbit's built-in SQLiteRetriever.

Usage:
    Copy this file to orbit/server/retrievers/duckdb.py
    Register in orbit/server/retrievers/__init__.py

Configuration (adapters.yaml):
    implementation: retrievers.duckdb.DuckDBRetriever
    config:
        parquet_path: "data/gold/"
        anthropic_model: "claude-sonnet-4-20250514"
"""

from pathlib import Path
from typing import Any

import anthropic
import duckdb
from pydantic import BaseModel, Field


class SQLQuery(BaseModel):
    """Structured output for SQL generation."""

    sql: str = Field(description="DuckDB-compatible SELECT query")
    explanation: str = Field(description="Brief explanation of what the query does")


class DuckDBRetriever:
    """Orbit retriever for DuckDB parquet queries.

    This retriever uses Claude structured outputs to generate SQL from
    natural language, then executes against DuckDB in-memory views.

    Attributes:
        parquet_path: Path to directory containing parquet files.
        model: Anthropic model ID to use for SQL generation.
    """

    SYSTEM_PROMPT = """You are a SQL expert for the WiQ (Workforce Intelligence) database.
Generate DuckDB-compatible SELECT queries only. Never modify data.
The database contains Canadian occupational data:
- dim_noc: National Occupational Classification hierarchy
- dim_occupations: Occupational groups with TBS metadata
- cops_*: Canadian Occupational Projection System forecasts
- oasis_*: Occupational attributes (skills, abilities, knowledge)
- element_*: NOC element data (titles, duties, requirements)
- job_architecture: Internal job architecture hierarchy"""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the retriever.

        Args:
            config: Retriever configuration from adapters.yaml.
                - parquet_path: Path to parquet files directory (default: "data/gold")
                - anthropic_model: Claude model ID (default: "claude-sonnet-4-20250514")
        """
        self.parquet_path = Path(config.get("parquet_path", "data/gold"))
        self.model = config.get("anthropic_model", "claude-sonnet-4-20250514")
        self._conn: duckdb.DuckDBPyConnection | None = None
        self._schema_ddl: str | None = None
        self._client: anthropic.Anthropic | None = None

    def initialize(self) -> None:
        """Initialize DuckDB connection and register parquet tables as views.

        Creates an in-memory DuckDB connection and registers each parquet file
        in the parquet_path directory as a view. Also generates schema DDL for
        use in the SQL generation prompt.
        """
        self._conn = duckdb.connect(":memory:")
        self._client = anthropic.Anthropic()

        ddl_parts = []
        for parquet in sorted(self.parquet_path.glob("*.parquet")):
            table_name = parquet.stem
            # Use absolute path for parquet file
            abs_path = str(parquet.resolve()).replace("\\", "/")
            self._conn.execute(
                f"CREATE VIEW {table_name} AS SELECT * FROM '{abs_path}'"
            )
            # Get schema for DDL
            cols = self._conn.execute(f"DESCRIBE {table_name}").fetchall()
            col_defs = [f"  {col[0]} {col[1]}" for col in cols]
            ddl_parts.append(
                f"CREATE TABLE {table_name} (\n" + ",\n".join(col_defs) + "\n);"
            )

        self._schema_ddl = "\n\n".join(ddl_parts)

    def retrieve(self, query: str, collection_name: str = "") -> list[dict]:
        """Generate SQL from query and execute.

        Args:
            query: Natural language question about the data.
            collection_name: Unused parameter for interface compatibility with
                other Orbit retrievers.

        Returns:
            List of result dictionaries. On error, returns a single dict with
            'error' and 'query' keys.
        """
        if self._conn is None:
            self.initialize()

        try:
            # Generate SQL using Claude structured outputs
            response = self._client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=self._get_system_prompt(),
                messages=[
                    {
                        "role": "user",
                        "content": f"Schema:\n{self._schema_ddl}\n\nQuestion: {query}",
                    }
                ],
                extra_headers={"anthropic-beta": "structured-outputs-2025-11-13"},
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "sql_query",
                        "schema": SQLQuery.model_json_schema(),
                    },
                },
            )

            sql_result = SQLQuery.model_validate_json(response.content[0].text)

            # Execute and return results
            df = self._conn.execute(sql_result.sql).fetchdf()
            return df.to_dict(orient="records")

        except Exception as e:
            return [{"error": str(e), "query": query}]

    def _get_system_prompt(self) -> str:
        """Get the system prompt for SQL generation."""
        return self.SYSTEM_PROMPT

    def close(self) -> None:
        """Close DuckDB connection and release resources."""
        if self._conn:
            self._conn.close()
            self._conn = None
        self._client = None
        self._schema_ddl = None
