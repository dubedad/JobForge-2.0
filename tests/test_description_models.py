"""Tests for description generation models and source cascade logic.

Tests cover:
- DescriptionSource enum values
- DescriptionProvenance creation and precedence mapping
- GeneratedDescription creation and serialization
- Lead statement loading and lookup
- Source type determination cascade
"""

from datetime import datetime, timezone

import pytest

from jobforge.description import (
    DescriptionProvenance,
    DescriptionSource,
    GeneratedDescription,
    clear_lead_statement_cache,
    determine_source_type,
    get_lead_statement_for_oasis,
    load_lead_statements,
)
from jobforge.external.models import SourcePrecedence
from jobforge.pipeline.config import PipelineConfig


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear lead statement cache before each test."""
    clear_lead_statement_cache()
    yield
    clear_lead_statement_cache()


@pytest.fixture
def gold_path():
    """Get gold path for tests."""
    return PipelineConfig().gold_path()


@pytest.fixture
def sample_provenance():
    """Create a sample DescriptionProvenance for tests."""
    return DescriptionProvenance(
        source_type=DescriptionSource.AUTHORITATIVE,
        confidence=1.0,
        timestamp=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        resolution_method="DIRECT_MATCH",
        matched_text="Software engineers",
    )


# =============================================================================
# DescriptionSource Enum Tests
# =============================================================================


class TestDescriptionSource:
    """Tests for DescriptionSource enum."""

    def test_authoritative_value(self):
        """Test AUTHORITATIVE enum value."""
        assert DescriptionSource.AUTHORITATIVE.value == "authoritative"

    def test_onet_value(self):
        """Test ONET enum value."""
        assert DescriptionSource.ONET.value == "onet"

    def test_llm_value(self):
        """Test LLM enum value."""
        assert DescriptionSource.LLM.value == "llm"

    def test_all_values_are_strings(self):
        """Test all enum values are strings."""
        for source in DescriptionSource:
            assert isinstance(source.value, str)


# =============================================================================
# DescriptionProvenance Tests
# =============================================================================


class TestDescriptionProvenance:
    """Tests for DescriptionProvenance model."""

    def test_create_with_all_fields(self):
        """Test provenance creation with all fields populated."""
        provenance = DescriptionProvenance(
            source_type=DescriptionSource.LLM,
            confidence=0.85,
            timestamp=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
            model_version="gpt-4o-2024-08-06",
            input_context="NOC boundary words: Software engineer, systems",
            resolution_method="LABEL_IMPUTATION",
            matched_text="Software engineer",
        )

        assert provenance.source_type == DescriptionSource.LLM
        assert provenance.confidence == 0.85
        assert provenance.model_version == "gpt-4o-2024-08-06"
        assert provenance.input_context is not None
        assert provenance.resolution_method == "LABEL_IMPUTATION"
        assert provenance.matched_text == "Software engineer"

    def test_create_with_minimal_fields(self):
        """Test provenance creation with only required fields."""
        provenance = DescriptionProvenance(
            source_type=DescriptionSource.AUTHORITATIVE,
            confidence=1.0,
        )

        assert provenance.source_type == DescriptionSource.AUTHORITATIVE
        assert provenance.confidence == 1.0
        assert provenance.model_version is None
        assert provenance.input_context is None
        assert provenance.resolution_method is None
        assert provenance.matched_text is None
        # Timestamp should have a default
        assert provenance.timestamp is not None

    def test_precedence_authoritative(self):
        """Test precedence property returns AUTHORITATIVE for authoritative source."""
        provenance = DescriptionProvenance(
            source_type=DescriptionSource.AUTHORITATIVE,
            confidence=1.0,
        )
        assert provenance.precedence == SourcePrecedence.AUTHORITATIVE
        assert provenance.precedence == 3

    def test_precedence_onet(self):
        """Test precedence property returns ONET for O*NET source."""
        provenance = DescriptionProvenance(
            source_type=DescriptionSource.ONET,
            confidence=0.5,
        )
        assert provenance.precedence == SourcePrecedence.ONET
        assert provenance.precedence == 2

    def test_precedence_llm(self):
        """Test precedence property returns LLM for LLM source."""
        provenance = DescriptionProvenance(
            source_type=DescriptionSource.LLM,
            confidence=0.75,
        )
        assert provenance.precedence == SourcePrecedence.LLM
        assert provenance.precedence == 1

    def test_confidence_bounds_valid_low(self):
        """Test confidence 0.0 is valid."""
        provenance = DescriptionProvenance(
            source_type=DescriptionSource.LLM,
            confidence=0.0,
        )
        assert provenance.confidence == 0.0

    def test_confidence_bounds_valid_high(self):
        """Test confidence 1.0 is valid."""
        provenance = DescriptionProvenance(
            source_type=DescriptionSource.AUTHORITATIVE,
            confidence=1.0,
        )
        assert provenance.confidence == 1.0

    def test_confidence_bounds_invalid_too_high(self):
        """Test confidence > 1.0 raises validation error."""
        with pytest.raises(ValueError):
            DescriptionProvenance(
                source_type=DescriptionSource.LLM,
                confidence=1.5,
            )

    def test_confidence_bounds_invalid_too_low(self):
        """Test confidence < 0.0 raises validation error."""
        with pytest.raises(ValueError):
            DescriptionProvenance(
                source_type=DescriptionSource.LLM,
                confidence=-0.1,
            )


# =============================================================================
# GeneratedDescription Tests
# =============================================================================


class TestGeneratedDescription:
    """Tests for GeneratedDescription model."""

    def test_create_title_entity(self, sample_provenance):
        """Test GeneratedDescription creation for title entity."""
        desc = GeneratedDescription(
            entity_type="title",
            entity_id="jt_123",
            entity_name="Senior Data Analyst",
            description="Senior data analysts lead data analysis projects...",
            provenance=sample_provenance,
        )

        assert desc.entity_type == "title"
        assert desc.entity_id == "jt_123"
        assert desc.entity_name == "Senior Data Analyst"
        assert "data analysis" in desc.description.lower()
        assert desc.provenance.source_type == DescriptionSource.AUTHORITATIVE

    def test_create_family_entity(self, sample_provenance):
        """Test GeneratedDescription creation for family entity."""
        desc = GeneratedDescription(
            entity_type="family",
            entity_id="Analytics & Insights",
            entity_name="Analytics & Insights",
            description="The Analytics family covers roles focused on data...",
            provenance=sample_provenance,
        )

        assert desc.entity_type == "family"
        assert desc.entity_id == "Analytics & Insights"

    def test_create_function_entity(self, sample_provenance):
        """Test GeneratedDescription creation for function entity."""
        desc = GeneratedDescription(
            entity_type="function",
            entity_id="Information Technology",
            entity_name="Information Technology",
            description="Information Technology function encompasses...",
            provenance=sample_provenance,
        )

        assert desc.entity_type == "function"
        assert desc.entity_id == "Information Technology"

    def test_invalid_entity_type(self, sample_provenance):
        """Test invalid entity_type raises validation error."""
        with pytest.raises(ValueError):
            GeneratedDescription(
                entity_type="invalid",  # Not title/family/function
                entity_id="123",
                entity_name="Test",
                description="Test description",
                provenance=sample_provenance,
            )

    def test_json_serialization(self, sample_provenance):
        """Test GeneratedDescription serializes to JSON properly."""
        desc = GeneratedDescription(
            entity_type="title",
            entity_id="jt_456",
            entity_name="Software Engineer",
            description="Engineers who design software...",
            provenance=sample_provenance,
        )

        json_data = desc.model_dump_json()

        # Check key fields are in JSON
        assert "title" in json_data
        assert "jt_456" in json_data
        assert "Software Engineer" in json_data
        # Check datetime serialization (ISO format)
        assert "2024-01-15" in json_data
        # Check source type
        assert "authoritative" in json_data


# =============================================================================
# Lead Statement Loading Tests
# =============================================================================


class TestLoadLeadStatements:
    """Tests for load_lead_statements function."""

    def test_returns_dict_with_entries(self, gold_path):
        """Test load_lead_statements returns dict with ~900 entries."""
        lead_statements = load_lead_statements(gold_path)

        assert isinstance(lead_statements, dict)
        assert len(lead_statements) >= 800  # Should be ~900
        assert len(lead_statements) <= 1000

    def test_keys_are_oasis_codes(self, gold_path):
        """Test dictionary keys look like OASIS codes."""
        lead_statements = load_lead_statements(gold_path)

        # Check a sample of keys
        for key in list(lead_statements.keys())[:10]:
            # OASIS codes have format like "21231.00"
            assert isinstance(key, str)
            assert "." in key or key.isdigit()

    def test_values_are_strings(self, gold_path):
        """Test dictionary values are non-empty strings."""
        lead_statements = load_lead_statements(gold_path)

        for value in list(lead_statements.values())[:10]:
            assert isinstance(value, str)
            assert len(value) > 0


class TestGetLeadStatementForOasis:
    """Tests for get_lead_statement_for_oasis function."""

    def test_returns_text_for_valid_code(self, gold_path):
        """Test returns lead statement text for valid OASIS code."""
        # First get a valid code from the loaded statements
        lead_statements = load_lead_statements(gold_path)
        valid_code = list(lead_statements.keys())[0]

        result = get_lead_statement_for_oasis(valid_code, gold_path)

        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    def test_returns_none_for_invalid_code(self, gold_path):
        """Test returns None for invalid OASIS code."""
        result = get_lead_statement_for_oasis("INVALID_CODE_999", gold_path)

        assert result is None

    def test_returns_none_for_empty_code(self, gold_path):
        """Test returns None for empty string code."""
        result = get_lead_statement_for_oasis("", gold_path)

        assert result is None


# =============================================================================
# Source Type Determination Tests
# =============================================================================


class TestDetermineSourceType:
    """Tests for determine_source_type function."""

    def test_returns_authoritative_when_has_lead_statement(self):
        """Test returns AUTHORITATIVE when has_lead_statement=True."""
        result = determine_source_type("21231.00", has_lead_statement=True)

        assert result == DescriptionSource.AUTHORITATIVE

    def test_returns_llm_when_no_lead_statement(self):
        """Test returns LLM when has_lead_statement=False."""
        result = determine_source_type("21231.00", has_lead_statement=False)

        assert result == DescriptionSource.LLM

    def test_returns_llm_when_oasis_code_is_none(self):
        """Test returns LLM when oasis_profile_code is None."""
        result = determine_source_type(None, has_lead_statement=False)

        assert result == DescriptionSource.LLM

    def test_returns_llm_when_oasis_none_even_if_has_lead_statement(self):
        """Test returns LLM when oasis_profile_code is None regardless of has_lead_statement.

        This is a defensive case - if oasis_profile_code is None,
        has_lead_statement should logically be False, but we test
        that the function handles edge cases correctly.
        """
        # This combination shouldn't happen in practice, but test defensive behavior
        result = determine_source_type(None, has_lead_statement=True)

        # When oasis_profile_code is None, should still return LLM
        assert result == DescriptionSource.LLM


# =============================================================================
# Cache Management Tests
# =============================================================================


class TestClearLeadStatementCache:
    """Tests for clear_lead_statement_cache function."""

    def test_clear_cache_works(self, gold_path):
        """Test clear_lead_statement_cache clears the cache."""
        # Load to populate cache
        load_lead_statements(gold_path)

        # Get cache info before clear
        cache_info_before = load_lead_statements.cache_info()
        assert cache_info_before.currsize == 1

        # Clear cache
        clear_lead_statement_cache()

        # Get cache info after clear
        cache_info_after = load_lead_statements.cache_info()
        assert cache_info_after.currsize == 0
