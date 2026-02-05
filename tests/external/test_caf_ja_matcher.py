"""Tests for CAF-JA matcher with two-level matching and JA context.

Tests:
- CAFJAMatcher class and match() method
- match_caf_to_ja() convenience function
- JA context capture (job_function, job_family)
- FK relationships to dim_caf_occupation and job_architecture
- Audit trail completeness
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import polars as pl
import pytest

from jobforge.external.caf.matchers import (
    CAFJAMapping,
    CAFJAMatcher,
    match_caf_to_ja,
    _compute_similarity,
    _score_to_confidence,
    CONFIDENCE_EXACT,
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_LOW,
)


class TestScoreToConfidence:
    """Tests for _score_to_confidence mapping."""

    def test_exact_match(self):
        confidence, tier = _score_to_confidence(0.95)
        assert confidence == CONFIDENCE_EXACT
        assert tier == "exact"

    def test_high_match(self):
        confidence, tier = _score_to_confidence(0.92)
        assert confidence == CONFIDENCE_HIGH
        assert tier == "high"

    def test_medium_match(self):
        confidence, tier = _score_to_confidence(0.85)
        assert confidence == CONFIDENCE_MEDIUM
        assert tier == "medium"

    def test_low_match(self):
        confidence, tier = _score_to_confidence(0.65)
        assert confidence == CONFIDENCE_LOW
        assert tier == "low"


class TestComputeSimilarity:
    """Tests for _compute_similarity fuzzy matching."""

    def test_identical_strings(self):
        score = _compute_similarity("Pilot", "Pilot")
        assert score == 1.0

    def test_similar_strings(self):
        score = _compute_similarity("Administrative Officer", "Admin Officer")
        assert score > 0.7

    def test_dissimilar_strings(self):
        score = _compute_similarity("Pilot", "Accountant")
        assert score < 0.5

    def test_case_insensitive(self):
        score1 = _compute_similarity("PILOT", "pilot")
        score2 = _compute_similarity("Pilot", "Pilot")
        assert score1 == score2


class TestCAFJAMapping:
    """Tests for CAFJAMapping Pydantic model."""

    def test_valid_mapping(self):
        mapping = CAFJAMapping(
            caf_occupation_id="pilot",
            caf_title_en="Pilot",
            ja_job_title_id=123,
            ja_job_title_en="Airline Pilot",
            ja_job_function_en="Transportation",
            ja_job_family_en="Aviation",
            confidence=0.95,
            similarity_score=0.95,
            match_method="related_civilian",
            matched_text="Airline Pilot",
            source_attribution="algorithmic_rapidfuzz_exact",
            rationale="Test",
            matched_at=datetime.now(timezone.utc),
        )
        assert mapping.caf_occupation_id == "pilot"
        assert mapping.ja_job_title_id == 123

    def test_optional_ja_context(self):
        """JA context fields (job_function, job_family) can be None."""
        mapping = CAFJAMapping(
            caf_occupation_id="pilot",
            caf_title_en="Pilot",
            ja_job_title_id=123,
            ja_job_title_en="Airline Pilot",
            ja_job_function_en=None,
            ja_job_family_en=None,
            confidence=0.95,
            similarity_score=0.95,
            match_method="related_civilian",
            matched_text="Airline Pilot",
            source_attribution="algorithmic_rapidfuzz_exact",
            rationale="Test",
            matched_at=datetime.now(timezone.utc),
        )
        assert mapping.ja_job_function_en is None
        assert mapping.ja_job_family_en is None


class TestCAFJAMatcher:
    """Tests for CAFJAMatcher class."""

    @pytest.fixture
    def mock_caf_data(self):
        return [
            {
                "career_id": "pilot",
                "title_en": "Pilot",
                "related_civilian_occupations": '["Airline Pilot", "Commercial Pilot"]'
            },
            {
                "career_id": "infantry-officer",
                "title_en": "Infantry Officer",
                "related_civilian_occupations": "[]"
            },
        ]

    @pytest.fixture
    def mock_ja_data(self):
        return [
            {
                "jt_id": 1,
                "job_title_en": "Airline Pilot",
                "job_function_en": "Transportation",
                "job_family_en": "Aviation"
            },
            {
                "jt_id": 2,
                "job_title_en": "Commercial Pilot",
                "job_function_en": "Transportation",
                "job_family_en": "Aviation"
            },
            {
                "jt_id": 3,
                "job_title_en": "Security Officer",
                "job_function_en": "Security",
                "job_family_en": "Security Services"
            },
        ]

    @patch("jobforge.external.caf.matchers._load_caf_occupations")
    @patch("jobforge.external.caf.matchers._load_job_architecture")
    def test_match_with_related_civilian(self, mock_ja, mock_caf, mock_caf_data, mock_ja_data):
        mock_caf.return_value = mock_caf_data
        mock_ja.return_value = mock_ja_data

        matcher = CAFJAMatcher()
        matches = matcher.match("pilot")

        assert len(matches) > 0
        # Should match via related_civilian first
        assert any(m.match_method == "related_civilian" for m in matches)
        # Should have JA context
        pilot_match = next((m for m in matches if m.ja_job_title_en == "Airline Pilot"), None)
        assert pilot_match is not None
        assert pilot_match.ja_job_function_en == "Transportation"
        assert pilot_match.ja_job_family_en == "Aviation"

    @patch("jobforge.external.caf.matchers._load_caf_occupations")
    @patch("jobforge.external.caf.matchers._load_job_architecture")
    def test_match_not_found(self, mock_ja, mock_caf, mock_caf_data, mock_ja_data):
        mock_caf.return_value = mock_caf_data
        mock_ja.return_value = mock_ja_data

        matcher = CAFJAMatcher()
        matches = matcher.match("nonexistent-career")

        assert len(matches) == 0

    @patch("jobforge.external.caf.matchers._load_caf_occupations")
    @patch("jobforge.external.caf.matchers._load_job_architecture")
    def test_match_returns_audit_trail(self, mock_ja, mock_caf, mock_caf_data, mock_ja_data):
        mock_caf.return_value = mock_caf_data
        mock_ja.return_value = mock_ja_data

        matcher = CAFJAMatcher()
        matches = matcher.match("pilot")

        assert len(matches) > 0
        m = matches[0]
        # Check audit trail fields
        assert m.match_method in ["related_civilian", "title_fuzzy", "best_guess"]
        assert m.source_attribution.startswith("algorithmic_rapidfuzz_")
        assert "score:" in m.rationale
        assert m.matched_at is not None

    @patch("jobforge.external.caf.matchers._load_caf_occupations")
    @patch("jobforge.external.caf.matchers._load_job_architecture")
    def test_match_sorted_by_confidence(self, mock_ja, mock_caf, mock_caf_data, mock_ja_data):
        mock_caf.return_value = mock_caf_data
        mock_ja.return_value = mock_ja_data

        matcher = CAFJAMatcher()
        matches = matcher.match("pilot")

        # Results should be sorted by confidence descending
        confidences = [m.confidence for m in matches]
        assert confidences == sorted(confidences, reverse=True)

    @patch("jobforge.external.caf.matchers._load_caf_occupations")
    @patch("jobforge.external.caf.matchers._load_job_architecture")
    def test_top_n_limit(self, mock_ja, mock_caf, mock_caf_data, mock_ja_data):
        mock_caf.return_value = mock_caf_data
        mock_ja.return_value = mock_ja_data

        matcher = CAFJAMatcher()
        matches = matcher.match("pilot", top_n=2)

        assert len(matches) <= 2


class TestMatchCafToJaFunction:
    """Tests for match_caf_to_ja convenience function."""

    @patch("jobforge.external.caf.matchers._load_caf_occupations")
    @patch("jobforge.external.caf.matchers._load_job_architecture")
    def test_convenience_function(self, mock_ja, mock_caf):
        mock_caf.return_value = [{
            "career_id": "test",
            "title_en": "Test",
            "related_civilian_occupations": "[]"
        }]
        mock_ja.return_value = [{
            "jt_id": 1,
            "job_title_en": "Test Job",
            "job_function_en": "Testing",
            "job_family_en": "QA"
        }]

        matches = match_caf_to_ja("test")
        assert isinstance(matches, list)


class TestFKRelationships:
    """Tests for FK relationship validation."""

    def test_bridge_has_caf_fk(self):
        """Bridge table should have caf_occupation_id FK."""
        bridge_path = Path("data/gold/bridge_caf_ja.parquet")
        if not bridge_path.exists():
            pytest.skip("Bridge table not generated yet")

        df = pl.read_parquet(bridge_path)
        assert "caf_occupation_id" in df.columns

    def test_bridge_has_ja_fk(self):
        """Bridge table should have ja_job_title_id FK."""
        bridge_path = Path("data/gold/bridge_caf_ja.parquet")
        if not bridge_path.exists():
            pytest.skip("Bridge table not generated yet")

        df = pl.read_parquet(bridge_path)
        assert "ja_job_title_id" in df.columns

    def test_bridge_has_ja_context(self):
        """Bridge table should have JA context columns."""
        bridge_path = Path("data/gold/bridge_caf_ja.parquet")
        if not bridge_path.exists():
            pytest.skip("Bridge table not generated yet")

        df = pl.read_parquet(bridge_path)
        assert "ja_job_function_en" in df.columns
        assert "ja_job_family_en" in df.columns
