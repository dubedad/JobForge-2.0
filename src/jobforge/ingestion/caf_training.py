"""CAF training table ingestion.

Ingests CAF training data to gold layer tables:
- dim_caf_training_location: Normalized training base locations
- fact_caf_training: Training requirements per occupation

Per 16-05-PLAN.md and CONTEXT.md:
- Duration: standardized weeks + original text
- Locations: normalized with FK to dim_caf_training_location
- Handle sparse data gracefully (not all 107 occupations have training info)
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import polars as pl
import structlog

from jobforge.external.caf.training_parser import (
    CAFTraining,
    get_all_canonical_locations,
    parse_training_info,
)
from jobforge.pipeline.config import PipelineConfig
from jobforge.pipeline.provenance import generate_batch_id

logger = structlog.get_logger(__name__)


def ingest_dim_caf_training_location(
    config: Optional[PipelineConfig] = None,
    table_name: str = "dim_caf_training_location",
) -> dict:
    """Create dim_caf_training_location from canonical training bases.

    Uses the canonical location list from training_parser which includes
    all major CAF training bases with province/country/base_type metadata.

    Args:
        config: Pipeline configuration (defaults to PipelineConfig()).
        table_name: Output table name (defaults to "dim_caf_training_location").

    Returns:
        Dict with gold_path, batch_id, row_count.
    """
    if config is None:
        config = PipelineConfig()

    batch_id = generate_batch_id()
    ingested_at = datetime.now(timezone.utc).isoformat()

    # Get canonical locations from parser
    locations = get_all_canonical_locations()

    # Build records for DataFrame
    records = []
    for loc in locations:
        records.append({
            "training_location_id": loc["id"],
            "location_name": loc["name"],
            "province": loc["province"],
            "country": loc["country"],
            "base_type": loc["base_type"],
            # Provenance columns
            "_source": "canonical_training_locations",
            "_ingested_at": ingested_at,
            "_batch_id": batch_id,
            "_layer": "gold",
        })

    # Create DataFrame
    df = pl.DataFrame(records)

    # Write to gold
    gold_dir = config.gold_path()
    gold_dir.mkdir(parents=True, exist_ok=True)
    output_path = gold_dir / f"{table_name}.parquet"

    df.write_parquet(output_path, compression="zstd")

    logger.info(
        "dim_caf_training_location_ingested",
        row_count=len(df),
        output_path=str(output_path),
    )

    return {
        "gold_path": output_path,
        "batch_id": batch_id,
        "row_count": len(df),
    }


def _load_occupations_json(source_path: Path) -> list[dict]:
    """Load occupations.json from CAF scraper output.

    Args:
        source_path: Path to occupations.json.

    Returns:
        List of occupation dicts.
    """
    data = json.loads(source_path.read_text(encoding="utf-8"))
    return data.get("occupations", [])


def ingest_fact_caf_training(
    source_path: Optional[Path] = None,
    config: Optional[PipelineConfig] = None,
    table_name: str = "fact_caf_training",
) -> dict:
    """Ingest CAF training data to fact_caf_training gold table.

    Transforms applied:
    - Bronze: Load occupations.json, parse training_en field
    - Silver: Normalize locations (FK to dim_caf_training_location),
              validate FK to dim_caf_occupation
    - Gold: Write fact_caf_training.parquet

    Args:
        source_path: Path to occupations.json file.
            Defaults to data/caf/occupations.json.
        config: Pipeline configuration (defaults to PipelineConfig()).
        table_name: Output table name (defaults to "fact_caf_training").

    Returns:
        Dict with gold_path, batch_id, row_count, occupation_count, metrics.
    """
    if source_path is None:
        source_path = Path("data/caf/occupations.json")
    source_path = Path(source_path)

    if config is None:
        config = PipelineConfig()

    batch_id = generate_batch_id()
    ingested_at = datetime.now(timezone.utc).isoformat()

    # Load occupations
    occupations = _load_occupations_json(source_path)

    # Parse training info for each occupation
    all_training_records: list[CAFTraining] = []
    occupations_with_training = 0
    occupations_without_training = 0

    for occ in occupations:
        career_id = occ.get("career_id", "")
        training_records = parse_training_info(occ)

        if training_records:
            all_training_records.extend(training_records)
            occupations_with_training += 1
        else:
            occupations_without_training += 1
            logger.debug(
                "occupation_no_training_info",
                career_id=career_id,
            )

    logger.info(
        "training_parsing_complete",
        total_occupations=len(occupations),
        with_training=occupations_with_training,
        without_training=occupations_without_training,
        total_training_records=len(all_training_records),
    )

    # If no training records, return empty result
    if not all_training_records:
        logger.warning("no_training_records_found")
        return {
            "gold_path": None,
            "batch_id": batch_id,
            "row_count": 0,
            "occupation_count": 0,
            "metrics": {
                "occupations_with_training": 0,
                "occupations_without_training": len(occupations),
                "coverage_pct": 0.0,
            },
        }

    # Convert to DataFrame records
    records = []
    for tr in all_training_records:
        records.append({
            "caf_occupation_id": tr.caf_occupation_id,
            "training_type": tr.training_type,
            "duration_weeks": tr.duration_weeks,
            "duration_text": tr.duration_text,
            "training_location_id": tr.training_location_id,
            "training_location_text": tr.training_location_text,
            "certifications_awarded": json.dumps(tr.certifications_awarded),
            "qualifications_awarded": json.dumps(tr.qualifications_awarded),
            "prerequisite_courses": json.dumps(tr.prerequisite_courses),
            "minimum_rank": tr.minimum_rank,
            "civilian_credential_level": tr.civilian_credential_level,
            "civilian_equivalency_text": tr.civilian_equivalency_text,
            "recertification_required": tr.recertification_required,
            "recertification_frequency": tr.recertification_frequency,
            # Provenance columns
            "_source_url": tr.source_url,
            "_extracted_at": tr.extracted_at,
            "_ingested_at": ingested_at,
            "_batch_id": batch_id,
            "_layer": "gold",
        })

    # Create DataFrame with explicit schema
    df = pl.DataFrame(records)

    # Validate FK to dim_caf_occupation (soft validation - log warnings)
    gold_dir = config.gold_path()
    caf_occupation_path = gold_dir / "dim_caf_occupation.parquet"

    if caf_occupation_path.exists():
        caf_occupations = pl.read_parquet(caf_occupation_path)
        valid_career_ids = set(caf_occupations["career_id"].to_list())

        orphan_records = df.filter(
            ~pl.col("caf_occupation_id").is_in(list(valid_career_ids))
        )

        if len(orphan_records) > 0:
            orphan_ids = orphan_records["caf_occupation_id"].unique().to_list()
            logger.warning(
                "orphan_training_records",
                count=len(orphan_records),
                career_ids=orphan_ids[:10],  # Log first 10
            )
    else:
        logger.warning(
            "dim_caf_occupation_not_found",
            path=str(caf_occupation_path),
            message="FK validation skipped",
        )

    # Write to gold
    gold_dir.mkdir(parents=True, exist_ok=True)
    output_path = gold_dir / f"{table_name}.parquet"

    df.write_parquet(output_path, compression="zstd")

    # Calculate metrics
    coverage_pct = round(
        (occupations_with_training / len(occupations)) * 100, 1
    ) if occupations else 0.0

    unique_occupations = df["caf_occupation_id"].n_unique()

    logger.info(
        "fact_caf_training_ingested",
        row_count=len(df),
        occupation_count=unique_occupations,
        coverage_pct=coverage_pct,
        output_path=str(output_path),
    )

    return {
        "gold_path": output_path,
        "batch_id": batch_id,
        "row_count": len(df),
        "occupation_count": unique_occupations,
        "metrics": {
            "occupations_with_training": occupations_with_training,
            "occupations_without_training": occupations_without_training,
            "coverage_pct": coverage_pct,
        },
    }


if __name__ == "__main__":
    # Quick manual test
    print("Ingesting dim_caf_training_location...")
    result_loc = ingest_dim_caf_training_location()
    print(f"  Rows: {result_loc['row_count']}")
    print(f"  Path: {result_loc['gold_path']}")

    print("\nIngesting fact_caf_training...")
    result_train = ingest_fact_caf_training()
    print(f"  Rows: {result_train['row_count']}")
    print(f"  Occupations: {result_train['occupation_count']}")
    print(f"  Path: {result_train['gold_path']}")
    print(f"  Metrics: {result_train['metrics']}")
