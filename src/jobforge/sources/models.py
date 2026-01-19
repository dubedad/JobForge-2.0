"""Pydantic models for source metadata management."""

from typing import Optional

from pydantic import BaseModel, Field


class BilingualName(BaseModel):
    """Bilingual name for Canadian government sources."""

    en: str
    fr: str


class SchemaMetadata(BaseModel):
    """Schema classification metadata per prototype pattern."""

    source: str = Field(description="Source system: noc, oasis, cops, gc")
    data_type: str = Field(description="Data type: QL (qualitative), QN (quantitative)")
    subtype: Optional[str] = Field(default=None, description="Subtype: OA, NE, RF, 00")
    provides_categories: list[str] = Field(default_factory=list)


class BusinessMetadata(BaseModel):
    """Business context for a source."""

    business_purpose: str
    data_owner: str
    authority_level: str = Field(default="authoritative")


class SourceMetadata(BaseModel):
    """Complete metadata for a data source."""

    source_id: str = Field(description="Unique source identifier")
    name: BilingualName
    source_type: str = Field(description="Source type: open_data, local, api")
    url: Optional[str] = Field(default=None)
    schema_metadata: SchemaMetadata
    business_metadata: BusinessMetadata
    bronze_path: Optional[str] = Field(default=None)
