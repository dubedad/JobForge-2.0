"""COPS forecasting table ingestion."""
from pathlib import Path
from typing import Optional

import polars as pl

from jobforge.pipeline.config import PipelineConfig
from jobforge.pipeline.engine import PipelineEngine


# COPS supply tables (where workers come from)
COPS_SUPPLY_TABLES = [
    "school_leavers",
    "immigration",
    "other_seekers",
    "job_seekers_total",
]

# COPS demand tables (why positions need filling)
COPS_DEMAND_TABLES = [
    "employment",
    "employment_growth",
    "job_openings",
    "retirements",
    "retirement_rates",
    "other_replacement",
]

# Summary/assessment tables
COPS_SUMMARY_TABLES = [
    "summary",
    "flmc",
    "rlmc",
]

# All COPS tables
COPS_TABLES = COPS_SUPPLY_TABLES + COPS_DEMAND_TABLES + COPS_SUMMARY_TABLES


def _is_unit_group_code(code: str) -> bool:
    """Check if a COPS code is a unit group (5-digit NOC code).

    COPS includes aggregate codes:
    - 00000: All occupations
    - TEER_0 through TEER_5: TEER level aggregates
    - NOC1_0 through NOC1_9: Major group aggregates

    Only 5-digit numeric codes are unit groups.
    """
    if code is None or len(code) != 5:
        return False
    return code.isdigit()


def ingest_cops_table(
    source_path: Path,
    table_name: str,
    config: Optional[PipelineConfig] = None,
    filter_to_unit_groups: bool = True,
) -> dict:
    """Ingest a COPS forecasting table to gold layer.

    COPS tables contain 10-year projections for workforce supply/demand.
    Each row represents one occupation (by Code).

    Transforms applied:
    - Bronze: Rename columns to snake_case
    - Silver: Derive unit_group_id, optionally filter to unit groups
    - Gold: Final column ordering

    Args:
        source_path: Path to COPS CSV file
        table_name: Output table name (e.g., "cops_employment")
        config: Pipeline configuration (defaults to PipelineConfig())
        filter_to_unit_groups: If True, filter out aggregate rows (default True)

    Returns:
        Dict with gold_path, batch_id, and row counts
    """
    engine = PipelineEngine(config=config)

    # Bronze: rename columns to snake_case
    bronze_schema = {
        "rename": {
            "Code": "code",
            "Occupation Name": "occupation_name_en",
            "Nom de la profession": "occupation_name_fr",
        },
    }

    # Silver transforms
    def derive_unit_group_id(df: pl.LazyFrame) -> pl.LazyFrame:
        """Derive unit_group_id for valid 5-digit NOC unit group codes.

        Excludes aggregate codes:
        - 00000: All occupations aggregate
        - TEER_*: TEER level aggregates
        - NOC1_*: Major group aggregates

        Valid unit groups are 5-digit codes that don't start with 00000.
        """
        return df.with_columns(
            pl.when(
                (pl.col("code").str.len_chars() == 5)
                & (pl.col("code").str.contains(r"^\d{5}$"))
                & (pl.col("code") != "00000")  # Exclude "All occupations" aggregate
            )
            .then(pl.col("code").str.zfill(5))
            .otherwise(pl.lit(None))
            .alias("unit_group_id")
        )

    def filter_unit_groups_only(df: pl.LazyFrame) -> pl.LazyFrame:
        """Filter to unit group rows only (exclude aggregates)."""
        return df.filter(pl.col("unit_group_id").is_not_null())

    silver_transforms = [derive_unit_group_id]
    if filter_to_unit_groups:
        silver_transforms.append(filter_unit_groups_only)

    # Gold: reorder columns
    def reorder_columns(df: pl.LazyFrame) -> pl.LazyFrame:
        """Reorder columns: FK first, then code/names, then years, then provenance."""
        cols = df.collect_schema().names()

        # Priority columns
        priority = ["unit_group_id", "code", "occupation_name_en", "occupation_name_fr"]

        # Provenance columns
        provenance = ["_source_file", "_ingested_at", "_batch_id", "_layer"]

        # Year columns (numeric columns like 2023, 2024, etc.)
        year_cols = [c for c in cols if c not in priority and c not in provenance]

        # Final order
        final_order = priority + year_cols + provenance
        return df.select([c for c in final_order if c in cols])

    gold_transforms = [reorder_columns]

    result = engine.run_full_pipeline(
        source_path=source_path,
        table_name=table_name,
        domain="cops",
        bronze_schema=bronze_schema,
        silver_transforms=silver_transforms,
        gold_transforms=gold_transforms,
    )

    return result


def ingest_all_cops_tables(
    source_dir: Path,
    config: Optional[PipelineConfig] = None,
    filter_to_unit_groups: bool = True,
) -> dict[str, dict]:
    """Ingest all COPS tables from a source directory.

    Args:
        source_dir: Directory containing COPS CSV files
        config: Pipeline configuration
        filter_to_unit_groups: Filter out aggregate rows

    Returns:
        Dict mapping table name to ingestion result
    """
    results = {}
    for table in COPS_TABLES:
        # Try common file patterns
        patterns = [
            f"{table}_*.csv",
            f"*{table}*.csv",
            f"{table.replace('_', '-')}*.csv",
        ]
        for pattern in patterns:
            matches = list(source_dir.glob(pattern))
            if matches:
                source_path = matches[0]
                results[table] = ingest_cops_table(
                    source_path=source_path,
                    table_name=f"cops_{table}",
                    config=config,
                    filter_to_unit_groups=filter_to_unit_groups,
                )
                break
    return results
