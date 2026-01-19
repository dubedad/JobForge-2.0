"""Imputation provenance tracking utilities.

This module provides consistent column naming and provenance tracking
for all imputed values in the hierarchical inheritance system.

Imputation provenance is separate from pipeline provenance (ingestion tracking).
Pipeline provenance tracks source files and ingestion timestamps.
Imputation provenance tracks which NOC level provided each inherited value.
"""

from datetime import datetime, timezone
from typing import Literal

import polars as pl


class ImputationProvenanceColumns:
    """Named constants for imputation provenance column names.

    These columns are added to DataFrames during attribute inheritance
    to track the source of each imputed/inherited value.

    Attributes:
        IMPUTATION_SOURCE_LEVEL: NOC level (5, 6, or 7) that provided the value
        IMPUTATION_SOURCE_ID: OASIS code or unit_group_id of the source
        IMPUTATION_PROVENANCE: How value was obtained (native/inherited/imputed)
        IMPUTATION_CONFIDENCE: Confidence score from resolution (0.0-1.0)
        IMPUTATION_AT: UTC timestamp of when imputation occurred
    """

    IMPUTATION_SOURCE_LEVEL = "_imputation_source_level"
    IMPUTATION_SOURCE_ID = "_imputation_source_id"
    IMPUTATION_PROVENANCE = "_imputation_provenance"
    IMPUTATION_CONFIDENCE = "_imputation_confidence"
    IMPUTATION_AT = "_imputation_at"


def add_imputation_provenance(
    df: pl.LazyFrame,
    source_level: int,
    source_id_col: str,
    provenance: Literal["native", "inherited", "imputed"],
    confidence: float,
) -> pl.LazyFrame:
    """Add imputation provenance columns to a DataFrame.

    Adds all five imputation provenance columns to track the source
    of inherited/imputed values for audit and traceability.

    Args:
        df: Input LazyFrame to add provenance columns to.
        source_level: NOC hierarchy level (5=UG, 6=Label, 7=Example).
        source_id_col: Column name containing the source identifier
            (OASIS code or unit_group_id).
        provenance: How the value was obtained:
            - "native": Value exists at this level in source data
            - "inherited": Value inherited from parent level
            - "imputed": Value generated via external source (O*NET, LLM)
        confidence: Confidence score from resolution (0.0-1.0).

    Returns:
        LazyFrame with imputation provenance columns added.

    Example:
        >>> df = pl.LazyFrame({"unit_group_id": ["21231"], "skill": ["Python"]})
        >>> df_with_prov = add_imputation_provenance(
        ...     df,
        ...     source_level=5,
        ...     source_id_col="unit_group_id",
        ...     provenance="inherited",
        ...     confidence=0.85,
        ... )
    """
    return df.with_columns(
        pl.lit(source_level).alias(ImputationProvenanceColumns.IMPUTATION_SOURCE_LEVEL),
        pl.col(source_id_col).alias(ImputationProvenanceColumns.IMPUTATION_SOURCE_ID),
        pl.lit(provenance).alias(ImputationProvenanceColumns.IMPUTATION_PROVENANCE),
        pl.lit(confidence).alias(ImputationProvenanceColumns.IMPUTATION_CONFIDENCE),
        pl.lit(datetime.now(timezone.utc)).alias(
            ImputationProvenanceColumns.IMPUTATION_AT
        ),
    )


def create_imputed_attribute_row(
    value: str,
    attribute_name: str,
    source_level: int,
    source_id: str,
    provenance: Literal["native", "inherited", "imputed"],
    confidence: float,
) -> dict:
    """Create a single imputed attribute row with full provenance.

    Helper function for building individual imputed values with
    provenance tracking. Returns a dict compatible with Polars row creation.

    Args:
        value: The imputed attribute value.
        attribute_name: Name of the attribute (e.g., "skill", "ability").
        source_level: NOC hierarchy level (5=UG, 6=Label, 7=Example).
        source_id: OASIS code or unit_group_id of the source.
        provenance: How the value was obtained (native/inherited/imputed).
        confidence: Confidence score from resolution (0.0-1.0).

    Returns:
        Dict with attribute value and all provenance columns,
        ready for use with pl.DataFrame() or row operations.

    Example:
        >>> row = create_imputed_attribute_row(
        ...     value="Critical Thinking",
        ...     attribute_name="skill",
        ...     source_level=5,
        ...     source_id="21231",
        ...     provenance="inherited",
        ...     confidence=0.85,
        ... )
        >>> row["skill"]
        'Critical Thinking'
        >>> row["_imputation_source_level"]
        5
    """
    return {
        attribute_name: value,
        ImputationProvenanceColumns.IMPUTATION_SOURCE_LEVEL: source_level,
        ImputationProvenanceColumns.IMPUTATION_SOURCE_ID: source_id,
        ImputationProvenanceColumns.IMPUTATION_PROVENANCE: provenance,
        ImputationProvenanceColumns.IMPUTATION_CONFIDENCE: confidence,
        ImputationProvenanceColumns.IMPUTATION_AT: datetime.now(timezone.utc),
    }


def get_provenance_column_names() -> list[str]:
    """Get list of all imputation provenance column names.

    Useful for selecting or excluding provenance columns in DataFrame operations.

    Returns:
        List of the five imputation provenance column names.
    """
    return [
        ImputationProvenanceColumns.IMPUTATION_SOURCE_LEVEL,
        ImputationProvenanceColumns.IMPUTATION_SOURCE_ID,
        ImputationProvenanceColumns.IMPUTATION_PROVENANCE,
        ImputationProvenanceColumns.IMPUTATION_CONFIDENCE,
        ImputationProvenanceColumns.IMPUTATION_AT,
    ]
