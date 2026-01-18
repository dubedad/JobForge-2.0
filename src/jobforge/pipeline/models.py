"""Pydantic models for pipeline provenance and metadata tracking."""

from datetime import datetime, timezone
from typing import ClassVar, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


class ProvenanceColumns(BaseModel):
    """Row-level provenance columns added to every parquet file.

    These columns track data origin per DAMA DMBOK requirements.

    Note: Field names use serialization aliases to produce underscore-prefixed
    column names in parquet files (e.g., source_file -> _source_file).
    """

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
        populate_by_name=True,
    )

    source_file: str = Field(
        description="Original source filename/path",
        serialization_alias="_source_file",
    )
    ingested_at: datetime = Field(
        default_factory=utc_now,
        description="UTC timestamp of ingestion",
        serialization_alias="_ingested_at",
    )
    batch_id: str = Field(
        description="Unique batch identifier (UUID)",
        serialization_alias="_batch_id",
    )
    layer: str = Field(
        description="Current medallion layer name",
        serialization_alias="_layer",
    )

    # Class-level constants for column names used in DataFrames
    COLUMN_NAMES: ClassVar[list[str]] = ["_source_file", "_ingested_at", "_batch_id", "_layer"]


class LayerTransitionLog(BaseModel):
    """Captures each layer movement for queryable audit trail.

    Records the transformation from one medallion layer to the next,
    per DAMA DMBOK Chapter 7 lineage requirements.
    """

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
    )

    transition_id: str = Field(description="Unique transition identifier (UUID)")
    batch_id: str = Field(description="Links to row-level _batch_id")
    source_layer: Literal["staged", "bronze", "silver"] = Field(
        description="Layer data is moving from"
    )
    target_layer: Literal["bronze", "silver", "gold"] = Field(
        description="Layer data is moving to"
    )
    source_files: list[str] = Field(description="Input file paths")
    target_file: str = Field(description="Output file path")
    row_count_in: int = Field(ge=0, description="Number of input rows")
    row_count_out: int = Field(ge=0, description="Number of output rows")
    transforms_applied: list[str] = Field(
        default_factory=list,
        description="List of transform function names applied",
    )
    started_at: datetime = Field(description="Transformation start time (UTC)")
    completed_at: datetime = Field(description="Transformation end time (UTC)")
    status: Literal["success", "partial", "failed"] = Field(
        description="Outcome of the transition"
    )
    errors: Optional[list[str]] = Field(
        default=None,
        description="Error messages if status is not success",
    )


class ColumnMetadata(BaseModel):
    """Column-level metadata per DAMA DMBOK Chapter 5.

    Links technical metadata to business glossary and tracks lineage.
    """

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
    )

    name: str = Field(description="Column name")
    data_type: str = Field(description="Data type (e.g., 'string', 'int64', 'datetime')")
    nullable: bool = Field(description="Whether column allows null values")
    description: str = Field(description="Business description of the column")
    glossary_term_id: Optional[str] = Field(
        default=None,
        description="Link to business glossary term",
    )
    source_columns: list[str] = Field(
        default_factory=list,
        description="Upstream columns this was derived from",
    )
    pii_classification: Optional[str] = Field(
        default=None,
        description="PII/security classification (e.g., 'public', 'confidential')",
    )
    example_values: list[str] = Field(
        default_factory=list,
        description="Sample values for documentation",
    )


class TableMetadata(BaseModel):
    """Table-level metadata per DAMA DMBOK Chapter 5.

    Comprehensive metadata linking technical, business, lineage,
    and governance information for a single table.
    """

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
    )

    # Identification
    table_name: str = Field(description="Logical table name")
    layer: str = Field(description="Medallion layer (staged, bronze, silver, gold)")
    domain: str = Field(description="Data domain (e.g., 'noc', 'job_architecture')")
    file_path: str = Field(description="Physical file path")

    # Technical metadata
    row_count: int = Field(ge=0, description="Number of rows")
    column_count: int = Field(ge=1, description="Number of columns")
    file_size_bytes: int = Field(ge=0, description="File size in bytes")
    schema_version: str = Field(description="Schema version identifier")
    created_at: datetime = Field(description="Table creation time (UTC)")
    updated_at: datetime = Field(description="Last update time (UTC)")

    # Business metadata
    description: str = Field(description="Business description of the table")
    business_purpose: str = Field(description="Business use case for this table")
    data_owner: str = Field(description="Accountable data owner")
    data_steward: Optional[str] = Field(
        default=None,
        description="Responsible data steward",
    )

    # Lineage metadata
    upstream_tables: list[str] = Field(
        default_factory=list,
        description="Tables this was derived from",
    )
    downstream_tables: list[str] = Field(
        default_factory=list,
        description="Tables derived from this",
    )
    transform_script: Optional[str] = Field(
        default=None,
        description="Path to transformation script",
    )

    # Governance metadata
    retention_days: Optional[int] = Field(
        default=None,
        ge=0,
        description="Data retention period in days",
    )
    classification: str = Field(
        default="internal",
        description="Data classification (public, internal, confidential)",
    )

    # Column metadata
    columns: list[ColumnMetadata] = Field(
        default_factory=list,
        description="Column-level metadata",
    )
