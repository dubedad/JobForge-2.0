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

import sys
from pathlib import Path
from typing import Any

import anthropic
import duckdb
from pydantic import BaseModel, Field

# Add project root to path for jobforge imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from jobforge.api.schema_ddl import generate_schema_ddl
from jobforge.pipeline.config import PipelineConfig


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
Given a schema and question, generate a DuckDB-compatible SELECT query.
The database contains Canadian occupational data:
- dim_noc: National Occupational Classification hierarchy (NOC 2021)
- dim_occupations: Occupational groups with TBS metadata
- cops_*: Canadian Occupational Projection System forecasts (2023-2033)
- oasis_*: Occupational attributes (skills, abilities, knowledge)
- element_*: NOC element data (titles, duties, requirements)
- job_architecture: Internal job architecture hierarchy

WORKFORCE INTELLIGENCE PATTERNS:
- demand tables: cops_employment, cops_employment_growth, cops_retirements, cops_retirement_rates, cops_other_replacement
- supply tables: cops_immigration, cops_school_leavers, cops_other_seekers
- For "shortage" or "gap" queries: compare demand vs supply
- NOC codes are 5-digit strings (e.g., '21232' for Software Engineers)
- Year columns MUST be quoted: SELECT "2025" FROM cops_employment

ENTITY RECOGNITION:
- NOC codes: 5-digit numbers like 21232, 41200, 00010
- Occupation names: "Software Engineers", "Financial Managers", etc.
- Years: 2023-2033 (projection period)

IMPORTANT:
- Only generate SELECT queries (never INSERT, UPDATE, DELETE, DROP)
- Use DuckDB SQL syntax
- Quote year columns with double quotes: SELECT "2025"
- Keep queries simple and focused on answering the question
- Limit results to 100 rows unless explicitly asked for more"""

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
        """Initialize DuckDB connection and generate enhanced schema DDL."""
        self._conn = duckdb.connect(":memory:")
        self._client = anthropic.Anthropic()

        # Register parquet files as views
        for parquet in sorted(self.parquet_path.glob("*.parquet")):
            table_name = parquet.stem
            abs_path = str(parquet.resolve()).replace("\\", "/")
            self._conn.execute(
                f"CREATE VIEW {table_name} AS SELECT * FROM '{abs_path}'"
            )

        # Use enhanced DDL generator (reads enriched catalog)
        try:
            config = PipelineConfig()
            self._schema_ddl = generate_schema_ddl(config)
        except Exception:
            # Fallback to basic DDL if jobforge not available
            self._schema_ddl = self._generate_basic_ddl()

    def _generate_basic_ddl(self) -> str:
        """Generate basic DDL as fallback."""
        ddl_parts = []
        for parquet in sorted(self.parquet_path.glob("*.parquet")):
            table_name = parquet.stem
            cols = self._conn.execute(f"DESCRIBE {table_name}").fetchall()
            col_defs = [f"  {col[0]} {col[1]}" for col in cols]
            ddl_parts.append(f"CREATE TABLE {table_name} (\n" + ",\n".join(col_defs) + "\n);")
        return "\n\n".join(ddl_parts)

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
