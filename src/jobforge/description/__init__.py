"""Description generation package for job architecture entities.

This package provides:
- Description source types (AUTHORITATIVE, ONET, LLM)
- Provenance tracking models for auditability
- Generated description models for titles, families, and functions
- Source cascade logic for determining description source

Example usage:
    from jobforge.description import (
        DescriptionSource,
        DescriptionProvenance,
        GeneratedDescription,
    )
    from datetime import datetime, timezone

    # Create provenance for an authoritative description
    provenance = DescriptionProvenance(
        source_type=DescriptionSource.AUTHORITATIVE,
        confidence=1.0,
        timestamp=datetime.now(timezone.utc),
        resolution_method="DIRECT_MATCH",
    )

    # Create description with provenance
    desc = GeneratedDescription(
        entity_type="title",
        entity_id="123",
        entity_name="Data Analyst",
        description="Data analysts collect, process, and analyze data...",
        provenance=provenance,
    )
"""

from jobforge.description.models import (
    DescriptionProvenance,
    DescriptionSource,
    GeneratedDescription,
)

__all__ = [
    # Models
    "DescriptionSource",
    "DescriptionProvenance",
    "GeneratedDescription",
]
