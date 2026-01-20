"""Pydantic models for description generation with provenance tracking.

This module defines the data models for description generation including
source types, provenance tracking, and generated description output.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from jobforge.external.models import SourcePrecedence


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


class DescriptionSource(str, Enum):
    """Source types for description generation.

    Indicates where a description came from for provenance tracking.

    - AUTHORITATIVE: Direct NOC lead statement (Canadian authoritative source)
    - ONET: O*NET occupation description (future work)
    - LLM: GPT-synthesized description with NOC boundary words
    """

    AUTHORITATIVE = "authoritative"
    ONET = "onet"
    LLM = "llm"


class DescriptionProvenance(BaseModel):
    """Provenance tracking for a generated description.

    Captures full lineage for auditing: source type, confidence,
    timestamp, and context used for generation.

    Attributes:
        source_type: Where the description came from.
        confidence: Confidence score (0.0-1.0) in the description.
        timestamp: When the description was generated/retrieved.
        model_version: For LLM sources, the model used (e.g., "gpt-4o-2024-08-06").
        input_context: Boundary words or prompts used for generation.
        resolution_method: How the entity was resolved (e.g., "DIRECT_MATCH").
        matched_text: What text was matched against (for L6/L7 matches).
    """

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
    )

    source_type: DescriptionSource
    confidence: float = Field(ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=utc_now)
    model_version: str | None = None
    input_context: str | None = None
    resolution_method: str | None = None
    matched_text: str | None = None

    @property
    def precedence(self) -> SourcePrecedence:
        """Get source precedence for conflict resolution.

        Maps description source type to SourcePrecedence value for
        determining which description wins when multiple exist.

        Returns:
            SourcePrecedence enum value (AUTHORITATIVE=3, ONET=2, LLM=1)
        """
        mapping = {
            DescriptionSource.AUTHORITATIVE: SourcePrecedence.AUTHORITATIVE,
            DescriptionSource.ONET: SourcePrecedence.ONET,
            DescriptionSource.LLM: SourcePrecedence.LLM,
        }
        return mapping[self.source_type]


class GeneratedDescription(BaseModel):
    """A generated description for a job architecture entity.

    Represents a description for job titles, families, or functions
    with full provenance tracking for auditability.

    Attributes:
        entity_type: Type of entity ("title", "family", "function").
        entity_id: Unique identifier (jt_id for titles, name for family/function).
        entity_name: Human-readable name for the entity.
        description: The generated/retrieved description text.
        provenance: Full provenance information for the description.
    """

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
    )

    entity_type: Literal["title", "family", "function"]
    entity_id: str
    entity_name: str
    description: str
    provenance: DescriptionProvenance
