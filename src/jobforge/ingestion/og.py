"""OG (Occupational Groups) table ingestion.

Ingests TBS Occupational Groups data to gold layer tables:
- dim_og: 31 unique occupational groups
- dim_og_subgroup: ~111 subgroups linked to parent groups
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import polars as pl

from jobforge.pipeline.config import PipelineConfig
from jobforge.pipeline.provenance import generate_batch_id


def _load_occupational_groups_json(source_path: Path) -> tuple[pl.DataFrame, str, str]:
    """Load occupational_groups_en.json and extract unique groups.

    The source JSON has structure:
    {
        "url": "...",
        "scraped_at": "...",
        "rows": [
            {
                "group_abbrev": "AI",
                "group_code": "402",
                "group_name": "Air Traffic Control(AI)",
                "subgroup": "N/A",
                "definition_url": "...",
                "qualification_standard_url": "...",
                "provenance": {"source_url": "...", "scraped_at": "..."}
            },
            ...
        ]
    }

    Returns:
        Tuple of (DataFrame with unique groups, source_url, scraped_at).
    """
    data = json.loads(source_path.read_text())
    source_url = data.get("url", "")
    scraped_at = data.get("scraped_at", "")
    rows = data.get("rows", [])

    # Extract unique groups - keep first occurrence of each group_abbrev
    seen_groups = set()
    unique_groups = []

    for row in rows:
        group_abbrev = row.get("group_abbrev", "")
        if group_abbrev and group_abbrev not in seen_groups:
            seen_groups.add(group_abbrev)
            # Clean group name by removing the abbreviation suffix like "(AI)"
            group_name = row.get("group_name", "")
            if "(" in group_name:
                group_name = group_name.rsplit("(", 1)[0].strip()

            unique_groups.append({
                "og_code": group_abbrev,
                "og_numeric_code": row.get("group_code", ""),
                "og_name": group_name,
                "definition_url": row.get("definition_url"),
                "qualification_standard_url": row.get("qualification_standard_url"),
                "rates_of_pay_url": None,  # Not in source, but in schema
                "_source_url": source_url,
                "_scraped_at": scraped_at,
            })

    return pl.DataFrame(unique_groups), source_url, scraped_at


def normalize_og_codes(df: pl.LazyFrame) -> pl.LazyFrame:
    """Normalize OG codes: uppercase and strip whitespace."""
    return df.with_columns([
        pl.col("og_code").str.to_uppercase().str.strip_chars(),
        pl.col("og_numeric_code").str.strip_chars(),
    ])


def dedupe_groups(df: pl.LazyFrame) -> pl.LazyFrame:
    """Remove duplicate OG codes, keeping first occurrence."""
    return df.unique(subset=["og_code"], keep="first")


def validate_required_og_fields(df: pl.LazyFrame) -> pl.LazyFrame:
    """Ensure og_code and og_name are not null."""
    return df.filter(
        pl.col("og_code").is_not_null() & pl.col("og_name").is_not_null()
    )


def select_dim_og_columns(df: pl.LazyFrame) -> pl.LazyFrame:
    """Select and order columns for dim_og gold table."""
    return df.select([
        "og_code",
        "og_numeric_code",
        "og_name",
        "definition_url",
        "qualification_standard_url",
        "rates_of_pay_url",
        "_source_url",
        "_scraped_at",
        "_source_file",
        "_ingested_at",
        "_batch_id",
        "_layer",
    ])


def ingest_dim_og(
    source_path: Optional[Path] = None,
    config: Optional[PipelineConfig] = None,
    table_name: str = "dim_og",
) -> dict:
    """Ingest TBS Occupational Groups JSON to gold layer as dim_og.

    Transforms applied:
    - Bronze: Load JSON, extract unique groups, rename columns
    - Silver: Normalize codes, dedupe, validate required fields
    - Gold: Final column selection with provenance

    Args:
        source_path: Path to occupational_groups_en.json file.
            Defaults to data/tbs/occupational_groups_en.json.
        config: Pipeline configuration (defaults to PipelineConfig()).
        table_name: Output table name (defaults to "dim_og").

    Returns:
        Dict with gold_path, batch_id, row_count, and metadata.
    """
    if source_path is None:
        source_path = Path("data/tbs/occupational_groups_en.json")
    source_path = Path(source_path)

    if config is None:
        config = PipelineConfig()

    batch_id = generate_batch_id()
    ingested_at = datetime.now(timezone.utc).isoformat()

    # Load and extract unique groups from JSON
    df, source_url, scraped_at = _load_occupational_groups_json(source_path)

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
    lf = normalize_og_codes(lf)
    lf = dedupe_groups(lf)
    lf = validate_required_og_fields(lf)

    # Apply gold transforms
    lf = select_dim_og_columns(lf)

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
        "source_url": source_url,
        "scraped_at": scraped_at,
    }


def _load_og_subgroups_json(source_path: Path) -> tuple[pl.DataFrame, str, str]:
    """Load og_subgroups_en.json.

    The source JSON is a flat array:
    [
        {
            "og_code": "AI",
            "subgroup_code": "AI-NOP",
            "subgroup_name": "Non-Operational",
            "definition_url": "...",
            "qualification_standard_url": "...",
            "rates_of_pay_url": null,
            "source_url": "...",
            "scraped_at": "..."
        },
        ...
    ]

    Returns:
        Tuple of (DataFrame, source_url from first record, scraped_at from first record).
    """
    data = json.loads(source_path.read_text())

    # Extract source_url and scraped_at from first record
    source_url = data[0].get("source_url", "") if data else ""
    scraped_at = data[0].get("scraped_at", "") if data else ""

    # Build DataFrame with renamed columns
    records = []
    for row in data:
        records.append({
            "og_code": row.get("og_code", ""),
            "og_subgroup_code": row.get("subgroup_code", ""),
            "og_subgroup_name": row.get("subgroup_name", ""),
            "definition_url": row.get("definition_url"),
            "qualification_standard_url": row.get("qualification_standard_url"),
            "rates_of_pay_url": row.get("rates_of_pay_url"),
            "_source_url": row.get("source_url", source_url),
            "_scraped_at": row.get("scraped_at", scraped_at),
        })

    return pl.DataFrame(records), source_url, scraped_at


def normalize_subgroup_codes(df: pl.LazyFrame) -> pl.LazyFrame:
    """Normalize subgroup codes: uppercase and strip whitespace."""
    return df.with_columns([
        pl.col("og_code").str.to_uppercase().str.strip_chars(),
        pl.col("og_subgroup_code").str.to_uppercase().str.strip_chars(),
    ])


def dedupe_subgroups(df: pl.LazyFrame) -> pl.LazyFrame:
    """Remove duplicate subgroup codes, keeping first occurrence."""
    return df.unique(subset=["og_subgroup_code"], keep="first")


def validate_parent_exists(df: pl.LazyFrame, parent_codes: set[str]) -> pl.LazyFrame:
    """Ensure og_code exists in parent dim_og table (FK validation).

    Args:
        df: Subgroup LazyFrame.
        parent_codes: Set of valid og_codes from dim_og.

    Returns:
        Filtered LazyFrame with only valid parent codes.
    """
    # Convert to list for Polars expression
    valid_codes = list(parent_codes)
    return df.filter(pl.col("og_code").is_in(valid_codes))


def select_dim_og_subgroup_columns(df: pl.LazyFrame) -> pl.LazyFrame:
    """Select and order columns for dim_og_subgroup gold table."""
    return df.select([
        "og_subgroup_code",
        "og_code",
        "og_subgroup_name",
        "definition_url",
        "qualification_standard_url",
        "rates_of_pay_url",
        "_source_url",
        "_scraped_at",
        "_source_file",
        "_ingested_at",
        "_batch_id",
        "_layer",
    ])


def ingest_dim_og_subgroup(
    source_path: Optional[Path] = None,
    config: Optional[PipelineConfig] = None,
    table_name: str = "dim_og_subgroup",
    validate_fk: bool = True,
) -> dict:
    """Ingest TBS OG Subgroups JSON to gold layer as dim_og_subgroup.

    Note: dim_og must be ingested first as dim_og_subgroup has FK dependency.

    Transforms applied:
    - Bronze: Load JSON, rename columns
    - Silver: Normalize codes, dedupe, validate parent FK
    - Gold: Final column selection with provenance

    Args:
        source_path: Path to og_subgroups_en.json file.
            Defaults to data/tbs/og_subgroups_en.json.
        config: Pipeline configuration (defaults to PipelineConfig()).
        table_name: Output table name (defaults to "dim_og_subgroup").
        validate_fk: Whether to validate og_code FK against dim_og.
            Defaults to True.

    Returns:
        Dict with gold_path, batch_id, row_count, orphans_removed, and metadata.

    Raises:
        FileNotFoundError: If dim_og.parquet doesn't exist and validate_fk is True.
    """
    if source_path is None:
        source_path = Path("data/tbs/og_subgroups_en.json")
    source_path = Path(source_path)

    if config is None:
        config = PipelineConfig()

    batch_id = generate_batch_id()
    ingested_at = datetime.now(timezone.utc).isoformat()

    # Load subgroups from JSON
    df, source_url, scraped_at = _load_og_subgroups_json(source_path)

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
    lf = normalize_subgroup_codes(lf)
    lf = dedupe_subgroups(lf)

    # Count before FK validation
    count_before_fk = lf.select(pl.len()).collect().item()

    # FK validation against dim_og
    orphans_removed = 0
    if validate_fk:
        parent_path = config.gold_path() / "dim_og.parquet"
        if not parent_path.exists():
            raise FileNotFoundError(
                f"dim_og.parquet not found at {parent_path}. "
                "Run ingest_dim_og() first."
            )
        parent_df = pl.read_parquet(parent_path)
        parent_codes = set(parent_df["og_code"].to_list())
        lf = validate_parent_exists(lf, parent_codes)

        # Count orphans removed
        count_after_fk = lf.select(pl.len()).collect().item()
        orphans_removed = count_before_fk - count_after_fk

    # Apply gold transforms
    lf = select_dim_og_subgroup_columns(lf)

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
        "orphans_removed": orphans_removed,
        "source_url": source_url,
        "scraped_at": scraped_at,
    }


if __name__ == "__main__":
    # Quick manual test
    print("Ingesting dim_og...")
    result_og = ingest_dim_og()
    print(f"  Rows: {result_og['row_count']}")
    print(f"  Path: {result_og['gold_path']}")

    print("\nIngesting dim_og_subgroup...")
    result_subgroup = ingest_dim_og_subgroup()
    print(f"  Rows: {result_subgroup['row_count']}")
    print(f"  Orphans removed: {result_subgroup['orphans_removed']}")
    print(f"  Path: {result_subgroup['gold_path']}")
