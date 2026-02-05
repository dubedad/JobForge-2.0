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


class CAFNOCMatcher:
    """Matcher for CAF occupations to NOC codes."""

    def __init__(self, gold_path: Optional[Path] = None):
        if gold_path is None:
            gold_path = PipelineConfig().gold_path()
        self.gold_path = gold_path

    def match(
        self,
        caf_occupation_id: str,
        top_n: int = 10,
        min_threshold: float = 0.50,
    ) -> list[CAFNOCMapping]:
        """Match CAF occupation to NOC codes."""
        noc_data = _load_noc_codes(self.gold_path)
        caf_data = _load_caf_occupations(self.gold_path)

        caf_occ = next((o for o in caf_data if o.get("career_id") == caf_occupation_id), None)
        if caf_occ is None:
            return []

        caf_title = caf_occ.get("title_en", "")
        related_civs_json = caf_occ.get("related_civilian_occupations", "[]")
        try:
            related_civs = json.loads(related_civs_json) if related_civs_json else []
        except (json.JSONDecodeError, TypeError):
            related_civs = []

        matches = []
        now = datetime.now(timezone.utc)

        # Level 1: Match related_civilian_occupations
        for civ_occ in related_civs:
            for noc in noc_data:
                noc_title = noc.get("class_title", "")
                noc_code = noc.get("unit_group_id", "")
                score = _compute_similarity(civ_occ, noc_title)
                if score < min_threshold:
                    continue
                confidence, tier = _score_to_confidence(score)
                matches.append(CAFNOCMapping(
                    caf_occupation_id=caf_occupation_id, caf_title_en=caf_title,
                    noc_unit_group_id=noc_code, noc_title=noc_title,
                    confidence=confidence, similarity_score=score,
                    match_method="related_civilian", matched_text=civ_occ,
                    source_attribution=f"algorithmic_rapidfuzz_{tier}",
                    rationale=f"Related civilian '{civ_occ}' -> NOC '{noc_title}' (score: {score:.2f})",
                    matched_at=now,
                ))

        # Level 2: Direct title matching
        for noc in noc_data:
            noc_title = noc.get("class_title", "")
            noc_code = noc.get("unit_group_id", "")
            score = _compute_similarity(caf_title, noc_title)
            if score < min_threshold:
                continue
            if any(m.noc_unit_group_id == noc_code and m.match_method == "related_civilian" for m in matches):
                continue
            confidence, tier = _score_to_confidence(score)
            matches.append(CAFNOCMapping(
                caf_occupation_id=caf_occupation_id, caf_title_en=caf_title,
                noc_unit_group_id=noc_code, noc_title=noc_title,
                confidence=confidence, similarity_score=score,
                match_method="title_fuzzy", matched_text=caf_title,
                source_attribution=f"algorithmic_rapidfuzz_{tier}",
                rationale=f"Direct title '{caf_title}' -> NOC '{noc_title}' (score: {score:.2f})",
                matched_at=now,
            ))

        # Best guess fallback
        if not matches and noc_data:
            best_match, best_score = None, 0.0
            for noc in noc_data:
                score = _compute_similarity(caf_title, noc.get("class_title", ""))
                if score > best_score:
                    best_score, best_match = score, noc
            if best_match:
                matches.append(CAFNOCMapping(
                    caf_occupation_id=caf_occupation_id, caf_title_en=caf_title,
                    noc_unit_group_id=best_match.get("unit_group_id", ""),
                    noc_title=best_match.get("class_title", ""),
                    confidence=CONFIDENCE_LOW, similarity_score=best_score,
                    match_method="best_guess", matched_text=caf_title,
                    source_attribution="algorithmic_rapidfuzz_best_guess",
                    rationale=f"Best guess: '{caf_title}' -> '{best_match.get('class_title', '')}' (score: {best_score:.2f})",
                    matched_at=now,
                ))

        matches.sort(key=lambda m: (m.confidence, m.similarity_score), reverse=True)
        seen = set()
        deduped = [m for m in matches if not (m.noc_unit_group_id in seen or seen.add(m.noc_unit_group_id))]
        return deduped[:top_n]

    def build_all_matches(self) -> list[CAFNOCMapping]:
        """Build matches for all CAF occupations.

        Returns:
            List of all CAFNOCMapping for all CAF occupations.
        """
        caf_data = _load_caf_occupations(self.gold_path)
        all_matches = []
        for caf_occ in caf_data:
            matches = self.match(caf_occ["career_id"])
            all_matches.extend(matches)
        return all_matches


def match_caf_to_noc(
    caf_occupation_id: str,
    gold_path: Optional[Path] = None,
    top_n: int = 10,
    min_threshold: float = 0.50,
) -> list[CAFNOCMapping]:
    """Convenience function to match CAF occupation to NOC codes."""
    if gold_path is None:
        gold_path = PipelineConfig().gold_path()
    return CAFNOCMatcher(gold_path).match(caf_occupation_id, top_n=top_n, min_threshold=min_threshold)


# =============================================================================
# JA MATCHING (for 15-05 CAF-JA bridge)
# =============================================================================


class CAFJAMapping(BaseModel):
    """A single CAF-to-JA match with confidence and full audit trail."""

    caf_occupation_id: str
    caf_title_en: str
    ja_job_title_id: int
    ja_job_title_en: str
    ja_job_function_en: Optional[str] = None  # May be null in JA table
    ja_job_family_en: Optional[str] = None  # May be null in JA table
    confidence: float
    similarity_score: float
    match_method: str
    matched_text: str
    source_attribution: str
    rationale: str
    matched_at: datetime


class CAFJAMatcher:
    """Matcher for CAF occupations to Job Architecture titles."""

    def __init__(self, gold_path: Optional[Path] = None):
        if gold_path is None:
            gold_path = PipelineConfig().gold_path()
        self.gold_path = gold_path

    def match(
        self,
        caf_occupation_id: str,
        top_n: int = 10,
        min_threshold: float = 0.50,
    ) -> list[CAFJAMapping]:
        """Match CAF occupation to Job Architecture titles."""
        ja_data = _load_job_architecture(self.gold_path)
        caf_data = _load_caf_occupations(self.gold_path)

        caf_occ = next((o for o in caf_data if o.get("career_id") == caf_occupation_id), None)
        if caf_occ is None:
            return []

        caf_title = caf_occ.get("title_en", "")
        related_civs_json = caf_occ.get("related_civilian_occupations", "[]")
        try:
            related_civs = json.loads(related_civs_json) if related_civs_json else []
        except (json.JSONDecodeError, TypeError):
            related_civs = []

        matches = []
        now = datetime.now(timezone.utc)

        # Level 1: Match related_civilian_occupations to JA titles
        for civ_occ in related_civs:
            for ja in ja_data:
                ja_title = ja.get("job_title_en", "")
                score = _compute_similarity(civ_occ, ja_title)
                if score < min_threshold:
                    continue
                confidence, tier = _score_to_confidence(score)
                matches.append(CAFJAMapping(
                    caf_occupation_id=caf_occupation_id, caf_title_en=caf_title,
                    ja_job_title_id=ja.get("jt_id", 0), ja_job_title_en=ja_title,
                    ja_job_function_en=ja.get("job_function_en", ""),
                    ja_job_family_en=ja.get("job_family_en", ""),
                    confidence=confidence, similarity_score=score,
                    match_method="related_civilian", matched_text=civ_occ,
                    source_attribution=f"algorithmic_rapidfuzz_{tier}",
                    rationale=f"Related civilian '{civ_occ}' -> JA '{ja_title}' (score: {score:.2f})",
                    matched_at=now,
                ))

        # Level 2: Direct title matching
        for ja in ja_data:
            ja_title = ja.get("job_title_en", "")
            score = _compute_similarity(caf_title, ja_title)
            if score < min_threshold:
                continue
            if any(m.ja_job_title_id == ja.get("jt_id", 0) and m.match_method == "related_civilian" for m in matches):
                continue
            confidence, tier = _score_to_confidence(score)
            matches.append(CAFJAMapping(
                caf_occupation_id=caf_occupation_id, caf_title_en=caf_title,
                ja_job_title_id=ja.get("jt_id", 0), ja_job_title_en=ja_title,
                ja_job_function_en=ja.get("job_function_en", ""),
                ja_job_family_en=ja.get("job_family_en", ""),
                confidence=confidence, similarity_score=score,
                match_method="title_fuzzy", matched_text=caf_title,
                source_attribution=f"algorithmic_rapidfuzz_{tier}",
                rationale=f"Direct title '{caf_title}' -> JA '{ja_title}' (score: {score:.2f})",
                matched_at=now,
            ))

        # Best guess fallback
        if not matches and ja_data:
            best_match, best_score = None, 0.0
            for ja in ja_data:
                score = _compute_similarity(caf_title, ja.get("job_title_en", ""))
                if score > best_score:
                    best_score, best_match = score, ja
            if best_match:
                matches.append(CAFJAMapping(
                    caf_occupation_id=caf_occupation_id, caf_title_en=caf_title,
                    ja_job_title_id=best_match.get("jt_id", 0),
                    ja_job_title_en=best_match.get("job_title_en", ""),
                    ja_job_function_en=best_match.get("job_function_en", ""),
                    ja_job_family_en=best_match.get("job_family_en", ""),
                    confidence=CONFIDENCE_LOW, similarity_score=best_score,
                    match_method="best_guess", matched_text=caf_title,
                    source_attribution="algorithmic_rapidfuzz_best_guess",
                    rationale=f"Best guess: '{caf_title}' -> '{best_match.get('job_title_en', '')}' (score: {best_score:.2f})",
                    matched_at=now,
                ))

        matches.sort(key=lambda m: (m.confidence, m.similarity_score), reverse=True)
        seen = set()
        deduped = [m for m in matches if not (m.ja_job_title_id in seen or seen.add(m.ja_job_title_id))]
        return deduped[:top_n]


def match_caf_to_ja(
    caf_occupation_id: str,
    gold_path: Optional[Path] = None,
    top_n: int = 10,
    min_threshold: float = 0.50,
) -> list[CAFJAMapping]:
    """Convenience function to match CAF occupation to Job Architecture."""
    if gold_path is None:
        gold_path = PipelineConfig().gold_path()
    return CAFJAMatcher(gold_path).match(caf_occupation_id, top_n=top_n, min_threshold=min_threshold)
