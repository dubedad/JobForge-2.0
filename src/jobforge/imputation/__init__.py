"""Imputation package for NOC resolution and attribute inheritance.

This package provides:
- NOC resolution service for mapping job titles to NOC hierarchy levels
- Pydantic models for resolution results and imputed values
- Provenance tracking for audit trails

Example usage:
    from jobforge.imputation import resolve_job_title, NOCResolutionResult

    result = resolve_job_title("Software Engineer", "21231")
    print(f"Resolved at L{result.noc_level_used} with {result.confidence_score} confidence")
"""

from jobforge.imputation.models import (
    ImputedValue,
    NOCResolutionResult,
    ProvenanceEnum,
    ResolutionMethodEnum,
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
]
