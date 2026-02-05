"""Tests for TBS OG scraper, subgroup parser, and definition fetcher.

Tests cover:
- OGSubgroup model validation
- OGDefinition model validation
- parse_og_subgroups function with various input patterns
- fetch_og_definition with mocked HTTP responses
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from jobforge.external.tbs.link_fetcher import fetch_og_definition
from jobforge.external.tbs.models import (
    OccupationalGroupRow,
    OGDefinition,
    OGScrapedData,
    OGSubgroup,
    ScrapedProvenance,
)
from jobforge.external.tbs.parser import parse_og_subgroups


class TestOGSubgroupModel:
    """Tests for OGSubgroup Pydantic model."""

    def test_valid_subgroup(self):
        """Test creating a valid OGSubgroup."""
        subgroup = OGSubgroup(
            og_code="AS",
            subgroup_code="AS-01",
            subgroup_name="Administrative Support Level 1",
            definition_url="https://example.com/def",
            qualification_standard_url="https://example.com/qual",
            rates_of_pay_url=None,
            source_url="https://www.canada.ca/en/tbs/og",
            scraped_at=datetime.now(timezone.utc),
        )
        assert subgroup.og_code == "AS"
        assert subgroup.subgroup_code == "AS-01"
        assert subgroup.subgroup_name == "Administrative Support Level 1"
        assert subgroup.rates_of_pay_url is None

    def test_subgroup_with_all_optional_none(self):
        """Test subgroup with all optional fields as None."""
        subgroup = OGSubgroup(
            og_code="AI",
            subgroup_code="AI-NOP",
            subgroup_name="Non-Operational",
            definition_url=None,
            qualification_standard_url=None,
            rates_of_pay_url=None,
            source_url="https://www.canada.ca/en/tbs/og",
            scraped_at=datetime.now(timezone.utc),
        )
        assert subgroup.definition_url is None
        assert subgroup.qualification_standard_url is None

    def test_subgroup_serialization(self):
        """Test that OGSubgroup serializes to JSON correctly."""
        scraped_at = datetime(2026, 1, 20, 12, 0, 0, tzinfo=timezone.utc)
        subgroup = OGSubgroup(
            og_code="AS",
            subgroup_code="AS-01",
            subgroup_name="Test",
            source_url="https://example.com",
            scraped_at=scraped_at,
        )
        data = subgroup.model_dump(mode="json")
        assert data["og_code"] == "AS"
        assert data["subgroup_code"] == "AS-01"
        assert "scraped_at" in data


class TestOGDefinitionModel:
    """Tests for OGDefinition Pydantic model."""

    def test_valid_definition_with_subgroup(self):
        """Test creating a definition for a subgroup."""
        definition = OGDefinition(
            og_code="AS",
            subgroup_code="AS-01",
            definition_text="This is the definition text for AS-01.",
            page_title="TBS Definitions",
            source_url="https://example.com/def",
            scraped_at=datetime.now(timezone.utc),
        )
        assert definition.og_code == "AS"
        assert definition.subgroup_code == "AS-01"
        assert "AS-01" in definition.definition_text

    def test_valid_definition_parent_only(self):
        """Test creating a definition for parent OG (no subgroup)."""
        definition = OGDefinition(
            og_code="AI",
            subgroup_code=None,
            definition_text="Air Traffic Control Group comprises positions...",
            page_title="TBS Definitions",
            source_url="https://example.com/def",
            scraped_at=datetime.now(timezone.utc),
        )
        assert definition.og_code == "AI"
        assert definition.subgroup_code is None

    def test_definition_serialization(self):
        """Test that OGDefinition serializes to JSON correctly."""
        definition = OGDefinition(
            og_code="AI",
            subgroup_code=None,
            definition_text="Test definition",
            page_title="Test Title",
            source_url="https://example.com",
            scraped_at=datetime.now(timezone.utc),
        )
        data = definition.model_dump(mode="json")
        assert data["og_code"] == "AI"
        assert data["subgroup_code"] is None
        assert "scraped_at" in data


class TestOGScrapedDataModel:
    """Tests for OGScrapedData container model."""

    def test_empty_scraped_data(self):
        """Test creating OGScrapedData with empty lists."""
        data = OGScrapedData(
            groups=[],
            subgroups=[],
            definitions=[],
            scraped_at=datetime.now(timezone.utc),
            source_url="https://example.com",
        )
        assert len(data.groups) == 0
        assert len(data.subgroups) == 0
        assert len(data.definitions) == 0


class TestParseOGSubgroups:
    """Tests for parse_og_subgroups function."""

    @pytest.fixture
    def sample_provenance(self):
        """Create sample provenance for test rows."""
        return ScrapedProvenance(
            source_url="https://www.canada.ca/tbs/og",
            scraped_at=datetime.now(timezone.utc),
            extraction_method="table_cell",
            page_title="TBS OG Page",
        )

    @pytest.fixture
    def sample_rows(self, sample_provenance):
        """Create sample OG rows for testing."""
        return [
            # Row with subgroup
            OccupationalGroupRow(
                group_abbrev="AI",
                group_code="402",
                group_name="Air Traffic Control(AI)",
                subgroup="Non-Operational(AI-NOP)",
                definition_url="https://example.com/def-ai-nop",
                provenance=sample_provenance,
            ),
            # Row without subgroup (N/A)
            OccupationalGroupRow(
                group_abbrev="AI",
                group_code="402",
                group_name="Air Traffic Control(AI)",
                subgroup="N/A",
                definition_url="https://example.com/def-ai",
                provenance=sample_provenance,
            ),
            # Another subgroup
            OccupationalGroupRow(
                group_abbrev="AO",
                group_code="401",
                group_name="Aircraft Operations(AO)",
                subgroup="Civil Aviation Inspection(AO-CAI)",
                definition_url="https://example.com/def-ao-cai",
                provenance=sample_provenance,
            ),
            # Row with None subgroup
            OccupationalGroupRow(
                group_abbrev="CP",
                group_code="",
                group_name="Commerce and Purchasing(CP)",
                subgroup=None,
                definition_url="https://example.com/def-cp",
                provenance=sample_provenance,
            ),
        ]

    def test_parse_extracts_subgroups_only(self, sample_rows):
        """Test that parse_og_subgroups only extracts actual subgroups."""
        scraped_at = datetime.now(timezone.utc)
        source_url = "https://www.canada.ca/tbs/og"

        subgroups = parse_og_subgroups(sample_rows, source_url, scraped_at)

        # Should only get 2 subgroups (AI-NOP and AO-CAI)
        assert len(subgroups) == 2

    def test_parse_extracts_correct_codes(self, sample_rows):
        """Test that subgroup codes are correctly extracted."""
        scraped_at = datetime.now(timezone.utc)
        source_url = "https://www.canada.ca/tbs/og"

        subgroups = parse_og_subgroups(sample_rows, source_url, scraped_at)

        codes = [s.subgroup_code for s in subgroups]
        assert "AI-NOP" in codes
        assert "AO-CAI" in codes

    def test_parse_extracts_correct_names(self, sample_rows):
        """Test that subgroup names are correctly extracted."""
        scraped_at = datetime.now(timezone.utc)
        source_url = "https://www.canada.ca/tbs/og"

        subgroups = parse_og_subgroups(sample_rows, source_url, scraped_at)

        names = [s.subgroup_name for s in subgroups]
        assert "Non-Operational" in names
        assert "Civil Aviation Inspection" in names

    def test_parse_links_to_parent_og(self, sample_rows):
        """Test that subgroups are linked to correct parent OG code."""
        scraped_at = datetime.now(timezone.utc)
        source_url = "https://www.canada.ca/tbs/og"

        subgroups = parse_og_subgroups(sample_rows, source_url, scraped_at)

        ai_subgroup = next(s for s in subgroups if s.subgroup_code == "AI-NOP")
        assert ai_subgroup.og_code == "AI"

        ao_subgroup = next(s for s in subgroups if s.subgroup_code == "AO-CAI")
        assert ao_subgroup.og_code == "AO"

    def test_parse_includes_provenance(self, sample_rows):
        """Test that parsed subgroups include provenance data."""
        scraped_at = datetime.now(timezone.utc)
        source_url = "https://www.canada.ca/tbs/og"

        subgroups = parse_og_subgroups(sample_rows, source_url, scraped_at)

        for subgroup in subgroups:
            assert subgroup.source_url == source_url
            assert subgroup.scraped_at == scraped_at

    def test_parse_empty_rows(self):
        """Test parsing empty row list returns empty subgroup list."""
        subgroups = parse_og_subgroups(
            [],
            "https://example.com",
            datetime.now(timezone.utc),
        )
        assert len(subgroups) == 0


class TestFetchOGDefinition:
    """Tests for fetch_og_definition function with mocked HTTP."""

    @pytest.fixture
    def mock_definition_html(self):
        """Sample HTML for a definition page."""
        return """
        <html>
        <head><title>TBS Definitions</title></head>
        <body>
        <h1>Definitions for occupational groups</h1>
        <main>
            <p>The Air Traffic Control Group comprises positions that are
            primarily involved in the development and enforcement of
            legislation, regulations, standards and policies.</p>
            <li>First inclusion item</li>
            <li>Second inclusion item</li>
        </main>
        </body>
        </html>
        """

    @patch("jobforge.external.tbs.link_fetcher.requests.get")
    @patch("jobforge.external.tbs.link_fetcher.time.sleep")
    def test_fetch_successful_definition(self, mock_sleep, mock_get, mock_definition_html):
        """Test successful definition fetch and parse."""
        mock_response = MagicMock()
        mock_response.text = mock_definition_html
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        definition = fetch_og_definition(
            url="https://example.com/def",
            og_code="AI",
            subgroup_code=None,
        )

        assert definition is not None
        assert definition.og_code == "AI"
        assert definition.subgroup_code is None
        assert "Air Traffic Control Group" in definition.definition_text
        assert definition.page_title == "Definitions for occupational groups"

        # Verify rate limiting was applied
        mock_sleep.assert_called_once_with(1.5)

    @patch("jobforge.external.tbs.link_fetcher.requests.get")
    @patch("jobforge.external.tbs.link_fetcher.time.sleep")
    def test_fetch_definition_with_subgroup(self, mock_sleep, mock_get, mock_definition_html):
        """Test fetching definition for a subgroup."""
        mock_response = MagicMock()
        mock_response.text = mock_definition_html
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        definition = fetch_og_definition(
            url="https://example.com/def-ai-nop",
            og_code="AI",
            subgroup_code="AI-NOP",
        )

        assert definition is not None
        assert definition.og_code == "AI"
        assert definition.subgroup_code == "AI-NOP"

    @patch("jobforge.external.tbs.link_fetcher.requests.get")
    @patch("jobforge.external.tbs.link_fetcher.time.sleep")
    def test_fetch_handles_404(self, mock_sleep, mock_get):
        """Test that 404 errors are handled gracefully."""
        import requests

        mock_response = MagicMock()
        mock_response.status_code = 404
        error = requests.exceptions.HTTPError(response=mock_response)
        mock_get.return_value.raise_for_status.side_effect = error
        mock_get.side_effect = error

        definition = fetch_og_definition(
            url="https://example.com/missing",
            og_code="AI",
        )

        assert definition is None
        # Should still rate limit even on error
        mock_sleep.assert_called_once_with(1.5)

    @patch("jobforge.external.tbs.link_fetcher.requests.get")
    @patch("jobforge.external.tbs.link_fetcher.time.sleep")
    def test_fetch_handles_timeout(self, mock_sleep, mock_get):
        """Test that timeout errors are handled gracefully."""
        import requests

        mock_get.side_effect = requests.exceptions.Timeout()

        definition = fetch_og_definition(
            url="https://example.com/slow",
            og_code="AI",
        )

        assert definition is None
        mock_sleep.assert_called_once_with(1.5)

    @patch("jobforge.external.tbs.link_fetcher.requests.get")
    @patch("jobforge.external.tbs.link_fetcher.time.sleep")
    def test_fetch_includes_provenance(self, mock_sleep, mock_get, mock_definition_html):
        """Test that fetched definitions include provenance."""
        mock_response = MagicMock()
        mock_response.text = mock_definition_html
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        definition = fetch_og_definition(
            url="https://example.com/def",
            og_code="AI",
        )

        assert definition is not None
        assert definition.source_url == "https://example.com/def"
        assert definition.scraped_at is not None
