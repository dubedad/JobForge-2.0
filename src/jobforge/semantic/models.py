"""Pydantic models for Power BI compatible semantic schema definition.

This module defines the data structures for representing dimensional models
with relationships and cardinality suitable for Power BI consumption.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TableType(str, Enum):
    """Classification of tables in the dimensional model.

    - DIMENSION: Lookup tables providing context (who, what, where, when)
    - FACT: Event/transaction tables with measures
    - ATTRIBUTE: Extension tables that provide additional attributes for dimensions
    """

    DIMENSION = "dimension"
    FACT = "fact"
    ATTRIBUTE = "attribute"


class Cardinality(str, Enum):
    """Relationship cardinality types for Power BI.

    Defines the multiplicity between related tables.
    """

    ONE_TO_MANY = "1:*"
    MANY_TO_ONE = "*:1"
    ONE_TO_ONE = "1:1"
    MANY_TO_MANY = "*:*"


class CrossFilterDirection(str, Enum):
    """Cross-filter direction for Power BI relationships.

    - SINGLE: Filters propagate in one direction (from 'one' to 'many' side)
    - BOTH: Filters propagate in both directions (use sparingly)
    """

    SINGLE = "Single"
    BOTH = "Both"


class Column(BaseModel):
    """Column metadata for schema definition.

    Captures both technical metadata (name, type) and semantic metadata
    (primary/foreign key designations, references).
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "unit_group_id",
                "data_type": "VARCHAR",
                "is_primary_key": True,
                "is_foreign_key": False,
            }
        }
    )

    name: str = Field(description="Column name as it appears in the parquet file")
    data_type: str = Field(description="Data type from DuckDB DESCRIBE (e.g., VARCHAR, BIGINT)")
    is_primary_key: bool = Field(default=False, description="Whether this column is the primary key")
    is_foreign_key: bool = Field(default=False, description="Whether this column is a foreign key")
    references_table: Optional[str] = Field(
        default=None,
        description="Table this FK references (if is_foreign_key=True)",
    )
    references_column: Optional[str] = Field(
        default=None,
        description="Column this FK references (if is_foreign_key=True)",
    )


class Table(BaseModel):
    """Table definition in the semantic model.

    Represents a single table with its columns, type classification,
    and optional primary key designation.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "dim_noc",
                "table_type": "dimension",
                "primary_key": "unit_group_id",
            }
        }
    )

    name: str = Field(description="Table name (lowercase, matches parquet filename stem)")
    table_type: TableType = Field(description="Classification: dimension, fact, or attribute")
    columns: list[Column] = Field(default_factory=list, description="Column definitions")
    primary_key: Optional[str] = Field(
        default=None,
        description="Name of primary key column (if applicable)",
    )
    description: str = Field(default="", description="Business description of the table")


class Relationship(BaseModel):
    """Power BI compatible relationship definition.

    Captures all properties needed for Power BI relationship creation:
    - From/to table and column pairs
    - Cardinality (1:*, *:1, 1:1, *:*)
    - Cross-filter direction (Single or Both)
    - Active status (inactive relationships are available but not used by default)
    """

    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "from_table": "dim_noc",
                "from_column": "unit_group_id",
                "to_table": "oasis_skills",
                "to_column": "unit_group_id",
                "cardinality": "1:*",
                "cross_filter_direction": "Single",
                "is_active": True,
            }
        },
    )

    from_table: str = Field(description="Source table name (typically the 'one' side)")
    from_column: str = Field(description="Source column name")
    to_table: str = Field(description="Target table name (typically the 'many' side)")
    to_column: str = Field(description="Target column name")
    cardinality: Cardinality = Field(description="Relationship cardinality")
    cross_filter_direction: CrossFilterDirection = Field(
        default=CrossFilterDirection.SINGLE,
        description="Filter propagation direction",
    )
    is_active: bool = Field(
        default=True,
        description="Whether relationship is active (used by default in queries)",
    )


class SemanticSchema(BaseModel):
    """Complete semantic model definition.

    Root model containing all tables and relationships for a dimensional model.
    Provides helper methods for navigating the schema and serialization.
    """

    model_config = ConfigDict(
        use_enum_values=True,
    )

    name: str = Field(description="Schema name (e.g., 'WiQ')")
    tables: list[Table] = Field(default_factory=list, description="All tables in the model")
    relationships: list[Relationship] = Field(
        default_factory=list,
        description="All relationships between tables",
    )
    validated: bool = Field(
        default=False,
        description="Whether schema has been validated against actual parquet files",
    )
    validation_date: Optional[datetime] = Field(
        default=None,
        description="When validation was last performed",
    )

    def get_dimension_tables(self) -> list[Table]:
        """Get all dimension tables in the schema.

        Returns:
            List of Table objects where table_type is DIMENSION.
        """
        return [t for t in self.tables if t.table_type == TableType.DIMENSION]

    def get_fact_tables(self) -> list[Table]:
        """Get all fact tables in the schema.

        Returns:
            List of Table objects where table_type is FACT.
        """
        return [t for t in self.tables if t.table_type == TableType.FACT]

    def get_attribute_tables(self) -> list[Table]:
        """Get all attribute tables in the schema.

        Returns:
            List of Table objects where table_type is ATTRIBUTE.
        """
        return [t for t in self.tables if t.table_type == TableType.ATTRIBUTE]

    def get_relationships_for_table(self, table_name: str) -> list[Relationship]:
        """Get all relationships involving a specific table.

        Args:
            table_name: Name of the table to find relationships for.

        Returns:
            List of Relationship objects where table is from_table or to_table.
        """
        return [
            r
            for r in self.relationships
            if r.from_table == table_name or r.to_table == table_name
        ]

    def get_table(self, table_name: str) -> Optional[Table]:
        """Get a table by name.

        Args:
            table_name: Name of the table to retrieve.

        Returns:
            Table object if found, None otherwise.
        """
        for table in self.tables:
            if table.name == table_name:
                return table
        return None

    def to_json(self) -> str:
        """Export schema to JSON string.

        Returns:
            Pretty-printed JSON representation of the schema.
        """
        return self.model_dump_json(indent=2)
