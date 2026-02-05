"""CAF (Canadian Armed Forces) table ingestion.

Ingests CAF occupation and job family data to gold layer tables:
- dim_caf_occupation: 88 CAF occupations with bilingual content
- dim_caf_job_family: 11 inferred job families

Per 15-02-SUMMARY.md:
- Bilingual content stored in same record (EN/FR columns)
- Provenance includes source URLs, content hashes, scraped_at timestamps
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import polars as pl

from jobforge.pipeline.config import PipelineConfig
from jobforge.pipeline.provenance import generate_batch_id


def _load_occupations_json(source_path: Path) -> tuple[pl.DataFrame, str]:
    """Load occupations.json from CAF scraper output.

    The source JSON has structure:
    {
        "scraped_at": "...",
        "occupation_count": 88,
        "occupations": [
            {
                "career_id": "aerospace-engineering-officer",
                "title_en": "...",
                "title_fr": "...",
                "environment": ["air_force", "navy"],
                "commission_status": "officer",
                "employment_type": ["full_time", "part_time"],
                "overview_en": "...",
                "overview_fr": "...",
                ...
                "url_en": "...",
                "url_fr": "...",
                "provenance_en": {...},
                "provenance_fr": {...}
            },
            ...
        ]
    }

    Returns:
        Tuple of (DataFrame with occupations, scraped_at timestamp).
    """
    data = json.loads(source_path.read_text(encoding="utf-8"))
    scraped_at = data.get("scraped_at", "")
    occupations = data.get("occupations", [])

    # Build records for DataFrame
    records = []
    for occ in occupations:
        # Extract provenance data
        prov_en = occ.get("provenance_en") or {}
        prov_fr = occ.get("provenance_fr") or {}

        # Determine job family from link_fetcher inference (if available)
        # We'll match against job_families.json later, for now use career_id pattern
        job_family_id = _infer_job_family_from_career_id(occ.get("career_id", ""))

        records.append({
            "career_id": occ.get("career_id"),
            "title_en": occ.get("title_en"),
            "title_fr": occ.get("title_fr"),
            "environment": json.dumps(occ.get("environment", [])),  # Store as JSON array string
            "commission_status": occ.get("commission_status"),
            "employment_type": json.dumps(occ.get("employment_type", [])),  # Store as JSON array string
            "overview_en": occ.get("overview_en"),
            "overview_fr": occ.get("overview_fr"),
            "work_environment_en": occ.get("work_environment_en"),
            "work_environment_fr": occ.get("work_environment_fr"),
            "training_en": occ.get("training_en"),
            "training_fr": occ.get("training_fr"),
            "entry_plans_en": occ.get("entry_plans_en"),
            "entry_plans_fr": occ.get("entry_plans_fr"),
            "part_time_options_en": occ.get("part_time_options_en"),
            "part_time_options_fr": occ.get("part_time_options_fr"),
            "related_civilian_occupations": json.dumps(occ.get("related_civilian_occupations", [])),
            "related_careers": json.dumps(occ.get("related_careers", [])),
            "keywords": json.dumps(occ.get("keywords", [])),
            "description_meta": occ.get("description_meta"),
            "url_en": occ.get("url_en"),
            "url_fr": occ.get("url_fr"),
            "job_family_id": job_family_id,
            # Provenance columns
            "_source_url_en": prov_en.get("source_url"),
            "_source_url_fr": prov_fr.get("source_url"),
            "_content_hash_en": prov_en.get("content_hash"),
            "_content_hash_fr": prov_fr.get("content_hash"),
            "_scraped_at": prov_en.get("scraped_at") or scraped_at,
        })

    return pl.DataFrame(records), scraped_at


def _infer_job_family_from_career_id(career_id: str) -> str:
    """Infer job family ID from career_id using title patterns.

    Matches the inference logic from link_fetcher.py.

    Args:
        career_id: The career_id slug.

    Returns:
        Inferred job family ID.
    """
    career_lower = career_id.lower()

    # Medical/Health careers
    medical_keywords = [
        "medical", "nurse", "physician", "dental", "pharmacy",
        "health", "technologist", "physiotherapy", "bioscience",
    ]
    if any(kw in career_lower for kw in medical_keywords):
        return "medical-health"

    # Engineering/Technical careers
    engineering_keywords = [
        "engineer", "technician", "systems", "electronics",
        "construction", "electrical", "mechanical", "avionics",
        "aerospace", "weapons", "marine-tech", "aviation",
    ]
    if any(kw in career_lower for kw in engineering_keywords):
        return "engineering-technical"

    # Combat/Operations careers
    combat_keywords = [
        "infantry", "armour", "artillery", "combat", "gunner",
        "soldier", "warfare", "pilot", "diver",
    ]
    if any(kw in career_lower for kw in combat_keywords):
        return "combat-operations"

    # Intelligence/Signals careers
    intel_keywords = [
        "intelligence", "signals", "communicator", "cyber",
        "sensor", "operator", "sonar",
    ]
    if any(kw in career_lower for kw in intel_keywords):
        return "intelligence-signals"

    # Support/Logistics careers
    support_keywords = [
        "logistics", "supply", "traffic", "cook", "steward",
        "postal", "firefighter", "mobile-support",
    ]
    if any(kw in career_lower for kw in support_keywords):
        return "support-logistics"

    # Administration/HR careers
    admin_keywords = [
        "admin", "human-resources", "financial", "legal",
        "public-affairs", "chaplain", "personnel",
    ]
    if any(kw in career_lower for kw in admin_keywords):
        return "administration-hr"

    # Training/Development careers
    training_keywords = ["training", "instruction", "development-officer"]
    if any(kw in career_lower for kw in training_keywords):
        return "training-development"

    # Police/Security careers
    police_keywords = ["police", "military-police"]
    if any(kw in career_lower for kw in police_keywords):
        return "police-security"

    # Music careers
    if "musician" in career_lower:
        return "music"

    # Default: ncm-general or officer-general based on career pattern
    if "officer" in career_lower:
        return "officer-general"
    else:
        return "ncm-general"


def normalize_caf_occupation_codes(df: pl.LazyFrame) -> pl.LazyFrame:
    """Normalize career_id: lowercase and strip whitespace."""
    return df.with_columns([
        pl.col("career_id").str.to_lowercase().str.strip_chars(),
        pl.col("job_family_id").str.to_lowercase().str.strip_chars(),
    ])


def dedupe_occupations(df: pl.LazyFrame) -> pl.LazyFrame:
    """Remove duplicate career_ids, keeping first occurrence."""
    return df.unique(subset=["career_id"], keep="first")


def validate_required_occupation_fields(df: pl.LazyFrame) -> pl.LazyFrame:
    """Ensure career_id and title_en are not null."""
    return df.filter(
        pl.col("career_id").is_not_null() & pl.col("title_en").is_not_null()
    )


def select_dim_caf_occupation_columns(df: pl.LazyFrame) -> pl.LazyFrame:
    """Select and order columns for dim_caf_occupation gold table."""
    return df.select([
        "career_id",
        "title_en",
        "title_fr",
        "job_family_id",
        "environment",
        "commission_status",
        "employment_type",
        "overview_en",
        "overview_fr",
        "work_environment_en",
        "work_environment_fr",
        "training_en",
        "training_fr",
        "entry_plans_en",
        "entry_plans_fr",
        "part_time_options_en",
        "part_time_options_fr",
        "related_civilian_occupations",
        "related_careers",
        "keywords",
        "description_meta",
        "url_en",
        "url_fr",
        # Provenance columns
        "_source_url_en",
        "_source_url_fr",
        "_content_hash_en",
        "_content_hash_fr",
        "_scraped_at",
        "_source_file",
        "_ingested_at",
        "_batch_id",
        "_layer",
    ])


def ingest_dim_caf_occupation(
    source_path: Optional[Path] = None,
    config: Optional[PipelineConfig] = None,
    table_name: str = "dim_caf_occupation",
) -> dict:
    """Ingest CAF occupations JSON to gold layer as dim_caf_occupation.

    Transforms applied:
    - Bronze: Load JSON, extract occupations, flatten nested structures
    - Silver: Normalize codes, dedupe, validate required fields
    - Gold: Final column selection with provenance

    Args:
        source_path: Path to occupations.json file.
            Defaults to data/caf/occupations.json.
        config: Pipeline configuration (defaults to PipelineConfig()).
        table_name: Output table name (defaults to "dim_caf_occupation").

    Returns:
        Dict with gold_path, batch_id, row_count, and metadata.
    """
    if source_path is None:
        source_path = Path("data/caf/occupations.json")
    source_path = Path(source_path)

    if config is None:
        config = PipelineConfig()

    batch_id = generate_batch_id()
    ingested_at = datetime.now(timezone.utc).isoformat()

    # Load occupations from JSON
    df, scraped_at = _load_occupations_json(source_path)

    # Add provenance columns
    df = df.with_columns([
        pl.lit(str(source_path)).alias("_source_file"),
        pl.lit(ingested_at).alias("_ingested_at"),
        pl.lit(batch_id).alias("_batch_id"),
        pl.lit("gold").alias("_layer"),
    ])

    # Convert to lazy for transforms
    lf = df.lazy()

    # Apply silver transforms
    lf = normalize_caf_occupation_codes(lf)
    lf = dedupe_occupations(lf)
    lf = validate_required_occupation_fields(lf)

    # Apply gold transforms
    lf = select_dim_caf_occupation_columns(lf)

    # Write to gold
    gold_dir = config.gold_path()
    gold_dir.mkdir(parents=True, exist_ok=True)
    output_path = gold_dir / f"{table_name}.parquet"

    result_df = lf.collect()
    result_df.write_parquet(output_path, compression="zstd")

    return {
        "gold_path": output_path,
        "batch_id": batch_id,
        "row_count": len(result_df),
        "scraped_at": scraped_at,
    }


def _load_job_families_json(source_path: Path) -> tuple[pl.DataFrame, str]:
    """Load job_families.json from CAF link fetcher output.

    The source JSON has structure:
    {
        "generated_at": "...",
        "family_count": 11,
        "families": [
            {
                "family_id": "administration-hr",
                "family_name": "Administration Hr",
                "description": "CAF careers in the Administration Hr category.",
                "career_count": 6,
                "source_url": null
            },
            ...
        ]
    }

    Returns:
        Tuple of (DataFrame with job families, generated_at timestamp).
    """
    data = json.loads(source_path.read_text(encoding="utf-8"))
    generated_at = data.get("generated_at", "")
    families = data.get("families", [])

    # Build records for DataFrame
    records = []
    for fam in families:
        records.append({
            "job_family_id": fam.get("family_id"),
            "job_family_name": fam.get("family_name"),
            "description": fam.get("description"),
            "career_count": fam.get("career_count"),
            "_source_url": fam.get("source_url"),  # May be null (inferred)
        })

    return pl.DataFrame(records), generated_at


def normalize_job_family_codes(df: pl.LazyFrame) -> pl.LazyFrame:
    """Normalize job_family_id: lowercase and strip whitespace."""
    return df.with_columns([
        pl.col("job_family_id").str.to_lowercase().str.strip_chars(),
    ])


def dedupe_job_families(df: pl.LazyFrame) -> pl.LazyFrame:
    """Remove duplicate job_family_ids, keeping first occurrence."""
    return df.unique(subset=["job_family_id"], keep="first")


def validate_required_job_family_fields(df: pl.LazyFrame) -> pl.LazyFrame:
    """Ensure job_family_id and job_family_name are not null."""
    return df.filter(
        pl.col("job_family_id").is_not_null() & pl.col("job_family_name").is_not_null()
    )


def select_dim_caf_job_family_columns(df: pl.LazyFrame) -> pl.LazyFrame:
    """Select and order columns for dim_caf_job_family gold table."""
    return df.select([
        "job_family_id",
        "job_family_name",
        "description",
        "career_count",
        "_source_url",
        "_generated_at",
        "_source_file",
        "_ingested_at",
        "_batch_id",
        "_layer",
    ])


def ingest_dim_caf_job_family(
    source_path: Optional[Path] = None,
    config: Optional[PipelineConfig] = None,
    table_name: str = "dim_caf_job_family",
) -> dict:
    """Ingest CAF job families JSON to gold layer as dim_caf_job_family.

    Transforms applied:
    - Bronze: Load JSON, extract job families
    - Silver: Normalize codes, dedupe, validate required fields
    - Gold: Final column selection with provenance

    Args:
        source_path: Path to job_families.json file.
            Defaults to data/caf/job_families.json.
        config: Pipeline configuration (defaults to PipelineConfig()).
        table_name: Output table name (defaults to "dim_caf_job_family").

    Returns:
        Dict with gold_path, batch_id, row_count, and metadata.
    """
    if source_path is None:
        source_path = Path("data/caf/job_families.json")
    source_path = Path(source_path)

    if config is None:
        config = PipelineConfig()

    batch_id = generate_batch_id()
    ingested_at = datetime.now(timezone.utc).isoformat()

    # Load job families from JSON
    df, generated_at = _load_job_families_json(source_path)

    # Add provenance columns
    df = df.with_columns([
        pl.lit(generated_at).alias("_generated_at"),
        pl.lit(str(source_path)).alias("_source_file"),
        pl.lit(ingested_at).alias("_ingested_at"),
        pl.lit(batch_id).alias("_batch_id"),
        pl.lit("gold").alias("_layer"),
    ])

    # Convert to lazy for transforms
    lf = df.lazy()

    # Apply silver transforms
    lf = normalize_job_family_codes(lf)
    lf = dedupe_job_families(lf)
    lf = validate_required_job_family_fields(lf)

    # Apply gold transforms
    lf = select_dim_caf_job_family_columns(lf)

    # Write to gold
    gold_dir = config.gold_path()
    gold_dir.mkdir(parents=True, exist_ok=True)
    output_path = gold_dir / f"{table_name}.parquet"

    result_df = lf.collect()
    result_df.write_parquet(output_path, compression="zstd")

    return {
        "gold_path": output_path,
        "batch_id": batch_id,
        "row_count": len(result_df),
        "generated_at": generated_at,
    }


if __name__ == "__main__":
    # Quick manual test
    print("Ingesting dim_caf_occupation...")
    result_occ = ingest_dim_caf_occupation()
    print(f"  Rows: {result_occ['row_count']}")
    print(f"  Path: {result_occ['gold_path']}")

    print("\nIngesting dim_caf_job_family...")
    result_fam = ingest_dim_caf_job_family()
    print(f"  Rows: {result_fam['row_count']}")
    print(f"  Path: {result_fam['gold_path']}")
