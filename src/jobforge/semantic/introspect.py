"""DuckDB-based utilities for introspecting parquet file schemas.

Provides functions to extract column metadata from gold layer parquet files
and convert them to semantic model Table objects.
"""

from pathlib import Path
from typing import Optional

import duckdb

from jobforge.pipeline.config import PipelineConfig
from jobforge.semantic.models import Column, Table, TableType


# Provenance columns to skip - these are system columns, not business data
PROVENANCE_COLUMNS = frozenset(["_source_file", "_ingested_at", "_batch_id", "_layer"])


def introspect_parquet_schema(parquet_path: Path) -> list[Column]:
    """Introspect column schema from a parquet file using DuckDB.

    Args:
        parquet_path: Path to the parquet file to introspect.

    Returns:
        List of Column objects with name and data_type populated.

    Raises:
        ValueError: If the parquet file does not exist or cannot be read.
    """
    if not parquet_path.exists():
        raise ValueError(f"Parquet file not found: {parquet_path}")

    conn = duckdb.connect(":memory:")
    try:
        # DESCRIBE returns: column_name, column_type, null, key, default, extra
        result = conn.execute(
            f"DESCRIBE SELECT * FROM '{parquet_path}'"
        ).fetchall()

        columns = []
        for row in result:
            column_name = row[0]
            column_type = row[1]

            # Skip provenance columns - they're system metadata, not business schema
            if column_name in PROVENANCE_COLUMNS:
                continue

            columns.append(
                Column(
                    name=column_name,
                    data_type=column_type,
                    is_primary_key=False,
                    is_foreign_key=False,
                )
            )

        return columns
    finally:
        conn.close()


def classify_table_type(table_name: str) -> TableType:
    """Classify a table as dimension, fact, or attribute based on naming convention.

    Naming conventions:
    - dim_*: Dimension tables (lookup/context)
    - cops_*: Fact tables (forecast/measures)
    - element_*, oasis_*: Attribute tables (dimension extensions)
    - job_architecture: Attribute table (special case)

    Args:
        table_name: Name of the table (lowercase, no extension).

    Returns:
        TableType enum value.
    """
    name_lower = table_name.lower()

    if name_lower.startswith("dim_"):
        return TableType.DIMENSION
    elif name_lower.startswith("cops_"):
        return TableType.FACT
    elif name_lower.startswith("element_") or name_lower.startswith("oasis_"):
        return TableType.ATTRIBUTE
    elif name_lower == "job_architecture":
        return TableType.ATTRIBUTE
    else:
        # Default to attribute for unknown patterns
        return TableType.ATTRIBUTE


def introspect_all_gold_tables(config: Optional[PipelineConfig] = None) -> list[Table]:
    """Introspect all parquet files in the gold layer.

    Scans the gold directory for parquet files, introspects each one's schema,
    and creates Table objects with appropriate type classification.

    Args:
        config: Pipeline configuration for locating gold files.
                If None, creates a default PipelineConfig().

    Returns:
        List of Table objects sorted by name.
    """
    if config is None:
        config = PipelineConfig()

    gold_path = config.gold_path()

    if not gold_path.exists():
        return []

    tables = []
    for parquet_file in gold_path.glob("*.parquet"):
        # Normalize table name to lowercase
        table_name = parquet_file.stem.lower()

        # Introspect columns
        columns = introspect_parquet_schema(parquet_file)

        # Classify table type
        table_type = classify_table_type(table_name)

        # Create Table object
        table = Table(
            name=table_name,
            table_type=table_type,
            columns=columns,
        )

        tables.append(table)

    # Sort by name for consistent ordering
    return sorted(tables, key=lambda t: t.name)
