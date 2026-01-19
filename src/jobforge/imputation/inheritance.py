"""Attribute inheritance logic for NOC hierarchical imputation.

This module provides functions to cascade attributes from L5 Unit Groups
down to L7 job titles with full provenance tracking.

The inheritance flow is:
L5 (Unit Group) -> L6 (Label) -> L7 (Job Title)

Attributes at L5 are inherited by all job titles within that Unit Group.
Each inherited value carries provenance showing it came from L5.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import polars as pl

from jobforge.imputation.models import (
    ImputedValue,
    NOCResolutionResult,
    ProvenanceEnum,
)
from jobforge.imputation.provenance import (
    ImputationProvenanceColumns,
    add_imputation_provenance,
)
from jobforge.imputation.resolution import resolve_job_title
from jobforge.pipeline.config import PipelineConfig


def _get_default_gold_path() -> Path:
    """Get default gold path from PipelineConfig."""
    return PipelineConfig().gold_path()


def inherit_attributes_to_job_titles(
    job_arch: pl.LazyFrame,
    attribute_df: pl.LazyFrame,
    attribute_name: str,
    gold_path: Path | None = None,
) -> pl.LazyFrame:
    """Inherit L5 attributes to job titles via unit_group_id.

    Joins OASIS attribute data to job architecture via unit_group_id,
    adding imputation provenance columns to track the inheritance.

    Since attributes are at L5 (Unit Group level), all job titles within
    a Unit Group inherit the same attribute values. The provenance columns
    indicate source_level=5 and provenance="inherited".

    Confidence scores are based on the resolution method:
    - Single-label UG: 0.85
    - Direct L6 match: 1.00
    - L7 example match: 0.95
    - Fuzzy match: 0.60
    - UG fallback: 0.40

    For batch operations, we use 0.85 as default (most common case is
    single-label UG). For single title resolution, use apply_imputation()
    to get exact confidence per title.

    Args:
        job_arch: Job Architecture LazyFrame with unit_group_id column.
        attribute_df: OASIS attribute table (e.g., oasis_skills) with unit_group_id.
        attribute_name: Name for identifying this attribute type (e.g., "skill").
            Used for logging/tracing, not for column prefixing.
        gold_path: Path to gold layer directory. Defaults to PipelineConfig().gold_path().

    Returns:
        LazyFrame with job architecture columns plus:
        - All attribute columns from attribute_df (excluding provenance columns)
        - _imputation_source_level (always 5 for L5 inheritance)
        - _imputation_source_id (unit_group_id)
        - _imputation_provenance ("inherited")
        - _imputation_confidence (default 0.85 for batch)
        - _imputation_at (timestamp)

    Example:
        >>> job_arch = pl.scan_parquet("data/gold/job_architecture.parquet")
        >>> oasis_skills = pl.scan_parquet("data/gold/oasis_skills.parquet")
        >>> result = inherit_attributes_to_job_titles(job_arch, oasis_skills, "skill")
        >>> result.collect_schema().names()  # Has provenance columns
    """
    if gold_path is None:
        gold_path = _get_default_gold_path()

    # Get attribute columns (exclude pipeline provenance columns)
    pipeline_provenance_cols = {"_source_file", "_ingested_at", "_batch_id", "_layer"}
    attr_schema = attribute_df.collect_schema()
    attr_cols = [c for c in attr_schema.names() if c not in pipeline_provenance_cols]

    # Select only attribute columns for join
    attribute_selected = attribute_df.select(attr_cols)

    # Left join attributes to job architecture on unit_group_id
    result = job_arch.join(
        attribute_selected,
        on="unit_group_id",
        how="left",
    )

    # Add imputation provenance columns
    # Default confidence of 0.85 for batch (most common case)
    result = add_imputation_provenance(
        df=result,
        source_level=5,
        source_id_col="unit_group_id",
        provenance="inherited",
        confidence=0.85,
    )

    return result


def apply_imputation(
    job_title: str,
    unit_group_id: str,
    attribute_tables: dict[str, pl.LazyFrame],
    gold_path: Path | None = None,
) -> dict[str, list[dict]]:
    """Impute attributes for a single job title with full provenance.

    Resolves the job title through the NOC hierarchy to get the exact
    confidence score, then fetches all matching attributes from each
    provided attribute table.

    This function is for interactive/demo use. For batch operations,
    use inherit_attributes_to_job_titles() which is more efficient.

    Args:
        job_title: The job title to impute attributes for.
        unit_group_id: The 5-digit Unit Group ID (e.g., "21231").
        attribute_tables: Dict mapping attribute name to OASIS LazyFrame.
            Example: {"skills": skills_lf, "abilities": abilities_lf}
        gold_path: Path to gold layer directory. Defaults to PipelineConfig().gold_path().

    Returns:
        Dict mapping attribute_name to list of ImputedValue-like dicts.
        Each dict contains:
        - value: The attribute value
        - source_level: NOC level (5)
        - source_identifier: unit_group_id
        - provenance: "inherited"
        - confidence: Resolution confidence score
        - imputed_at: Timestamp

        Returns empty dict if resolution fails.

    Example:
        >>> skills = pl.scan_parquet("data/gold/oasis_skills.parquet")
        >>> result = apply_imputation(
        ...     "Software Developer",
        ...     "21231",
        ...     {"skills": skills}
        ... )
        >>> len(result.get("skills", []))  # Number of inherited skills
    """
    if gold_path is None:
        gold_path = _get_default_gold_path()

    # Resolve job title to get confidence score
    resolution = resolve_job_title(job_title, unit_group_id, gold_path)
    if resolution is None:
        return {}

    now = datetime.now(timezone.utc)
    results: dict[str, list[dict]] = {}

    # For each attribute table, fetch matching L5 attributes
    for attr_name, attr_lf in attribute_tables.items():
        # Filter to matching unit_group_id
        # Exclude pipeline provenance columns from results
        pipeline_provenance_cols = ["_source_file", "_ingested_at", "_batch_id", "_layer"]
        attr_schema = attr_lf.collect_schema()
        select_cols = [c for c in attr_schema.names() if c not in pipeline_provenance_cols]

        matching = (
            attr_lf.filter(pl.col("unit_group_id") == unit_group_id)
            .select(select_cols)
            .collect()
        )

        if matching.is_empty():
            results[attr_name] = []
            continue

        # Build imputed values with provenance
        imputed_values = []
        for row in matching.iter_rows(named=True):
            # Get primary value column (e.g., oasis_label for OASIS tables)
            value = row.get("oasis_label", "")

            imputed_values.append({
                "value": value,
                "source_level": 5,  # L5 inheritance
                "source_identifier": unit_group_id,
                "provenance": ProvenanceEnum.INHERITED.value,
                "confidence": resolution.confidence_score,
                "imputed_at": now,
                "resolution_method": resolution.resolution_method.value,
                "raw_attributes": {k: v for k, v in row.items() if k not in ["unit_group_id", "oasis_code", "noc_element_code", "oasis_label"]},
            })

        results[attr_name] = imputed_values

    return results


def get_imputation_summary(imputed_df: pl.LazyFrame) -> dict:
    """Generate summary statistics for imputed data.

    Provides statistics about imputed values for monitoring and validation.

    Args:
        imputed_df: LazyFrame with imputation provenance columns.

    Returns:
        Dict with:
        - total_rows: Total number of rows
        - rows_by_source_level: Dict of {level: count}
        - rows_by_provenance: Dict of {provenance_type: count}
        - avg_confidence: Average confidence score
        - min_confidence: Minimum confidence score
        - max_confidence: Maximum confidence score

    Example:
        >>> result = inherit_attributes_to_job_titles(job_arch, skills, "skill")
        >>> summary = get_imputation_summary(result)
        >>> print(f"Imputed {summary['total_rows']} rows")
    """
    # Collect the full DataFrame for statistics
    df = imputed_df.collect()

    total_rows = len(df)

    # Check if imputation columns exist
    cols = df.columns
    source_level_col = ImputationProvenanceColumns.IMPUTATION_SOURCE_LEVEL
    provenance_col = ImputationProvenanceColumns.IMPUTATION_PROVENANCE
    confidence_col = ImputationProvenanceColumns.IMPUTATION_CONFIDENCE

    summary: dict = {
        "total_rows": total_rows,
        "rows_by_source_level": {},
        "rows_by_provenance": {},
        "avg_confidence": 0.0,
        "min_confidence": 0.0,
        "max_confidence": 0.0,
    }

    if total_rows == 0:
        return summary

    # Group by source level
    if source_level_col in cols:
        level_counts = (
            df.group_by(source_level_col)
            .count()
            .to_dicts()
        )
        summary["rows_by_source_level"] = {
            row[source_level_col]: row["count"] for row in level_counts
        }

    # Group by provenance
    if provenance_col in cols:
        prov_counts = (
            df.group_by(provenance_col)
            .count()
            .to_dicts()
        )
        summary["rows_by_provenance"] = {
            row[provenance_col]: row["count"] for row in prov_counts
        }

    # Confidence statistics
    if confidence_col in cols:
        conf_stats = df.select([
            pl.col(confidence_col).mean().alias("avg"),
            pl.col(confidence_col).min().alias("min"),
            pl.col(confidence_col).max().alias("max"),
        ]).to_dicts()[0]

        summary["avg_confidence"] = conf_stats["avg"] if conf_stats["avg"] is not None else 0.0
        summary["min_confidence"] = conf_stats["min"] if conf_stats["min"] is not None else 0.0
        summary["max_confidence"] = conf_stats["max"] if conf_stats["max"] is not None else 0.0

    return summary
