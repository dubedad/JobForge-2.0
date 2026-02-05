"""Tests for TBS Represented Pay Rates scraper.

Tests cover:
- RepresentedPayRate model validation
- Pay rate parsing
- Date parsing
- Classification extraction from table captions
- Collective agreement ID linking
- Historical date range coverage
"""

import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jobforge.external.tbs.represented_pay_scraper import (
    RepresentedPayRate,
    extract_classification_from_caption,
    parse_effective_date,
    parse_pay_table,
    parse_rate_value,
    parse_step_number,
    scrape_all_represented_pay_rates,
    scrape_represented_pay_rates,
)


class TestRepresentedPayRateModel:
    """Tests for RepresentedPayRate Pydantic model."""

    def test_model_basic_validation(self):
        """Test basic model creation with required fields."""
        rate = RepresentedPayRate(
            og_code="EC",
            og_subgroup_code="EC",
            classification_level="EC-04",
            step=1,
            annual_rate=Decimal("85778"),
            source_url="https://example.com",
            scraped_at="2026-02-05T10:00:00Z",
        )

        assert rate.og_code == "EC"
        assert rate.classification_level == "EC-04"
        assert rate.step == 1
        assert rate.annual_rate == Decimal("85778")
        assert rate.is_represented is True
        assert rate.pay_progression_type == "step"

    def test_model_with_collective_agreement_id(self):
        """Test model with collective agreement FK."""
        rate = RepresentedPayRate(
            og_code="PA",
            og_subgroup_code="PA",
            classification_level="PA-02",
            step=3,
            annual_rate=Decimal("65000"),
            collective_agreement_id="ca-uuid-123",
            source_url="https://example.com",
            scraped_at="2026-02-05T10:00:00Z",
        )

        assert rate.collective_agreement_id == "ca-uuid-123"
        assert rate.is_represented is True

    def test_model_pay_progression_type(self):
        """Test model with different pay progression types."""
        rate = RepresentedPayRate(
            og_code="EX",
            og_subgroup_code="EX",
            classification_level="EX-01",
            step=1,
            annual_rate=Decimal("150000"),
            pay_progression_type="performance",
            source_url="https://example.com",
            scraped_at="2026-02-05T10:00:00Z",
        )

        assert rate.pay_progression_type == "performance"

    def test_model_serialization(self):
        """Test model can be serialized to JSON."""
        rate = RepresentedPayRate(
            og_code="EC",
            og_subgroup_code="EC",
            classification_level="EC-01",
            step=1,
            annual_rate=Decimal("55567"),
            source_url="https://example.com",
            scraped_at="2026-02-05T10:00:00Z",
        )

        json_data = rate.model_dump(mode="json")
        assert isinstance(json_data, dict)
        assert json_data["annual_rate"] == 55567.0
        assert json_data["is_represented"] is True


class TestRateParsing:
    """Tests for rate value parsing."""

    def test_parse_rate_basic(self):
        """Test parsing basic rate values."""
        assert parse_rate_value("55,567") == Decimal("55567")
        assert parse_rate_value("100,220") == Decimal("100220")

    def test_parse_rate_with_dollar_sign(self):
        """Test parsing rates with dollar signs."""
        assert parse_rate_value("$55,567") == Decimal("55567")
        assert parse_rate_value("$100,220") == Decimal("100220")

    def test_parse_rate_range(self):
        """Test parsing rate ranges (returns minimum)."""
        assert parse_rate_value("$100,220 to $114,592") == Decimal("100220")
        assert parse_rate_value("85,000 to 95,000") == Decimal("85000")

    def test_parse_rate_empty(self):
        """Test parsing empty values."""
        assert parse_rate_value("") is None
        assert parse_rate_value("-") is None
        assert parse_rate_value("N/A") is None

    def test_parse_rate_not_applicable(self):
        """Test parsing not applicable values."""
        assert parse_rate_value("not applicable") is None
        assert parse_rate_value("Not Applicable") is None

    def test_parse_rate_invalid(self):
        """Test parsing invalid values."""
        assert parse_rate_value("abc") is None
        assert parse_rate_value("Step 1") is None


class TestDateParsing:
    """Tests for effective date parsing."""

    def test_parse_date_with_prefix(self):
        """Test parsing dates with $ or A) prefix."""
        assert parse_effective_date("$) June 22, 2021") == "2021-06-22"
        assert parse_effective_date("A) June 22, 2022") == "2022-06-22"

    def test_parse_date_various_months(self):
        """Test parsing various months."""
        assert parse_effective_date("January 1, 2020") == "2020-01-01"
        assert parse_effective_date("December 31, 2025") == "2025-12-31"

    def test_parse_date_empty(self):
        """Test parsing empty dates."""
        assert parse_effective_date("") is None
        assert parse_effective_date(None) is None


class TestStepParsing:
    """Tests for step number parsing."""

    def test_parse_step_basic(self):
        """Test parsing basic step numbers."""
        assert parse_step_number("Step 1") == 1
        assert parse_step_number("Step 5") == 5
        assert parse_step_number("Step 10") == 10

    def test_parse_step_with_nbsp(self):
        """Test parsing step with non-breaking space."""
        assert parse_step_number("Step\xa01") == 1

    def test_parse_step_invalid(self):
        """Test parsing invalid step values."""
        assert parse_step_number("Effective Date") is None
        assert parse_step_number("") is None


class TestClassificationExtraction:
    """Tests for classification extraction from captions."""

    def test_extract_classification_basic(self):
        """Test extracting basic classification levels."""
        assert extract_classification_from_caption("EC-01 - Annual Rates of Pay (in dollars)") == "EC-01"
        assert extract_classification_from_caption("PA-05 - Annual Rates of Pay") == "PA-05"

    def test_extract_classification_double_digit(self):
        """Test extracting double-digit levels."""
        assert extract_classification_from_caption("TC-10 - Annual Rates of Pay") == "TC-10"

    def test_extract_classification_none(self):
        """Test returning None for non-classification captions."""
        assert extract_classification_from_caption("Table legend") is None
        assert extract_classification_from_caption("Penological factor allowance") is None
        assert extract_classification_from_caption("") is None


class TestPayTableParsing:
    """Tests for pay table parsing."""

    @pytest.fixture
    def mock_table_html(self):
        """Create mock HTML table element."""
        from bs4 import BeautifulSoup
        html = """
        <table>
            <caption>EC-04 - Annual Rates of Pay (in dollars)</caption>
            <tr>
                <th>Effective Date</th>
                <th>Step 1</th>
                <th>Step 2</th>
                <th>Step 3</th>
            </tr>
            <tr>
                <td>$) June 22, 2021</td>
                <td>74,122</td>
                <td>76,658</td>
                <td>79,309</td>
            </tr>
            <tr>
                <td>A) June 22, 2022</td>
                <td>76,716</td>
                <td>79,341</td>
                <td>82,085</td>
            </tr>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")
        return soup.find("table")

    def test_parse_pay_table_extracts_rates(self, mock_table_html):
        """Test that pay table parsing extracts all rates."""
        rates = parse_pay_table(
            table=mock_table_html,
            og_code="EC",
            collective_agreement_id="ca-123",
            source_url="https://example.com",
            scraped_at="2026-02-05T10:00:00Z",
        )

        # 2 dates * 3 steps = 6 rates
        assert len(rates) == 6

        # Check first rate
        rate1 = rates[0]
        assert rate1.classification_level == "EC-04"
        assert rate1.step == 1
        assert rate1.annual_rate == Decimal("74122")
        assert rate1.effective_date == "2021-06-22"
        assert rate1.collective_agreement_id == "ca-123"

    def test_parse_pay_table_multiple_dates(self, mock_table_html):
        """Test that multiple effective dates are captured."""
        rates = parse_pay_table(
            table=mock_table_html,
            og_code="EC",
            collective_agreement_id="ca-123",
            source_url="https://example.com",
            scraped_at="2026-02-05T10:00:00Z",
        )

        # Get unique effective dates
        dates = set(r.effective_date for r in rates)
        assert "2021-06-22" in dates
        assert "2022-06-22" in dates


class TestScraperIntegration:
    """Integration tests for scraper functions."""

    @pytest.fixture
    def mock_agreement_html(self):
        """Create mock collective agreement page HTML."""
        return """
        <html>
        <body>
        <main>
            <h2>Appendix A</h2>
            <table>
                <caption>EC-01 - Annual Rates of Pay (in dollars)</caption>
                <tr>
                    <th>Effective Date</th>
                    <th>Step 1</th>
                    <th>Step 2</th>
                </tr>
                <tr>
                    <td>$) June 22, 2021</td>
                    <td>55,567</td>
                    <td>57,508</td>
                </tr>
            </table>
            <table>
                <caption>EC-02 - Annual Rates of Pay (in dollars)</caption>
                <tr>
                    <th>Effective Date</th>
                    <th>Step 1</th>
                    <th>Step 2</th>
                </tr>
                <tr>
                    <td>$) June 22, 2021</td>
                    <td>62,168</td>
                    <td>63,675</td>
                </tr>
            </table>
        </main>
        </body>
        </html>
        """

    def test_scrape_represented_pay_rates_parses_tables(self, mock_agreement_html):
        """Test that scraper correctly parses pay tables."""
        mock_resp = MagicMock()
        mock_resp.text = mock_agreement_html
        mock_resp.raise_for_status = MagicMock()

        with patch(
            "jobforge.external.tbs.represented_pay_scraper.requests.get",
            return_value=mock_resp,
        ):
            rates = scrape_represented_pay_rates(
                og_code="EC",
                url="https://example.com/ec.html",
                collective_agreement_id="ca-ec-123",
            )

        # 2 tables * 1 date * 2 steps = 4 rates
        assert len(rates) == 4

        # Check EC-01 rates
        ec01_rates = [r for r in rates if r.classification_level == "EC-01"]
        assert len(ec01_rates) == 2

        # Check EC-02 rates
        ec02_rates = [r for r in rates if r.classification_level == "EC-02"]
        assert len(ec02_rates) == 2

    def test_scrape_handles_network_error(self):
        """Test that scraper returns empty list on network error."""
        with patch(
            "jobforge.external.tbs.represented_pay_scraper.requests.get",
            side_effect=Exception("Network error"),
        ):
            rates = scrape_represented_pay_rates(
                og_code="EC",
                url="https://example.com/ec.html",
                collective_agreement_id="ca-123",
            )

        assert rates == []

    def test_scrape_all_saves_json(self, mock_agreement_html, tmp_path):
        """Test that scrape_all saves rates to JSON file."""
        # Create mock collective agreements file
        ca_data = [
            {"og_code": "EC", "agreement_id": "ca-ec-123"},
        ]
        ca_file = tmp_path / "collective_agreements.json"
        with open(ca_file, "w") as f:
            json.dump(ca_data, f)

        # Mock index page
        index_html = """
        <html>
        <body>
        <main>
            <a href="/en/treasury-board-secretariat/topics/pay/collective-agreements/ec.html">Economics</a>
        </main>
        </body>
        </html>
        """

        def mock_get(url, **kwargs):
            mock = MagicMock()
            mock.raise_for_status = MagicMock()
            if "collective-agreements.html" in url:
                mock.text = index_html
            else:
                mock.text = mock_agreement_html
            return mock

        with patch(
            "jobforge.external.tbs.represented_pay_scraper.requests.get",
            side_effect=mock_get,
        ):
            output_path = scrape_all_represented_pay_rates(output_dir=tmp_path, delay=0)

        assert output_path.exists()

        with open(output_path) as f:
            data = json.load(f)

        assert len(data) > 0
        assert all(d["is_represented"] is True for d in data)


class TestCollectiveAgreementLinking:
    """Tests for collective agreement FK linking."""

    def test_collective_agreement_id_preserved(self):
        """Test that collective_agreement_id is set correctly."""
        from bs4 import BeautifulSoup
        html = """
        <table>
            <caption>PA-01 - Annual Rates of Pay (in dollars)</caption>
            <tr>
                <th>Effective Date</th>
                <th>Step 1</th>
            </tr>
            <tr>
                <td>$) January 1, 2024</td>
                <td>50,000</td>
            </tr>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")

        rates = parse_pay_table(
            table=table,
            og_code="PA",
            collective_agreement_id="pa-agreement-uuid",
            source_url="https://example.com",
            scraped_at="2026-02-05T10:00:00Z",
        )

        assert len(rates) == 1
        assert rates[0].collective_agreement_id == "pa-agreement-uuid"


class TestHistoricalDateCoverage:
    """Tests for historical date range coverage."""

    def test_multiple_effective_dates_captured(self):
        """Test that multiple historical dates are captured."""
        from bs4 import BeautifulSoup
        html = """
        <table>
            <caption>TC-01 - Annual Rates of Pay (in dollars)</caption>
            <tr>
                <th>Effective Date</th>
                <th>Step 1</th>
            </tr>
            <tr>
                <td>$) June 22, 2020</td>
                <td>45,000</td>
            </tr>
            <tr>
                <td>A) June 22, 2021</td>
                <td>46,000</td>
            </tr>
            <tr>
                <td>B) June 22, 2022</td>
                <td>47,000</td>
            </tr>
            <tr>
                <td>C) June 22, 2023</td>
                <td>48,000</td>
            </tr>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")

        rates = parse_pay_table(
            table=table,
            og_code="TC",
            collective_agreement_id="tc-123",
            source_url="https://example.com",
            scraped_at="2026-02-05T10:00:00Z",
        )

        # 4 dates captured
        assert len(rates) == 4

        dates = [r.effective_date for r in rates]
        assert "2020-06-22" in dates
        assert "2021-06-22" in dates
        assert "2022-06-22" in dates
        assert "2023-06-22" in dates
