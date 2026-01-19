"""Imputation package for NOC resolution and attribute inheritance.

This package provides:
- NOC resolution service for mapping job titles to NOC hierarchy levels
- Hierarchical attribute inheritance from L5 to L7
- Pydantic models for resolution results and imputed values
- Provenance tracking for audit trails

Example usage:
    from jobforge.imputation import resolve_job_title, NOCResolutionResult

    result = resolve_job_title("Software Engineer", "21231")
    print(f"Resolved at L{result.noc_level_used} with {result.confidence_score} confidence")

    # Inherit attributes to job titles
    from jobforge.imputation import inherit_attributes_to_job_titles
    import polars as pl

    job_arch = pl.scan_parquet("data/gold/job_architecture.parquet")
    skills = pl.scan_parquet("data/gold/oasis_skills.parquet")
    result = inherit_attributes_to_job_titles(job_arch, skills, "skill")
"""

from jobforge.imputation.inheritance import (
    apply_imputation,
    get_imputation_summary,
    inherit_attributes_to_job_titles,
)
from jobforge.imputation.models import (
    ImputedValue,
    NOCResolutionResult,
    ProvenanceEnum,
    ResolutionMethodEnum,
)
from jobforge.imputation.provenance import (
    ImputationProvenanceColumns,
    add_imputation_provenance,
    create_imputed_attribute_row,
    get_provenance_column_names,
)
from jobforge.imputation.resolution import (
    ResolutionContext,
    build_resolution_context,
    clear_resolution_cache,
    resolve_job_title,
)

__all__ = [
    # Models
    "ResolutionMethodEnum",
    "ProvenanceEnum",
    "NOCResolutionResult",
    "ImputedValue",
    # Resolution service
    "resolve_job_title",
    "build_resolution_context",
    "ResolutionContext",
    "clear_resolution_cache",
    # Inheritance
    "inherit_attributes_to_job_titles",
    "apply_imputation",
    "get_imputation_summary",
    # Provenance utilities
    "ImputationProvenanceColumns",
    "add_imputation_provenance",
    "create_imputed_attribute_row",
    "get_provenance_column_names",
]
