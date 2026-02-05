"""OG Qualification Standards table ingestion.

Ingests TBS Qualification Standard text data to gold layer table:
- dim_og_qualifications: Qualification standards per occupational group

The source data comes from og_qualification_text.json (extracted from TBS HTML).
This module parses the qualification text to extract structured fields while
preserving the raw text for full-text search capability.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import polars as pl
import structlog

from jobforge.pipeline.config import PipelineConfig
from jobforge.pipeline.provenance import generate_batch_id

logger = structlog.get_logger(__name__)

# Maximum character limit for full_text column
MAX_FULL_TEXT_LENGTH = 50000
# Maximum character limit for structured fields
MAX_FIELD_LENGTH = 2000


def parse_qualification_text(full_text: str) -> dict:
    """Extract structured fields from qualification standard text.

    Uses regex patterns to identify common TBS qualification standard sections.
    Returns dict with structured fields + raw text.

    The TBS qualification standards typically include sections like:
    - "The minimum standard" for education requirements
    - "Experience" requirements
    - "Occupational Certification" / "Professional Certification"
    - Language requirements
    - Security clearance requirements

    Args:
        full_text: Full extracted qualification text.

    Returns:
        Dict with structured fields:
        - education_requirement: Extracted education section
        - experience_requirement: Extracted experience section
        - certification_requirement: Extracted certification section
        - language_requirement: Extracted language section
        - other_requirements: Extracted other requirements
        - full_text: Original text (for full-text search)
    """
    fields = {
        "education_requirement": None,
        "experience_requirement": None,
        "certification_requirement": None,
        "language_requirement": None,
        "other_requirements": None,
        "full_text": full_text[:MAX_FULL_TEXT_LENGTH],  # Truncate if too long
    }

    # Skip if text is too short to contain meaningful content
    if len(full_text.strip()) < 100:
        logger.warning("qualification_text_too_short", length=len(full_text))
        return fields

    # Education section patterns
    # Typically starts with "The minimum standard" followed by education requirements
    education_patterns = [
        # Primary pattern: "The minimum standard is:" followed by content
        r"(?:The minimum standard(?:s)?\s+(?:is|are)[:\s]*)(.+?)(?=The minimum standard|Experience|Certification|Occupational Certification|Professional Certification|Language|Security|Note[:\s]|$)",
        # Secondary pattern: Education section header
        r"(?:Education|EDUCATION)[:\s]+(.+?)(?=Experience|EXPERIENCE|Certification|Language|Security|$)",
        # Pattern for specific level requirements
        r"(?:The minimum standard for positions)[:\s]*(.+?)(?=The minimum standard|Experience|Certification|$)",
    ]

    for pattern in education_patterns:
        education_match = re.search(pattern, full_text, re.DOTALL | re.IGNORECASE)
        if education_match:
            edu_text = education_match.group(1).strip()
            if len(edu_text) > 50:  # Ensure we got meaningful content
                fields["education_requirement"] = edu_text[:MAX_FIELD_LENGTH]
                break

    # Experience section patterns
    experience_patterns = [
        r"(?:Experience|EXPERIENCE)[:\s]+(.+?)(?=Education|Certification|Language|Security|The minimum|$)",
        r"(?:experience\s+(?:is|are)\s+(?:required|needed|necessary))[:\s]*(.+?)(?=Certification|Language|Security|$)",
    ]

    for pattern in experience_patterns:
        experience_match = re.search(pattern, full_text, re.DOTALL | re.IGNORECASE)
        if experience_match:
            exp_text = experience_match.group(1).strip()
            if len(exp_text) > 30:
                fields["experience_requirement"] = exp_text[:MAX_FIELD_LENGTH]
                break

    # Certification section patterns
    certification_patterns = [
        r"(?:Occupational Certification|Professional Certification|Certification)[:\s]+(.+?)(?=Education|Experience|Language|Security|The minimum|$)",
        r"(?:Eligibility for|Possession of)\s+([^.]+(?:certification|licence|membership)[^.]+\.)",
        r"(?:certification|licence|Licence)\s+(?:is|are)\s+(?:required|needed)[:\s]*(.+?)(?=Education|Experience|Language|Security|$)",
    ]

    for pattern in certification_patterns:
        cert_match = re.search(pattern, full_text, re.DOTALL | re.IGNORECASE)
        if cert_match:
            cert_text = cert_match.group(1).strip()
            if len(cert_text) > 30:
                fields["certification_requirement"] = cert_text[:MAX_FIELD_LENGTH]
                break

    # Language requirements patterns
    language_patterns = [
        r"(?:Language Requirements?|Language Proficiency|Official Languages?)[:\s]+(.+?)(?=Education|Experience|Certification|Security|The minimum|$)",
        r"(?:Bilingual|English|French)\s+(?:is|are)\s+(?:required|essential)[:\s]*(.+?)(?=Education|Experience|Certification|Security|$)",
    ]

    for pattern in language_patterns:
        lang_match = re.search(pattern, full_text, re.DOTALL | re.IGNORECASE)
        if lang_match:
            lang_text = lang_match.group(1).strip()
            if len(lang_text) > 20:
                fields["language_requirement"] = lang_text[:MAX_FIELD_LENGTH]
                break

    # Security clearance patterns
    security_patterns = [
        r"(?:Security Clearance|Security Requirements?)[:\s]+(.+?)(?=Education|Experience|Certification|Language|The minimum|$)",
        r"(?:security clearance|reliability status|secret clearance)\s+(?:is|are)\s+(?:required|needed)[:\s]*(.+?)(?=Education|Experience|Certification|Language|$)",
    ]

    for pattern in security_patterns:
        sec_match = re.search(pattern, full_text, re.DOTALL | re.IGNORECASE)
        if sec_match:
            sec_text = sec_match.group(1).strip()
            if len(sec_text) > 20:
                fields["other_requirements"] = sec_text[:MAX_FIELD_LENGTH]
                break

    # Log extraction results
    extracted_fields = [k for k, v in fields.items() if v is not None and k != "full_text"]
    if not extracted_fields:
        logger.warning("no_structured_fields_extracted", text_length=len(full_text))
    else:
        logger.debug("structured_fields_extracted", fields=extracted_fields)

    return fields


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


def normalize_qualification_codes(df: pl.LazyFrame) -> pl.LazyFrame:
    """Normalize OG codes: uppercase and strip whitespace."""
    return df.with_columns([
        pl.col("og_code").str.to_uppercase().str.strip_chars(),
        pl.col("og_subgroup_code").str.to_uppercase().str.strip_chars(),
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


def select_dim_og_qualifications_columns(df: pl.LazyFrame) -> pl.LazyFrame:
    """Select and order columns for dim_og_qualifications gold table."""
    return df.select([
        "og_code",
        "og_subgroup_code",
        "education_requirement",
        "experience_requirement",
        "certification_requirement",
        "language_requirement",
        "other_requirements",
        "full_text",
        "page_count",
        "_source_url",
        "_source_file",
        "_extracted_at",
        "_ingested_at",
        "_batch_id",
        "_layer",
    ])


def ingest_dim_og_qualifications(
    source_path: Optional[Path] = None,
    config: Optional[PipelineConfig] = None,
    table_name: str = "dim_og_qualifications",
    validate_fk: bool = True,
) -> dict:
    """Ingest TBS Qualification Standards JSON to gold layer.

    Transforms qualification text to extract structured fields while
    preserving raw text for full-text search capability.

    Transforms applied:
    - Bronze: Load JSON, parse structured fields from full_text
    - Silver: Normalize codes, validate FK to dim_og
    - Gold: Final column selection with provenance

    Args:
        source_path: Path to og_qualification_text.json file.
            Defaults to data/tbs/og_qualification_text.json.
        config: Pipeline configuration (defaults to PipelineConfig()).
        table_name: Output table name (defaults to "dim_og_qualifications").
        validate_fk: Whether to validate og_code FK against dim_og.
            Defaults to True.

    Returns:
        Dict with gold_path, batch_id, row_count, structured_extractions.
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
    structured_count = 0

    for item in raw_data:
        og_code = item.get("og_code", "")
        subgroup_code = item.get("subgroup_code")
        full_text = item.get("full_text", "")

        # Parse structured fields from full_text
        parsed = parse_qualification_text(full_text)

        # Count records with any structured extraction
        if any(
            v is not None
            for k, v in parsed.items()
            if k != "full_text"
        ):
            structured_count += 1

        records.append({
            "og_code": og_code,
            "og_subgroup_code": subgroup_code,
            "education_requirement": parsed["education_requirement"],
            "experience_requirement": parsed["experience_requirement"],
            "certification_requirement": parsed["certification_requirement"],
            "language_requirement": parsed["language_requirement"],
            "other_requirements": parsed["other_requirements"],
            "full_text": parsed["full_text"],
            "page_count": item.get("page_count", 1),
            "_source_url": item.get("source_url", ""),
            "_source_file": item.get("source_file", ""),
            "_extracted_at": item.get("extracted_at", ""),
            "_ingested_at": ingested_at,
            "_batch_id": batch_id,
            "_layer": "gold",
        })

    logger.info(
        "qualification_records_loaded",
        total=len(records),
        with_structured_fields=structured_count,
    )

    # Create DataFrame
    df = pl.DataFrame(records)

    # Convert to lazy for transforms
    lf = df.lazy()

    # Apply silver transforms
    lf = normalize_qualification_codes(lf)

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
    lf = select_dim_og_qualifications_columns(lf)

    # Write to gold
    gold_dir = config.gold_path()
    gold_dir.mkdir(parents=True, exist_ok=True)
    output_path = gold_dir / f"{table_name}.parquet"

    result_df = lf.collect()
    result_df.write_parquet(output_path, compression="zstd")

    logger.info(
        "dim_og_qualifications_ingested",
        rows=len(result_df),
        path=str(output_path),
    )

    return {
        "gold_path": output_path,
        "batch_id": batch_id,
        "row_count": len(result_df),
        "structured_extractions": structured_count,
        "total_records": len(records),
    }


if __name__ == "__main__":
    # Quick manual test
    print("Ingesting dim_og_qualifications...")
    result = ingest_dim_og_qualifications()
    print(f"  Rows: {result['row_count']}")
    print(f"  Structured extractions: {result['structured_extractions']}/{result['total_records']}")
    print(f"  Path: {result['gold_path']}")

    # Show sample data
    df = pl.read_parquet(result['gold_path'])
    print("\nSample data:")
    print(df.select(['og_code', 'education_requirement']).head(5))
