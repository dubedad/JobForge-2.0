"""OG Job Evaluation Standards table ingestion.

Ingests TBS Job Evaluation Standards data to gold layer table:
- dim_og_job_evaluation_standard: Evaluation factors and points per occupational group

The source data comes from og_evaluation_standards.json (scraped from TBS pages).
This module processes evaluation standards with factors, points, and level descriptions.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import polars as pl
import structlog

from jobforge.pipeline.config import PipelineConfig
from jobforge.pipeline.provenance import generate_batch_id

logger = structlog.get_logger(__name__)

# Maximum character limit for text columns
MAX_TEXT_LENGTH = 10000


def _load_evaluation_standards_json(source_path: Path) -> list[dict]:
    """Load og_evaluation_standards.json.

    The source JSON is a flat array of EvaluationStandard records:
    [
        {
            "og_code": "IT",
            "og_subgroup_code": null,
            "standard_name": "Information Technology Job Evaluation Standard",
            "standard_type": "classification_standard" | "evaluation_factor",
            "factor_name": "Technical Knowledge",
            "factor_points": 300,
            ...
        },
        ...
    ]

    Returns:
        List of records from the JSON file.
    """
    with open(source_path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_og_codes(df: pl.LazyFrame) -> pl.LazyFrame:
    """Normalize OG codes: uppercase and strip whitespace.

    Handles null values in og_subgroup_code gracefully.
    """
    return df.with_columns([
        pl.col("og_code").str.to_uppercase().str.strip_chars(),
        # Handle null subgroup codes - only apply string ops when not null
        pl.when(pl.col("og_subgroup_code").is_not_null())
        .then(pl.col("og_subgroup_code").str.to_uppercase().str.strip_chars())
        .otherwise(None)
        .alias("og_subgroup_code"),
    ])


def validate_og_exists(
    df: pl.LazyFrame,
    valid_og_codes: set[str],
) -> pl.LazyFrame:
    """Validate og_code exists in dim_og (FK validation).

    This is a soft validation - logs warnings but doesn't filter rows.
    All records are kept to preserve data, but warnings are logged for
    og_codes that don't exist in dim_og.

    Args:
        df: Evaluation standards LazyFrame.
        valid_og_codes: Set of valid og_codes from dim_og.

    Returns:
        Same LazyFrame (no filtering, just logging).
    """
    # Collect og_codes for validation logging
    collected = df.select("og_code").unique().collect()
    og_codes_in_data = set(collected["og_code"].to_list())

    # Find orphan og_codes (those not in dim_og)
    orphan_codes = og_codes_in_data - valid_og_codes
    if orphan_codes:
        logger.warning(
            "og_codes_not_in_dim_og",
            orphan_codes=sorted(list(orphan_codes)),
            count=len(orphan_codes),
        )

    # Return original df without filtering
    return df


def select_gold_columns(df: pl.LazyFrame) -> pl.LazyFrame:
    """Select and order columns for dim_og_job_evaluation_standard gold table."""
    return df.select([
        "og_code",
        "og_subgroup_code",
        "standard_name",
        "standard_type",
        "factor_name",
        "factor_description",
        "factor_points",
        "factor_percentage",
        "factor_level",
        "level_points",
        "level_description",
        "full_text",
        "effective_date",
        "version",
        "_source_url",
        "_scraped_at",
        "_ingested_at",
        "_batch_id",
        "_layer",
    ])


def ingest_dim_og_job_evaluation_standard(
    source_path: Optional[Path] = None,
    config: Optional[PipelineConfig] = None,
    table_name: str = "dim_og_job_evaluation_standard",
    validate_fk: bool = True,
) -> dict:
    """Ingest TBS Job Evaluation Standards JSON to gold layer.

    Transforms evaluation standards to extract factors, points, and descriptions.

    Transforms applied:
    - Bronze: Load JSON, validate required fields
    - Silver: Normalize codes, validate FK to dim_og (soft validation)
    - Gold: Final column selection with provenance

    Args:
        source_path: Path to og_evaluation_standards.json file.
            Defaults to data/tbs/og_evaluation_standards.json.
        config: Pipeline configuration (defaults to PipelineConfig()).
        table_name: Output table name (defaults to "dim_og_job_evaluation_standard").
        validate_fk: Whether to validate og_code FK against dim_og.
            Defaults to True.

    Returns:
        Dict with gold_path, batch_id, row_count, og_coverage.
    """
    if source_path is None:
        source_path = Path("data/tbs/og_evaluation_standards.json")
    source_path = Path(source_path)

    if config is None:
        config = PipelineConfig()

    batch_id = generate_batch_id()
    ingested_at = datetime.now(timezone.utc).isoformat()

    logger.info("loading_evaluation_standards", source=str(source_path))

    # Load evaluation standards from JSON
    raw_data = _load_evaluation_standards_json(source_path)

    # Transform to records with provenance fields
    records = []
    classification_count = 0
    factor_count = 0

    for item in raw_data:
        standard_type = item.get("standard_type", "unknown")
        if standard_type == "classification_standard":
            classification_count += 1
        elif standard_type == "evaluation_factor":
            factor_count += 1

        # Truncate full_text if too long
        full_text = item.get("full_text", "")
        if len(full_text) > MAX_TEXT_LENGTH:
            full_text = full_text[:MAX_TEXT_LENGTH]

        records.append({
            "og_code": item.get("og_code", ""),
            "og_subgroup_code": item.get("og_subgroup_code"),
            "standard_name": item.get("standard_name", ""),
            "standard_type": standard_type,
            "factor_name": item.get("factor_name"),
            "factor_description": item.get("factor_description"),
            "factor_points": item.get("factor_points"),
            "factor_percentage": item.get("factor_percentage"),
            "factor_level": item.get("factor_level"),
            "level_points": item.get("level_points"),
            "level_description": item.get("level_description"),
            "full_text": full_text,
            "effective_date": item.get("effective_date"),
            "version": item.get("version"),
            "_source_url": item.get("source_url", ""),
            "_scraped_at": item.get("scraped_at", ""),
            "_ingested_at": ingested_at,
            "_batch_id": batch_id,
            "_layer": "gold",
        })

    logger.info(
        "evaluation_records_loaded",
        total=len(records),
        classification_standards=classification_count,
        evaluation_factors=factor_count,
    )

    # Create DataFrame with explicit schema to handle nullable columns
    schema = {
        "og_code": pl.Utf8,
        "og_subgroup_code": pl.Utf8,
        "standard_name": pl.Utf8,
        "standard_type": pl.Utf8,
        "factor_name": pl.Utf8,
        "factor_description": pl.Utf8,
        "factor_points": pl.Int32,
        "factor_percentage": pl.Float64,
        "factor_level": pl.Utf8,
        "level_points": pl.Int32,
        "level_description": pl.Utf8,
        "full_text": pl.Utf8,
        "effective_date": pl.Utf8,
        "version": pl.Utf8,
        "_source_url": pl.Utf8,
        "_scraped_at": pl.Utf8,
        "_ingested_at": pl.Utf8,
        "_batch_id": pl.Utf8,
        "_layer": pl.Utf8,
    }
    df = pl.DataFrame(records, schema=schema)

    # Convert to lazy for transforms
    lf = df.lazy()

    # Apply silver transforms
    lf = normalize_og_codes(lf)

    # FK validation against dim_og (soft - logs warnings only)
    if validate_fk:
        parent_path = config.gold_path() / "dim_og.parquet"
        if parent_path.exists():
            parent_df = pl.read_parquet(parent_path)
            valid_og_codes = set(parent_df["og_code"].to_list())
            lf = validate_og_exists(lf, valid_og_codes)
        else:
            logger.warning(
                "dim_og_not_found_skipping_fk_validation",
                expected_path=str(parent_path),
            )

    # Apply gold transforms
    lf = select_gold_columns(lf)

    # Write to gold
    gold_dir = config.gold_path()
    gold_dir.mkdir(parents=True, exist_ok=True)
    output_path = gold_dir / f"{table_name}.parquet"

    result_df = lf.collect()
    result_df.write_parquet(output_path, compression="zstd")

    # Calculate OG coverage stats
    unique_og_codes = result_df["og_code"].unique().to_list()

    logger.info(
        "dim_og_job_evaluation_standard_ingested",
        rows=len(result_df),
        path=str(output_path),
        unique_og_codes=len(unique_og_codes),
    )

    return {
        "gold_path": output_path,
        "batch_id": batch_id,
        "row_count": len(result_df),
        "classification_standards": classification_count,
        "evaluation_factors": factor_count,
        "og_coverage": unique_og_codes,
    }


if __name__ == "__main__":
    # Quick manual test
    print("Ingesting dim_og_job_evaluation_standard...")
    result = ingest_dim_og_job_evaluation_standard()
    print(f"  Rows: {result['row_count']}")
    print(f"  Classification standards: {result['classification_standards']}")
    print(f"  Evaluation factors: {result['evaluation_factors']}")
    print(f"  OG codes covered: {result['og_coverage']}")
    print(f"  Path: {result['gold_path']}")

    # Show sample data
    df = pl.read_parquet(result["gold_path"])
    print("\nSample data:")
    print(df.select(["og_code", "standard_type", "factor_name", "factor_points"]).head(10))
