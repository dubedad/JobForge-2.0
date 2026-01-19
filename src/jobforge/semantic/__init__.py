"""Semantic model definitions for Power BI compatible dimensional schemas.

This module provides Pydantic models for defining dimensional models with
relationships and cardinality suitable for Power BI consumption.

Example:
    >>> from jobforge.semantic import SemanticSchema, Table, Relationship, Cardinality
    >>> schema = SemanticSchema(name="WiQ", tables=[], relationships=[])
    >>> print(schema.to_json())
"""

from jobforge.semantic.models import (
    Cardinality,
    Column,
    CrossFilterDirection,
    Relationship,
    SemanticSchema,
    Table,
    TableType,
)

__all__ = [
    "TableType",
    "Cardinality",
    "CrossFilterDirection",
    "Column",
    "Table",
    "Relationship",
    "SemanticSchema",
]
