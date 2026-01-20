"""Pydantic models for external data sources with provenance tracking.

This module defines the data models for external integrations including
O*NET attributes and source precedence for provenance tracking.
"""

from datetime import datetime, timezone
from enum import IntEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


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
