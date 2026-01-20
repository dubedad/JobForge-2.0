"""DDL generator for gold tables.

Generates CREATE TABLE statements from gold parquet files for
use in text-to-SQL prompting.
"""

import duckdb

from jobforge.pipeline.config import PipelineConfig


def generate_schema_ddl(config: PipelineConfig | None = None) -> str:
    """Generate DDL for all gold tables.

    Introspects parquet files in the gold layer and generates CREATE TABLE
    statements that describe the schema. These DDL statements are used
    as context for Claude's text-to-SQL generation.

    Args:
        config: Pipeline configuration. Defaults to standard PipelineConfig.

    Returns:
        DDL string containing CREATE TABLE statements for all gold tables.
    """
    config = config or PipelineConfig()
    conn = duckdb.connect(":memory:")

    ddl_parts = []
    gold_path = config.gold_path()

    if not gold_path.exists():
        return "-- No gold tables found"

    for parquet in sorted(gold_path.glob("*.parquet")):
        table_name = parquet.stem
        # Create view to introspect schema
        parquet_path = str(parquet).replace("\\", "/")
        conn.execute(f"CREATE VIEW {table_name} AS SELECT * FROM '{parquet_path}'")
        # Get column info
        cols = conn.execute(f"DESCRIBE {table_name}").fetchall()
        col_defs = [f"  {col[0]} {col[1]}" for col in cols]
        ddl_parts.append(f"CREATE TABLE {table_name} (\n" + ",\n".join(col_defs) + "\n);")

    conn.close()
    return "\n\n".join(ddl_parts)
