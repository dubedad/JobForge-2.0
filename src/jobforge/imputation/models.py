"""Pydantic models for NOC resolution and imputation with provenance tracking."""

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


class ResolutionMethodEnum(str, Enum):
    """Resolution method with associated confidence scores.

    Algorithm spec confidence levels:
    - DIRECT_MATCH: L6 Label exact match -> 1.00
    - EXAMPLE_MATCH: L7 Example Title match -> 0.95
    - UG_DOMINANT: Single-label Unit Group -> 0.85
    - LABEL_IMPUTATION: Best-match fuzzy -> 0.60
    - UG_IMPUTATION: Fallback to UG context -> 0.40
    """

    DIRECT_MATCH = "direct_match"
    EXAMPLE_MATCH = "example_match"
    UG_DOMINANT = "ug_dominant"
    LABEL_IMPUTATION = "label_imputation"
    UG_IMPUTATION = "ug_imputation"


class ProvenanceEnum(str, Enum):
    """Provenance tracking for attribute values.

    Indicates how a value was obtained:
    - NATIVE: Value exists at this level in source data
    - INHERITED: Value inherited from parent level
    - IMPUTED: Value generated via external source (O*NET, LLM)
    """

    NATIVE = "native"
    INHERITED = "inherited"
    IMPUTED = "imputed"


class NOCResolutionResult(BaseModel):
    """Result of resolving a job title through the NOC hierarchy.

    Captures which NOC level (L5/L6/L7) provided the match,
    the resolution method used, and full provenance for audit.
    """

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
    )

    noc_level_used: Literal[5, 6, 7] = Field(
        description="NOC hierarchy level that provided the resolution (5=UG, 6=Label, 7=Example)"
    )
    resolution_method: ResolutionMethodEnum = Field(
        description="Algorithm method used to resolve the job title"
    )
    confidence_score: float = Field(
        ge=0.0, le=1.0, description="Confidence score based on resolution method"
    )
    source_identifier: str = Field(
        description="OASIS profile code (e.g., '21231.01') or unit_group_id"
    )
    matched_text: str | None = Field(
        default=None, description="The text that matched (label, example title, or UG title)"
    )
    rationale: str = Field(description="Human-readable explanation of the resolution")
    resolved_at: datetime = Field(
        default_factory=utc_now, description="UTC timestamp of resolution"
    )


class ImputedValue(BaseModel):
    """Single imputed value with full provenance tracking.

    Every imputed attribute value carries its source lineage
    for complete audit trail through the hierarchy.
    """

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
    )

    value: str = Field(description="The imputed value")
    source_level: Literal[5, 6, 7] = Field(
        description="NOC hierarchy level that provided the value"
    )
    source_identifier: str = Field(
        description="OASIS profile code or unit_group_id of the source"
    )
    provenance: ProvenanceEnum = Field(
        description="How this value was obtained (native, inherited, imputed)"
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence score for this imputed value"
    )
    imputed_at: datetime = Field(
        default_factory=utc_now, description="UTC timestamp of imputation"
    )
