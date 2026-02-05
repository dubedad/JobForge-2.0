"""OG Qualification Standards enhanced ingestion.

Ingests TBS Qualification Standard text data to gold layer table:
- dim_og_qualification_standard: Enhanced qualification standards with structured fields

This module replaces the basic dim_og_qualifications with CONTEXT.md enhanced fields:
- Education level (standardized + original text)
- Experience years (numeric + original text)
- Essential vs Asset qualifications
- Bilingual requirements (reading, writing, oral levels)
- Security clearance levels
- Conditions of employment (travel, shift work, physical demands)
- Operational requirements (overtime, on-call, deployments)

Uses parse_enhanced_qualification from qualification_parser module.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import polars as pl
import structlog

from jobforge.external.tbs.qualification_parser import parse_enhanced_qualification
from jobforge.pipeline.config import PipelineConfig
from jobforge.pipeline.provenance import generate_batch_id

logger = structlog.get_logger(__name__)


def _load_qualification_text_json(source_path: Path) -> list[dict]:
    """Load og_qualification_text.json.

    The source JSON is a flat array:
    [
        {
            "og_code": "AI",
            "subgroup_code": null,
            "full_text": "...",
            "tables": [],
            "page_count": 1,
            "source_url": "https://...",
            "source_file": "html",
            "source_type": "html",
            "extracted_at": "2026-01-20T00:29:09.573286Z",
            "pdf_metadata": {...}
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
        df: Qualifications LazyFrame.
        valid_og_codes: Set of valid og_codes from dim_og.

    Returns:
        Same LazyFrame (no filtering, just logging).
    """
    # Collect og_codes for validation logging
    collected = df.select("og_code").unique().collect()
    og_codes_in_data = set(collected["og_code"].to_list())

    # Find orphan og_codes
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
    """Select and order columns for dim_og_qualification_standard gold table."""
    return df.select([
        # Primary keys
        "og_code",
        "og_subgroup_code",
        # Education: structured + original
        "education_level",
        "education_requirement_text",
        # Experience: numeric + original
        "min_years_experience",
        "experience_requirement_text",
        # Essential vs Asset qualifications
        "essential_qualification_text",
        "asset_qualification_text",
        # Equivalency
        "has_equivalency",
        "equivalency_statement",
        # Bilingual requirements
        "bilingual_reading_level",
        "bilingual_writing_level",
        "bilingual_oral_level",
        # Security clearance
        "security_clearance",
        # Conditions of employment
        "requires_travel",
        "shift_work",
        "physical_demands",
        # Operational requirements
        "overtime_required",
        "on_call_required",
        "deployments_required",
        # Certification
        "certification_requirement",
        # Full text for search
        "full_text",
        # Provenance
        "_source_url",
        "_extracted_at",
        "_ingested_at",
        "_batch_id",
        "_layer",
    ])


def ingest_dim_og_qualification_standard(
    source_path: Optional[Path] = None,
    config: Optional[PipelineConfig] = None,
    table_name: str = "dim_og_qualification_standard",
    validate_fk: bool = True,
) -> dict:
    """Ingest TBS Qualification Standards JSON to gold layer with enhanced fields.

    Transforms qualification text using parse_enhanced_qualification to extract
    CONTEXT.md structured fields while preserving raw text for full-text search.

    Transforms applied:
    - Bronze: Load JSON, parse structured fields from full_text
    - Silver: Normalize codes, validate FK to dim_og
    - Gold: Final column selection with provenance

    Args:
        source_path: Path to og_qualification_text.json file.
            Defaults to data/tbs/og_qualification_text.json.
        config: Pipeline configuration (defaults to PipelineConfig()).
        table_name: Output table name (defaults to "dim_og_qualification_standard").
        validate_fk: Whether to validate og_code FK against dim_og.
            Defaults to True.

    Returns:
        Dict with gold_path, batch_id, row_count, extraction_stats.
    """
    if source_path is None:
        source_path = Path("data/tbs/og_qualification_text.json")
    source_path = Path(source_path)

    if config is None:
        config = PipelineConfig()

    batch_id = generate_batch_id()
    ingested_at = datetime.now(timezone.utc).isoformat()

    logger.info("loading_qualification_text", source=str(source_path))

    # Load qualification text from JSON
    raw_data = _load_qualification_text_json(source_path)

    # Transform to records with parsed fields
    records = []
    stats = {
        "education_level": 0,
        "min_years_experience": 0,
        "bilingual_levels": 0,
        "security_clearance": 0,
        "equivalency": 0,
        "certification": 0,
        "essential_qualification": 0,
        "asset_qualification": 0,
    }

    for item in raw_data:
        og_code = item.get("og_code", "")
        subgroup_code = item.get("subgroup_code")
        full_text = item.get("full_text", "")

        # Parse enhanced qualification fields
        parsed = parse_enhanced_qualification(full_text)

        # Track extraction stats
        if parsed.education_level:
            stats["education_level"] += 1
        if parsed.min_years_experience is not None:
            stats["min_years_experience"] += 1
        if parsed.bilingual_reading_level or parsed.bilingual_writing_level or parsed.bilingual_oral_level:
            stats["bilingual_levels"] += 1
        if parsed.security_clearance:
            stats["security_clearance"] += 1
        if parsed.has_equivalency:
            stats["equivalency"] += 1
        if parsed.certification_requirement:
            stats["certification"] += 1
        if parsed.essential_qualification_text:
            stats["essential_qualification"] += 1
        if parsed.asset_qualification_text:
            stats["asset_qualification"] += 1

        records.append({
            "og_code": og_code,
            "og_subgroup_code": subgroup_code,
            # Education
            "education_level": parsed.education_level,
            "education_requirement_text": parsed.education_requirement_text,
            # Experience
            "min_years_experience": parsed.min_years_experience,
            "experience_requirement_text": parsed.experience_requirement_text,
            # Essential vs Asset
            "essential_qualification_text": parsed.essential_qualification_text,
            "asset_qualification_text": parsed.asset_qualification_text,
            # Equivalency
            "has_equivalency": parsed.has_equivalency,
            "equivalency_statement": parsed.equivalency_statement,
            # Bilingual
            "bilingual_reading_level": parsed.bilingual_reading_level,
            "bilingual_writing_level": parsed.bilingual_writing_level,
            "bilingual_oral_level": parsed.bilingual_oral_level,
            # Security
            "security_clearance": parsed.security_clearance,
            # Conditions
            "requires_travel": parsed.requires_travel,
            "shift_work": parsed.shift_work,
            "physical_demands": parsed.physical_demands,
            # Operations
            "overtime_required": parsed.overtime_required,
            "on_call_required": parsed.on_call_required,
            "deployments_required": parsed.deployments_required,
            # Certification
            "certification_requirement": parsed.certification_requirement,
            # Full text
            "full_text": parsed.full_text,
            # Provenance
            "_source_url": item.get("source_url", ""),
            "_extracted_at": item.get("extracted_at", ""),
            "_ingested_at": ingested_at,
            "_batch_id": batch_id,
            "_layer": "gold",
        })

    logger.info(
        "qualification_records_loaded",
        total=len(records),
        extraction_stats=stats,
    )

    # Create DataFrame with explicit schema to handle nullable columns
    schema = {
        "og_code": pl.Utf8,
        "og_subgroup_code": pl.Utf8,
        "education_level": pl.Utf8,
        "education_requirement_text": pl.Utf8,
        "min_years_experience": pl.Int32,
        "experience_requirement_text": pl.Utf8,
        "essential_qualification_text": pl.Utf8,
        "asset_qualification_text": pl.Utf8,
        "has_equivalency": pl.Boolean,
        "equivalency_statement": pl.Utf8,
        "bilingual_reading_level": pl.Utf8,
        "bilingual_writing_level": pl.Utf8,
        "bilingual_oral_level": pl.Utf8,
        "security_clearance": pl.Utf8,
        "requires_travel": pl.Boolean,
        "shift_work": pl.Boolean,
        "physical_demands": pl.Boolean,
        "overtime_required": pl.Boolean,
        "on_call_required": pl.Boolean,
        "deployments_required": pl.Boolean,
        "certification_requirement": pl.Utf8,
        "full_text": pl.Utf8,
        "_source_url": pl.Utf8,
        "_extracted_at": pl.Utf8,
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

    logger.info(
        "dim_og_qualification_standard_ingested",
        rows=len(result_df),
        columns=len(result_df.columns),
        path=str(output_path),
    )

    return {
        "gold_path": output_path,
        "batch_id": batch_id,
        "row_count": len(result_df),
        "column_count": len(result_df.columns),
        "extraction_stats": stats,
    }


if __name__ == "__main__":
    # Quick manual test
    print("Ingesting dim_og_qualification_standard...")
    result = ingest_dim_og_qualification_standard()
    print(f"  Rows: {result['row_count']}")
    print(f"  Columns: {result['column_count']}")
    print(f"  Extraction stats: {result['extraction_stats']}")
    print(f"  Path: {result['gold_path']}")

    # Show sample data
    df = pl.read_parquet(result['gold_path'])
    print("\nSample data:")
    print(df.select(['og_code', 'education_level', 'min_years_experience', 'security_clearance']).head(10))
