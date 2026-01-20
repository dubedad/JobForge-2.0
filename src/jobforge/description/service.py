"""Description generation service with source cascade and provenance.

This module provides the main service class that orchestrates description
generation for job titles, families, and functions with full provenance tracking.

Source cascade per CONTEXT.md:
1. Resolve job title to OASIS profile using existing resolution
2. If resolved, look up authoritative lead statement
3. If no lead statement, generate with LLM using NOC context

Per CONTEXT.md:
- NOC vocabulary acts as "boundary words" for semantic anchoring
- Use NOC title + Unit Group description as context constraints
- Formal, third-person voice matching NOC style
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

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
from jobforge.description.sources import (
    determine_source_type,
    get_lead_statement_for_oasis,
)
from jobforge.external.llm import LLMClient
from jobforge.imputation.resolution import build_resolution_context, resolve_job_title
from jobforge.pipeline.config import PipelineConfig


class DescriptionGenerationService:
    """Service for generating descriptions with source cascade and provenance.

    Orchestrates the description generation process:
    1. Resolve job title to OASIS profile code (for titles)
    2. Check for authoritative lead statement
    3. If no authoritative source, generate with LLM
    4. Return description with full provenance

    Attributes:
        llm_client: LLMClient instance for LLM fallback.
        gold_path: Path to gold layer data.

    Example:
        >>> service = DescriptionGenerationService()
        >>> result = service.generate_title_description(
        ...     job_title="Data Analyst",
        ...     unit_group_id="21211",
        ... )
        >>> print(f"{result.description} (source: {result.provenance.source_type})")
    """

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        gold_path: Path | None = None,
    ):
        """Initialize the service.

        Args:
            llm_client: LLMClient instance. If not provided, creates a new one.
            gold_path: Path to gold layer directory.
                Defaults to PipelineConfig().gold_path().
        """
        self.llm_client = llm_client or LLMClient()
        self.gold_path = gold_path or PipelineConfig().gold_path()

    def generate_title_description(
        self,
        job_title: str,
        unit_group_id: str,
        job_family: str | None = None,
        job_function: str | None = None,
    ) -> GeneratedDescription:
        """Generate description for a job title.

        Source cascade per CONTEXT.md:
        1. Resolve job title to OASIS profile using existing resolution
        2. If resolved, look up authoritative lead statement
        3. If no lead statement, generate with LLM using NOC context

        Args:
            job_title: The job title to describe.
            unit_group_id: The 5-digit NOC Unit Group ID.
            job_family: Optional job family context.
            job_function: Optional job function context.

        Returns:
            GeneratedDescription with full provenance.
        """
        now = datetime.now(timezone.utc)

        # Step 1: Resolve job title to OASIS profile
        resolution = resolve_job_title(job_title, unit_group_id, self.gold_path)

        # Step 2: Check for authoritative lead statement
        oasis_code = resolution.source_identifier if resolution else None
        lead_statement = None
        if oasis_code:
            lead_statement = get_lead_statement_for_oasis(oasis_code, self.gold_path)

        # Determine source type based on cascade
        source_type = determine_source_type(oasis_code, lead_statement is not None)

        if source_type == DescriptionSource.AUTHORITATIVE and lead_statement:
            # Return authoritative description
            provenance = DescriptionProvenance(
                source_type=DescriptionSource.AUTHORITATIVE,
                confidence=resolution.confidence_score if resolution else 1.0,
                timestamp=now,
                resolution_method=resolution.resolution_method.value if resolution else None,
                matched_text=resolution.matched_text if resolution else None,
            )
            return GeneratedDescription(
                entity_type="title",
                entity_id=job_title,  # Use job_title as ID for simplicity
                entity_name=job_title,
                description=lead_statement,
                provenance=provenance,
            )

        # Step 3: Fall back to LLM with NOC boundary words
        return self._generate_title_with_llm(
            job_title=job_title,
            unit_group_id=unit_group_id,
            job_family=job_family,
            job_function=job_function,
            resolution=resolution,
            timestamp=now,
        )

    def _generate_title_with_llm(
        self,
        job_title: str,
        unit_group_id: str,
        job_family: str | None,
        job_function: str | None,
        resolution,  # NOCResolutionResult | None
        timestamp: datetime,
    ) -> GeneratedDescription:
        """Generate title description using LLM with NOC context.

        Args:
            job_title: The job title to describe.
            unit_group_id: The 5-digit NOC Unit Group ID.
            job_family: Optional job family context.
            job_function: Optional job function context.
            resolution: Resolution result (if any).
            timestamp: Timestamp for provenance.

        Returns:
            GeneratedDescription with LLM provenance.
        """
        # Build context from resolution context
        context = build_resolution_context(unit_group_id, self.gold_path)

        # Extract NOC boundary words
        unit_group_title = context.unit_group_title if context else None
        unit_group_definition = context.unit_group_definition if context else None
        labels = [label.label for label in context.labels] if context else None

        # Build prompt with boundary words
        prompt = build_title_description_prompt(
            job_title=job_title,
            job_family=job_family,
            job_function=job_function,
            unit_group_title=unit_group_title,
            unit_group_definition=unit_group_definition,
            labels=labels,
        )

        # Call LLM
        messages = [
            {"role": "system", "content": DESCRIPTION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        response = self.llm_client.parse(
            messages=messages,
            response_format=DescriptionResponse,
        )

        # Build provenance
        provenance = DescriptionProvenance(
            source_type=DescriptionSource.LLM,
            confidence=response.confidence,
            timestamp=timestamp,
            model_version=self.llm_client.model,
            input_context=response.context_used,
            resolution_method=resolution.resolution_method.value if resolution else None,
            matched_text=resolution.matched_text if resolution else None,
        )

        return GeneratedDescription(
            entity_type="title",
            entity_id=job_title,
            entity_name=job_title,
            description=response.description,
            provenance=provenance,
        )

    def generate_family_description(
        self,
        family_name: str,
        member_titles: list[str] | None = None,
    ) -> GeneratedDescription:
        """Generate description for a job family.

        Per CONTEXT.md, families are at L5 level. Uses LLM with
        member job titles as context since there's no direct
        authoritative source for family descriptions.

        Args:
            family_name: Name of the job family.
            member_titles: Sample job titles in this family.

        Returns:
            GeneratedDescription with LLM source provenance.
        """
        return self._generate_aggregate_description(
            entity_name=family_name,
            entity_type="family",
            member_titles=member_titles or [],
        )

    def generate_function_description(
        self,
        function_name: str,
        member_titles: list[str] | None = None,
    ) -> GeneratedDescription:
        """Generate description for a job function.

        Per CONTEXT.md, functions are at L4 level. Uses LLM with
        member job titles as context.

        Args:
            function_name: Name of the job function.
            member_titles: Sample job titles in this function.

        Returns:
            GeneratedDescription with LLM source provenance.
        """
        return self._generate_aggregate_description(
            entity_name=function_name,
            entity_type="function",
            member_titles=member_titles or [],
        )

    def _generate_aggregate_description(
        self,
        entity_name: str,
        entity_type: Literal["family", "function"],
        member_titles: list[str],
    ) -> GeneratedDescription:
        """Generate description for a family or function using LLM.

        Args:
            entity_name: Name of the entity.
            entity_type: "family" or "function".
            member_titles: Sample job titles.

        Returns:
            GeneratedDescription with LLM provenance.
        """
        now = datetime.now(timezone.utc)

        # Build prompt
        prompt = build_aggregate_description_prompt(
            entity_name=entity_name,
            entity_type=entity_type,
            member_titles=member_titles,
            noc_context=None,  # Could be enhanced with NOC context in future
        )

        # Call LLM
        messages = [
            {"role": "system", "content": DESCRIPTION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        response = self.llm_client.parse(
            messages=messages,
            response_format=DescriptionResponse,
        )

        # Build provenance
        provenance = DescriptionProvenance(
            source_type=DescriptionSource.LLM,
            confidence=response.confidence,
            timestamp=now,
            model_version=self.llm_client.model,
            input_context=response.context_used,
        )

        return GeneratedDescription(
            entity_type=entity_type,
            entity_id=entity_name,
            entity_name=entity_name,
            description=response.description,
            provenance=provenance,
        )


def generate_description(
    entity_type: Literal["title", "family", "function"],
    entity_name: str,
    **kwargs,
) -> GeneratedDescription:
    """Convenience function for single description generation.

    Creates a one-off DescriptionGenerationService instance and
    generates a description for the specified entity.

    Args:
        entity_type: Type of entity ("title", "family", "function").
        entity_name: Name of the entity to describe.
        **kwargs: Additional arguments passed to the appropriate method:
            - For "title": unit_group_id (required), job_family, job_function
            - For "family": member_titles
            - For "function": member_titles

    Returns:
        GeneratedDescription with full provenance.

    Raises:
        ValueError: If entity_type is "title" but unit_group_id not provided.

    Example:
        >>> # Generate title description
        >>> desc = generate_description(
        ...     entity_type="title",
        ...     entity_name="Data Analyst",
        ...     unit_group_id="21211",
        ...     job_family="Analytics",
        ... )

        >>> # Generate family description
        >>> desc = generate_description(
        ...     entity_type="family",
        ...     entity_name="Analytics & Insights",
        ...     member_titles=["Data Analyst", "BI Developer"],
        ... )
    """
    service = DescriptionGenerationService()

    if entity_type == "title":
        unit_group_id = kwargs.get("unit_group_id")
        if not unit_group_id:
            raise ValueError("unit_group_id is required for title descriptions")
        return service.generate_title_description(
            job_title=entity_name,
            unit_group_id=unit_group_id,
            job_family=kwargs.get("job_family"),
            job_function=kwargs.get("job_function"),
        )
    elif entity_type == "family":
        return service.generate_family_description(
            family_name=entity_name,
            member_titles=kwargs.get("member_titles"),
        )
    elif entity_type == "function":
        return service.generate_function_description(
            function_name=entity_name,
            member_titles=kwargs.get("member_titles"),
        )
    else:
        raise ValueError(f"Unknown entity_type: {entity_type}")
