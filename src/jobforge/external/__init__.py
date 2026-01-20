"""External data integration package.

This package provides integrations with external data sources:
- O*NET API for SOC-aligned occupational attributes
- LLM services for attribute imputation
- TBS scraping for occupational group metadata

All external data carries full provenance tracking.
"""

from jobforge.external.models import (
    ImputationResponse,
    ImputedAttributeValue,
    LLMImputedAttribute,
    ONetAttribute,
    ONetAttributeSet,
    SourcePrecedence,
)

__all__ = [
    # O*NET models
    "ONetAttribute",
    "ONetAttributeSet",
    # LLM imputation models
    "ImputedAttributeValue",
    "ImputationResponse",
    "LLMImputedAttribute",
    # Provenance
    "SourcePrecedence",
]
