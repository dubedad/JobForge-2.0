"""Tests for CAF-to-NOC matching with confidence scoring.

Tests cover:
- CAFNOCMapping model validation
- CAFNOCMatcher match() method
- Confidence scoring tiers
- Audit trail completeness
- FK relationship validation
- build_all_matches() batch processing
- Edge cases (no matches, best_guess fallback)
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import polars as pl
import pytest

from jobforge.external.caf.matchers import (
    ALGORITHM_VERSION,
    CONFIDENCE_EXACT,
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    CAFNOCMapping,
    CAFNOCMatcher,
    _compute_similarity,
    _score_to_confidence,
    match_caf_to_noc,
)


# =============================================================================
# Test Data Fixtures
# =============================================================================


@pytest.fixture
def mock_noc_data():
    """Sample NOC data for testing."""
    return [
        {"unit_group_id": "10010", "class_title": "Financial managers"},
        {"unit_group_id": "12200", "class_title": "Accounting technicians and bookkeepers"},
        {"unit_group_id": "21231", "class_title": "Software engineers and designers"},
        {"unit_group_id": "31100", "class_title": "Physicians"},
        {"unit_group_id": "42100", "class_title": "Police officers"},
        {"unit_group_id": "73100", "class_title": "Carpenters"},
    ]


@pytest.fixture
def mock_caf_data():
    """Sample CAF occupation data for testing."""
    return [
        {
            "career_id": "financial-services-administrator",
            "title_en": "Financial Services Administrator",
            "related_civilian_occupations": json.dumps(["Financial Manager", "Accounting Technician"]),
        },
        {
            "career_id": "infantry-officer",
            "title_en": "Infantry Officer",
            "related_civilian_occupations": json.dumps(["Operations and Project Management"]),
        },
        {
            "career_id": "military-police",
            "title_en": "Military Police",
            "related_civilian_occupations": json.dumps(["Police Officer", "Security Guard"]),
        },
        {
            "career_id": "armoured-soldier",
            "title_en": "Armoured Soldier",
            "related_civilian_occupations": json.dumps([]),
        },
    ]


@pytest.fixture
def mock_gold_path(tmp_path, mock_noc_data, mock_caf_data):
    """Create mock gold directory with parquet files."""
    gold_dir = tmp_path / "gold"
    gold_dir.mkdir()

    # Write mock dim_noc.parquet
    noc_df = pl.DataFrame(mock_noc_data)
    noc_df.write_parquet(gold_dir / "dim_noc.parquet")

    # Write mock dim_caf_occupation.parquet
    caf_df = pl.DataFrame(mock_caf_data)
    caf_df.write_parquet(gold_dir / "dim_caf_occupation.parquet")

    return gold_dir


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestComputeSimilarity:
    """Tests for _compute_similarity function."""

    def test_exact_match(self):
        """Exact strings should return 1.0."""
        score = _compute_similarity("Financial Manager", "Financial Manager")
        assert score == 1.0

    def test_case_insensitive(self):
        """Matching should be case-insensitive."""
        score = _compute_similarity("Financial Manager", "financial manager")
        assert score == 1.0

    def test_partial_match(self):
        """Partial matches should return intermediate scores."""
        score = _compute_similarity("Financial Manager", "Financial Managers")
        assert 0.8 < score < 1.0

    def test_unrelated_strings(self):
        """Unrelated strings should return low scores."""
        score = _compute_similarity("Financial Manager", "Software Engineer")
        assert score < 0.5

    def test_token_order_invariant(self):
        """Token sort ratio should handle word order changes."""
        score = _compute_similarity("Project Manager", "Manager Project")
        assert score > 0.8


class TestScoreToConfidence:
    """Tests for _score_to_confidence function."""

    def test_exact_tier(self):
        """Scores >= 0.95 should return EXACT confidence."""
        confidence, tier = _score_to_confidence(0.98)
        assert confidence == CONFIDENCE_EXACT
        assert tier == "exact"

    def test_high_tier(self):
        """Scores >= 0.90 should return HIGH confidence."""
        confidence, tier = _score_to_confidence(0.92)
        assert confidence == CONFIDENCE_HIGH
        assert tier == "high"

    def test_medium_tier(self):
        """Scores >= 0.80 should return MEDIUM confidence."""
        confidence, tier = _score_to_confidence(0.85)
        assert confidence == CONFIDENCE_MEDIUM
        assert tier == "medium"

    def test_low_tier(self):
        """Scores < 0.80 should return LOW confidence."""
        confidence, tier = _score_to_confidence(0.65)
        assert confidence == CONFIDENCE_LOW
        assert tier == "low"


# =============================================================================
# CAFNOCMapping Model Tests
# =============================================================================


class TestCAFNOCMappingModel:
    """Tests for CAFNOCMapping Pydantic model."""

    def test_valid_mapping(self):
        """Test creating a valid CAFNOCMapping."""
        mapping = CAFNOCMapping(
            caf_occupation_id="financial-services-administrator",
            caf_title_en="Financial Services Administrator",
            noc_unit_group_id="10010",
            noc_title="Financial managers",
            confidence=0.95,
            similarity_score=0.97,
            match_method="related_civilian",
            matched_text="Financial Manager",
            source_attribution="algorithmic_rapidfuzz_exact",
            rationale="Related civilian 'Financial Manager' -> NOC 'Financial managers' (score: 0.97)",
            matched_at=datetime.now(timezone.utc),
        )
        assert mapping.caf_occupation_id == "financial-services-administrator"
        assert mapping.noc_unit_group_id == "10010"
        assert mapping.confidence == 0.95
        assert mapping.match_method == "related_civilian"

    def test_mapping_has_audit_fields(self):
        """Mapping should have all audit trail fields."""
        mapping = CAFNOCMapping(
            caf_occupation_id="test",
            caf_title_en="Test",
            noc_unit_group_id="00000",
            noc_title="Test",
            confidence=0.5,
            similarity_score=0.5,
            match_method="title_fuzzy",
            matched_text="Test",
            source_attribution="test",
            rationale="Test rationale",
            matched_at=datetime.now(timezone.utc),
        )
        # Verify all audit fields exist
        assert hasattr(mapping, "match_method")
        assert hasattr(mapping, "similarity_score")
        assert hasattr(mapping, "matched_text")
        assert hasattr(mapping, "rationale")
        assert hasattr(mapping, "matched_at")
        assert hasattr(mapping, "source_attribution")


# =============================================================================
# CAFNOCMatcher Tests
# =============================================================================


class TestCAFNOCMatcher:
    """Tests for CAFNOCMatcher class."""

    def test_match_with_related_civilian(self, mock_gold_path):
        """Match using related_civilian_occupations should work."""
        matcher = CAFNOCMatcher(mock_gold_path)
        matches = matcher.match("financial-services-administrator")

        assert len(matches) > 0
        # Should find Financial managers via "Financial Manager" related civilian
        noc_codes = [m.noc_unit_group_id for m in matches]
        assert "10010" in noc_codes

    def test_match_returns_sorted_by_confidence(self, mock_gold_path):
        """Matches should be sorted by confidence descending."""
        matcher = CAFNOCMatcher(mock_gold_path)
        matches = matcher.match("financial-services-administrator")

        confidences = [m.confidence for m in matches]
        assert confidences == sorted(confidences, reverse=True)

    def test_match_includes_audit_trail(self, mock_gold_path):
        """Each match should have complete audit trail."""
        matcher = CAFNOCMatcher(mock_gold_path)
        matches = matcher.match("financial-services-administrator")

        for match in matches:
            assert match.match_method in ["related_civilian", "title_fuzzy", "best_guess"]
            assert match.similarity_score > 0
            assert len(match.matched_text) > 0
            assert len(match.rationale) > 0
            assert match.matched_at is not None

    def test_match_nonexistent_occupation(self, mock_gold_path):
        """Matching nonexistent occupation should return empty list."""
        matcher = CAFNOCMatcher(mock_gold_path)
        matches = matcher.match("nonexistent-occupation")
        assert matches == []

    def test_match_respects_top_n(self, mock_gold_path):
        """Match should respect top_n limit."""
        matcher = CAFNOCMatcher(mock_gold_path)
        matches = matcher.match("financial-services-administrator", top_n=2)
        assert len(matches) <= 2

    def test_match_respects_min_threshold(self, mock_gold_path):
        """Match should filter by min_threshold."""
        matcher = CAFNOCMatcher(mock_gold_path)
        matches = matcher.match("financial-services-administrator", min_threshold=0.8)

        for match in matches:
            # Either score is above threshold, or it's a best_guess
            assert match.similarity_score >= 0.8 or match.match_method == "best_guess"

    def test_match_dedupes_noc_codes(self, mock_gold_path):
        """Each NOC should appear at most once in results."""
        matcher = CAFNOCMatcher(mock_gold_path)
        matches = matcher.match("financial-services-administrator")

        noc_codes = [m.noc_unit_group_id for m in matches]
        assert len(noc_codes) == len(set(noc_codes))

    def test_best_guess_fallback(self, mock_gold_path):
        """When no good matches, should return best_guess."""
        matcher = CAFNOCMatcher(mock_gold_path)
        # Armoured Soldier has no related_civilian_occupations
        matches = matcher.match("armoured-soldier")

        # Should still return at least one match (best_guess)
        assert len(matches) > 0

    def test_build_all_matches(self, mock_gold_path):
        """build_all_matches should process all CAF occupations."""
        matcher = CAFNOCMatcher(mock_gold_path)
        all_matches = matcher.build_all_matches()

        # Should have matches for all 4 CAF occupations
        caf_ids = set(m.caf_occupation_id for m in all_matches)
        assert len(caf_ids) == 4


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestMatchCafToNocFunction:
    """Tests for match_caf_to_noc convenience function."""

    def test_convenience_function_works(self, mock_gold_path):
        """match_caf_to_noc should return matches."""
        matches = match_caf_to_noc(
            "financial-services-administrator",
            gold_path=mock_gold_path,
        )
        assert len(matches) > 0

    def test_convenience_function_passes_params(self, mock_gold_path):
        """Parameters should be passed through."""
        matches = match_caf_to_noc(
            "financial-services-administrator",
            gold_path=mock_gold_path,
            top_n=1,
            min_threshold=0.9,
        )
        assert len(matches) <= 1


# =============================================================================
# FK Relationship Tests
# =============================================================================


class TestFKRelationships:
    """Tests validating foreign key relationships."""

    def test_caf_occupation_id_valid(self, mock_gold_path, mock_caf_data):
        """caf_occupation_id should reference valid dim_caf_occupation records."""
        matcher = CAFNOCMatcher(mock_gold_path)
        all_matches = matcher.build_all_matches()

        valid_caf_ids = set(c["career_id"] for c in mock_caf_data)
        for match in all_matches:
            assert match.caf_occupation_id in valid_caf_ids

    def test_noc_unit_group_id_valid(self, mock_gold_path, mock_noc_data):
        """noc_unit_group_id should reference valid dim_noc records."""
        matcher = CAFNOCMatcher(mock_gold_path)
        all_matches = matcher.build_all_matches()

        valid_noc_ids = set(n["unit_group_id"] for n in mock_noc_data)
        for match in all_matches:
            assert match.noc_unit_group_id in valid_noc_ids


# =============================================================================
# Confidence Score Tests
# =============================================================================


class TestConfidenceScoring:
    """Tests for confidence score bounds and consistency."""

    def test_confidence_bounds(self, mock_gold_path):
        """Confidence scores should be between 0 and 1."""
        matcher = CAFNOCMatcher(mock_gold_path)
        all_matches = matcher.build_all_matches()

        for match in all_matches:
            assert 0.0 <= match.confidence <= 1.0
            assert 0.0 <= match.similarity_score <= 1.0

    def test_related_civilian_higher_confidence(self, mock_gold_path):
        """related_civilian matches should generally have higher confidence."""
        matcher = CAFNOCMatcher(mock_gold_path)
        matches = matcher.match("financial-services-administrator")

        related_civilian_matches = [m for m in matches if m.match_method == "related_civilian"]
        title_fuzzy_matches = [m for m in matches if m.match_method == "title_fuzzy"]

        if related_civilian_matches and title_fuzzy_matches:
            # Best related_civilian should beat best title_fuzzy
            best_rc = max(m.confidence for m in related_civilian_matches)
            best_tf = max(m.confidence for m in title_fuzzy_matches)
            # This is a soft assertion - related_civilian gets same score for same similarity
            assert best_rc >= best_tf


# =============================================================================
# Integration Tests (requires real data)
# =============================================================================


@pytest.mark.integration
class TestCAFNOCMatcherIntegration:
    """Integration tests using real data files."""

    def test_real_data_match(self):
        """Test matching against real gold layer data."""
        from jobforge.pipeline.config import PipelineConfig

        gold_path = PipelineConfig().gold_path()
        if not (gold_path / "dim_caf_occupation.parquet").exists():
            pytest.skip("Real CAF data not available")
        if not (gold_path / "dim_noc.parquet").exists():
            pytest.skip("Real NOC data not available")

        matches = match_caf_to_noc("financial-services-administrator")
        assert len(matches) > 0

        # Financial Services Administrator should match Financial managers
        noc_codes = [m.noc_unit_group_id for m in matches]
        assert "10010" in noc_codes
