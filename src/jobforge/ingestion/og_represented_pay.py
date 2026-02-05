"""Represented Pay Rates ingestion pipeline.

This module ingests represented (unionized) pay rates and collective agreement
metadata into the gold layer, extending the fact_og_pay_rates table created
in Phase 14-04.

Transforms applied:
1. ingest_dim_collective_agreement(): Collective agreement dimension table
2. extend_fact_og_pay_rates(): Merge excluded and represented rates

Prerequisites:
- data/gold/fact_og_pay_rates.parquet must exist (from Phase 14-04)
- data/tbs/collective_agreements.json must exist
- data/tbs/og_represented_pay_rates.json must exist (or will be created)
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

# Source file paths
DEFAULT_CA_SOURCE = Path("data/tbs/collective_agreements.json")
DEFAULT_REPRESENTED_SOURCE = Path("data/tbs/og_represented_pay_rates.json")
DEFAULT_EXCLUDED_SOURCE = Path("data/gold/fact_og_pay_rates.parquet")

# Gold layer output
GOLD_DIR = Path("data/gold")


def verify_prerequisites() -> None:
    """Verify Phase 14-04 output exists before extending.

    Raises:
        FileNotFoundError: If fact_og_pay_rates.parquet doesn't exist.
    """
    if not DEFAULT_EXCLUDED_SOURCE.exists():
        raise FileNotFoundError(
            f"Phase 14-04 output missing: {DEFAULT_EXCLUDED_SOURCE} must exist before extending. "
            "Run Phase 14-04 first to create excluded pay rates."
        )


def ingest_dim_collective_agreement(
    source_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
) -> dict:
    """Ingest collective agreement metadata to gold layer.

    Bronze: Parse JSON, validate agreement IDs
    Silver: Normalize og_codes, validate dates
    Gold: Write dim_collective_agreement.parquet

    Args:
        source_path: Path to collective_agreements.json
        output_dir: Output directory for parquet file

    Returns:
        Dict with gold_path, batch_id, row_count
    """
    source_path = source_path or DEFAULT_CA_SOURCE
    output_dir = output_dir or GOLD_DIR

    if not source_path.exists():
        raise FileNotFoundError(f"Collective agreements not found: {source_path}")

    logger.info("ingest_dim_collective_agreement_start", source_path=str(source_path))

    # Load JSON
    with open(source_path, encoding="utf-8") as f:
        data = json.load(f)

    if not data:
        raise ValueError(f"Empty data in source file: {source_path}")

    # Bronze: Create DataFrame with provenance
    batch_id = str(uuid4())
    ingested_at = datetime.now(timezone.utc).isoformat()

    rows = []
    for record in data:
        rows.append({
            "agreement_id": record.get("agreement_id"),
            "agreement_name": record.get("agreement_name"),
            "og_code": record.get("og_code", "").upper(),
            "og_subgroup_codes": json.dumps(record.get("og_subgroup_codes", [])),
            "bargaining_agent": record.get("bargaining_agent"),
            "employer": record.get("employer", "Treasury Board of Canada Secretariat"),
            "signing_date": record.get("signing_date"),
            "effective_date": record.get("effective_date"),
            "expiry_date": record.get("expiry_date"),
            "_source_url": record.get("source_url"),
            "_scraped_at": record.get("scraped_at"),
            "_source_file": str(source_path),
            "_ingested_at": ingested_at,
            "_batch_id": batch_id,
            "_layer": "gold",
        })

    df = pl.DataFrame(rows)

    # Silver: Validate and normalize
    df = df.with_columns([
        pl.col("og_code").str.to_uppercase().alias("og_code"),
    ])

    # Remove duplicates by agreement_id
    df = df.unique(subset=["agreement_id"], maintain_order=True)

    # Gold: Write to parquet
    output_dir.mkdir(parents=True, exist_ok=True)
    gold_path = output_dir / "dim_collective_agreement.parquet"
    df.write_parquet(gold_path)

    row_count = len(df)

    logger.info(
        "ingest_dim_collective_agreement_complete",
        gold_path=str(gold_path),
        row_count=row_count,
    )

    return {
        "gold_path": gold_path,
        "batch_id": batch_id,
        "row_count": row_count,
    }


def extend_fact_og_pay_rates(
    excluded_path: Optional[Path] = None,
    represented_source: Optional[Path] = None,
    output_dir: Optional[Path] = None,
) -> dict:
    """Extend fact_og_pay_rates with represented (unionized) rates.

    This function:
    1. Loads existing fact_og_pay_rates.parquet (excluded rates from 14-04)
    2. Loads represented rates from JSON
    3. Merges both with is_represented flag
    4. Adds collective_agreement_id FK and pay_progression_type
    5. Dedupes by natural key
    6. Writes extended fact_og_pay_rates.parquet

    Args:
        excluded_path: Path to existing fact_og_pay_rates.parquet
        represented_source: Path to og_represented_pay_rates.json
        output_dir: Output directory for parquet file

    Returns:
        Dict with gold_path, batch_id, row_count, excluded_count, represented_count
    """
    excluded_path = excluded_path or DEFAULT_EXCLUDED_SOURCE
    represented_source = represented_source or DEFAULT_REPRESENTED_SOURCE
    output_dir = output_dir or GOLD_DIR

    # Verify prerequisites
    verify_prerequisites()

    logger.info(
        "extend_fact_og_pay_rates_start",
        excluded_path=str(excluded_path),
        represented_source=str(represented_source),
    )

    batch_id = str(uuid4())
    ingested_at = datetime.now(timezone.utc).isoformat()

    # Load existing excluded pay rates
    excluded_df = pl.read_parquet(excluded_path)
    excluded_count = len(excluded_df)

    logger.info("loaded_excluded_rates", count=excluded_count)

    # Add new columns to excluded rates if they don't exist
    if "collective_agreement_id" not in excluded_df.columns:
        excluded_df = excluded_df.with_columns([
            pl.lit(None).cast(pl.Utf8).alias("collective_agreement_id"),
        ])

    if "pay_progression_type" not in excluded_df.columns:
        excluded_df = excluded_df.with_columns([
            pl.lit("step").alias("pay_progression_type"),
        ])

    # Ensure is_represented column exists and is False for excluded
    if "is_represented" not in excluded_df.columns:
        excluded_df = excluded_df.with_columns([
            pl.lit(False).alias("is_represented"),
        ])
    else:
        excluded_df = excluded_df.with_columns([
            pl.lit(False).alias("is_represented"),
        ])

    # Load represented pay rates if available
    represented_count = 0
    if represented_source.exists():
        with open(represented_source, encoding="utf-8") as f:
            represented_data = json.load(f)

        if represented_data:
            # Convert to DataFrame
            rep_rows = []
            for record in represented_data:
                rep_rows.append({
                    "og_code": record.get("og_code", "").upper(),
                    "og_subgroup_code": record.get("og_subgroup_code", "").upper(),
                    "classification_level": record.get("classification_level", "").upper(),
                    "step": record.get("step", 1),
                    "annual_rate": record.get("annual_rate"),
                    "hourly_rate": record.get("hourly_rate"),
                    "effective_date": record.get("effective_date"),
                    "is_represented": True,
                    "collective_agreement": None,  # Will use collective_agreement_id instead
                    "collective_agreement_id": record.get("collective_agreement_id"),
                    "pay_progression_type": record.get("pay_progression_type", "step"),
                    "_source_url": record.get("source_url"),
                    "_scraped_at": record.get("scraped_at"),
                    "_source_file": str(represented_source),
                    "_ingested_at": ingested_at,
                    "_batch_id": batch_id,
                    "_layer": "gold",
                })

            represented_df = pl.DataFrame(rep_rows)
            represented_count = len(represented_df)
            logger.info("loaded_represented_rates", count=represented_count)

            # Cast types to match excluded_df schema
            if "_ingested_at" in excluded_df.columns:
                excluded_df = excluded_df.with_columns([
                    pl.col("_ingested_at").cast(pl.Utf8).alias("_ingested_at"),
                ])

            # Cast step to Int32 to match excluded schema
            represented_df = represented_df.with_columns([
                pl.col("step").cast(pl.Int32).alias("step"),
            ])

            # Align columns with excluded_df
            # Get the common columns
            target_columns = [
                "og_subgroup_code",
                "og_code",
                "classification_level",
                "step",
                "annual_rate",
                "hourly_rate",
                "effective_date",
                "is_represented",
                "collective_agreement",
                "collective_agreement_id",
                "pay_progression_type",
                "_source_url",
                "_scraped_at",
                "_source_file",
                "_ingested_at",
                "_batch_id",
                "_layer",
            ]

            # Ensure excluded_df has all columns
            for col in ["collective_agreement", "collective_agreement_id", "pay_progression_type"]:
                if col not in excluded_df.columns:
                    if col == "pay_progression_type":
                        excluded_df = excluded_df.with_columns([
                            pl.lit("step").alias(col),
                        ])
                    else:
                        excluded_df = excluded_df.with_columns([
                            pl.lit(None).cast(pl.Utf8).alias(col),
                        ])

            # Select and order columns for both DataFrames
            available_excluded = [c for c in target_columns if c in excluded_df.columns]
            available_rep = [c for c in target_columns if c in represented_df.columns]

            # Use intersection
            common_columns = list(set(available_excluded) & set(available_rep))

            # Add missing columns to excluded_df with null
            for col in common_columns:
                if col not in excluded_df.columns:
                    excluded_df = excluded_df.with_columns([
                        pl.lit(None).alias(col),
                    ])

            # Add missing columns to represented_df with null
            for col in common_columns:
                if col not in represented_df.columns:
                    represented_df = represented_df.with_columns([
                        pl.lit(None).alias(col),
                    ])

            # Select same columns in same order
            excluded_df = excluded_df.select(common_columns)
            represented_df = represented_df.select(common_columns)

            # Concatenate
            combined_df = pl.concat([excluded_df, represented_df], how="vertical")
        else:
            combined_df = excluded_df
            logger.info("no_represented_rates_found")
    else:
        combined_df = excluded_df
        logger.info("represented_source_not_found", path=str(represented_source))

    # Dedupe by natural key
    # Natural key: (og_subgroup_code, classification_level, step, effective_date, is_represented)
    combined_df = combined_df.unique(
        subset=["og_subgroup_code", "classification_level", "step", "effective_date", "is_represented"],
        maintain_order=True,
    )

    # Write extended fact table
    output_dir.mkdir(parents=True, exist_ok=True)
    gold_path = output_dir / "fact_og_pay_rates.parquet"
    combined_df.write_parquet(gold_path)

    row_count = len(combined_df)

    logger.info(
        "extend_fact_og_pay_rates_complete",
        gold_path=str(gold_path),
        row_count=row_count,
        excluded_count=excluded_count,
        represented_count=represented_count,
    )

    return {
        "gold_path": gold_path,
        "batch_id": batch_id,
        "row_count": row_count,
        "excluded_count": excluded_count,
        "represented_count": represented_count,
    }


def ingest_all() -> dict:
    """Run full ingestion pipeline for represented pay rates.

    1. Ingest dim_collective_agreement
    2. Extend fact_og_pay_rates with represented rates

    Returns:
        Dict with results from both ingestion steps
    """
    logger.info("ingest_all_start")

    # Verify prerequisites
    verify_prerequisites()

    # Step 1: Ingest collective agreements
    ca_result = ingest_dim_collective_agreement()

    # Step 2: Extend fact_og_pay_rates
    pay_result = extend_fact_og_pay_rates()

    logger.info(
        "ingest_all_complete",
        collective_agreements=ca_result["row_count"],
        pay_rates=pay_result["row_count"],
    )

    return {
        "dim_collective_agreement": ca_result,
        "fact_og_pay_rates": pay_result,
    }


if __name__ == "__main__":
    result = ingest_all()
    print(f"Collective agreements: {result['dim_collective_agreement']['row_count']}")
    print(f"Pay rates: {result['fact_og_pay_rates']['row_count']}")
    print(f"  Excluded: {result['fact_og_pay_rates']['excluded_count']}")
    print(f"  Represented: {result['fact_og_pay_rates']['represented_count']}")
