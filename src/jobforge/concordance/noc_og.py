"""NOC-OG concordance matching with confidence scoring.

Maps NOC codes to TBS Occupational Groups using fuzzy matching
with full provenance tracking. Since no official TBS concordance exists,
this uses algorithmic matching with source attribution.

Confidence tiers:
- 1.00: Exact match (rare for algorithmic)
- 0.85: High similarity (Jaro-Winkler >= 0.90)
- 0.70: Medium similarity (Jaro-Winkler >= 0.80)
- 0.50: Low similarity (Jaro-Winkler >= 0.70)

Keyword boosting:
- Domain-specific keywords boost scores for relevant OG groups
- Addresses semantic gaps in pure fuzzy string matching
"""

from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Optional

import polars as pl
from pydantic import BaseModel
from rapidfuzz import fuzz

from jobforge.pipeline.config import PipelineConfig


# Confidence tiers (from RESEARCH.md)
CONFIDENCE_EXACT = 1.00
CONFIDENCE_HIGH = 0.85
CONFIDENCE_MEDIUM = 0.70
CONFIDENCE_LOW = 0.50

# Keyword boosting for semantic matching
# Maps (keywords tuple) -> (og_code, boost_value)
# Boost is added to fuzzy score when any keyword found in NOC title
KEYWORD_BOOSTS: dict[tuple[str, ...], tuple[str, float]] = {
    # IT-related -> IT (Information Technology)
    # Higher boost (0.6) to overcome false positives from fuzzy matching
    ("software", "developer", "programmer", "computer", "systems analyst",
     "database", "network", "cyber", "web developer", "cloud", "devops",
     "it specialist", "it manager", "information technology"): ("IT", 0.6),
    # Finance-related -> CT (Comptrollership)
    ("financial", "finance manager", "accountant", "accounting",
     "auditor", "budget", "comptroller"): ("CT", 0.4),
    # HR-related -> HM (Human Resources Management)
    ("human resources", "hr manager", "recruitment", "staffing",
     "personnel", "talent acquisition"): ("HM", 0.4),
    # Research-related -> RE (Research)
    ("research scientist", "researcher", "research manager"): ("RE", 0.3),
    # University-related -> UT (University Teaching)
    ("professor", "lecturer", "university teacher", "academic",
     "postsecondary instructor"): ("UT", 0.5),
    # Economics -> EC (Economics and Social Science Services)
    ("economist", "economic analyst", "economics"): ("EC", 0.4),
    # Translation -> TR (Translation)
    ("translator", "interpreter", "translation"): ("TR", 0.5),
    # Foreign service -> FS (Foreign Service)
    ("diplomat", "foreign service", "embassy", "consular"): ("FS", 0.5),
}


class NOCOGMatch(BaseModel):
    """A single NOC-to-OG match with confidence and provenance."""

    noc_code: str
    og_code: str
    og_subgroup_code: Optional[str] = None
    og_name: str
    confidence: float
    similarity_score: float
    source_attribution: str
    rationale: str
    matched_at: datetime


@lru_cache(maxsize=1)
def _load_og_groups(gold_path: Path) -> list[dict]:
    """Load OG groups from dim_og."""
    path = gold_path / "dim_og.parquet"
    if not path.exists():
        return []
    df = pl.read_parquet(path)
    return df.to_dicts()


@lru_cache(maxsize=1)
def _load_og_subgroups(gold_path: Path) -> list[dict]:
    """Load OG subgroups from dim_og_subgroup."""
    path = gold_path / "dim_og_subgroup.parquet"
    if not path.exists():
        return []
    df = pl.read_parquet(path)
    return df.to_dicts()


def _get_keyword_boost(noc_title: str, og_code: str) -> float:
    """Get keyword boost for NOC title matching to OG code.

    Returns boost value (0.0-0.5) if NOC title contains keywords
    associated with the OG code, otherwise 0.0.
    """
    noc_lower = noc_title.lower()

    for keywords, (target_og, boost) in KEYWORD_BOOSTS.items():
        if target_og != og_code:
            continue
        # Check if any keyword appears in the NOC title
        for keyword in keywords:
            if keyword in noc_lower:
                return boost
    return 0.0


def _compute_similarity(noc_title: str, og_name: str, og_code: str = "") -> float:
    """Compute best similarity score using multiple strategies.

    Uses rapidfuzz with multiple strategies (ratio, token_sort_ratio, WRatio)
    and applies keyword boosting for semantic matching.

    Args:
        noc_title: The NOC occupation title
        og_name: The OG group/subgroup name
        og_code: The OG code (for keyword boosting)

    Returns:
        Similarity score between 0.0 and 1.0
    """
    noc_lower = noc_title.lower()
    og_lower = og_name.lower()

    # Try multiple matching strategies
    ratio_score = fuzz.ratio(noc_lower, og_lower) / 100.0
    token_score = fuzz.token_sort_ratio(noc_lower, og_lower) / 100.0
    wratio_score = fuzz.WRatio(noc_lower, og_lower) / 100.0

    base_score = max(ratio_score, token_score, wratio_score)

    # Apply keyword boosting
    boost = _get_keyword_boost(noc_title, og_code)

    # Cap total score at 1.0
    return min(base_score + boost, 1.0)


def _score_to_confidence(score: float) -> tuple[float, str]:
    """Map similarity score to confidence tier."""
    if score >= 0.95:
        return CONFIDENCE_EXACT, "exact"
    elif score >= 0.90:
        return CONFIDENCE_HIGH, "high"
    elif score >= 0.80:
        return CONFIDENCE_MEDIUM, "medium"
    else:
        return CONFIDENCE_LOW, "low"


def match_noc_to_og(
    noc_code: str,
    noc_title: str,
    gold_path: Optional[Path] = None,
    top_n: int = 5,
    min_threshold: float = 0.50,
) -> list[NOCOGMatch]:
    """Match NOC occupation to OG groups using fuzzy matching.

    Args:
        noc_code: The NOC code (e.g., "10010", "21231")
        noc_title: The NOC occupation title
        gold_path: Path to gold layer (defaults to PipelineConfig)
        top_n: Maximum matches to return (default 5)
        min_threshold: Minimum similarity to include (default 0.50)

    Returns:
        List of NOCOGMatch sorted by confidence (highest first).
        Always returns at least one match (best guess) per CONTEXT.md.
    """
    if gold_path is None:
        gold_path = PipelineConfig().gold_path()

    og_groups = _load_og_groups(gold_path)
    og_subgroups = _load_og_subgroups(gold_path)

    # Build candidates from both groups and subgroups
    candidates = []

    # Add OG groups
    for og in og_groups:
        candidates.append({
            "og_code": og["og_code"],
            "og_subgroup_code": None,
            "og_name": og["og_name"],
        })

    # Add OG subgroups
    for sub in og_subgroups:
        candidates.append({
            "og_code": sub["og_code"],
            "og_subgroup_code": sub["og_subgroup_code"],
            "og_name": sub["og_subgroup_name"],
        })

    matches = []
    now = datetime.now(timezone.utc)

    for candidate in candidates:
        best_score = _compute_similarity(noc_title, candidate["og_name"], candidate["og_code"])

        if best_score < min_threshold:
            continue

        confidence, tier = _score_to_confidence(best_score)

        matches.append(NOCOGMatch(
            noc_code=noc_code,
            og_code=candidate["og_code"],
            og_subgroup_code=candidate["og_subgroup_code"],
            og_name=candidate["og_name"],
            confidence=confidence,
            similarity_score=best_score,
            source_attribution=f"algorithmic_rapidfuzz_{tier}",
            rationale=f"Fuzzy match ({tier}): '{noc_title}' -> '{candidate['og_name']}' (score: {best_score:.2f})",
            matched_at=now,
        ))

    # Sort by confidence (descending), then similarity (descending)
    matches.sort(key=lambda m: (m.confidence, m.similarity_score), reverse=True)

    # Always return at least one match (best guess) per CONTEXT.md
    if not matches and candidates:
        # Find best match even below threshold
        best_candidate = None
        best_score = 0.0
        for candidate in candidates:
            score = _compute_similarity(noc_title, candidate["og_name"], candidate["og_code"])
            if score > best_score:
                best_score = score
                best_candidate = candidate

        if best_candidate:
            # Scale confidence below LOW for very weak matches
            confidence = CONFIDENCE_LOW * (best_score / 0.50) if best_score < 0.50 else CONFIDENCE_LOW
            matches.append(NOCOGMatch(
                noc_code=noc_code,
                og_code=best_candidate["og_code"],
                og_subgroup_code=best_candidate["og_subgroup_code"],
                og_name=best_candidate["og_name"],
                confidence=min(confidence, CONFIDENCE_LOW),  # Cap at LOW
                similarity_score=best_score,
                source_attribution="algorithmic_rapidfuzz_best_guess",
                rationale=f"Best guess: '{noc_title}' -> '{best_candidate['og_name']}' (score: {best_score:.2f})",
                matched_at=now,
            ))

    return matches[:top_n]


def build_bridge_noc_og(
    gold_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
) -> dict:
    """Build bridge_noc_og table by matching all NOC codes to OG groups.

    Creates a many-to-many bridge table with ranked matches and provenance.

    Args:
        gold_path: Path to gold layer (defaults to PipelineConfig)
        output_path: Output parquet path (defaults to gold_path/bridge_noc_og.parquet)

    Returns:
        Dict with output_path and row_count
    """
    if gold_path is None:
        gold_path = PipelineConfig().gold_path()
    if output_path is None:
        output_path = gold_path / "bridge_noc_og.parquet"

    # Load all NOC codes from dim_noc
    noc_path = gold_path / "dim_noc.parquet"
    noc_df = pl.read_parquet(noc_path)

    all_matches = []
    for row in noc_df.iter_rows(named=True):
        noc_code = row["unit_group_id"]
        noc_title = row["class_title"]

        matches = match_noc_to_og(noc_code, noc_title, gold_path)
        for match in matches:
            all_matches.append(match.model_dump())

    # Create DataFrame and save
    df = pl.DataFrame(all_matches)

    # Add provenance columns
    now = datetime.now(timezone.utc)
    df = df.with_columns([
        pl.lit("dim_noc + dim_og").alias("_source_file"),
        pl.lit(now.isoformat()).alias("_ingested_at"),
        pl.lit(f"noc_og_concordance_{now.strftime('%Y%m%d')}").alias("_batch_id"),
        pl.lit("gold").alias("_layer"),
    ])

    df.write_parquet(output_path)

    return {
        "output_path": str(output_path),
        "row_count": len(df),
        "noc_count": noc_df.shape[0],
        "match_count": len(all_matches),
    }
