"""External data integration package.

This package provides integrations with external data sources:
- O*NET API for SOC-aligned occupational attributes
- LLM services for attribute imputation (planned)
- TBS scraping for occupational group metadata (planned)

All external data carries full provenance tracking.
"""

from jobforge.external.models import (
    ONetAttribute,
    ONetAttributeSet,
    SourcePrecedence,
)

__all__ = [
    "ONetAttribute",
    "ONetAttributeSet",
    "SourcePrecedence",
]
