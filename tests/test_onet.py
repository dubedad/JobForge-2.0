"""Tests for O*NET integration.

Tests cover crosswalk loading, client availability checks, and adapter functionality.
API tests that require ONET_API_KEY skip gracefully when not set.
"""

import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from jobforge.external.models import ONetAttribute, ONetAttributeSet
from jobforge.external.onet import NOCSOCCrosswalk, ONetAdapter, ONetClient


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def crosswalk_path():
    """Path to the NOC-SOC crosswalk CSV."""
    return "data/crosswalk/noc2021_onet26.csv"


@pytest.fixture
def crosswalk(crosswalk_path):
    """NOCSOCCrosswalk instance."""
    return NOCSOCCrosswalk(crosswalk_path)


@pytest.fixture
def mock_client():
    """Mock ONetClient with API key."""
    client = MagicMock(spec=ONetClient)
    client.is_available.return_value = True
    return client


@pytest.fixture
def sample_onet_skill_response():
    """Sample O*NET API response for skills."""
    return [
        {
            "id": "2.A.1.a",
            "name": "Reading Comprehension",
            "description": "Understanding written sentences and paragraphs in work-related documents.",
            "score": {"value": 75.0},
            "level": {"value": 4.5},
        },
        {
            "id": "2.A.1.b",
            "name": "Active Listening",
            "description": "Giving full attention to what other people are saying.",
            "score": {"value": 68.0},
        },
    ]


@pytest.fixture
def sample_onet_ability_response():
    """Sample O*NET API response for abilities."""
    return [
        {
            "id": "1.A.1.a.1",
            "name": "Oral Comprehension",
            "description": "The ability to listen to and understand information and ideas.",
            "score": {"value": 62.0},
        },
    ]


@pytest.fixture
def sample_onet_knowledge_response():
    """Sample O*NET API response for knowledge."""
    return [
        {
            "id": "2.C.1.a",
            "name": "Computers and Electronics",
            "description": "Knowledge of circuit boards, processors, chips, etc.",
            "score": {"value": 85.0},
        },
    ]


# ============================================================================
# Crosswalk Tests (no API key needed)
# ============================================================================


class TestCrosswalkLoading:
    """Tests for crosswalk CSV loading."""

    def test_crosswalk_loads_csv(self, crosswalk):
        """Verify CSV loads without error."""
        assert crosswalk is not None
        assert len(crosswalk) > 0

    def test_crosswalk_has_minimum_mappings(self, crosswalk):
        """Verify crosswalk has expected number of mappings."""
        stats = crosswalk.coverage_stats()
        assert stats["total_mappings"] >= 1400

    def test_crosswalk_noc_to_soc_found(self, crosswalk):
        """Known NOC returns SOC code(s)."""
        # 21211 is Data Scientists - should have mapping
        socs = crosswalk.noc_to_soc("21211")
        assert len(socs) >= 1
        assert all(isinstance(soc, str) for soc in socs)

    def test_crosswalk_noc_to_soc_not_found(self, crosswalk):
        """Unknown NOC returns empty list."""
        socs = crosswalk.noc_to_soc("99999")
        assert socs == []

    def test_crosswalk_has_mapping_true(self, crosswalk):
        """has_mapping returns True for known NOC."""
        assert crosswalk.has_mapping("21211") is True

    def test_crosswalk_has_mapping_false(self, crosswalk):
        """has_mapping returns False for unknown NOC."""
        assert crosswalk.has_mapping("99999") is False

    def test_crosswalk_handles_one_to_many(self, crosswalk):
        """NOC with multiple SOC mappings returns all."""
        # Find a NOC that maps to multiple SOCs
        for noc in crosswalk.noc_codes[:100]:
            socs = crosswalk.noc_to_soc(noc)
            if len(socs) > 1:
                assert len(socs) > 1
                return
        # If no multi-mapping found in first 100, skip
        pytest.skip("No multi-mapping NOC found in sample")

    def test_crosswalk_soc_format_valid(self, crosswalk):
        """All SOC codes have valid format (XX-XXXX.XX)."""
        # Check a sample of NOC codes
        for noc in crosswalk.noc_codes[:20]:
            for soc in crosswalk.noc_to_soc(noc):
                # SOC format is XX-XXXX.XX (one hyphen, one period)
                assert "-" in soc, f"SOC {soc} missing hyphen"
                assert "." in soc, f"SOC {soc} missing period"

    def test_crosswalk_coverage_stats_keys(self, crosswalk):
        """coverage_stats returns expected keys."""
        stats = crosswalk.coverage_stats()
        expected_keys = {
            "total_mappings",
            "unique_noc_codes",
            "unique_soc_codes",
            "avg_soc_per_noc",
            "max_soc_per_noc",
            "avg_noc_per_soc",
            "max_noc_per_soc",
        }
        assert set(stats.keys()) == expected_keys

    def test_crosswalk_soc_to_noc(self, crosswalk):
        """soc_to_noc returns NOC code(s) for known SOC."""
        # First get a SOC from a known mapping
        socs = crosswalk.noc_to_soc("21211")
        if socs:
            nocs = crosswalk.soc_to_noc(socs[0])
            assert "21211" in nocs

    def test_crosswalk_file_not_found(self):
        """Raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            NOCSOCCrosswalk("nonexistent/path.csv")


# ============================================================================
# Client Tests
# ============================================================================


class TestONetClientAvailability:
    """Tests for ONetClient availability checks."""

    def test_client_is_available_no_key(self):
        """Returns False when no key configured."""
        # Clear env var temporarily
        original = os.environ.get("ONET_API_KEY")
        if original:
            del os.environ["ONET_API_KEY"]

        try:
            client = ONetClient()
            assert client.is_available() is False
        finally:
            if original:
                os.environ["ONET_API_KEY"] = original

    def test_client_is_available_with_key(self):
        """Returns True when key is provided."""
        client = ONetClient(api_key="test-key")
        assert client.is_available() is True

    def test_client_is_available_from_env(self):
        """Returns True when key is in environment."""
        os.environ["ONET_API_KEY"] = "test-key-from-env"
        try:
            client = ONetClient()
            assert client.is_available() is True
        finally:
            del os.environ["ONET_API_KEY"]


# ============================================================================
# Adapter Tests (with mocked API)
# ============================================================================


class TestONetAdapterMocked:
    """Tests for ONetAdapter with mocked API responses."""

    @pytest.mark.asyncio
    async def test_adapter_get_attributes_for_noc(
        self,
        crosswalk,
        sample_onet_skill_response,
        sample_onet_ability_response,
        sample_onet_knowledge_response,
    ):
        """Adapter returns ONetAttribute list for NOC."""
        mock_client = AsyncMock(spec=ONetClient)
        mock_client.is_available.return_value = True
        mock_client.get_skills.return_value = sample_onet_skill_response
        mock_client.get_abilities.return_value = sample_onet_ability_response
        mock_client.get_knowledge.return_value = sample_onet_knowledge_response
        mock_client.get_occupation_summary.return_value = {"title": "Test Occupation"}

        adapter = ONetAdapter(mock_client, crosswalk)
        attributes = await adapter.get_attributes_for_noc("21211")

        # Should have attributes (skills + abilities + knowledge) * num SOCs
        assert len(attributes) > 0
        assert all(isinstance(attr, ONetAttribute) for attr in attributes)

    @pytest.mark.asyncio
    async def test_adapter_no_mapping_returns_empty(self, crosswalk):
        """Unknown NOC returns empty list."""
        mock_client = AsyncMock(spec=ONetClient)
        mock_client.is_available.return_value = True

        adapter = ONetAdapter(mock_client, crosswalk)
        attributes = await adapter.get_attributes_for_noc("99999")

        assert attributes == []

    @pytest.mark.asyncio
    async def test_adapter_client_unavailable_returns_empty(self, crosswalk):
        """Returns empty list when client unavailable."""
        mock_client = AsyncMock(spec=ONetClient)
        mock_client.is_available.return_value = False

        adapter = ONetAdapter(mock_client, crosswalk)
        attributes = await adapter.get_attributes_for_noc("21211")

        assert attributes == []

    @pytest.mark.asyncio
    async def test_adapter_sets_confidence(
        self,
        crosswalk,
        sample_onet_skill_response,
    ):
        """All attributes have confidence=0.5 per CONTEXT.md."""
        mock_client = AsyncMock(spec=ONetClient)
        mock_client.is_available.return_value = True
        mock_client.get_skills.return_value = sample_onet_skill_response
        mock_client.get_abilities.return_value = []
        mock_client.get_knowledge.return_value = []
        mock_client.get_occupation_summary.return_value = {}

        adapter = ONetAdapter(mock_client, crosswalk)
        attributes = await adapter.get_attributes_for_noc("21211")

        assert len(attributes) > 0
        for attr in attributes:
            assert attr.confidence == 0.5

    @pytest.mark.asyncio
    async def test_adapter_sets_provenance(
        self,
        crosswalk,
        sample_onet_skill_response,
    ):
        """Attributes have source_type='ONET' and source_noc set."""
        mock_client = AsyncMock(spec=ONetClient)
        mock_client.is_available.return_value = True
        mock_client.get_skills.return_value = sample_onet_skill_response
        mock_client.get_abilities.return_value = []
        mock_client.get_knowledge.return_value = []
        mock_client.get_occupation_summary.return_value = {}

        adapter = ONetAdapter(mock_client, crosswalk)
        attributes = await adapter.get_attributes_for_noc("21211")

        assert len(attributes) > 0
        for attr in attributes:
            assert attr.source_type == "ONET"
            assert attr.source_noc == "21211"
            assert attr.source_soc != ""

    @pytest.mark.asyncio
    async def test_adapter_aggregates_multiple_socs(
        self,
        crosswalk,
        sample_onet_skill_response,
    ):
        """1:N mapping aggregates attributes from all SOCs."""
        # Find a NOC with multiple SOC mappings
        test_noc = None
        for noc in crosswalk.noc_codes[:100]:
            if len(crosswalk.noc_to_soc(noc)) > 1:
                test_noc = noc
                break

        if not test_noc:
            pytest.skip("No multi-mapping NOC found")

        soc_count = len(crosswalk.noc_to_soc(test_noc))

        mock_client = AsyncMock(spec=ONetClient)
        mock_client.is_available.return_value = True
        mock_client.get_skills.return_value = sample_onet_skill_response
        mock_client.get_abilities.return_value = []
        mock_client.get_knowledge.return_value = []
        mock_client.get_occupation_summary.return_value = {}

        adapter = ONetAdapter(mock_client, crosswalk)
        attributes = await adapter.get_attributes_for_noc(test_noc)

        # Should have attributes from each SOC
        expected_min = len(sample_onet_skill_response) * soc_count
        assert len(attributes) >= expected_min

    @pytest.mark.asyncio
    async def test_adapter_fetched_at_timestamp(
        self,
        crosswalk,
        sample_onet_skill_response,
    ):
        """Attributes have fetched_at timestamp."""
        mock_client = AsyncMock(spec=ONetClient)
        mock_client.is_available.return_value = True
        mock_client.get_skills.return_value = sample_onet_skill_response
        mock_client.get_abilities.return_value = []
        mock_client.get_knowledge.return_value = []
        mock_client.get_occupation_summary.return_value = {}

        adapter = ONetAdapter(mock_client, crosswalk)
        before = datetime.now(timezone.utc)
        attributes = await adapter.get_attributes_for_noc("21211")
        after = datetime.now(timezone.utc)

        assert len(attributes) > 0
        for attr in attributes:
            assert before <= attr.fetched_at <= after


# ============================================================================
# ONetAttribute Model Tests
# ============================================================================


class TestONetAttributeModel:
    """Tests for ONetAttribute Pydantic model."""

    def test_onet_attribute_creation(self):
        """ONetAttribute can be created with required fields."""
        attr = ONetAttribute(
            element_id="2.A.1.a",
            name="Reading Comprehension",
            description="Understanding written sentences.",
            importance_score=75.0,
            source_soc="15-1252.00",
            source_noc="21211",
        )
        assert attr.element_id == "2.A.1.a"
        assert attr.name == "Reading Comprehension"
        assert attr.source_type == "ONET"
        assert attr.confidence == 0.5

    def test_onet_attribute_defaults(self):
        """ONetAttribute has correct defaults."""
        attr = ONetAttribute(
            element_id="test",
            name="Test",
            description="Test",
            importance_score=50.0,
            source_soc="15-1252.00",
            source_noc="21211",
        )
        assert attr.source_type == "ONET"
        assert attr.confidence == 0.5
        assert attr.level_score is None
        assert attr.fetched_at is not None


class TestONetAttributeSetModel:
    """Tests for ONetAttributeSet Pydantic model."""

    def test_onet_attribute_set_creation(self):
        """ONetAttributeSet can be created."""
        attr_set = ONetAttributeSet(
            soc_code="15-1252.00",
            soc_title="Software Developers",
            skills=[],
            abilities=[],
            knowledge=[],
        )
        assert attr_set.soc_code == "15-1252.00"
        assert attr_set.all_attributes == []
        assert attr_set.attribute_count == 0

    def test_onet_attribute_set_all_attributes(self):
        """all_attributes combines all attribute lists."""
        skill = ONetAttribute(
            element_id="s1",
            name="Skill",
            description="A skill",
            importance_score=50.0,
            source_soc="15-1252.00",
            source_noc="21211",
        )
        ability = ONetAttribute(
            element_id="a1",
            name="Ability",
            description="An ability",
            importance_score=50.0,
            source_soc="15-1252.00",
            source_noc="21211",
        )

        attr_set = ONetAttributeSet(
            soc_code="15-1252.00",
            skills=[skill],
            abilities=[ability],
            knowledge=[],
        )

        assert attr_set.attribute_count == 2
        assert len(attr_set.all_attributes) == 2
        assert skill in attr_set.all_attributes
        assert ability in attr_set.all_attributes


# ============================================================================
# Live API Tests (skipped without API key)
# ============================================================================


@pytest.mark.skipif(
    not os.environ.get("ONET_API_KEY"),
    reason="ONET_API_KEY not set - skipping live API tests",
)
class TestONetClientLive:
    """Live API tests - only run when ONET_API_KEY is set."""

    @pytest.mark.asyncio
    async def test_client_get_skills_valid_soc(self):
        """Fetch skills for a valid SOC code."""
        client = ONetClient()
        skills = await client.get_skills("15-1252.00")  # Software Developers
        assert isinstance(skills, list)
        # May be empty if API changes, but should be a list
        if skills:
            assert "name" in skills[0] or "id" in skills[0]

    @pytest.mark.asyncio
    async def test_client_handles_invalid_soc(self):
        """Invalid SOC returns empty or raises gracefully."""
        client = ONetClient()
        skills = await client.get_skills("00-0000.00")
        assert skills == []
