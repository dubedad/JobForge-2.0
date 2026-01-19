"""OASIS attribute table ingestion (proficiency-scored tables)."""
from pathlib import Path
from typing import Optional

import polars as pl

from jobforge.pipeline.config import PipelineConfig
from jobforge.pipeline.engine import PipelineEngine


# OASIS tables with proficiency scores (1-5)
OASIS_TABLES = [
    "skills",
    "abilities",
    "personal_attributes",
    "knowledges",
    "workactivities",
    "workcontext",
]


def ingest_oasis_table(
    source_path: Path,
    table_name: str,
    config: Optional[PipelineConfig] = None,
    oasis_code_column: str = "OaSIS Code - Final",
) -> dict:
    """Ingest an OASIS attribute table to gold layer.

    OASIS tables contain proficiency scores (1-5) for various attributes
    per NOC occupation. Each row represents one occupation (by OaSIS code).

    Transforms applied:
    - Bronze: Passthrough (keep original schema)
    - Silver: Derive unit_group_id and noc_element_code from OaSIS code
    - Gold: Keep all columns including proficiency scores

    Args:
        source_path: Path to OASIS CSV file
        table_name: Output table name (e.g., "oasis_skills")
        config: Pipeline configuration (defaults to PipelineConfig())
        oasis_code_column: Column containing OaSIS code (default: "OaSIS Code - Final")

    Returns:
        Dict with gold_path, batch_id, and row counts
    """
    engine = PipelineEngine(config=config)

    # Bronze: minimal schema - just clean column names
    # Keep proficiency columns as-is since they vary by table
    # Note: Polars infers "00010.00" as f64, so we handle the conversion in silver
    bronze_schema = {
        "rename": {
            oasis_code_column: "oasis_code",
            "OaSIS Label - Final": "oasis_label",
        },
    }

    # Silver transforms: derive FK columns
    def derive_fk_columns(df: pl.LazyFrame) -> pl.LazyFrame:
        """Derive unit_group_id and noc_element_code from oasis_code.

        OaSIS code format: XXXXX.YY (e.g., 00010.00)
        When read as float by Polars: 10.0 (loses leading zeros)

        Reconstruction:
        - Integer part (floor): 5-digit unit_group_id, zero-padded
        - Decimal part: 2-digit noc_element_code, zero-padded

        Example: 10.01 -> unit_group_id="00010", noc_element_code="01"
        """
        return df.with_columns([
            # Reconstruct oasis_code as proper string format XXXXX.YY
            (
                pl.col("oasis_code").floor().cast(pl.Int64).cast(pl.Utf8).str.zfill(5)
                + "."
                + ((pl.col("oasis_code") - pl.col("oasis_code").floor()) * 100)
                .round(0).cast(pl.Int64).cast(pl.Utf8).str.zfill(2)
            ).alias("oasis_code"),
            # unit_group_id: integer part, 5-digit zero-padded
            pl.col("oasis_code")
            .floor()
            .cast(pl.Int64)
            .cast(pl.Utf8)
            .str.zfill(5)
            .alias("unit_group_id"),
            # noc_element_code: decimal part * 100, 2-digit zero-padded
            ((pl.col("oasis_code") - pl.col("oasis_code").floor()) * 100)
            .round(0)
            .cast(pl.Int64)
            .cast(pl.Utf8)
            .str.zfill(2)
            .alias("noc_element_code"),
        ])

    silver_transforms = [derive_fk_columns]

    # Gold: keep all columns, reorder to put FKs first
    def reorder_columns(df: pl.LazyFrame) -> pl.LazyFrame:
        """Reorder columns to put foreign keys first."""
        # Get all column names
        cols = df.collect_schema().names()
        # Define priority columns
        priority = ["unit_group_id", "noc_element_code", "oasis_code", "oasis_label"]
        # Provenance columns
        provenance = ["_source_file", "_ingested_at", "_batch_id", "_layer"]
        # Proficiency columns (everything else)
        proficiency = [c for c in cols if c not in priority and c not in provenance]
        # Final order
        final_order = priority + proficiency + provenance
        return df.select([c for c in final_order if c in cols])

    gold_transforms = [reorder_columns]

    result = engine.run_full_pipeline(
        source_path=source_path,
        table_name=table_name,
        domain="oasis",
        bronze_schema=bronze_schema,
        silver_transforms=silver_transforms,
        gold_transforms=gold_transforms,
    )

    return result


def ingest_all_oasis_tables(
    source_dir: Path,
    config: Optional[PipelineConfig] = None,
) -> dict[str, dict]:
    """Ingest all OASIS tables from a source directory.

    Looks for CSV files matching OASIS table names in source_dir.

    Args:
        source_dir: Directory containing OASIS CSV files
        config: Pipeline configuration

    Returns:
        Dict mapping table name to ingestion result
    """
    results = {}
    for table in OASIS_TABLES:
        # Try common file patterns
        patterns = [
            f"{table}_oasis_*.csv",
            f"oasis_{table}*.csv",
            f"{table}.csv",
        ]
        for pattern in patterns:
            matches = list(source_dir.glob(pattern))
            if matches:
                source_path = matches[0]
                results[table] = ingest_oasis_table(
                    source_path=source_path,
                    table_name=f"oasis_{table}",
                    config=config,
                )
                break
    return results
