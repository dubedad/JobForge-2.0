"""Job Architecture and DIM Occupations ingestion."""
from pathlib import Path
from typing import Optional

import polars as pl

from jobforge.pipeline.config import PipelineConfig
from jobforge.pipeline.engine import PipelineEngine


def ingest_job_architecture(
    source_path: Path,
    config: Optional[PipelineConfig] = None,
    table_name: str = "job_architecture",
) -> dict:
    """Ingest Job Architecture CSV to gold layer.

    Job Architecture maps organizational job titles to NOC codes.
    Each row is one job title (L7 level).

    Transforms applied:
    - Bronze: Clean column names (remove special chars)
    - Silver: Derive unit_group_id from 2021_NOC_UID
    - Gold: Select key columns for semantic model

    Args:
        source_path: Path to Job Architecture CSV file
        config: Pipeline configuration (defaults to PipelineConfig())
        table_name: Output table name (defaults to "job_architecture")

    Returns:
        Dict with gold_path, batch_id, and row counts
    """
    engine = PipelineEngine(config=config)

    # Bronze: clean column names
    bronze_schema = {
        "rename": {
            "JT_ID": "jt_id",
            "Job_Title": "job_title_en",
            "Titre_de_poste": "job_title_fr",
            "Job_Function": "job_function_en",
            "Fonction_professionnelle": "job_function_fr",
            "Job_Family": "job_family_en",
            "Famille_d'emplois": "job_family_fr",
            "Managerial_Level": "managerial_level_en",
            "Niveau_de_gestion": "managerial_level_fr",
            "2021_NOC_UID": "noc_2021_uid",
            "2021_NOC_Title": "noc_2021_title",
            "2016_NOC_UID": "noc_2016_uid",
            "2016_NOC_Title": "noc_2016_title",
            "Match_Key": "match_key",
        },
    }

    # Silver transforms
    def derive_unit_group_id(df: pl.LazyFrame) -> pl.LazyFrame:
        """Derive unit_group_id from 2021_NOC_UID.

        NOC 2021 codes should be 5 digits. Zero-pad if needed.
        Handle null/missing NOC codes gracefully.
        """
        return df.with_columns(
            pl.when(pl.col("noc_2021_uid").is_not_null())
            .then(
                pl.col("noc_2021_uid")
                .cast(pl.Utf8)
                .str.replace_all(r"[^\d]", "")  # Remove non-numeric chars
                .str.zfill(5)
            )
            .otherwise(pl.lit(None))
            .alias("unit_group_id")
        )

    silver_transforms = [derive_unit_group_id]

    # Gold: select final columns
    def select_gold_columns(df: pl.LazyFrame) -> pl.LazyFrame:
        """Select and order columns for Job Architecture gold table."""
        cols = df.collect_schema().names()
        priority = [
            "jt_id",
            "unit_group_id",
            "job_title_en",
            "job_title_fr",
            "job_function_en",
            "job_function_fr",
            "job_family_en",
            "job_family_fr",
            "managerial_level_en",
            "managerial_level_fr",
            "noc_2021_uid",
            "noc_2021_title",
        ]
        provenance = ["_source_file", "_ingested_at", "_batch_id", "_layer"]
        available = [c for c in priority if c in cols]
        return df.select(available + provenance)

    gold_transforms = [select_gold_columns]

    result = engine.run_full_pipeline(
        source_path=source_path,
        table_name=table_name,
        domain="gc",
        bronze_schema=bronze_schema,
        silver_transforms=silver_transforms,
        gold_transforms=gold_transforms,
    )

    return result


def extract_dim_occupations(
    job_arch_gold_path: Path,
    config: Optional[PipelineConfig] = None,
) -> dict:
    """Extract DIM Occupations (Occupational Groups) from Job Architecture.

    Creates a dimension table of unique job families and functions
    from the Job Architecture table. This is the L6 level hierarchy.

    Args:
        job_arch_gold_path: Path to Job Architecture gold parquet
        config: Pipeline configuration

    Returns:
        Dict with gold_path and row count
    """
    config = config or PipelineConfig()

    # Read Job Architecture gold table
    job_arch = pl.scan_parquet(job_arch_gold_path)

    # Extract unique job families with their functions
    dim_occupations = (
        job_arch.select(
            [
                "job_family_en",
                "job_family_fr",
                "job_function_en",
                "job_function_fr",
            ]
        )
        .unique()
        .with_columns(
            [
                # Create a family_id based on hash of family name
                pl.concat_str([pl.col("job_family_en"), pl.col("job_function_en")])
                .hash()
                .cast(pl.Utf8)
                .str.slice(0, 8)
                .alias("occupation_group_id"),
            ]
        )
        .sort("job_function_en", "job_family_en")
    )

    # Add provenance columns
    from datetime import datetime, timezone
    import uuid

    batch_id = str(uuid.uuid4())
    ingested_at = datetime.now(timezone.utc).isoformat()

    dim_occupations = dim_occupations.with_columns(
        [
            pl.lit(str(job_arch_gold_path)).alias("_source_file"),
            pl.lit(ingested_at).alias("_ingested_at"),
            pl.lit(batch_id).alias("_batch_id"),
            pl.lit("gold").alias("_layer"),
        ]
    )

    # Write to gold
    gold_dir = config.gold_path()
    gold_dir.mkdir(parents=True, exist_ok=True)
    output_path = gold_dir / "dim_occupations.parquet"

    result_df = dim_occupations.collect()
    result_df.write_parquet(output_path, compression="zstd")

    return {
        "gold_path": output_path,
        "row_count": len(result_df),
        "batch_id": batch_id,
    }


def ingest_job_architecture_with_dim_occupations(
    source_path: Path,
    config: Optional[PipelineConfig] = None,
) -> dict:
    """Ingest Job Architecture and extract DIM Occupations in one call.

    Args:
        source_path: Path to Job Architecture CSV file
        config: Pipeline configuration

    Returns:
        Dict with job_architecture_result and dim_occupations_result
    """
    config = config or PipelineConfig()

    # First, ingest Job Architecture
    job_arch_result = ingest_job_architecture(source_path, config)

    # Then, extract DIM Occupations from it
    dim_occ_result = extract_dim_occupations(job_arch_result["gold_path"], config)

    return {
        "job_architecture": job_arch_result,
        "dim_occupations": dim_occ_result,
    }
