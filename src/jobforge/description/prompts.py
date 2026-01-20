"""Prompt templates for NOC-style description generation.

Provides system prompts and prompt builders for generating occupational
descriptions using OpenAI's GPT models with structured outputs.

Per CONTEXT.md:
- Use NOC vocabulary as "boundary words" to keep descriptions semantically
  tethered to Canadian occupational classification
- Formal, third-person voice matching NOC style
- Descriptions supplement authoritative Canadian data where none exists
"""

from typing import Literal

from pydantic import BaseModel, Field


DESCRIPTION_SYSTEM_PROMPT = """You are generating occupational descriptions for a Canadian workforce classification system.

Guidelines:
- Use formal, third-person voice matching NOC (National Occupational Classification) style
- Start descriptions with the occupation/entity name (e.g., "Software engineers design...")
- Focus on typical duties, responsibilities, and characteristics
- Keep descriptions between 2-4 sentences
- Use NOC-aligned terminology provided in the context
- Do NOT use "you", "your", or "this role involves" phrasing

Your descriptions will supplement authoritative Canadian occupational data where none exists."""


class DescriptionResponse(BaseModel):
    """LLM response for description generation.

    Used with OpenAI Structured Outputs to ensure type-safe
    parsing of generated descriptions.
    """

    description: str = Field(
        description="Generated occupational description in NOC style"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="LLM's confidence in this description (0.0-1.0)",
    )
    context_used: str = Field(
        description="Summary of NOC context that influenced the description"
    )


def build_title_description_prompt(
    job_title: str,
    job_family: str | None,
    job_function: str | None,
    unit_group_title: str | None,
    unit_group_definition: str | None,
    labels: list[str] | None = None,
) -> str:
    """Build prompt for job title description.

    Includes NOC context as "boundary words" per CONTEXT.md. The NOC
    vocabulary acts as semantic anchors keeping generated content
    aligned with Canadian occupational classification.

    Args:
        job_title: The job title to describe.
        job_family: Job family context (L5 level).
        job_function: Job function context (L4 level).
        unit_group_title: NOC Unit Group title (L5 context).
        unit_group_definition: NOC Unit Group definition.
        labels: List of L6 labels in the Unit Group (boundary words).

    Returns:
        Formatted prompt string for the LLM.

    Example:
        >>> prompt = build_title_description_prompt(
        ...     job_title="Data Analyst",
        ...     job_family="Analytics",
        ...     job_function="IT",
        ...     unit_group_title="Data scientists",
        ...     unit_group_definition="Data scientists develop...",
        ...     labels=["Data scientists", "Data analysts"],
        ... )
    """
    parts = [f"Generate an occupational description for: {job_title}"]

    # Build context section
    context_parts = []

    if job_function:
        context_parts.append(f"Job Function: {job_function}")
    if job_family:
        context_parts.append(f"Job Family: {job_family}")

    # NOC boundary words (most important context)
    if unit_group_title:
        context_parts.append(f"NOC Unit Group: {unit_group_title}")
    if unit_group_definition:
        context_parts.append(f"Unit Group Definition: {unit_group_definition}")
    if labels:
        labels_str = ", ".join(labels)
        context_parts.append(f"Related Labels (NOC vocabulary): {labels_str}")

    if context_parts:
        parts.append("\nContext:")
        parts.extend(f"- {cp}" for cp in context_parts)

    parts.append(
        "\nGenerate a 2-4 sentence description in formal NOC style, "
        "starting with the job title. Focus on typical duties and responsibilities."
    )

    return "\n".join(parts)


def build_aggregate_description_prompt(
    entity_name: str,
    entity_type: Literal["family", "function"],
    member_titles: list[str],
    noc_context: str | None = None,
) -> str:
    """Build prompt for job family or function description.

    Uses member job titles as context for describing the aggregate entity.
    Per CONTEXT.md, families are at L5 level and functions are at L4 level.

    Args:
        entity_name: Name of the family or function.
        entity_type: "family" or "function".
        member_titles: Sample job titles that belong to this entity.
        noc_context: Additional NOC context if available.

    Returns:
        Formatted prompt string for the LLM.

    Example:
        >>> prompt = build_aggregate_description_prompt(
        ...     entity_name="Analytics & Insights",
        ...     entity_type="family",
        ...     member_titles=["Data Analyst", "BI Developer", "Data Scientist"],
        ...     noc_context="Unit Group 21211 - Data scientists",
        ... )
    """
    entity_label = "job family" if entity_type == "family" else "job function"

    parts = [f"Generate an occupational description for the {entity_label}: {entity_name}"]

    # Context section
    parts.append("\nContext:")

    if member_titles:
        # Limit to reasonable number of example titles
        sample_titles = member_titles[:10] if len(member_titles) > 10 else member_titles
        titles_str = ", ".join(sample_titles)
        parts.append(f"- Sample job titles in this {entity_label}: {titles_str}")
        if len(member_titles) > 10:
            parts.append(f"  (showing 10 of {len(member_titles)} titles)")
    else:
        parts.append(f"- No sample job titles provided for this {entity_label}")

    if noc_context:
        parts.append(f"- NOC context: {noc_context}")

    parts.append(
        f"\nGenerate a 2-4 sentence description in formal NOC style that describes "
        f"what this {entity_label} encompasses. Start with the {entity_label} name. "
        f"Focus on the common themes across the member job titles."
    )

    return "\n".join(parts)
