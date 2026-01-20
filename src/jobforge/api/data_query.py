"""Data Query Service using Claude Text-to-SQL.

Converts natural language questions into DuckDB SQL queries using Claude
structured outputs, then executes them against gold parquet files.
"""

import anthropic
from pydantic import BaseModel, Field

from jobforge.api.schema_ddl import generate_schema_ddl
from jobforge.pipeline.config import PipelineConfig
import duckdb


class SQLQuery(BaseModel):
    """Structured output for SQL generation."""

    sql: str = Field(description="DuckDB-compatible SELECT query")
    explanation: str = Field(description="Brief explanation of what the query does")
    tables_used: list[str] = Field(description="Tables referenced in the query")


class DataQueryResult(BaseModel):
    """Result of a data query."""

    question: str
    sql: str
    explanation: str
    results: list[dict]
    row_count: int
    error: str | None = None


class DataQueryService:
    """Service for natural language to SQL queries.

    Uses Claude's structured outputs to generate DuckDB-compatible SQL
    from natural language questions, then executes against gold tables.
    """

    SYSTEM_PROMPT = """You are a SQL expert for the WiQ (Workforce Intelligence) database.
Given a schema and question, generate a DuckDB-compatible SELECT query.
The database contains Canadian occupational data:
- dim_noc: National Occupational Classification hierarchy
- dim_occupations: Occupational groups with TBS metadata
- cops_*: Canadian Occupational Projection System forecasts
- oasis_*: Occupational attributes (skills, abilities, knowledge)
- element_*: NOC element data (titles, duties, requirements)
- job_architecture: Internal job architecture hierarchy

IMPORTANT:
- Only generate SELECT queries (never INSERT, UPDATE, DELETE, DROP)
- Use DuckDB SQL syntax
- Keep queries simple and focused on answering the question
- Limit results to 100 rows unless explicitly asked for more"""

    def __init__(
        self,
        config: PipelineConfig | None = None,
        client: anthropic.Anthropic | None = None,
    ):
        """Initialize the data query service.

        Args:
            config: Pipeline configuration for gold table paths.
            client: Anthropic client. If None, creates one from env vars.
        """
        self.config = config or PipelineConfig()
        self.client = client or anthropic.Anthropic()
        self._schema_ddl: str | None = None
        self._conn: duckdb.DuckDBPyConnection | None = None

    @property
    def schema_ddl(self) -> str:
        """Get or generate schema DDL lazily."""
        if self._schema_ddl is None:
            self._schema_ddl = generate_schema_ddl(self.config)
        return self._schema_ddl

    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        """Get or create DuckDB connection with gold tables registered."""
        if self._conn is None:
            self._conn = duckdb.connect(":memory:")
            # Register all gold tables as views
            gold_path = self.config.gold_path()
            if gold_path.exists():
                for parquet in gold_path.glob("*.parquet"):
                    table_name = parquet.stem
                    parquet_path = str(parquet).replace("\\", "/")
                    self._conn.execute(
                        f"CREATE VIEW {table_name} AS SELECT * FROM '{parquet_path}'"
                    )
        return self._conn

    def query(self, question: str) -> DataQueryResult:
        """Generate SQL from question and execute.

        Args:
            question: Natural language question about WiQ data.

        Returns:
            DataQueryResult with SQL, explanation, and results (or error).
        """
        try:
            # Generate SQL using Claude structured outputs
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=self.SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": f"Schema:\n{self.schema_ddl}\n\nQuestion: {question}",
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

            # Execute query
            df = self.conn.execute(sql_result.sql).fetchdf()
            results = df.to_dict(orient="records")

            return DataQueryResult(
                question=question,
                sql=sql_result.sql,
                explanation=sql_result.explanation,
                results=results,
                row_count=len(results),
            )

        except anthropic.AuthenticationError as e:
            return DataQueryResult(
                question=question,
                sql="",
                explanation="",
                results=[],
                row_count=0,
                error=f"Anthropic API authentication error: {e}",
            )
        except Exception as e:
            return DataQueryResult(
                question=question,
                sql="",
                explanation="",
                results=[],
                row_count=0,
                error=str(e),
            )

    def close(self) -> None:
        """Close the DuckDB connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
