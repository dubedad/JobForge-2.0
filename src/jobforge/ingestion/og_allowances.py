"""Fact OG Allowances table ingestion.

Transforms scraped TBS allowances data into a gold-layer fact table
with full provenance tracking and FK relationships to dim_og.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

import polars as pl
import structlog

from jobforge.pipeline.config import PipelineConfig
from jobforge.pipeline.engine import PipelineEngine

logger = structlog.get_logger(__name__)

# Source file path
DEFAULT_SOURCE_PATH = Path("data/tbs/og_allowances.json")


def normalize_allowance_type(df: pl.LazyFrame) -> pl.LazyFrame:
    """Normalize allowance_type to lowercase with underscores.

    Silver transform that ensures consistent type categorization.
    """
    return df.with_columns([
        pl.col("allowance_type").str.to_lowercase().str.replace(" ", "_").alias("allowance_type"),
    ])


def validate_amounts(df: pl.LazyFrame) -> pl.LazyFrame:
    """Validate allowance amounts are positive where not null.

    Silver transform that filters out invalid amount values.
    Amounts should be > 0 when present.
    """
    return df.filter(
        (pl.col("amount").is_null()) | (pl.col("amount") > 0)
    )


def normalize_og_codes(df: pl.LazyFrame) -> pl.LazyFrame:
    """Normalize OG codes to uppercase.

    Silver transform that ensures consistent code formatting
    for FK relationships. og_code can be null for universal allowances.
    """
    return df.with_columns([
        pl.when(pl.col("og_code").is_not_null())
        .then(pl.col("og_code").str.to_uppercase())
        .otherwise(pl.lit(None))
        .alias("og_code"),
    ])


def select_fact_columns(df: pl.LazyFrame) -> pl.LazyFrame:
    """Select and order final columns for fact table.

    Gold transform that produces the final schema.
    """
    return df.select([
        # Primary key
        "allowance_id",
        # Allowance attributes
        "allowance_type",
        "allowance_name",
        "amount",
        "rate_type",
        "percentage",
        # FK and level
        "og_code",
        "classification_level",
        "eligibility_criteria",
        # Temporal
        "effective_date",
        # Provenance columns
        "_source_url",
        "_scraped_at",
        "_source_file",
        "_ingested_at",
        "_batch_id",
        "_layer",
    ])


def ingest_fact_og_allowances(
    source_path: Optional[Path] = None,
    config: Optional[PipelineConfig] = None,
    table_name: str = "fact_og_allowances",
) -> dict:
    """Ingest OG allowances JSON to gold layer as fact table.

    Transforms applied:
    - Bronze: Rename/cast columns, add provenance
    - Silver: Normalize types, validate amounts, normalize og_codes
    - Gold: Select final schema columns

    Args:
        source_path: Path to og_allowances.json (defaults to data/tbs/).
        config: Pipeline configuration (defaults to PipelineConfig()).
        table_name: Output table name (defaults to "fact_og_allowances").

    Returns:
        Dict with gold_path, batch_id, row_count, and logs.
    """
    source_path = source_path or DEFAULT_SOURCE_PATH
    source_path = Path(source_path)

    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    logger.info(
        "ingest_fact_og_allowances_start",
        source_path=str(source_path),
        table_name=table_name,
    )

    # Load JSON and convert to DataFrame
    with open(source_path, encoding="utf-8") as f:
        data = json.load(f)

    if not data:
        raise ValueError(f"Empty data in source file: {source_path}")

    # Create initial DataFrame from JSON
    # Define explicit schema for columns that may all be null
    schema = {
        "allowance_id": pl.Utf8,
        "allowance_type": pl.Utf8,
        "allowance_name": pl.Utf8,
        "amount": pl.Float64,
        "rate_type": pl.Utf8,
        "percentage": pl.Float64,
        "og_code": pl.Utf8,
        "classification_level": pl.Utf8,
        "eligibility_criteria": pl.Utf8,
        "effective_date": pl.Utf8,
        "source_url": pl.Utf8,
        "scraped_at": pl.Utf8,
    }
    df = pl.DataFrame(data, schema=schema)

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
                "allowance_id": "allowance_id",
                "allowance_type": "allowance_type",
                "allowance_name": "allowance_name",
                "amount": "amount",
                "rate_type": "rate_type",
                "percentage": "percentage",
                "og_code": "og_code",
                "classification_level": "classification_level",
                "eligibility_criteria": "eligibility_criteria",
                "effective_date": "effective_date",
                "source_url": "_source_url",
                "scraped_at": "_scraped_at",
            },
            "cast": {
                "allowance_id": pl.Utf8,
                "allowance_type": pl.Utf8,
                "allowance_name": pl.Utf8,
                "amount": pl.Float64,
                "rate_type": pl.Utf8,
                "percentage": pl.Float64,
                "og_code": pl.Utf8,
                "classification_level": pl.Utf8,
                "eligibility_criteria": pl.Utf8,
                "effective_date": pl.Utf8,
            }
        }

        # Silver transforms
        silver_transforms = [
            normalize_allowance_type,
            validate_amounts,
            normalize_og_codes,
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

        # Get unique allowance types
        allowance_types = gold_df["allowance_type"].unique().to_list()

        logger.info(
            "ingest_fact_og_allowances_complete",
            gold_path=str(result["gold_path"]),
            row_count=row_count,
            allowance_types=allowance_types,
        )

        return {
            **result,
            "row_count": row_count,
            "allowance_types": allowance_types,
        }

    finally:
        # Clean up temp file
        if temp_csv.exists():
            temp_csv.unlink()


if __name__ == "__main__":
    # Quick manual test
    result = ingest_fact_og_allowances()
    print(f"Ingested to: {result['gold_path']}")
    print(f"Rows: {result['row_count']}")
    print(f"Types: {result['allowance_types']}")
