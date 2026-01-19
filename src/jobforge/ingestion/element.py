"""Element attribute table ingestion (text description tables)."""
from pathlib import Path
from typing import Optional

import polars as pl

from jobforge.pipeline.config import PipelineConfig
from jobforge.pipeline.engine import PipelineEngine


# Element tables with text descriptions
ELEMENT_TABLES = [
    "labels",
    "lead_statement",
    "workplaces_employers",
    "example_titles",
    "main_duties",
    "employment_requirements",
    "additional_information",
    "exclusions",
]


def ingest_element_table(
    source_path: Path,
    table_name: str,
    config: Optional[PipelineConfig] = None,
    profile_code_column: str = "OaSIS profile code",
) -> dict:
    """Ingest an Element attribute table to gold layer.

    Element tables contain text descriptions for NOC occupations.
    Unlike OASIS tables, Element tables may have multiple rows per
    occupation (e.g., multiple duty statements per NOC).

    Transforms applied:
    - Bronze: Rename profile code column
    - Silver: Derive unit_group_id and noc_element_code
    - Gold: Final column selection

    Args:
        source_path: Path to Element CSV file
        table_name: Output table name (e.g., "element_main_duties")
        config: Pipeline configuration (defaults to PipelineConfig())
        profile_code_column: Column containing OaSIS profile code

    Returns:
        Dict with gold_path, batch_id, and row counts
    """
    engine = PipelineEngine(config=config)

    # Bronze: rename profile code column
    # Note: Polars infers "00010.00" as f64, so we handle the conversion in silver
    bronze_schema = {
        "rename": {
            profile_code_column: "oasis_profile_code",
        },
    }

    # Silver transforms: derive FK columns
    def derive_fk_columns(df: pl.LazyFrame) -> pl.LazyFrame:
        """Derive unit_group_id and noc_element_code from profile code.

        OaSIS code format: XXXXX.YY (e.g., 00010.00)
        When read as float by Polars: 10.0 (loses leading zeros)

        Reconstruction:
        - Integer part (floor): 5-digit unit_group_id, zero-padded
        - Decimal part: 2-digit noc_element_code, zero-padded

        Example: 10.01 -> unit_group_id="00010", noc_element_code="01"
        """
        return df.with_columns([
            # Reconstruct oasis_profile_code as proper string format XXXXX.YY
            (
                pl.col("oasis_profile_code").floor().cast(pl.Int64).cast(pl.Utf8).str.zfill(5)
                + "."
                + ((pl.col("oasis_profile_code") - pl.col("oasis_profile_code").floor()) * 100)
                .round(0).cast(pl.Int64).cast(pl.Utf8).str.zfill(2)
            ).alias("oasis_profile_code"),
            # unit_group_id: integer part, 5-digit zero-padded
            pl.col("oasis_profile_code")
            .floor()
            .cast(pl.Int64)
            .cast(pl.Utf8)
            .str.zfill(5)
            .alias("unit_group_id"),
            # noc_element_code: decimal part * 100, 2-digit zero-padded
            ((pl.col("oasis_profile_code") - pl.col("oasis_profile_code").floor()) * 100)
            .round(0)
            .cast(pl.Int64)
            .cast(pl.Utf8)
            .str.zfill(2)
            .alias("noc_element_code"),
        ])

    silver_transforms = [derive_fk_columns]

    # Gold: reorder columns
    def reorder_columns(df: pl.LazyFrame) -> pl.LazyFrame:
        """Reorder columns to put foreign keys first."""
        cols = df.collect_schema().names()
        # Priority columns
        priority = ["unit_group_id", "noc_element_code", "oasis_profile_code"]
        # Provenance columns
        provenance = ["_source_file", "_ingested_at", "_batch_id", "_layer"]
        # Text columns (everything else)
        text_cols = [c for c in cols if c not in priority and c not in provenance]
        # Final order
        final_order = priority + text_cols + provenance
        return df.select([c for c in final_order if c in cols])

    gold_transforms = [reorder_columns]

    result = engine.run_full_pipeline(
        source_path=source_path,
        table_name=table_name,
        domain="element",
        bronze_schema=bronze_schema,
        silver_transforms=silver_transforms,
        gold_transforms=gold_transforms,
    )

    return result


def ingest_all_element_tables(
    source_dir: Path,
    config: Optional[PipelineConfig] = None,
) -> dict[str, dict]:
    """Ingest all Element tables from a source directory.

    Args:
        source_dir: Directory containing Element CSV files
        config: Pipeline configuration

    Returns:
        Dict mapping table name to ingestion result
    """
    results = {}
    for table in ELEMENT_TABLES:
        # Try common file patterns
        patterns = [
            f"{table}_element_*.csv",
            f"element_{table}*.csv",
            f"{table.replace('_', '-')}*.csv",
            f"{table}.csv",
        ]
        for pattern in patterns:
            matches = list(source_dir.glob(pattern))
            if matches:
                source_path = matches[0]
                results[table] = ingest_element_table(
                    source_path=source_path,
                    table_name=f"element_{table}",
                    config=config,
                )
                break
    return results
