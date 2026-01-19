"""Transform functions for data ingestion.

Transforms are pure functions: LazyFrame -> LazyFrame.
They are passed to PipelineEngine.run_full_pipeline() for silver/gold layers.
"""

import polars as pl


def filter_unit_groups(df: pl.LazyFrame) -> pl.LazyFrame:
    """Filter to Level 5 (Unit Group) rows only.

    NOC structure contains all hierarchy levels (1-5).
    For DIM NOC, we only want the 516 unit groups at Level 5.

    Args:
        df: Input LazyFrame with 'level' column.

    Returns:
        LazyFrame filtered to Level 5 rows only.
    """
    return df.filter(pl.col("level") == 5)


def derive_unit_group_id(df: pl.LazyFrame) -> pl.LazyFrame:
    """Create standardized unit_group_id from NOC code.

    NOC codes at Level 5 are 5-digit codes.
    Ensure zero-padding for consistency (e.g., '10' -> '00010').

    Args:
        df: Input LazyFrame with 'noc_code' column.

    Returns:
        LazyFrame with 'unit_group_id' column added.
    """
    return df.with_columns(
        pl.col("noc_code").str.zfill(5).alias("unit_group_id")
    )


def normalize_noc_code(df: pl.LazyFrame, code_column: str = "Code") -> pl.LazyFrame:
    """Normalize any NOC code column to 5-digit zero-padded format.

    Handles various input formats:
    - "10" -> "00010"
    - "00010" -> "00010" (no change)
    - "00010.00" -> "00010" (strip decimal portion)

    Args:
        df: Input LazyFrame.
        code_column: Name of column containing NOC code.

    Returns:
        LazyFrame with unit_group_id column added.
    """
    return df.with_columns(
        pl.col(code_column)
        .str.replace(r"\\..*$", "")  # Remove decimal portion if present
        .str.zfill(5)
        .alias("unit_group_id")
    )


def derive_noc_element_code(
    df: pl.LazyFrame, code_column: str = "OaSIS Code - Final"
) -> pl.LazyFrame:
    """Extract 2-digit NOC Element Code from OaSIS profile code.

    OaSIS code format: XXXXX.YY (e.g., 00010.00)
    Element code: Last 2 characters after decimal.

    Args:
        df: Input LazyFrame.
        code_column: Name of column containing OaSIS code.

    Returns:
        LazyFrame with 'noc_element_code' column added.
    """
    return df.with_columns(
        pl.col(code_column).str.slice(-2).alias("noc_element_code")
    )


def derive_unit_group_from_oasis(
    df: pl.LazyFrame, code_column: str = "OaSIS Code - Final"
) -> pl.LazyFrame:
    """Extract unit_group_id from OaSIS profile code.

    OaSIS code format: XXXXX.YY (e.g., 00010.00)
    Unit Group ID: First 5 characters, zero-padded.

    Args:
        df: Input LazyFrame.
        code_column: Name of column containing OaSIS code.

    Returns:
        LazyFrame with 'unit_group_id' column added.
    """
    return df.with_columns(
        pl.col(code_column).str.slice(0, 5).str.zfill(5).alias("unit_group_id")
    )
