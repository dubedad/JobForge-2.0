"""Pydantic models for external data sources with provenance tracking.

This module defines the data models for external integrations including
O*NET attributes, LLM imputation responses, and source precedence for provenance tracking.
"""

from datetime import datetime, timezone
from enum import IntEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


# =============================================================================
# LLM Imputation Models
# =============================================================================


class ImputedAttributeValue(BaseModel):
    """Single imputed attribute from LLM with confidence and rationale.

    This is the structure returned by the LLM for each requested attribute.
    Used as part of ImputationResponse for Structured Outputs.
    """

    attribute_name: str = Field(description="Name of the attribute being imputed")
    value: str = Field(description="The imputed attribute value")
    confidence: float = Field(
        ge=0.0, le=1.0, description="LLM's confidence in this imputation (0.0-1.0)"
    )
    rationale: str = Field(description="Explanation for the imputation")


class ImputationResponse(BaseModel):
    """LLM response for attribute imputation batch.

    This is the top-level response format for Structured Outputs.
    Contains all requested imputations plus context used.
    """

    imputations: list[ImputedAttributeValue] = Field(
        description="List of imputed attribute values"
    )
    context_used: str = Field(
        description="Summary of context that influenced the imputations"
    )


class LLMImputedAttribute(BaseModel):
    """Imputed attribute with full provenance for storage.

    Extended version of ImputedAttributeValue with provenance fields
    for tracking the source and timestamp of imputation.

    Attributes:
        attribute_name: Name of the imputed attribute.
        value: The imputed value.
        confidence: LLM's confidence (0.0-1.0).
        rationale: Explanation for the imputation.
        source_type: Always "LLM" for provenance tracking.
        model_used: The LLM model that generated this (e.g., "gpt-4o-2024-08-06").
        imputed_at: UTC timestamp when imputation occurred.
    """

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
    )

    attribute_name: str = Field(description="Name of the imputed attribute")
    value: str = Field(description="The imputed attribute value")
    confidence: float = Field(
        ge=0.0, le=1.0, description="LLM's confidence in this imputation (0.0-1.0)"
    )
    rationale: str = Field(description="Explanation for the imputation")
    source_type: Literal["LLM"] = Field(
        default="LLM", description="Source type for provenance tracking"
    )
    model_used: str = Field(description="LLM model that generated this imputation")
    imputed_at: datetime = Field(
        default_factory=utc_now, description="UTC timestamp when imputation occurred"
    )


class SourcePrecedence(IntEnum):
    """Source precedence for attribute values.

    Fixed hierarchy where higher values override lower values.
    Used for conflict resolution when multiple sources provide the same attribute.

    - LLM (1): Lowest precedence - AI-imputed values
    - ONET (2): Medium precedence - US occupational data
    - AUTHORITATIVE (3): Highest precedence - Canadian authoritative sources
    """

    LLM = 1
    ONET = 2
    AUTHORITATIVE = 3


class ONetAttribute(BaseModel):
    """Single attribute from O*NET with full provenance.

    Represents skills, abilities, or knowledge items from O*NET
    mapped to a Canadian NOC code via the NOC-SOC crosswalk.
    """

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
    )

    element_id: str = Field(
        description="O*NET element identifier (e.g., '2.A.1.a' for Reading Comprehension)"
    )
    name: str = Field(description="Human-readable attribute name")
    description: str = Field(description="Detailed description of the attribute")
    importance_score: float = Field(
        ge=0.0, le=100.0, description="O*NET importance score (0-100 scale)"
    )
    level_score: float | None = Field(
        default=None, ge=0.0, le=100.0, description="O*NET level score (0-100 scale)"
    )
    source_soc: str = Field(description="O*NET SOC code that provided this attribute")
    source_noc: str = Field(description="Canadian NOC code mapped via crosswalk")
    source_type: Literal["ONET"] = Field(
        default="ONET", description="Source type for provenance tracking"
    )
    confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Confidence score for WiQ integration"
    )
    fetched_at: datetime = Field(
        default_factory=utc_now, description="UTC timestamp when attribute was fetched"
    )


class ONetAttributeSet(BaseModel):
    """Collection of O*NET attributes for a single SOC code.

    Groups skills, abilities, and knowledge for one occupation,
    with provenance tracking for the source SOC code.
    """

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
    )

    soc_code: str = Field(description="O*NET SOC code (e.g., '15-1252.00')")
    soc_title: str = Field(default="", description="O*NET occupation title")
    skills: list[ONetAttribute] = Field(default_factory=list, description="Skill attributes")
    abilities: list[ONetAttribute] = Field(default_factory=list, description="Ability attributes")
    knowledge: list[ONetAttribute] = Field(
        default_factory=list, description="Knowledge attributes"
    )
    source_type: Literal["ONET"] = Field(
        default="ONET", description="Source type for provenance tracking"
    )
    fetched_at: datetime = Field(
        default_factory=utc_now, description="UTC timestamp when attributes were fetched"
    )

    @property
    def all_attributes(self) -> list[ONetAttribute]:
        """Get all attributes combined."""
        return self.skills + self.abilities + self.knowledge

    @property
    def attribute_count(self) -> int:
        """Get total number of attributes."""
        return len(self.skills) + len(self.abilities) + len(self.knowledge)
