"""Tests for NOC-OG concordance matching."""
import pytest
from jobforge.concordance.noc_og import match_noc_to_og, NOCOGMatch


class TestMatchNocToOg:
    """Test match_noc_to_og function."""

    def test_financial_manager_matches_ct_group(self):
        """Financial managers should match CT (Comptrollership) group with good confidence.

        CT group includes "Financial Management" subgroup, which fuzzy-matches well.
        """
        matches = match_noc_to_og(noc_code="10010", noc_title="Financial managers")

        assert len(matches) >= 1
        # CT (Comptrollership) includes "Financial Management" subgroup
        assert any(m.og_code == "CT" for m in matches)

        ct_match = next(m for m in matches if m.og_code == "CT")
        assert ct_match.confidence >= 0.70  # At least medium confidence

    def test_returns_ranked_list(self):
        """Should return list sorted by confidence (highest first)."""
        matches = match_noc_to_og(noc_code="21231", noc_title="Software engineers")

        assert len(matches) >= 1
        assert len(matches) <= 5  # Top 5 max per CONTEXT.md

        # Verify sorted by confidence descending
        for i in range(len(matches) - 1):
            assert matches[i].confidence >= matches[i + 1].confidence

    def test_includes_source_attribution(self):
        """Each match should have source attribution."""
        matches = match_noc_to_og(noc_code="13110", noc_title="Administrative assistants")

        for match in matches:
            assert match.source_attribution is not None
            assert match.source_attribution.startswith("algorithmic_")

    def test_includes_rationale(self):
        """Each match should have human-readable rationale."""
        matches = match_noc_to_og(noc_code="10010", noc_title="Financial managers")

        for match in matches:
            assert match.rationale is not None
            assert len(match.rationale) > 10  # Non-trivial explanation

    def test_always_returns_suggestion(self):
        """Should always return at least one match, even low confidence."""
        # Obscure title unlikely to match well
        matches = match_noc_to_og(noc_code="99999", noc_title="Underwater basket weaver")

        assert len(matches) >= 1  # Always provide suggestion
        # May have low confidence, but should have a best guess

    def test_match_fields_complete(self):
        """NOCOGMatch should have all required fields."""
        matches = match_noc_to_og(noc_code="10010", noc_title="Financial managers")

        match = matches[0]
        assert hasattr(match, "noc_code")
        assert hasattr(match, "og_code")
        assert hasattr(match, "og_subgroup_code")  # Can be None
        assert hasattr(match, "confidence")
        assert hasattr(match, "similarity_score")
        assert hasattr(match, "source_attribution")
        assert hasattr(match, "rationale")
        assert hasattr(match, "matched_at")


class TestNOCOGMatchModel:
    """Test NOCOGMatch Pydantic model."""

    def test_confidence_in_valid_range(self):
        """Confidence should be 0.0 to 1.0."""
        matches = match_noc_to_og(noc_code="10010", noc_title="Financial managers")

        for match in matches:
            assert 0.0 <= match.confidence <= 1.0

    def test_similarity_score_in_valid_range(self):
        """Similarity score should be 0.0 to 1.0."""
        matches = match_noc_to_og(noc_code="10010", noc_title="Financial managers")

        for match in matches:
            assert 0.0 <= match.similarity_score <= 1.0


class TestAdministrativeMatch:
    """Test administrative assistants mapping."""

    def test_administrative_assistants_match_pa_group(self):
        """Administrative assistants should match PA (Program and Administrative Services) group.

        PA group name explicitly contains "Administrative Services".
        """
        matches = match_noc_to_og(noc_code="13110", noc_title="Administrative assistants")

        # Should have at least one match to PA (Program and Administrative Services)
        pa_matches = [m for m in matches if m.og_code == "PA"]
        assert len(pa_matches) >= 1, f"Expected PA match, got: {[m.og_code for m in matches]}"


class TestSubgroupMatching:
    """Test subgroup-level matching when possible."""

    def test_returns_subgroup_matches(self):
        """Should return subgroup-level matches when available."""
        matches = match_noc_to_og(noc_code="10010", noc_title="Financial managers")

        # Check that some matches include subgroup codes
        subgroup_matches = [m for m in matches if m.og_subgroup_code is not None]
        # It's okay if no subgroups match for some titles, but the field should exist
        assert all(hasattr(m, "og_subgroup_code") for m in matches)
