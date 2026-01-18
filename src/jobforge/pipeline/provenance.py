"""Provenance helper functions for adding audit columns to DataFrames."""

import uuid
from datetime import datetime, timezone

import polars as pl


def generate_batch_id() -> str:
    """Generate a unique batch identifier.

    Returns:
        UUID4 string for batch identification.
    """
    return str(uuid.uuid4())


def add_provenance_columns(
    df: pl.LazyFrame,
    source_file: str,
    batch_id: str,
    layer: str,
) -> pl.LazyFrame:
    """Add standard provenance columns to a LazyFrame.

    Adds DAMA DMBOK compliant provenance columns:
    - _source_file: Original source filename/path
    - _ingested_at: UTC timestamp of ingestion
    - _batch_id: Unique batch identifier
    - _layer: Current medallion layer name

    Args:
        df: Input LazyFrame to add columns to.
        source_file: The source filename or path.
        batch_id: The batch identifier (UUID).
        layer: Current layer name (staged, bronze, silver, gold).

    Returns:
        LazyFrame with provenance columns added.
    """
    return df.with_columns(
        pl.lit(source_file).alias("_source_file"),
        pl.lit(datetime.now(timezone.utc)).alias("_ingested_at"),
        pl.lit(batch_id).alias("_batch_id"),
        pl.lit(layer).alias("_layer"),
    )


def update_layer_column(df: pl.LazyFrame, new_layer: str) -> pl.LazyFrame:
    """Update the layer column when data moves to a new layer.

    Updates _layer to the new layer name and refreshes _ingested_at
    to current timestamp. Preserves _source_file and _batch_id.

    Args:
        df: Input LazyFrame with existing provenance columns.
        new_layer: The new layer name to set.

    Returns:
        LazyFrame with updated layer and timestamp.
    """
    return df.with_columns(
        pl.lit(new_layer).alias("_layer"),
        pl.lit(datetime.now(timezone.utc)).alias("_ingested_at"),
    )
