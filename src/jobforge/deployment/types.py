"""Type mapping utilities for DuckDB to Power BI type conversion.

This module provides mappings from DuckDB data types (as returned by schema
introspection) to Power BI data types for semantic model deployment.
"""

import structlog

log = structlog.get_logger(__name__)

# Mapping from DuckDB types to Power BI types
# DuckDB types are uppercase as returned by DESCRIBE
DUCKDB_TO_POWERBI_TYPES: dict[str, str] = {
    "VARCHAR": "string",
    "BIGINT": "int64",
    "DOUBLE": "double",
    "BOOLEAN": "boolean",
    "TIMESTAMP": "dateTime",
    "DATE": "dateTime",
    "INTEGER": "int64",
    "FLOAT": "double",
    "DECIMAL": "decimal",
    # Additional types that may appear
    "SMALLINT": "int64",
    "TINYINT": "int64",
    "HUGEINT": "int64",
    "REAL": "double",
    "TIME": "dateTime",
    "INTERVAL": "string",
    "UUID": "string",
    "BLOB": "binary",
}

# Power BI numeric types for summarize_by determination
POWERBI_NUMERIC_TYPES: frozenset[str] = frozenset({
    "int64",
    "double",
    "decimal",
})


def map_duckdb_to_powerbi(duckdb_type: str) -> str:
    """Map a DuckDB data type to its Power BI equivalent.

    Args:
        duckdb_type: DuckDB type string (e.g., "VARCHAR", "BIGINT").
                     Case-insensitive matching is used.

    Returns:
        Power BI type string (e.g., "string", "int64").
        Defaults to "string" for unmapped types.

    Example:
        >>> map_duckdb_to_powerbi("VARCHAR")
        'string'
        >>> map_duckdb_to_powerbi("BIGINT")
        'int64'
        >>> map_duckdb_to_powerbi("unknown_type")
        'string'
    """
    normalized_type = duckdb_type.upper()

    # Handle parameterized types (e.g., DECIMAL(10,2) -> DECIMAL)
    if "(" in normalized_type:
        normalized_type = normalized_type.split("(")[0]

    powerbi_type = DUCKDB_TO_POWERBI_TYPES.get(normalized_type)

    if powerbi_type is None:
        log.warning(
            "unmapped_duckdb_type",
            duckdb_type=duckdb_type,
            defaulting_to="string",
        )
        return "string"

    return powerbi_type


def get_summarize_by(powerbi_type: str) -> str:
    """Get the default summarization method for a Power BI type.

    Power BI allows specifying a default aggregation for columns.
    Numeric columns typically default to "sum", while text columns
    should have no aggregation ("none").

    Args:
        powerbi_type: Power BI type string (e.g., "string", "int64").

    Returns:
        Summarization method: "none" for non-numeric types, "sum" for numeric types.

    Example:
        >>> get_summarize_by("string")
        'none'
        >>> get_summarize_by("int64")
        'sum'
        >>> get_summarize_by("double")
        'sum'
    """
    if powerbi_type in POWERBI_NUMERIC_TYPES:
        return "sum"
    return "none"
