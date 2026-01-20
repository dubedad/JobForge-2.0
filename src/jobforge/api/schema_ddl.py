"""DDL generator for gold tables.

Generates CREATE TABLE statements from gold parquet files for
use in text-to-SQL prompting.
"""

import json
from pathlib import Path

import duckdb

from jobforge.pipeline.config import PipelineConfig


def _load_catalog_metadata(config: PipelineConfig) -> dict[str, dict]:
    """Load catalog metadata for all tables.

    Args:
        config: Pipeline configuration.

    Returns:
        Dictionary mapping table_name -> full metadata dict.
    """
    catalog_path = config.catalog_tables_path()
    if not catalog_path.exists():
        return {}

    metadata = {}
    for json_file in catalog_path.glob("*.json"):
        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)
                table_name = data.get("table_name")
                if table_name:
                    metadata[table_name] = data
        except (json.JSONDecodeError, IOError):
            # Skip malformed or unreadable files
            continue

    return metadata


def _load_schema_relationships(config: PipelineConfig) -> list[dict]:
    """Load foreign key relationships from schema.

    Args:
        config: Pipeline configuration.

    Returns:
        List of relationship dicts with from_table, from_column, to_table, to_column.
    """
    schema_path = config.catalog_schemas_path() / "wiq_schema.json"
    if not schema_path.exists():
        return []

    try:
        with open(schema_path, encoding="utf-8") as f:
            schema = json.load(f)

        relationships = []
        for table in schema.get("tables", []):
            table_name = table.get("name")
            for column in table.get("columns", []):
                if column.get("is_foreign_key"):
                    relationships.append({
                        "from_table": table_name,
                        "from_column": column.get("name"),
                        "to_table": column.get("references_table"),
                        "to_column": column.get("references_column"),
                    })

        return relationships
    except (json.JSONDecodeError, IOError):
        return []


def _quote_column_name(name: str) -> str:
    """Quote column name if it's numeric.

    Args:
        name: Column name.

    Returns:
        Quoted name if numeric, otherwise name as-is.
    """
    if name.isdigit():
        return f'"{name}"'
    return name


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

    # Load catalog metadata and relationships
    catalog = _load_catalog_metadata(config)
    relationships = _load_schema_relationships(config)

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

        # Get table metadata from catalog
        table_meta = catalog.get(table_name, {})

        # Build column definitions with COMMENT if description exists
        col_defs = []
        for col in cols:
            col_name = _quote_column_name(col[0])
            col_type = col[1]

            # Get column metadata
            col_meta = None
            for c in table_meta.get("columns", []):
                if c.get("name") == col[0]:
                    col_meta = c
                    break

            desc = col_meta.get("description", "") if col_meta else ""
            # Only add COMMENT if description exists and is not generic
            if desc and "Column of type" not in desc:
                # Escape single quotes in description
                desc_escaped = desc.replace("'", "''")
                col_def = f"  {col_name} {col_type} COMMENT '{desc_escaped}'"
            else:
                col_def = f"  {col_name} {col_type}"

            col_defs.append(col_def)

        # Build CREATE TABLE statement
        create_stmt = f"CREATE TABLE {table_name} (\n" + ",\n".join(col_defs) + "\n);"

        # Add table-level comments
        comments = []
        if table_meta.get("description"):
            comments.append(f"-- Table: {table_meta['description']}")

        if table_meta.get("workforce_dynamic"):
            comments.append(f"-- Workforce dynamic: {table_meta['workforce_dynamic']}")

        if table_meta.get("domain"):
            comments.append(f"-- Source: {table_meta['domain']} domain")

        if comments:
            ddl_parts.append("\n".join(comments) + "\n" + create_stmt)
        else:
            ddl_parts.append(create_stmt)

    conn.close()

    # Add RELATIONSHIPS section
    if relationships:
        rel_lines = ["", "-- RELATIONSHIPS:"]
        for rel in relationships:
            rel_line = (
                f"-- {rel['from_table']}.{rel['from_column']} -> "
                f"{rel['to_table']}.{rel['to_column']}"
            )
            rel_lines.append(rel_line)
        ddl_parts.append("\n".join(rel_lines))

    # Add WORKFORCE INTELLIGENCE section
    intelligence = [
        "",
        "-- WORKFORCE INTELLIGENCE:",
        "-- demand tables: cops_employment, cops_employment_growth, cops_retirements, cops_retirement_rates, cops_other_replacement",
        "-- supply tables: cops_immigration, cops_school_leavers, cops_other_seekers",
        "-- Workforce Gap = SUM(job_openings) - SUM(job_seekers_total)",
        '-- For year columns, use quoted names: SELECT "2025" FROM cops_employment',
    ]
    ddl_parts.append("\n".join(intelligence))

    return "\n\n".join(ddl_parts)
