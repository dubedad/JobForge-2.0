"""Tests for TBS Collective Agreement scraper.

Tests cover:
- CollectiveAgreement model validation
- Date parsing (signing_date, expiry_date)
- Bargaining agent extraction
- OG code and subgroup extraction
- Scraper handles missing dates gracefully
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jobforge.external.tbs.collective_agreement_scraper import (
    CollectiveAgreement,
    extract_og_code,
    extract_subgroup_codes,
    generate_agreement_id,
    parse_date_string,
    scrape_collective_agreements,
    scrape_all_collective_agreements,
)


class TestCollectiveAgreementModel:
    """Tests for CollectiveAgreement Pydantic model."""

    def test_model_basic_validation(self):
        """Test basic model creation with required fields."""
        agreement = CollectiveAgreement(
            agreement_id="test-id-123",
            agreement_name="Economics and Social Science Services (EC)",
            og_code="EC",
            bargaining_agent="Canadian Association of Professional Employees",
            source_url="https://example.com/agreements",
            scraped_at="2026-02-05T10:00:00Z",
        )

        assert agreement.agreement_id == "test-id-123"
        assert agreement.agreement_name == "Economics and Social Science Services (EC)"
        assert agreement.og_code == "EC"
        assert agreement.bargaining_agent == "Canadian Association of Professional Employees"
        assert agreement.employer == "Treasury Board of Canada Secretariat"

    def test_model_with_dates(self):
        """Test model with effective and expiry dates."""
        agreement = CollectiveAgreement(
            agreement_id="test-id",
            agreement_name="Test Agreement (TA)",
            og_code="TA",
            bargaining_agent="Test Union",
            signing_date="2024-01-15",
            effective_date="2024-01-15",
            expiry_date="2027-01-14",
            source_url="https://example.com",
            scraped_at="2026-02-05T10:00:00Z",
        )

        assert agreement.signing_date == "2024-01-15"
        assert agreement.effective_date == "2024-01-15"
        assert agreement.expiry_date == "2027-01-14"

    def test_model_with_null_expiry(self):
        """Test model handles null expiry date (evergreen agreement)."""
        agreement = CollectiveAgreement(
            agreement_id="test-id",
            agreement_name="Evergreen Agreement (EA)",
            og_code="EA",
            bargaining_agent="Test Union",
            effective_date="2020-01-01",
            expiry_date=None,
            source_url="https://example.com",
            scraped_at="2026-02-05T10:00:00Z",
        )

        assert agreement.expiry_date is None

    def test_model_with_subgroup_codes(self):
        """Test model with multiple subgroup codes."""
        agreement = CollectiveAgreement(
            agreement_id="test-id",
            agreement_name="Comptrollership (CT)",
            og_code="CT",
            og_subgroup_codes=["CT", "EAV", "FIN", "IAU"],
            bargaining_agent="Association of Canadian Financial Officers",
            source_url="https://example.com",
            scraped_at="2026-02-05T10:00:00Z",
        )

        assert agreement.og_subgroup_codes == ["CT", "EAV", "FIN", "IAU"]

    def test_model_serialization(self):
        """Test model can be serialized to JSON."""
        agreement = CollectiveAgreement(
            agreement_id="test-id",
            agreement_name="Test (TA)",
            og_code="TA",
            bargaining_agent="Union",
            source_url="https://example.com",
            scraped_at="2026-02-05T10:00:00Z",
        )

        json_data = agreement.model_dump(mode="json")
        assert isinstance(json_data, dict)
        assert json_data["agreement_id"] == "test-id"


class TestDateParsing:
    """Tests for date parsing functions."""

    def test_parse_date_iso_format(self):
        """Test parsing dates already in YYYY-MM-DD format."""
        assert parse_date_string("2025-12-19") == "2025-12-19"
        assert parse_date_string("2024-06-30") == "2024-06-30"

    def test_parse_date_text_format(self):
        """Test parsing dates in Month Day, Year format."""
        assert parse_date_string("December 19, 2025") == "2025-12-19"
        assert parse_date_string("June 30, 2024") == "2024-06-30"
        assert parse_date_string("January 1, 2020") == "2020-01-01"

    def test_parse_date_empty_string(self):
        """Test parsing empty date strings."""
        assert parse_date_string("") is None
        assert parse_date_string("   ") is None

    def test_parse_date_none(self):
        """Test parsing None date."""
        assert parse_date_string(None) is None

    def test_parse_date_invalid(self):
        """Test parsing invalid date strings."""
        assert parse_date_string("not a date") is None
        assert parse_date_string("2025") is None


class TestOGCodeExtraction:
    """Tests for OG code extraction functions."""

    def test_extract_og_code_simple(self):
        """Test extracting OG code from simple abbreviation."""
        assert extract_og_code("(AI)", "Air Traffic Control (AI)") == "AI"
        assert extract_og_code("(EC)", "Economics (EC)") == "EC"

    def test_extract_og_code_multiple(self):
        """Test extracting primary OG code when multiple present."""
        assert extract_og_code("(CP)(AV)", "Commerce and Purchasing (CP [CO, PG])") == "CP"
        assert extract_og_code("(CT)(FI)", "Comptrollership (CT [EAV, FIN])") == "CT"

    def test_extract_subgroup_codes_single(self):
        """Test extracting single subgroup code."""
        codes = extract_subgroup_codes("Air Traffic Control (AI)")
        assert "AI" in codes

    def test_extract_subgroup_codes_multiple(self):
        """Test extracting multiple subgroup codes."""
        codes = extract_subgroup_codes("Comptrollership (CT [EAV, FIN, IAU])")
        assert "CT" in codes
        assert "EAV" in codes
        assert "FIN" in codes
        assert "IAU" in codes

    def test_extract_subgroup_codes_empty_brackets(self):
        """Test extracting from string without subgroups."""
        codes = extract_subgroup_codes("Simple Group (SG)")
        assert "SG" in codes


class TestAgreementIdGeneration:
    """Tests for agreement ID generation."""

    def test_generate_agreement_id_deterministic(self):
        """Test that ID generation is deterministic."""
        name = "Economics and Social Science Services (EC)"
        id1 = generate_agreement_id(name)
        id2 = generate_agreement_id(name)
        assert id1 == id2

    def test_generate_agreement_id_case_insensitive(self):
        """Test that ID generation is case-insensitive."""
        id1 = generate_agreement_id("Test Agreement")
        id2 = generate_agreement_id("test agreement")
        assert id1 == id2

    def test_generate_agreement_id_unique(self):
        """Test that different names produce different IDs."""
        id1 = generate_agreement_id("Agreement A")
        id2 = generate_agreement_id("Agreement B")
        assert id1 != id2


class TestScraperIntegration:
    """Integration tests for scraper functions."""

    @pytest.fixture
    def mock_html_response(self):
        """Create mock HTML response with collective agreements table."""
        return """
        <html>
        <body>
        <main>
        <table>
            <tr>
                <th>Abbreviation</th>
                <th>Group</th>
                <th>Group and sub-group abbreviation</th>
                <th>Code</th>
                <th>Union</th>
                <th>Signing date</th>
                <th>Expiry date</th>
            </tr>
            <tr>
                <td>(EC)</td>
                <td>Economics and Social Science Services</td>
                <td>Economics and Social Science Services (EC)</td>
                <td>201</td>
                <td>Canadian Association of Professional Employees</td>
                <td>2024-06-22</td>
                <td>2027-06-21</td>
            </tr>
            <tr>
                <td>(CT)(FI)</td>
                <td>Comptrollership</td>
                <td>Comptrollership (CT [EAV, FIN, IAU])</td>
                <td>30401</td>
                <td>Association of Canadian Financial Officers</td>
                <td>2022-12-02</td>
                <td>2026-11-06</td>
            </tr>
        </table>
        </main>
        </body>
        </html>
        """

    def test_scrape_collective_agreements_parses_table(self, mock_html_response):
        """Test that scraper correctly parses agreements from HTML table."""
        mock_resp = MagicMock()
        mock_resp.text = mock_html_response
        mock_resp.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_resp):
            agreements = scrape_collective_agreements()

        assert len(agreements) == 2

        # Check EC agreement
        ec = next((a for a in agreements if a.og_code == "EC"), None)
        assert ec is not None
        assert ec.bargaining_agent == "Canadian Association of Professional Employees"
        assert ec.signing_date == "2024-06-22"
        assert ec.expiry_date == "2027-06-21"

        # Check CT agreement with subgroups
        ct = next((a for a in agreements if a.og_code == "CT"), None)
        assert ct is not None
        assert ct.bargaining_agent == "Association of Canadian Financial Officers"
        assert "EAV" in ct.og_subgroup_codes

    def test_scrape_handles_missing_dates(self):
        """Test that scraper handles missing dates gracefully."""
        html = """
        <html>
        <body>
        <main>
        <table>
            <tr>
                <th>Abbreviation</th>
                <th>Group</th>
                <th>Group and sub-group abbreviation</th>
                <th>Code</th>
                <th>Union</th>
                <th>Signing date</th>
                <th>Expiry date</th>
            </tr>
            <tr>
                <td>(TE)</td>
                <td>Test Group</td>
                <td>Test Group (TE)</td>
                <td>999</td>
                <td>Test Union</td>
                <td></td>
                <td></td>
            </tr>
        </table>
        </main>
        </body>
        </html>
        """

        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_resp):
            agreements = scrape_collective_agreements()

        assert len(agreements) == 1
        assert agreements[0].signing_date is None
        assert agreements[0].expiry_date is None

    def test_scrape_handles_network_error(self):
        """Test that scraper returns empty list on network error."""
        with patch(
            "jobforge.external.tbs.collective_agreement_scraper.requests.get",
            side_effect=Exception("Network error"),
        ):
            agreements = scrape_collective_agreements()

        assert agreements == []

    def test_scrape_all_saves_json(self, mock_html_response, tmp_path):
        """Test that scrape_all saves agreements to JSON file."""
        mock_resp = MagicMock()
        mock_resp.text = mock_html_response
        mock_resp.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_resp):
            output_path = scrape_all_collective_agreements(output_dir=tmp_path)

        assert output_path.exists()

        with open(output_path) as f:
            data = json.load(f)

        assert len(data) == 2
        assert all("agreement_id" in d for d in data)
        assert all("bargaining_agent" in d for d in data)


class TestBargainingAgentExtraction:
    """Tests for bargaining agent extraction."""

    def test_bargaining_agent_preserved(self):
        """Test that full bargaining agent name is preserved."""
        html = """
        <html>
        <body>
        <main>
        <table>
            <tr>
                <th>Abbreviation</th>
                <th>Group</th>
                <th>Group and sub-group abbreviation</th>
                <th>Code</th>
                <th>Union</th>
                <th>Signing date</th>
                <th>Expiry date</th>
            </tr>
            <tr>
                <td>(PA)</td>
                <td>Program and Administrative Services</td>
                <td>Program and Administrative Services (PA [AS, CR, IS, PM, WP])</td>
                <td>303</td>
                <td>Public Service Alliance of Canada</td>
                <td>2024-01-15</td>
                <td>2027-01-14</td>
            </tr>
        </table>
        </main>
        </body>
        </html>
        """

        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_resp):
            agreements = scrape_collective_agreements()

        assert len(agreements) == 1
        assert agreements[0].bargaining_agent == "Public Service Alliance of Canada"
