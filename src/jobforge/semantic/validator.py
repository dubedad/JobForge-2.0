"""Schema validation utilities for Power BI compatibility.

This module provides validation functions to ensure the semantic schema
is compatible with Power BI requirements: no circular relationships,
valid column references, and appropriate cardinality.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import duckdb

from jobforge.pipeline.config import PipelineConfig
from jobforge.semantic.models import Cardinality, SemanticSchema


@dataclass
class ValidationResult:
    """Result of schema validation.

    Attributes:
        is_valid: True if schema passed all validation checks (no errors).
        errors: List of error messages (blocking issues).
        warnings: List of warning messages (non-blocking concerns).
    """

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        """Human-readable summary of validation result."""
        status = "VALID" if self.is_valid else "INVALID"
        parts = [f"ValidationResult({status})"]
        if self.errors:
            parts.append(f"  Errors ({len(self.errors)}):")
            for err in self.errors:
                parts.append(f"    - {err}")
        if self.warnings:
            parts.append(f"  Warnings ({len(self.warnings)}):")
            for warn in self.warnings:
                parts.append(f"    - {warn}")
        return "\n".join(parts)


def check_no_circular_relationships(schema: SemanticSchema) -> list[str]:
    """Check that relationships form a directed acyclic graph.

    Uses depth-first search to detect cycles in the relationship graph.

    Args:
        schema: The semantic schema to validate.

    Returns:
        List of error messages for any detected cycles.
    """
    # Build adjacency list: from_table -> [to_table, ...]
    graph: dict[str, list[str]] = defaultdict(list)
    for rel in schema.relationships:
        graph[rel.from_table].append(rel.to_table)

    # Track visit states: 0=unvisited, 1=visiting, 2=visited
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = defaultdict(int)
    errors: list[str] = []

    def dfs(node: str, path: list[str]) -> bool:
        """DFS to detect back edges (cycles).

        Returns True if cycle detected.
        """
        color[node] = GRAY
        path.append(node)

        for neighbor in graph[node]:
            if color[neighbor] == GRAY:
                # Back edge found - cycle detected
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                errors.append(f"Circular relationship detected: {' -> '.join(cycle)}")
                return True
            elif color[neighbor] == WHITE:
                if dfs(neighbor, path):
                    return True

        path.pop()
        color[node] = BLACK
        return False

    # Check all nodes (some may not be reachable from others)
    all_tables = set(graph.keys())
    for rel in schema.relationships:
        all_tables.add(rel.to_table)

    for table in all_tables:
        if color[table] == WHITE:
            dfs(table, [])

    return errors


def check_relationship_columns_exist(schema: SemanticSchema) -> list[str]:
    """Check that all relationship columns exist in their respective tables.

    Args:
        schema: The semantic schema to validate.

    Returns:
        List of error messages for missing columns.
    """
    errors: list[str] = []

    # Build column lookup: table_name -> set of column names
    table_columns: dict[str, set[str]] = {}
    for table in schema.tables:
        table_columns[table.name] = {col.name for col in table.columns}

    for rel in schema.relationships:
        # Check from_table exists
        if rel.from_table not in table_columns:
            errors.append(
                f"Relationship references non-existent table: {rel.from_table}"
            )
        elif rel.from_column not in table_columns[rel.from_table]:
            errors.append(
                f"Column '{rel.from_column}' not found in table '{rel.from_table}'"
            )

        # Check to_table exists
        if rel.to_table not in table_columns:
            errors.append(
                f"Relationship references non-existent table: {rel.to_table}"
            )
        elif rel.to_column not in table_columns[rel.to_table]:
            errors.append(
                f"Column '{rel.to_column}' not found in table '{rel.to_table}'"
            )

    return errors


def check_cardinality_valid(
    schema: SemanticSchema, config: Optional[PipelineConfig] = None
) -> list[str]:
    """Check that cardinality constraints are satisfied by the data.

    For ONE_TO_MANY relationships, the 'one' side should have unique values.
    This is a warning check - the relationship may still work in Power BI.

    Args:
        schema: The semantic schema to validate.
        config: Pipeline configuration for locating parquet files.
                If None, creates a default PipelineConfig().

    Returns:
        List of warning messages for cardinality violations.
    """
    if config is None:
        config = PipelineConfig()

    warnings: list[str] = []
    gold_path = config.gold_path()

    if not gold_path.exists():
        warnings.append(f"Gold path does not exist: {gold_path}")
        return warnings

    conn = duckdb.connect(":memory:")
    try:
        for rel in schema.relationships:
            if rel.cardinality == Cardinality.ONE_TO_MANY:
                # The 'one' side (from_table.from_column) should have unique values
                parquet_path = gold_path / f"{rel.from_table}.parquet"
                if not parquet_path.exists():
                    continue

                try:
                    result = conn.execute(
                        f"""
                        SELECT COUNT(*) = COUNT(DISTINCT {rel.from_column})
                        FROM '{parquet_path}'
                        """
                    ).fetchone()

                    if result and not result[0]:
                        warnings.append(
                            f"Cardinality warning: '{rel.from_table}.{rel.from_column}' "
                            f"has duplicate values but relationship is 1:*"
                        )
                except Exception as e:
                    warnings.append(
                        f"Could not validate cardinality for {rel.from_table}.{rel.from_column}: {e}"
                    )
    finally:
        conn.close()

    return warnings


def check_column_types_compatible(schema: SemanticSchema) -> list[str]:
    """Check that related columns have compatible data types.

    For relationships to work correctly, the from_column and to_column
    should have the same (or compatible) data types.

    Args:
        schema: The semantic schema to validate.

    Returns:
        List of error messages for type mismatches.
    """
    errors: list[str] = []

    # Build column type lookup: (table_name, column_name) -> data_type
    column_types: dict[tuple[str, str], str] = {}
    for table in schema.tables:
        for col in table.columns:
            column_types[(table.name, col.name)] = col.data_type

    # Type compatibility groups (types that can be joined)
    # In DuckDB/Power BI, these types are generally compatible
    STRING_TYPES = {"VARCHAR", "STRING", "TEXT", "CHAR"}
    INTEGER_TYPES = {"BIGINT", "INTEGER", "INT", "SMALLINT", "TINYINT", "HUGEINT"}
    FLOAT_TYPES = {"DOUBLE", "FLOAT", "REAL", "DECIMAL"}

    def get_type_group(dtype: str) -> str:
        """Get the type compatibility group for a data type."""
        dtype_upper = dtype.upper().split("(")[0].strip()  # Handle VARCHAR(255) etc.
        if dtype_upper in STRING_TYPES:
            return "STRING"
        elif dtype_upper in INTEGER_TYPES:
            return "INTEGER"
        elif dtype_upper in FLOAT_TYPES:
            return "FLOAT"
        else:
            return dtype_upper  # Return as-is for other types

    for rel in schema.relationships:
        from_key = (rel.from_table, rel.from_column)
        to_key = (rel.to_table, rel.to_column)

        if from_key not in column_types or to_key not in column_types:
            # Column existence is checked elsewhere
            continue

        from_type = column_types[from_key]
        to_type = column_types[to_key]

        from_group = get_type_group(from_type)
        to_group = get_type_group(to_type)

        if from_group != to_group:
            errors.append(
                f"Type mismatch in relationship: "
                f"'{rel.from_table}.{rel.from_column}' ({from_type}) vs "
                f"'{rel.to_table}.{rel.to_column}' ({to_type})"
            )

    return errors


def validate_schema(
    schema: SemanticSchema, config: Optional[PipelineConfig] = None
) -> ValidationResult:
    """Validate a semantic schema for Power BI compatibility.

    Runs all validation checks:
    - No circular relationships (error)
    - All relationship columns exist (error)
    - Column types are compatible (error)
    - Cardinality constraints are satisfied (warning)

    Args:
        schema: The semantic schema to validate.
        config: Pipeline configuration for locating parquet files.
                If None, creates a default PipelineConfig().

    Returns:
        ValidationResult with is_valid=True if no errors.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Check for circular relationships
    errors.extend(check_no_circular_relationships(schema))

    # Check relationship columns exist
    errors.extend(check_relationship_columns_exist(schema))

    # Check column type compatibility
    errors.extend(check_column_types_compatible(schema))

    # Check cardinality (warnings only)
    warnings.extend(check_cardinality_valid(schema, config))

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
