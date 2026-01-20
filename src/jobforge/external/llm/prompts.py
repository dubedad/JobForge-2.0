"""Prompt templates for LLM attribute imputation.

Provides system prompts and prompt builders for attribute imputation
using OpenAI's GPT models.
"""

IMPUTATION_SYSTEM_PROMPT = """You are an expert workforce analyst helping to complete occupational attribute data.

You will be given context about a job title including its job family, job function, and any known attributes.
Your task is to impute values for missing attributes based on the occupational context.

Guidelines:
- Use the job title, family, and function to understand the occupational domain
- Reference known attributes to maintain consistency
- Provide a confidence score (0.0-1.0) reflecting your certainty
- Include a brief rationale explaining your reasoning
- If highly uncertain, still provide your best estimate with low confidence

Your responses will be used to supplement authoritative data, so accuracy is important."""


def build_imputation_prompt(
    job_title: str,
    job_family: str | None,
    job_function: str | None,
    unit_group: str | None,
    known_attributes: dict[str, str],
    missing_attributes: list[str],
) -> str:
    """Build the user prompt for attribute imputation.

    Constructs a prompt with all available context about the job
    and the list of attributes that need to be imputed.

    Args:
        job_title: The job title being processed.
        job_family: Job family context (optional).
        job_function: Job function context (optional).
        unit_group: NOC Unit Group code or title (optional).
        known_attributes: Dict of already-known attribute name -> value pairs.
        missing_attributes: List of attribute names that need imputation.

    Returns:
        Formatted prompt string for the LLM.

    Example:
        >>> prompt = build_imputation_prompt(
        ...     job_title="Data Analyst",
        ...     job_family="Analytics",
        ...     job_function="Business Intelligence",
        ...     unit_group="21211",
        ...     known_attributes={"skill1": "Python"},
        ...     missing_attributes=["leadership", "communication"],
        ... )
    """
    context_parts = [f"Job Title: {job_title}"]

    if job_family:
        context_parts.append(f"Job Family: {job_family}")
    if job_function:
        context_parts.append(f"Job Function: {job_function}")
    if unit_group:
        context_parts.append(f"NOC Unit Group: {unit_group}")

    context = "\n".join(context_parts)

    if known_attributes:
        known_str = "\n".join(f"- {k}: {v}" for k, v in known_attributes.items())
    else:
        known_str = "None"

    missing_str = ", ".join(missing_attributes)

    return f"""
{context}

Known Attributes:
{known_str}

Please impute values for these missing attributes: {missing_str}

For each attribute, provide:
- The imputed value
- Your confidence (0.0-1.0)
- A brief rationale
"""
