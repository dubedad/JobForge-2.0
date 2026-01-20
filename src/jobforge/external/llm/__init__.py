"""LLM-powered attribute imputation package.

This package provides LLM integration for imputing missing attribute values
when hierarchical inheritance and O*NET fallback have no data.

Per CONTEXT.md:
- Accept all LLM answers regardless of confidence
- Store confidence + rationale for downstream filtering
- Mark source_type='LLM' for provenance tracking
"""

from jobforge.external.llm.client import LLM_IMPUTATION_MODEL, LLMClient
from jobforge.external.llm.prompts import IMPUTATION_SYSTEM_PROMPT, build_imputation_prompt
from jobforge.external.llm.service import (
    LLM_SOURCE_PRECEDENCE,
    AttributeImputationService,
    impute_missing_attributes,
)

__all__ = [
    "LLMClient",
    "LLM_IMPUTATION_MODEL",
    "AttributeImputationService",
    "impute_missing_attributes",
    "IMPUTATION_SYSTEM_PROMPT",
    "build_imputation_prompt",
    "LLM_SOURCE_PRECEDENCE",
]
