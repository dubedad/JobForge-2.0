"""Tests for LLM imputation module.

Tests cover:
- Prompt building (no API key needed)
- Client configuration and availability
- Service orchestration (mocked API)
- Response model parsing
"""

import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from jobforge.external.llm import (
    IMPUTATION_SYSTEM_PROMPT,
    LLM_IMPUTATION_MODEL,
    LLM_SOURCE_PRECEDENCE,
    AttributeImputationService,
    LLMClient,
    build_imputation_prompt,
    impute_missing_attributes,
)
from jobforge.external.models import (
    ImputationResponse,
    ImputedAttributeValue,
    LLMImputedAttribute,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_imputation_response():
    """Create a mock ImputationResponse for testing."""
    return ImputationResponse(
        imputations=[
            ImputedAttributeValue(
                attribute_name="leadership",
                value="Strong leadership skills required for team coordination",
                confidence=0.75,
                rationale="Data analysts often lead cross-functional projects",
            ),
            ImputedAttributeValue(
                attribute_name="communication",
                value="Excellent written and verbal communication",
                confidence=0.85,
                rationale="Role requires presenting findings to stakeholders",
            ),
        ],
        context_used="Job title and family context",
    )


@pytest.fixture
def mock_low_confidence_response():
    """Create a mock response with low confidence for acceptance testing."""
    return ImputationResponse(
        imputations=[
            ImputedAttributeValue(
                attribute_name="physical_demands",
                value="Sedentary work environment",
                confidence=0.2,  # Low confidence
                rationale="Uncertain without specific workplace context",
            ),
        ],
        context_used="Limited context available",
    )


# =============================================================================
# Prompt Building Tests (No API Key Needed)
# =============================================================================


class TestBuildImputationPrompt:
    """Tests for build_imputation_prompt function."""

    def test_build_prompt_minimal(self):
        """Test prompt with only job title and missing attrs."""
        prompt = build_imputation_prompt(
            job_title="Software Developer",
            job_family=None,
            job_function=None,
            unit_group=None,
            known_attributes={},
            missing_attributes=["leadership"],
        )

        assert "Job Title: Software Developer" in prompt
        assert "leadership" in prompt
        assert "Known Attributes:" in prompt

    def test_build_prompt_full_context(self):
        """Test prompt with all context fields populated."""
        prompt = build_imputation_prompt(
            job_title="Data Analyst",
            job_family="Analytics",
            job_function="Business Intelligence",
            unit_group="21211",
            known_attributes={"skill1": "Python", "skill2": "SQL"},
            missing_attributes=["leadership", "communication"],
        )

        assert "Job Title: Data Analyst" in prompt
        assert "Job Family: Analytics" in prompt
        assert "Job Function: Business Intelligence" in prompt
        assert "NOC Unit Group: 21211" in prompt
        assert "skill1: Python" in prompt
        assert "skill2: SQL" in prompt
        assert "leadership, communication" in prompt

    def test_build_prompt_known_attributes(self):
        """Test that known attributes are properly formatted."""
        prompt = build_imputation_prompt(
            job_title="Manager",
            job_family=None,
            job_function=None,
            unit_group=None,
            known_attributes={"domain_knowledge": "Healthcare", "years_experience": "5+"},
            missing_attributes=["certification"],
        )

        assert "- domain_knowledge: Healthcare" in prompt
        assert "- years_experience: 5+" in prompt

    def test_build_prompt_empty_known_attributes(self):
        """Test prompt when no known attributes exist."""
        prompt = build_imputation_prompt(
            job_title="Analyst",
            job_family=None,
            job_function=None,
            unit_group=None,
            known_attributes={},
            missing_attributes=["skill1"],
        )

        assert "Known Attributes:\nNone" in prompt

    def test_build_prompt_multiple_missing(self):
        """Test prompt with multiple missing attributes."""
        prompt = build_imputation_prompt(
            job_title="Engineer",
            job_family=None,
            job_function=None,
            unit_group=None,
            known_attributes={},
            missing_attributes=["attr1", "attr2", "attr3"],
        )

        assert "attr1, attr2, attr3" in prompt


class TestImputationSystemPrompt:
    """Tests for the system prompt constant."""

    def test_system_prompt_exists(self):
        """Test that system prompt is defined and non-empty."""
        assert IMPUTATION_SYSTEM_PROMPT
        assert len(IMPUTATION_SYSTEM_PROMPT) > 100

    def test_system_prompt_content(self):
        """Test that system prompt contains key instructions."""
        assert "workforce analyst" in IMPUTATION_SYSTEM_PROMPT.lower()
        assert "confidence" in IMPUTATION_SYSTEM_PROMPT.lower()
        assert "rationale" in IMPUTATION_SYSTEM_PROMPT.lower()


# =============================================================================
# Client Tests
# =============================================================================


class TestLLMClient:
    """Tests for LLMClient class."""

    def test_client_default_model(self):
        """Test client uses correct default model."""
        assert LLM_IMPUTATION_MODEL == "gpt-4o-2024-08-06"

    def test_client_is_available_no_key(self):
        """Test is_available returns False when no API key."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
            # Need to clear existing key if any
            env_copy = os.environ.copy()
            if "OPENAI_API_KEY" in env_copy:
                del env_copy["OPENAI_API_KEY"]

            with patch.dict(os.environ, env_copy, clear=True):
                client = LLMClient(api_key=None)
                assert client.is_available() is False

    def test_client_is_available_with_key(self):
        """Test is_available returns True with API key."""
        client = LLMClient(api_key="test-api-key")
        assert client.is_available() is True

    def test_client_custom_model(self):
        """Test client accepts custom model."""
        client = LLMClient(api_key="test-key", model="gpt-4-turbo")
        assert client.model == "gpt-4-turbo"

    def test_client_parse_requires_key(self):
        """Test that parse raises error without API key."""
        with patch.dict(os.environ, {}, clear=True):
            client = LLMClient(api_key=None)
            with pytest.raises(ValueError, match="No OpenAI API key"):
                client.parse(
                    messages=[{"role": "user", "content": "test"}],
                    response_format=ImputationResponse,
                )


# =============================================================================
# Service Tests (Mocked API)
# =============================================================================


class TestAttributeImputationService:
    """Tests for AttributeImputationService class."""

    def test_service_empty_missing_returns_empty(self):
        """Test service returns empty list for no missing attributes."""
        service = AttributeImputationService(client=MagicMock())
        result = service.impute_attributes(
            job_title="Analyst",
            missing_attributes=[],
        )
        assert result == []

    def test_service_imputes_single_attribute(self, mock_imputation_response):
        """Test service returns LLMImputedAttribute for single attribute."""
        mock_client = MagicMock()
        mock_client.parse.return_value = mock_imputation_response
        mock_client.model = LLM_IMPUTATION_MODEL

        service = AttributeImputationService(client=mock_client)
        result = service.impute_attributes(
            job_title="Data Analyst",
            missing_attributes=["leadership"],
        )

        assert len(result) == 2  # Response has 2 imputations
        assert all(isinstance(r, LLMImputedAttribute) for r in result)

    def test_service_imputes_multiple_attributes(self, mock_imputation_response):
        """Test service handles batch of attributes."""
        mock_client = MagicMock()
        mock_client.parse.return_value = mock_imputation_response
        mock_client.model = LLM_IMPUTATION_MODEL

        service = AttributeImputationService(client=mock_client)
        result = service.impute_attributes(
            job_title="Data Analyst",
            missing_attributes=["leadership", "communication"],
            job_family="Analytics",
        )

        assert len(result) == 2
        names = [r.attribute_name for r in result]
        assert "leadership" in names
        assert "communication" in names

    def test_service_sets_provenance(self, mock_imputation_response):
        """Test source_type='LLM' and model_used are set."""
        mock_client = MagicMock()
        mock_client.parse.return_value = mock_imputation_response
        mock_client.model = "gpt-4o-2024-08-06"

        service = AttributeImputationService(client=mock_client)
        result = service.impute_attributes(
            job_title="Data Analyst",
            missing_attributes=["leadership"],
        )

        assert all(r.source_type == "LLM" for r in result)
        assert all(r.model_used == "gpt-4o-2024-08-06" for r in result)

    def test_service_preserves_low_confidence(self, mock_low_confidence_response):
        """Test service doesn't filter by confidence per CONTEXT.md."""
        mock_client = MagicMock()
        mock_client.parse.return_value = mock_low_confidence_response
        mock_client.model = LLM_IMPUTATION_MODEL

        service = AttributeImputationService(client=mock_client)
        result = service.impute_attributes(
            job_title="Unknown Role",
            missing_attributes=["physical_demands"],
        )

        # Low confidence (0.2) should still be returned
        assert len(result) == 1
        assert result[0].confidence == 0.2

    def test_service_includes_rationale(self, mock_imputation_response):
        """Test rationale field is populated."""
        mock_client = MagicMock()
        mock_client.parse.return_value = mock_imputation_response
        mock_client.model = LLM_IMPUTATION_MODEL

        service = AttributeImputationService(client=mock_client)
        result = service.impute_attributes(
            job_title="Data Analyst",
            missing_attributes=["leadership"],
        )

        assert all(r.rationale for r in result)
        assert "cross-functional" in result[0].rationale

    def test_service_sets_timestamp(self, mock_imputation_response):
        """Test imputed_at timestamp is set."""
        mock_client = MagicMock()
        mock_client.parse.return_value = mock_imputation_response
        mock_client.model = LLM_IMPUTATION_MODEL

        before = datetime.now(timezone.utc)
        service = AttributeImputationService(client=mock_client)
        result = service.impute_attributes(
            job_title="Data Analyst",
            missing_attributes=["leadership"],
        )
        after = datetime.now(timezone.utc)

        assert all(before <= r.imputed_at <= after for r in result)


class TestImputeMissingAttributesFunction:
    """Tests for the convenience function."""

    def test_convenience_function_works(self, mock_imputation_response):
        """Test impute_missing_attributes function."""
        with patch(
            "jobforge.external.llm.service.LLMClient"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client.parse.return_value = mock_imputation_response
            mock_client.model = LLM_IMPUTATION_MODEL
            mock_client_class.return_value = mock_client

            result = impute_missing_attributes(
                job_title="Manager",
                missing_attributes=["leadership"],
            )

            assert len(result) == 2


# =============================================================================
# Response Model Tests
# =============================================================================


class TestResponseModels:
    """Tests for Pydantic response models."""

    def test_imputation_response_parses(self):
        """Test valid JSON parses to ImputationResponse."""
        data = {
            "imputations": [
                {
                    "attribute_name": "skill1",
                    "value": "Python programming",
                    "confidence": 0.9,
                    "rationale": "Common requirement",
                }
            ],
            "context_used": "Job title analysis",
        }
        response = ImputationResponse(**data)

        assert len(response.imputations) == 1
        assert response.imputations[0].attribute_name == "skill1"
        assert response.context_used == "Job title analysis"

    def test_imputed_attribute_confidence_bounds(self):
        """Test confidence is validated to 0.0-1.0 range."""
        # Valid bounds
        low = ImputedAttributeValue(
            attribute_name="test",
            value="test",
            confidence=0.0,
            rationale="test",
        )
        assert low.confidence == 0.0

        high = ImputedAttributeValue(
            attribute_name="test",
            value="test",
            confidence=1.0,
            rationale="test",
        )
        assert high.confidence == 1.0

        # Invalid bounds should raise
        with pytest.raises(ValueError):
            ImputedAttributeValue(
                attribute_name="test",
                value="test",
                confidence=1.5,  # Too high
                rationale="test",
            )

        with pytest.raises(ValueError):
            ImputedAttributeValue(
                attribute_name="test",
                value="test",
                confidence=-0.1,  # Too low
                rationale="test",
            )

    def test_llm_imputed_attribute_timestamp(self):
        """Test LLMImputedAttribute gets timestamp."""
        attr = LLMImputedAttribute(
            attribute_name="leadership",
            value="Strong",
            confidence=0.8,
            rationale="Required for role",
            model_used="gpt-4o",
        )

        assert attr.imputed_at is not None
        assert attr.source_type == "LLM"

    def test_llm_imputed_attribute_serialization(self):
        """Test model serializes to JSON properly."""
        attr = LLMImputedAttribute(
            attribute_name="skill",
            value="Python",
            confidence=0.9,
            rationale="Technical role",
            model_used="gpt-4o-2024-08-06",
            imputed_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        )

        json_data = attr.model_dump_json()
        assert "skill" in json_data
        assert "2024-01-15" in json_data


# =============================================================================
# Source Precedence Tests
# =============================================================================


class TestSourcePrecedence:
    """Tests for LLM source precedence."""

    def test_llm_precedence_is_lowest(self):
        """Test LLM has precedence 1 (lowest)."""
        assert LLM_SOURCE_PRECEDENCE == 1

    def test_llm_precedence_matches_enum(self):
        """Test LLM precedence matches SourcePrecedence enum."""
        from jobforge.external.models import SourcePrecedence

        assert LLM_SOURCE_PRECEDENCE == SourcePrecedence.LLM
