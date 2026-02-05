"""Fact OG Pay Rates table ingestion.

Transforms scraped TBS rates of pay data into a gold-layer fact table
with full provenance tracking and FK relationships to dim_og and dim_og_subgroup.
"""

import json
from pathlib import Path
from typing import Optional

import polars as pl
import structlog

from jobforge.pipeline.config import PipelineConfig
from jobforge.pipeline.engine import PipelineEngine

logger = structlog.get_logger(__name__)

# Source file path
DEFAULT_SOURCE_PATH = Path("data/tbs/og_pay_rates_en.json")


def normalize_codes(df: pl.LazyFrame) -> pl.LazyFrame:
    """Normalize OG codes to uppercase.

    Silver transform that ensures consistent code formatting
    for FK relationships.
    """
    return df.with_columns([
        pl.col("og_code").str.to_uppercase().alias("og_code"),
        pl.col("og_subgroup_code").str.to_uppercase().alias("og_subgroup_code"),
        pl.col("classification_level").str.to_uppercase().alias("classification_level"),
    ])


def validate_rates(df: pl.LazyFrame) -> pl.LazyFrame:
    """Validate pay rates are positive where not null.

    Silver transform that filters out invalid rate values.
    Rates should be > 0 when present.
    """
    return df.filter(
        (pl.col("annual_rate").is_null()) | (pl.col("annual_rate") > 0)
    )


def dedupe_rates(df: pl.LazyFrame) -> pl.LazyFrame:
    """Remove exact duplicate rows.

    Silver transform that removes duplicates based on the natural key:
    (og_subgroup_code, classification_level, step, effective_date)
    """
    return df.unique(
        subset=["og_subgroup_code", "classification_level", "step", "effective_date"],
        maintain_order=True,
    )


def select_fact_columns(df: pl.LazyFrame) -> pl.LazyFrame:
    """Select and order final columns for fact table.

    Gold transform that produces the final schema.
    """
    return df.select([
        # Dimension FKs
        "og_subgroup_code",
        "og_code",
        # Fact attributes
        "classification_level",
        "step",
        "annual_rate",
        "hourly_rate",
        "effective_date",
        "is_represented",
        "collective_agreement",
        # Provenance columns
        "_source_url",
        "_scraped_at",
        "_source_file",
        "_ingested_at",
        "_batch_id",
        "_layer",
    ])


def ingest_fact_og_pay_rates(
    source_path: Optional[Path] = None,
    config: Optional[PipelineConfig] = None,
    table_name: str = "fact_og_pay_rates",
) -> dict:
    """Ingest OG pay rates JSON to gold layer as fact table.

    Transforms applied:
    - Bronze: Rename/cast columns, add provenance
    - Silver: Normalize codes, validate rates, dedupe
    - Gold: Select final schema columns

    Args:
        source_path: Path to og_pay_rates_en.json (defaults to data/tbs/).
        config: Pipeline configuration (defaults to PipelineConfig()).
        table_name: Output table name (defaults to "fact_og_pay_rates").

    Returns:
        Dict with gold_path, batch_id, row_count, and logs.
    """
    source_path = source_path or DEFAULT_SOURCE_PATH
    source_path = Path(source_path)

    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    logger.info(
        "ingest_fact_og_pay_rates_start",
        source_path=str(source_path),
        table_name=table_name,
    )

    # Load JSON and convert to DataFrame
    with open(source_path, encoding="utf-8") as f:
        data = json.load(f)

    if not data:
        raise ValueError(f"Empty data in source file: {source_path}")

    # Create initial DataFrame from JSON
    df = pl.DataFrame(data)

    # Add source file provenance
    df = df.with_columns([
        pl.lit(str(source_path)).alias("_source_file"),
    ])

    # Save to temporary CSV for pipeline ingestion
    temp_csv = source_path.parent / f"_{table_name}_temp.csv"
    df.write_csv(temp_csv)

    try:
        engine = PipelineEngine(config=config)

        # Bronze schema: rename and cast columns
        bronze_schema = {
            "rename": {
                "og_code": "og_code",
                "og_subgroup_code": "og_subgroup_code",
                "classification_level": "classification_level",
                "step": "step",
                "annual_rate": "annual_rate",
                "hourly_rate": "hourly_rate",
                "effective_date": "effective_date",
                "represented": "is_represented",
                "collective_agreement": "collective_agreement",
                "source_url": "_source_url",
                "scraped_at": "_scraped_at",
            },
            "cast": {
                "og_code": pl.Utf8,
                "og_subgroup_code": pl.Utf8,
                "classification_level": pl.Utf8,
                "step": pl.Int32,
                "annual_rate": pl.Float64,
                "hourly_rate": pl.Float64,
                "is_represented": pl.Boolean,
            }
        }

        # Silver transforms
        silver_transforms = [
            normalize_codes,
            validate_rates,
            dedupe_rates,
        ]

        # Gold transforms
        gold_transforms = [
            select_fact_columns,
        ]

        result = engine.run_full_pipeline(
            source_path=temp_csv,
            table_name=table_name,
            domain="occupational_groups",
            bronze_schema=bronze_schema,
            silver_transforms=silver_transforms,
            gold_transforms=gold_transforms,
        )

        # Get row count from gold table
        gold_df = pl.read_parquet(result["gold_path"])
        row_count = len(gold_df)

        logger.info(
            "ingest_fact_og_pay_rates_complete",
            gold_path=str(result["gold_path"]),
            row_count=row_count,
        )

        return {
            **result,
            "row_count": row_count,
        }

    finally:
        # Clean up temp file
        if temp_csv.exists():
            temp_csv.unlink()


if __name__ == "__main__":
    # Quick manual test
    result = ingest_fact_og_pay_rates()
    print(f"Ingested to: {result['gold_path']}")
    print(f"Rows: {result['row_count']}")
