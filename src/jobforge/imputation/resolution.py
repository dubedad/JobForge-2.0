"""NOC resolution service for mapping job titles to NOC hierarchy levels.

This module provides deterministic resolution of job titles through the
NOC L5->L6->L7 hierarchy with confidence scoring and full provenance.

Resolution algorithm (priority order):
1. Single-label UG optimization -> UG_DOMINANT (0.85)
2. Direct L6 Label match -> DIRECT_MATCH (1.00)
3. L7 Example Title match -> EXAMPLE_MATCH (0.95)
4. Fuzzy L6 Label match -> LABEL_IMPUTATION (0.60)
5. Fallback to UG context -> UG_IMPUTATION (0.40)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import polars as pl
from rapidfuzz import fuzz

from jobforge.imputation.models import NOCResolutionResult, ResolutionMethodEnum
from jobforge.pipeline.config import PipelineConfig

# Confidence score constants (from algorithm spec)
CONFIDENCE_DIRECT_MATCH = 1.00
CONFIDENCE_EXAMPLE_MATCH = 0.95
CONFIDENCE_UG_DOMINANT = 0.85
CONFIDENCE_LABEL_IMPUTATION = 0.60
CONFIDENCE_UG_IMPUTATION = 0.40

# Fuzzy matching threshold
FUZZY_GOOD_MATCH_THRESHOLD = 70


@dataclass
class L6Label:
    """Internal representation of an L6 Label from element_labels."""

    oasis_profile_code: str
    unit_group_id: str
    label: str
    lead_statement: str | None = None


@dataclass
class L7ExampleTitle:
    """Internal representation of an L7 Example Title from element_example_titles."""

    element_text: str
    oasis_profile_code: str
    unit_group_id: str


@dataclass
class ResolutionContext:
    """Aggregated context for resolving a job title within a Unit Group.

    Contains all L5/L6/L7 data needed for resolution decisions.
    """

    unit_group_id: str
    unit_group_title: str
    unit_group_definition: str | None
    labels: list[L6Label] = field(default_factory=list)
    example_titles_by_oasis: dict[str, list[L7ExampleTitle]] = field(default_factory=dict)

    @property
    def label_count(self) -> int:
        """Number of L6 labels in this Unit Group."""
        return len(self.labels)

    @property
    def is_single_label(self) -> bool:
        """Whether this Unit Group has only one L6 label."""
        return self.label_count == 1


@dataclass
class BestMatchResult:
    """Result from fuzzy matching against L6 labels."""

    label: L6Label
    similarity_score: float
    matched_via: str  # "direct" or "fuzzy"


def _get_default_gold_path() -> Path:
    """Get default gold path from PipelineConfig."""
    return PipelineConfig().gold_path()


@lru_cache(maxsize=1)
def _build_labels_by_unit_group(gold_path: Path) -> dict[str, list[L6Label]]:
    """Build index of L6 Labels by Unit Group ID.

    Loads element_labels.parquet and groups by unit_group_id.
    Cached for efficiency across multiple resolution calls.

    Args:
        gold_path: Path to gold layer directory.

    Returns:
        Dict mapping unit_group_id to list of L6Label objects.
    """
    labels_path = gold_path / "element_labels.parquet"
    if not labels_path.exists():
        return {}

    df = pl.scan_parquet(labels_path).collect()

    index: dict[str, list[L6Label]] = {}
    for row in df.iter_rows(named=True):
        ug_id = row["unit_group_id"]
        label_obj = L6Label(
            oasis_profile_code=row["oasis_profile_code"],
            unit_group_id=ug_id,
            label=row["Label"],
            lead_statement=None,  # Lead statements are in separate table
        )
        if ug_id not in index:
            index[ug_id] = []
        index[ug_id].append(label_obj)

    return index


@lru_cache(maxsize=1)
def _build_example_titles_by_oasis(gold_path: Path) -> dict[str, list[L7ExampleTitle]]:
    """Build index of L7 Example Titles by OASIS profile code.

    Loads element_example_titles.parquet and groups by oasis_profile_code.
    Cached for efficiency across multiple resolution calls.

    Args:
        gold_path: Path to gold layer directory.

    Returns:
        Dict mapping oasis_profile_code to list of L7ExampleTitle objects.
    """
    titles_path = gold_path / "element_example_titles.parquet"
    if not titles_path.exists():
        return {}

    df = pl.scan_parquet(titles_path).collect()

    index: dict[str, list[L7ExampleTitle]] = {}
    for row in df.iter_rows(named=True):
        oasis_code = row["oasis_profile_code"]
        title_obj = L7ExampleTitle(
            element_text=row["Job title text"],
            oasis_profile_code=oasis_code,
            unit_group_id=row["unit_group_id"],
        )
        if oasis_code not in index:
            index[oasis_code] = []
        index[oasis_code].append(title_obj)

    return index


@lru_cache(maxsize=1)
def _load_noc_structure(gold_path: Path) -> dict[str, dict]:
    """Load NOC structure (unit group titles and definitions) from dim_noc.

    Args:
        gold_path: Path to gold layer directory.

    Returns:
        Dict mapping unit_group_id to dict with class_title and class_definition.
    """
    noc_path = gold_path / "dim_noc.parquet"
    if not noc_path.exists():
        return {}

    df = pl.scan_parquet(noc_path).collect()

    return {
        row["unit_group_id"]: {
            "class_title": row["class_title"],
            "class_definition": row.get("class_definition"),
        }
        for row in df.iter_rows(named=True)
    }


def build_resolution_context(
    unit_group_id: str,
    gold_path: Path | None = None,
) -> ResolutionContext | None:
    """Build resolution context for a Unit Group.

    Combines L5/L6/L7 data into a single context object for resolution.

    Args:
        unit_group_id: The 5-digit Unit Group ID (e.g., "21231").
        gold_path: Path to gold layer directory. Defaults to PipelineConfig().gold_path().

    Returns:
        ResolutionContext with all available data, or None if unit group not found.
    """
    if gold_path is None:
        gold_path = _get_default_gold_path()

    # Load NOC structure (L5)
    noc_structure = _load_noc_structure(gold_path)
    if unit_group_id not in noc_structure:
        return None

    ug_info = noc_structure[unit_group_id]

    # Load L6 labels
    labels_index = _build_labels_by_unit_group(gold_path)
    labels = labels_index.get(unit_group_id, [])

    # Load L7 example titles for each L6 label's OASIS code
    example_titles_index = _build_example_titles_by_oasis(gold_path)
    example_titles_by_oasis: dict[str, list[L7ExampleTitle]] = {}
    for label in labels:
        oasis_code = label.oasis_profile_code
        if oasis_code in example_titles_index:
            example_titles_by_oasis[oasis_code] = example_titles_index[oasis_code]

    return ResolutionContext(
        unit_group_id=unit_group_id,
        unit_group_title=ug_info["class_title"],
        unit_group_definition=ug_info.get("class_definition"),
        labels=labels,
        example_titles_by_oasis=example_titles_by_oasis,
    )


def _find_direct_label_match(
    job_title: str,
    labels: list[L6Label],
) -> L6Label | None:
    """Find exact (case-insensitive) match against L6 labels.

    Args:
        job_title: Job title to match.
        labels: List of L6Label objects to search.

    Returns:
        Matching L6Label or None.
    """
    job_title_lower = job_title.lower().strip()
    for label in labels:
        if label.label.lower().strip() == job_title_lower:
            return label
    return None


def _find_example_title_match(
    job_title: str,
    example_titles_by_oasis: dict[str, list[L7ExampleTitle]],
) -> tuple[L7ExampleTitle, str] | None:
    """Find exact (case-insensitive) match against L7 example titles.

    Args:
        job_title: Job title to match.
        example_titles_by_oasis: Dict mapping OASIS codes to example title lists.

    Returns:
        Tuple of (matching L7ExampleTitle, OASIS code) or None.
    """
    job_title_lower = job_title.lower().strip()
    for oasis_code, titles in example_titles_by_oasis.items():
        for title in titles:
            if title.element_text.lower().strip() == job_title_lower:
                return (title, oasis_code)
    return None


def _find_best_fuzzy_match(
    job_title: str,
    labels: list[L6Label],
) -> BestMatchResult | None:
    """Find best fuzzy match against L6 labels using rapidfuzz.

    Uses WRatio which handles partial matching, token ordering, and
    case insensitivity well for job title matching.

    Args:
        job_title: Job title to match.
        labels: List of L6Label objects to search.

    Returns:
        BestMatchResult with highest scoring label, or None if no labels.
    """
    if not labels:
        return None

    best_score = 0.0
    best_label: L6Label | None = None

    for label in labels:
        score = fuzz.WRatio(job_title, label.label)
        if score > best_score:
            best_score = score
            best_label = label

    if best_label is None:
        return None

    return BestMatchResult(
        label=best_label,
        similarity_score=best_score,
        matched_via="fuzzy",
    )


def resolve_job_title(
    job_title: str,
    unit_group_id: str,
    gold_path: Path | None = None,
) -> NOCResolutionResult | None:
    """Deterministic NOC semantic resolution following strict hierarchy.

    Resolves a job title through the NOC L5->L6->L7 hierarchy to find
    the best match with appropriate confidence scoring.

    Resolution order:
    1. Check if Unit Group has single label -> use UG context (0.85)
    2. Attempt direct L6 Label match -> confidence 1.00
    3. Attempt L7 Example Title match -> confidence 0.95
    4. Best-match label imputation -> confidence 0.60
    5. Fallback to UG context -> confidence 0.40

    Args:
        job_title: The job title to resolve.
        unit_group_id: The 5-digit Unit Group ID (e.g., "21231").
        gold_path: Path to gold layer directory. Defaults to PipelineConfig().gold_path().

    Returns:
        NOCResolutionResult with resolution details, or None if:
        - job_title is empty
        - unit_group_id is not found in NOC structure
    """
    # Validate inputs
    if not job_title or not job_title.strip():
        return None

    if not unit_group_id or not unit_group_id.strip():
        return None

    if gold_path is None:
        gold_path = _get_default_gold_path()

    # Build resolution context
    context = build_resolution_context(unit_group_id, gold_path)
    if context is None:
        return None

    now = datetime.now(timezone.utc)

    # STEP 1: Single-label UG optimization (68% of cases)
    if context.is_single_label:
        return NOCResolutionResult(
            noc_level_used=5,
            resolution_method=ResolutionMethodEnum.UG_DOMINANT,
            confidence_score=CONFIDENCE_UG_DOMINANT,
            source_identifier=context.labels[0].oasis_profile_code,
            matched_text=context.unit_group_title,
            rationale=f"Single-label Unit Group ({context.label_count} label)",
            resolved_at=now,
        )

    # STEP 2: Direct L6 Label match
    direct_match = _find_direct_label_match(job_title, context.labels)
    if direct_match:
        return NOCResolutionResult(
            noc_level_used=6,
            resolution_method=ResolutionMethodEnum.DIRECT_MATCH,
            confidence_score=CONFIDENCE_DIRECT_MATCH,
            source_identifier=direct_match.oasis_profile_code,
            matched_text=direct_match.label,
            rationale=f"Direct match to L6 Label: '{direct_match.label}'",
            resolved_at=now,
        )

    # STEP 3: L7 Example Title match
    example_match = _find_example_title_match(job_title, context.example_titles_by_oasis)
    if example_match:
        title, oasis_code = example_match
        return NOCResolutionResult(
            noc_level_used=7,
            resolution_method=ResolutionMethodEnum.EXAMPLE_MATCH,
            confidence_score=CONFIDENCE_EXAMPLE_MATCH,
            source_identifier=oasis_code,
            matched_text=title.element_text,
            rationale=f"Match to L7 Example Title: '{title.element_text}'",
            resolved_at=now,
        )

    # STEP 4 & 5: Fuzzy matching or fallback
    fuzzy_match = _find_best_fuzzy_match(job_title, context.labels)

    if fuzzy_match and fuzzy_match.similarity_score >= FUZZY_GOOD_MATCH_THRESHOLD:
        # STEP 4: Good fuzzy match -> LABEL_IMPUTATION
        return NOCResolutionResult(
            noc_level_used=6,
            resolution_method=ResolutionMethodEnum.LABEL_IMPUTATION,
            confidence_score=CONFIDENCE_LABEL_IMPUTATION,
            source_identifier=fuzzy_match.label.oasis_profile_code,
            matched_text=fuzzy_match.label.label,
            rationale=(
                f"Fuzzy match to L6 Label: '{fuzzy_match.label.label}' "
                f"(score: {fuzzy_match.similarity_score:.0f})"
            ),
            resolved_at=now,
        )

    # STEP 5: Fallback to UG context
    # Use first label's OASIS code as source identifier
    source_id = context.labels[0].oasis_profile_code if context.labels else context.unit_group_id
    fuzzy_score = fuzzy_match.similarity_score if fuzzy_match else 0
    return NOCResolutionResult(
        noc_level_used=5,
        resolution_method=ResolutionMethodEnum.UG_IMPUTATION,
        confidence_score=CONFIDENCE_UG_IMPUTATION,
        source_identifier=source_id,
        matched_text=context.unit_group_title,
        rationale=(
            f"Fallback to Unit Group context: '{context.unit_group_title}' "
            f"(best fuzzy score: {fuzzy_score:.0f})"
        ),
        resolved_at=now,
    )


def clear_resolution_cache() -> None:
    """Clear all lru_cache instances for resolution indexes.

    Call this when source data changes to force re-loading of indexes.
    """
    _build_labels_by_unit_group.cache_clear()
    _build_example_titles_by_oasis.cache_clear()
    _load_noc_structure.cache_clear()
