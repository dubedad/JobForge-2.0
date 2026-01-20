"""Attribute imputation service using LLM.

Provides the main service class for imputing missing attribute values
using OpenAI's GPT models with structured outputs.

Per CONTEXT.md:
- Accept ALL answers regardless of confidence
- Store confidence + rationale for downstream filtering
- Mark source_type='LLM' for provenance
"""

from datetime import datetime, timezone

from jobforge.external.llm.client import LLMClient
from jobforge.external.llm.prompts import IMPUTATION_SYSTEM_PROMPT, build_imputation_prompt
from jobforge.external.models import ImputationResponse, LLMImputedAttribute

# LLM has lowest precedence in the source hierarchy
LLM_SOURCE_PRECEDENCE = 1


class AttributeImputationService:
    """Service for imputing missing attributes using LLM.

    Orchestrates the imputation process by building prompts with job context,
    calling the LLM, and converting responses to LLMImputedAttribute models
    with full provenance tracking.

    Attributes:
        client: The LLMClient instance to use for API calls.

    Example:
        >>> service = AttributeImputationService()
        >>> results = service.impute_attributes(
        ...     job_title="Data Analyst",
        ...     missing_attributes=["leadership", "communication"],
        ...     job_family="Analytics",
        ... )
    """

    def __init__(self, client: LLMClient | None = None):
        """Initialize the imputation service.

        Args:
            client: LLMClient instance. If not provided, creates a new one.
        """
        self.client = client or LLMClient()

    def impute_attributes(
        self,
        job_title: str,
        missing_attributes: list[str],
        job_family: str | None = None,
        job_function: str | None = None,
        unit_group: str | None = None,
        known_attributes: dict[str, str] | None = None,
    ) -> list[LLMImputedAttribute]:
        """Impute missing attributes using LLM.

        Per CONTEXT.md:
        - Accept ALL answers regardless of confidence
        - Store confidence + rationale for downstream filtering
        - Mark source_type='LLM' for provenance

        Args:
            job_title: The job title being processed.
            missing_attributes: List of attribute names that need imputation.
            job_family: Job family context (optional).
            job_function: Job function context (optional).
            unit_group: NOC Unit Group code or title (optional).
            known_attributes: Dict of already-known attribute name -> value pairs.

        Returns:
            List of LLMImputedAttribute with full provenance.
            Empty list if missing_attributes is empty.

        Raises:
            ValueError: If LLM client has no API key configured.
            openai.APIError: If the API call fails.
        """
        if not missing_attributes:
            return []

        prompt = build_imputation_prompt(
            job_title=job_title,
            job_family=job_family,
            job_function=job_function,
            unit_group=unit_group,
            known_attributes=known_attributes or {},
            missing_attributes=missing_attributes,
        )

        messages = [
            {"role": "system", "content": IMPUTATION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        response = self.client.parse(
            messages=messages,
            response_format=ImputationResponse,
        )

        # Convert to LLMImputedAttribute with full provenance
        now = datetime.now(timezone.utc)
        return [
            LLMImputedAttribute(
                attribute_name=imp.attribute_name,
                value=imp.value,
                confidence=imp.confidence,
                rationale=imp.rationale,
                model_used=self.client.model,
                imputed_at=now,
            )
            for imp in response.imputations
        ]


def impute_missing_attributes(
    job_title: str,
    missing_attributes: list[str],
    **kwargs,
) -> list[LLMImputedAttribute]:
    """Convenience function for simple imputation usage.

    Creates a one-off AttributeImputationService and imputes attributes.

    Args:
        job_title: The job title being processed.
        missing_attributes: List of attribute names that need imputation.
        **kwargs: Additional arguments passed to impute_attributes()
            (job_family, job_function, unit_group, known_attributes).

    Returns:
        List of LLMImputedAttribute with full provenance.

    Example:
        >>> results = impute_missing_attributes(
        ...     job_title="Data Analyst",
        ...     missing_attributes=["leadership"],
        ...     job_family="Analytics",
        ... )
    """
    service = AttributeImputationService()
    return service.impute_attributes(job_title, missing_attributes, **kwargs)
