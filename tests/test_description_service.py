"""Tests for description generation service and prompts.

Tests cover:
- Prompt templates (system prompt, title prompt, aggregate prompt)
- DescriptionResponse model parsing
- DescriptionGenerationService instantiation and methods
- Source cascade (AUTHORITATIVE vs LLM)
- Provenance tracking for all descriptions
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jobforge.description import (
    DescriptionGenerationService,
    DescriptionSource,
    GeneratedDescription,
    clear_lead_statement_cache,
    generate_description,
)
from jobforge.description.prompts import (
    DESCRIPTION_SYSTEM_PROMPT,
    DescriptionResponse,
    build_aggregate_description_prompt,
    build_title_description_prompt,
)
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
def mock_llm_response():
    """Create a mock LLM response."""
    return DescriptionResponse(
        description="Data analysts collect, process, and analyze data to provide insights for business decisions.",
        confidence=0.85,
        context_used="NOC Unit Group: Data scientists, Job Family: Analytics",
    )


@pytest.fixture
def mock_llm_client(mock_llm_response):
    """Create a mock LLM client that returns a canned response."""
    client = MagicMock()
    client.parse.return_value = mock_llm_response
    client.model = "gpt-4o-2024-08-06"
    client.is_available.return_value = True
    return client


# =============================================================================
# DESCRIPTION_SYSTEM_PROMPT Tests
# =============================================================================


class TestDescriptionSystemPrompt:
    """Tests for DESCRIPTION_SYSTEM_PROMPT constant."""

    def test_contains_noc_style_guidance(self):
        """Test system prompt contains NOC style guidance."""
        assert "NOC" in DESCRIPTION_SYSTEM_PROMPT
        assert "National Occupational Classification" in DESCRIPTION_SYSTEM_PROMPT

    def test_prohibits_you_your_phrasing(self):
        """Test system prompt prohibits you/your phrasing."""
        assert 'Do NOT use "you"' in DESCRIPTION_SYSTEM_PROMPT
        assert '"your"' in DESCRIPTION_SYSTEM_PROMPT
        assert "this role involves" in DESCRIPTION_SYSTEM_PROMPT.lower()

    def test_specifies_third_person_voice(self):
        """Test system prompt specifies third-person voice."""
        assert "third-person" in DESCRIPTION_SYSTEM_PROMPT

    def test_specifies_formal_voice(self):
        """Test system prompt specifies formal voice."""
        assert "formal" in DESCRIPTION_SYSTEM_PROMPT.lower()

    def test_mentions_2_4_sentences(self):
        """Test system prompt specifies description length."""
        assert "2-4 sentences" in DESCRIPTION_SYSTEM_PROMPT


# =============================================================================
# build_title_description_prompt Tests
# =============================================================================


class TestBuildTitleDescriptionPrompt:
    """Tests for build_title_description_prompt function."""

    def test_includes_job_title(self):
        """Test prompt includes the job title."""
        prompt = build_title_description_prompt(
            job_title="Data Analyst",
            job_family=None,
            job_function=None,
            unit_group_title=None,
            unit_group_definition=None,
        )
        assert "Data Analyst" in prompt

    def test_includes_noc_context_when_provided(self):
        """Test prompt includes NOC context when provided."""
        prompt = build_title_description_prompt(
            job_title="Data Analyst",
            job_family="Analytics",
            job_function="Information Technology",
            unit_group_title="Data scientists",
            unit_group_definition="Data scientists develop and implement...",
            labels=["Data scientists", "Data analysts"],
        )

        assert "Data scientists" in prompt
        assert "Analytics" in prompt
        assert "Information Technology" in prompt
        assert "Data scientists develop and implement" in prompt
        assert "Data analysts" in prompt

    def test_handles_missing_optional_fields(self):
        """Test prompt handles missing optional fields gracefully."""
        prompt = build_title_description_prompt(
            job_title="Software Engineer",
            job_family=None,
            job_function=None,
            unit_group_title=None,
            unit_group_definition=None,
            labels=None,
        )

        assert "Software Engineer" in prompt
        assert prompt  # Should not be empty

    def test_includes_boundary_words_from_labels(self):
        """Test prompt includes labels as NOC boundary words."""
        labels = ["Software engineers", "Systems designers", "Application architects"]
        prompt = build_title_description_prompt(
            job_title="Backend Developer",
            job_family=None,
            job_function=None,
            unit_group_title="Software engineers and designers",
            unit_group_definition=None,
            labels=labels,
        )

        for label in labels:
            assert label in prompt

    def test_includes_unit_group_title(self):
        """Test prompt includes unit group title."""
        prompt = build_title_description_prompt(
            job_title="Network Admin",
            job_family=None,
            job_function=None,
            unit_group_title="Computer network technicians",
            unit_group_definition=None,
        )

        assert "Computer network technicians" in prompt


# =============================================================================
# build_aggregate_description_prompt Tests
# =============================================================================


class TestBuildAggregateDescriptionPrompt:
    """Tests for build_aggregate_description_prompt function."""

    def test_family_type_prompt(self):
        """Test prompt for family entity type."""
        prompt = build_aggregate_description_prompt(
            entity_name="Analytics & Insights",
            entity_type="family",
            member_titles=["Data Analyst", "BI Developer"],
        )

        assert "job family" in prompt
        assert "Analytics & Insights" in prompt

    def test_function_type_prompt(self):
        """Test prompt for function entity type."""
        prompt = build_aggregate_description_prompt(
            entity_name="Information Technology",
            entity_type="function",
            member_titles=["Developer", "DBA"],
        )

        assert "job function" in prompt
        assert "Information Technology" in prompt

    def test_includes_member_titles(self):
        """Test prompt includes member titles."""
        member_titles = ["Data Analyst", "BI Developer", "Data Scientist"]
        prompt = build_aggregate_description_prompt(
            entity_name="Analytics",
            entity_type="family",
            member_titles=member_titles,
        )

        for title in member_titles:
            assert title in prompt

    def test_truncates_long_member_list(self):
        """Test prompt truncates member titles list if too long."""
        many_titles = [f"Job Title {i}" for i in range(20)]
        prompt = build_aggregate_description_prompt(
            entity_name="Large Family",
            entity_type="family",
            member_titles=many_titles,
        )

        # Should mention showing subset
        assert "showing 10 of 20" in prompt

    def test_handles_empty_member_titles(self):
        """Test prompt handles empty member titles list."""
        prompt = build_aggregate_description_prompt(
            entity_name="Empty Family",
            entity_type="family",
            member_titles=[],
        )

        assert "No sample job titles provided" in prompt

    def test_includes_noc_context_when_provided(self):
        """Test prompt includes NOC context when provided."""
        prompt = build_aggregate_description_prompt(
            entity_name="Tech Family",
            entity_type="family",
            member_titles=["Developer"],
            noc_context="Unit Group 21231 - Software engineers",
        )

        assert "Unit Group 21231" in prompt


# =============================================================================
# DescriptionResponse Model Tests
# =============================================================================


class TestDescriptionResponse:
    """Tests for DescriptionResponse model."""

    def test_parsing_valid_response(self):
        """Test DescriptionResponse parses valid data."""
        response = DescriptionResponse(
            description="Engineers design software systems.",
            confidence=0.9,
            context_used="NOC context provided",
        )

        assert response.description == "Engineers design software systems."
        assert response.confidence == 0.9
        assert response.context_used == "NOC context provided"

    def test_confidence_bounds_valid_low(self):
        """Test confidence 0.0 is valid."""
        response = DescriptionResponse(
            description="Test",
            confidence=0.0,
            context_used="None",
        )
        assert response.confidence == 0.0

    def test_confidence_bounds_valid_high(self):
        """Test confidence 1.0 is valid."""
        response = DescriptionResponse(
            description="Test",
            confidence=1.0,
            context_used="Full context",
        )
        assert response.confidence == 1.0

    def test_confidence_bounds_invalid_too_high(self):
        """Test confidence > 1.0 raises validation error."""
        with pytest.raises(ValueError):
            DescriptionResponse(
                description="Test",
                confidence=1.5,
                context_used="None",
            )

    def test_confidence_bounds_invalid_too_low(self):
        """Test confidence < 0.0 raises validation error."""
        with pytest.raises(ValueError):
            DescriptionResponse(
                description="Test",
                confidence=-0.1,
                context_used="None",
            )


# =============================================================================
# Service Instantiation Tests
# =============================================================================


class TestServiceInstantiation:
    """Tests for DescriptionGenerationService instantiation."""

    def test_instantiation_with_defaults(self):
        """Test service instantiation with default settings."""
        service = DescriptionGenerationService()

        assert service.llm_client is not None
        assert service.gold_path is not None
        assert isinstance(service.gold_path, Path)

    def test_instantiation_with_custom_gold_path(self, gold_path):
        """Test service instantiation with custom gold_path."""
        service = DescriptionGenerationService(gold_path=gold_path)

        assert service.gold_path == gold_path

    def test_instantiation_with_custom_llm_client(self, mock_llm_client):
        """Test service instantiation with custom LLM client."""
        service = DescriptionGenerationService(llm_client=mock_llm_client)

        assert service.llm_client == mock_llm_client


# =============================================================================
# generate_title_description Tests
# =============================================================================


class TestGenerateTitleDescription:
    """Tests for generate_title_description method."""

    def test_returns_authoritative_when_lead_statement_exists(self, gold_path):
        """Test returns AUTHORITATIVE when lead statement exists."""
        # Use a mock client since we won't need it for authoritative path
        mock_client = MagicMock()
        service = DescriptionGenerationService(llm_client=mock_client, gold_path=gold_path)

        # Use a known job title that matches L6 label and has lead statement
        # "Administrative officers" should match in UG 13100
        result = service.generate_title_description(
            job_title="Administrative officers",
            unit_group_id="13100",
        )

        # Should be authoritative (from lead statement)
        assert result.provenance.source_type == DescriptionSource.AUTHORITATIVE
        assert result.description  # Should have content
        assert len(result.description) > 0

        # LLM should NOT have been called
        mock_client.parse.assert_not_called()

    def test_returns_llm_when_no_lead_statement(self, mock_llm_client, gold_path):
        """Test returns LLM when no lead statement found."""
        service = DescriptionGenerationService(llm_client=mock_llm_client, gold_path=gold_path)

        # Use a made-up job title that won't have a lead statement
        result = service.generate_title_description(
            job_title="Chief Innovation Specialist",
            unit_group_id="00018",  # Valid UG but unlikely title match
        )

        # Should be LLM (fallback)
        assert result.provenance.source_type == DescriptionSource.LLM
        mock_llm_client.parse.assert_called_once()

    def test_uses_resolution_to_find_oasis_code(self, gold_path):
        """Test uses resolution to find OASIS code."""
        mock_client = MagicMock()
        service = DescriptionGenerationService(llm_client=mock_client, gold_path=gold_path)

        # Direct L6 match should resolve
        result = service.generate_title_description(
            job_title="Administrative officers",
            unit_group_id="13100",
        )

        # Should have resolution method in provenance
        assert result.provenance.resolution_method is not None

    def test_includes_noc_boundary_words_in_llm_prompt(self, mock_llm_client, gold_path):
        """Test LLM prompt includes NOC boundary words."""
        service = DescriptionGenerationService(llm_client=mock_llm_client, gold_path=gold_path)

        # Use an invalid UG to ensure LLM path is taken (no authoritative source)
        service.generate_title_description(
            job_title="Custom Title",
            unit_group_id="00018",  # UG with limited labels
            job_family="Analytics",
        )

        # Check that parse was called with messages containing NOC context
        mock_llm_client.parse.assert_called_once()
        call_args = mock_llm_client.parse.call_args
        messages = call_args[1]["messages"]

        # User message should contain the job title and family
        user_message = messages[1]["content"]
        assert "Custom Title" in user_message
        assert "Analytics" in user_message


# =============================================================================
# generate_family_description Tests
# =============================================================================


class TestGenerateFamilyDescription:
    """Tests for generate_family_description method."""

    def test_returns_llm_source(self, mock_llm_client, gold_path):
        """Test family description always returns LLM source."""
        service = DescriptionGenerationService(llm_client=mock_llm_client, gold_path=gold_path)

        result = service.generate_family_description(
            family_name="Analytics & Insights",
            member_titles=["Data Analyst", "BI Developer"],
        )

        assert result.provenance.source_type == DescriptionSource.LLM
        assert result.entity_type == "family"

    def test_includes_member_titles_in_prompt(self, mock_llm_client, gold_path):
        """Test family description includes member titles in prompt."""
        service = DescriptionGenerationService(llm_client=mock_llm_client, gold_path=gold_path)

        member_titles = ["Data Analyst", "BI Developer", "Data Scientist"]
        service.generate_family_description(
            family_name="Analytics",
            member_titles=member_titles,
        )

        # Check prompt contains member titles
        call_args = mock_llm_client.parse.call_args
        user_message = call_args[1]["messages"][1]["content"]

        for title in member_titles:
            assert title in user_message


# =============================================================================
# generate_function_description Tests
# =============================================================================


class TestGenerateFunctionDescription:
    """Tests for generate_function_description method."""

    def test_returns_llm_source(self, mock_llm_client, gold_path):
        """Test function description always returns LLM source."""
        service = DescriptionGenerationService(llm_client=mock_llm_client, gold_path=gold_path)

        result = service.generate_function_description(
            function_name="Information Technology",
            member_titles=["Developer", "DBA"],
        )

        assert result.provenance.source_type == DescriptionSource.LLM
        assert result.entity_type == "function"

    def test_handles_empty_member_titles(self, mock_llm_client, gold_path):
        """Test function description handles empty member titles."""
        service = DescriptionGenerationService(llm_client=mock_llm_client, gold_path=gold_path)

        result = service.generate_function_description(
            function_name="Empty Function",
            member_titles=None,
        )

        assert result is not None
        assert result.entity_name == "Empty Function"


# =============================================================================
# generate_description Convenience Function Tests
# =============================================================================


class TestGenerateDescriptionConvenience:
    """Tests for generate_description convenience function."""

    def test_routes_title_correctly(self):
        """Test convenience function routes title type correctly."""
        from jobforge.description import DescriptionProvenance

        with patch("jobforge.description.service.DescriptionGenerationService") as MockService:
            mock_instance = MagicMock()
            mock_instance.generate_title_description.return_value = GeneratedDescription(
                entity_type="title",
                entity_id="Test",
                entity_name="Test",
                description="Test description",
                provenance=DescriptionProvenance(
                    source_type=DescriptionSource.LLM,
                    confidence=0.85,
                ),
            )
            MockService.return_value = mock_instance

            result = generate_description(
                entity_type="title",
                entity_name="Test Job",
                unit_group_id="21211",
            )

            mock_instance.generate_title_description.assert_called_once_with(
                job_title="Test Job",
                unit_group_id="21211",
                job_family=None,
                job_function=None,
            )

    def test_routes_family_correctly(self):
        """Test convenience function routes family type correctly."""
        from jobforge.description import DescriptionProvenance

        with patch("jobforge.description.service.DescriptionGenerationService") as MockService:
            mock_instance = MagicMock()
            mock_instance.generate_family_description.return_value = GeneratedDescription(
                entity_type="family",
                entity_id="Test Family",
                entity_name="Test Family",
                description="Test description",
                provenance=DescriptionProvenance(
                    source_type=DescriptionSource.LLM,
                    confidence=0.85,
                ),
            )
            MockService.return_value = mock_instance

            result = generate_description(
                entity_type="family",
                entity_name="Test Family",
                member_titles=["Title 1", "Title 2"],
            )

            mock_instance.generate_family_description.assert_called_once()

    def test_routes_function_correctly(self):
        """Test convenience function routes function type correctly."""
        from jobforge.description import DescriptionProvenance

        with patch("jobforge.description.service.DescriptionGenerationService") as MockService:
            mock_instance = MagicMock()
            mock_instance.generate_function_description.return_value = GeneratedDescription(
                entity_type="function",
                entity_id="Test Function",
                entity_name="Test Function",
                description="Test description",
                provenance=DescriptionProvenance(
                    source_type=DescriptionSource.LLM,
                    confidence=0.85,
                ),
            )
            MockService.return_value = mock_instance

            result = generate_description(
                entity_type="function",
                entity_name="Test Function",
            )

            mock_instance.generate_function_description.assert_called_once()

    def test_raises_error_for_title_without_unit_group(self):
        """Test convenience function raises error for title without unit_group_id."""
        with pytest.raises(ValueError, match="unit_group_id is required"):
            generate_description(
                entity_type="title",
                entity_name="Test Job",
                # Missing unit_group_id
            )


# =============================================================================
# Provenance Tests
# =============================================================================


class TestProvenanceTracking:
    """Tests for provenance tracking on descriptions."""

    def test_authoritative_description_has_confidence_from_resolution(self, gold_path):
        """Test AUTHORITATIVE description has confidence from resolution."""
        mock_client = MagicMock()
        service = DescriptionGenerationService(llm_client=mock_client, gold_path=gold_path)

        result = service.generate_title_description(
            job_title="Administrative officers",
            unit_group_id="13100",
        )

        # Confidence should be from resolution algorithm
        assert result.provenance.confidence is not None
        assert 0.0 <= result.provenance.confidence <= 1.0

    def test_llm_description_has_confidence_from_llm_response(self, mock_llm_client, gold_path):
        """Test LLM description has confidence from LLM response."""
        service = DescriptionGenerationService(llm_client=mock_llm_client, gold_path=gold_path)

        result = service.generate_title_description(
            job_title="Custom Title",
            unit_group_id="00018",
        )

        # Confidence should be 0.85 from mock response
        assert result.provenance.confidence == 0.85

    def test_authoritative_description_has_resolution_method(self, gold_path):
        """Test AUTHORITATIVE description has resolution_method populated."""
        mock_client = MagicMock()
        service = DescriptionGenerationService(llm_client=mock_client, gold_path=gold_path)

        result = service.generate_title_description(
            job_title="Administrative officers",
            unit_group_id="13100",
        )

        assert result.provenance.resolution_method is not None

    def test_llm_description_has_model_version(self, mock_llm_client, gold_path):
        """Test LLM description has model_version populated."""
        service = DescriptionGenerationService(llm_client=mock_llm_client, gold_path=gold_path)

        result = service.generate_title_description(
            job_title="Custom Title",
            unit_group_id="00018",
        )

        assert result.provenance.model_version == "gpt-4o-2024-08-06"

    def test_all_descriptions_have_timestamp(self, mock_llm_client, gold_path):
        """Test all descriptions have timestamp."""
        service = DescriptionGenerationService(llm_client=mock_llm_client, gold_path=gold_path)

        # Test LLM path
        result_llm = service.generate_title_description(
            job_title="Custom Title",
            unit_group_id="00018",
        )
        assert result_llm.provenance.timestamp is not None
        assert isinstance(result_llm.provenance.timestamp, datetime)

        # Test authoritative path
        mock_client2 = MagicMock()
        service2 = DescriptionGenerationService(llm_client=mock_client2, gold_path=gold_path)
        result_auth = service2.generate_title_description(
            job_title="Administrative officers",
            unit_group_id="13100",
        )
        assert result_auth.provenance.timestamp is not None
        assert isinstance(result_auth.provenance.timestamp, datetime)

    def test_llm_description_has_input_context(self, mock_llm_client, gold_path):
        """Test LLM description has input_context from response."""
        service = DescriptionGenerationService(llm_client=mock_llm_client, gold_path=gold_path)

        result = service.generate_title_description(
            job_title="Custom Title",
            unit_group_id="00018",
        )

        # Should have context_used from mock response
        assert result.provenance.input_context is not None
        assert "NOC Unit Group" in result.provenance.input_context


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_unknown_unit_group_still_generates(self, mock_llm_client, gold_path):
        """Test description generation for unknown unit group."""
        service = DescriptionGenerationService(llm_client=mock_llm_client, gold_path=gold_path)

        # Use a completely invalid UG ID
        result = service.generate_title_description(
            job_title="Mystery Job",
            unit_group_id="99999",  # Invalid UG
        )

        # Should still generate via LLM
        assert result is not None
        assert result.provenance.source_type == DescriptionSource.LLM

    def test_empty_labels_handled(self, mock_llm_client, gold_path):
        """Test prompt handles unit group with no labels."""
        service = DescriptionGenerationService(llm_client=mock_llm_client, gold_path=gold_path)

        # Valid UG but title won't match any label
        result = service.generate_title_description(
            job_title="Very Unique Title",
            unit_group_id="21211",
        )

        assert result is not None
