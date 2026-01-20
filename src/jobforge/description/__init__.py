"""Description generation package for job architecture entities.

This package provides:
- Description source types (AUTHORITATIVE, ONET, LLM)
- Provenance tracking models for auditability
- Generated description models for titles, families, and functions
- Source cascade logic for determining description source
- DescriptionGenerationService for orchestrating generation with provenance

Example usage:
    from jobforge.description import (
        DescriptionSource,
        DescriptionProvenance,
        GeneratedDescription,
        DescriptionGenerationService,
    )

    # Create service and generate description
    service = DescriptionGenerationService()
    result = service.generate_title_description(
        job_title="Data Analyst",
        unit_group_id="21211",
    )
    print(f"{result.description} (source: {result.provenance.source_type})")
"""

from jobforge.description.models import (
    DescriptionProvenance,
    DescriptionSource,
    GeneratedDescription,
)
from jobforge.description.prompts import (
    DESCRIPTION_SYSTEM_PROMPT,
    DescriptionResponse,
    build_aggregate_description_prompt,
    build_title_description_prompt,
)
from jobforge.description.service import (
    DescriptionGenerationService,
    generate_description,
)
from jobforge.description.sources import (
    clear_lead_statement_cache,
    determine_source_type,
    get_lead_statement_for_oasis,
    load_lead_statements,
)

__all__ = [
    # Models
    "DescriptionSource",
    "DescriptionProvenance",
    "GeneratedDescription",
    # Prompts
    "DESCRIPTION_SYSTEM_PROMPT",
    "DescriptionResponse",
    "build_title_description_prompt",
    "build_aggregate_description_prompt",
    # Service
    "DescriptionGenerationService",
    "generate_description",
    # Source functions
    "load_lead_statements",
    "get_lead_statement_for_oasis",
    "determine_source_type",
    "clear_lead_statement_cache",
]
