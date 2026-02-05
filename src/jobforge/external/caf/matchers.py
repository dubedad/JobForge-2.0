"""CAF concordance matching with confidence scoring.

Provides matchers for:
1. CAF-to-NOC: Maps CAF occupations to NOC codes for veteran transition planning
2. CAF-to-JA: Maps CAF occupations to Job Architecture titles

Matching strategy (per CONTEXT.md):
- Hybrid approach: automated fuzzy matching suggests candidates
- Use related_civilian_occupations from CAF data (higher confidence)
- Fall back to title matching (lower confidence)
- Always return at least one match (best guess)
- Full audit trail explaining what contributed to each score

Confidence tiers mirror NOC-OG concordance per 14-06-SUMMARY.md:
- 1.00: Exact match
- 0.85: High similarity (score >= 0.90)
- 0.70: Medium similarity (score >= 0.80)
- 0.50: Low similarity (score >= 0.70)
"""

import json
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Optional

import polars as pl
from pydantic import BaseModel
from rapidfuzz import fuzz

from jobforge.pipeline.config import PipelineConfig


# Algorithm version for audit trail
ALGORITHM_VERSION = "caf_matcher_v1.0"

# Confidence tiers (same as noc_og.py)
CONFIDENCE_EXACT = 1.00
CONFIDENCE_HIGH = 0.85
CONFIDENCE_MEDIUM = 0.70
CONFIDENCE_LOW = 0.50


# =============================================================================
# SHARED HELPERS
# =============================================================================


@lru_cache(maxsize=1)
def _load_caf_occupations(gold_path: Path) -> list[dict]:
    """Load CAF occupations from dim_caf_occupation.parquet."""
    path = gold_path / "dim_caf_occupation.parquet"
    if not path.exists():
        return []
    df = pl.read_parquet(path)
    return df.to_dicts()


@lru_cache(maxsize=1)
def _load_noc_codes(gold_path: Path) -> list[dict]:
    """Load NOC codes from dim_noc.parquet."""
    path = gold_path / "dim_noc.parquet"
    if not path.exists():
        return []
    df = pl.read_parquet(path)
    return df.to_dicts()


@lru_cache(maxsize=1)
def _load_job_architecture(gold_path: Path) -> list[dict]:
    """Load Job Architecture titles from job_architecture.parquet."""
    path = gold_path / "job_architecture.parquet"
    if not path.exists():
        return []
    df = pl.read_parquet(path)
    return df.to_dicts()


def _compute_similarity(text1: str, text2: str) -> float:
    """Compute best similarity score using multiple strategies."""
    text1_lower = text1.lower()
    text2_lower = text2.lower()
    ratio_score = fuzz.ratio(text1_lower, text2_lower) / 100.0
    token_score = fuzz.token_sort_ratio(text1_lower, text2_lower) / 100.0
    wratio_score = fuzz.WRatio(text1_lower, text2_lower) / 100.0
    return max(ratio_score, token_score, wratio_score)


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


# =============================================================================
# NOC MATCHING (for 15-04 CAF-NOC bridge)
# =============================================================================


class CAFNOCMapping(BaseModel):
    """A single CAF-to-NOC match with confidence and full audit trail."""

    caf_occupation_id: str
    caf_title_en: str
    noc_unit_group_id: str
    noc_title: str
    confidence: float
    similarity_score: float
    match_method: str
    matched_text: str
    source_attribution: str
    rationale: str
    matched_at: datetime
