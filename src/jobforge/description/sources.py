"""Source lookup and cascade logic for description generation.

This module provides:
- Cached lead statement loading from element_lead_statement.parquet
- Single OASIS profile code lookup
- Source type determination for cascade logic

The source cascade per CONTEXT.md:
1. If oasis_profile_code exists and has lead statement -> AUTHORITATIVE
2. Otherwise -> LLM (O*NET descriptions are future work)
"""

from functools import lru_cache
from pathlib import Path

import polars as pl

from jobforge.description.models import DescriptionSource
from jobforge.pipeline.config import PipelineConfig


def _get_default_gold_path() -> Path:
    """Get default gold path from PipelineConfig."""
    return PipelineConfig().gold_path()


@lru_cache(maxsize=1)
def load_lead_statements(gold_path: Path) -> dict[str, str]:
    """Load lead statements indexed by oasis_profile_code.

    Reads element_lead_statement.parquet and builds a lookup dict
    mapping OASIS profile codes to their lead statement text.

    Cached for efficiency across multiple lookups within a session.

    Args:
        gold_path: Path to gold layer directory containing
            element_lead_statement.parquet.

    Returns:
        Dict mapping oasis_profile_code -> lead statement text.
        Empty dict if file doesn't exist.

    Example:
        >>> from jobforge.pipeline.config import PipelineConfig
        >>> lead_statements = load_lead_statements(PipelineConfig().gold_path())
        >>> print(len(lead_statements))  # ~900
        >>> print(lead_statements.get("21231.00"))  # Lead statement text
    """
    lead_statement_path = gold_path / "element_lead_statement.parquet"
    if not lead_statement_path.exists():
        return {}

    df = pl.scan_parquet(lead_statement_path).collect()

    return {
        row["oasis_profile_code"]: row["Lead statement"]
        for row in df.iter_rows(named=True)
    }


def get_lead_statement_for_oasis(
    oasis_profile_code: str,
    gold_path: Path | None = None,
) -> str | None:
    """Get lead statement text for an OASIS profile code.

    Looks up the authoritative NOC lead statement for a given
    OASIS profile code. Returns None if not found.

    Args:
        oasis_profile_code: The OASIS profile code (e.g., "21231.00").
        gold_path: Path to gold layer. Defaults to PipelineConfig().gold_path().

    Returns:
        Lead statement text if found, None otherwise.

    Example:
        >>> text = get_lead_statement_for_oasis("21231.00")
        >>> if text:
        ...     print(f"Found: {text[:50]}...")
    """
    if gold_path is None:
        gold_path = _get_default_gold_path()

    lead_statements = load_lead_statements(gold_path)
    return lead_statements.get(oasis_profile_code)


def determine_source_type(
    oasis_profile_code: str | None,
    has_lead_statement: bool,
) -> DescriptionSource:
    """Determine which source should provide the description.

    Implements the source cascade logic per CONTEXT.md:
    1. If oasis_profile_code exists AND has lead statement -> AUTHORITATIVE
    2. Otherwise -> LLM (O*NET descriptions are future work)

    This function is pure logic - it doesn't do lookups. The caller
    should check has_lead_statement before calling.

    Args:
        oasis_profile_code: Resolved OASIS code from resolution (can be None).
        has_lead_statement: Whether authoritative lead statement was found.

    Returns:
        DescriptionSource indicating which source to use.

    Example:
        >>> # Job title resolved to OASIS code with lead statement
        >>> source = determine_source_type("21231.00", True)
        >>> assert source == DescriptionSource.AUTHORITATIVE

        >>> # Job title with no lead statement
        >>> source = determine_source_type("21231.00", False)
        >>> assert source == DescriptionSource.LLM

        >>> # Unmapped job title
        >>> source = determine_source_type(None, False)
        >>> assert source == DescriptionSource.LLM
    """
    if oasis_profile_code is not None and has_lead_statement:
        return DescriptionSource.AUTHORITATIVE
    return DescriptionSource.LLM


def clear_lead_statement_cache() -> None:
    """Clear the lead statement cache.

    Call this when source data changes to force re-loading of lead statements.
    Useful for testing and when gold layer is updated mid-session.
    """
    load_lead_statements.cache_clear()
