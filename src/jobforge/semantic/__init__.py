"""Semantic model definitions for Power BI compatible dimensional schemas.

This module provides Pydantic models for defining dimensional models with
relationships and cardinality suitable for Power BI consumption.

Example:
    >>> from jobforge.semantic import build_wiq_schema, validate_schema
    >>> schema = build_wiq_schema()
    >>> result = validate_schema(schema)
    >>> print(f"Valid: {result.is_valid}")
"""

from jobforge.semantic.introspect import (
    introspect_all_gold_tables,
    introspect_parquet_schema,
)
from jobforge.semantic.models import (
    Cardinality,
    Column,
    CrossFilterDirection,
    Relationship,
    SemanticSchema,
    Table,
    TableType,
)
from jobforge.semantic.schema import (
    WIQ_RELATIONSHIPS,
    build_wiq_schema,
    export_schema_json,
)
from jobforge.semantic.validator import (
    ValidationResult,
    validate_schema,
)

__all__ = [
    # Models
    "TableType",
    "Cardinality",
    "CrossFilterDirection",
    "Column",
    "Table",
    "Relationship",
    "SemanticSchema",
    # Introspection
    "introspect_parquet_schema",
    "introspect_all_gold_tables",
    # Schema building
    "build_wiq_schema",
    "WIQ_RELATIONSHIPS",
    "export_schema_json",
    # Validation
    "validate_schema",
    "ValidationResult",
]
