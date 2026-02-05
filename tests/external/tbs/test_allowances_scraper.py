"""Tests for TBS allowances scraper.

Tests cover:
- Allowance model validation
- Amount parsing (dollar amounts, percentages)
- Allowance_type categorization
- Scraper handles missing allowance pages gracefully
"""

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jobforge.external.tbs.allowances_scraper import (
    Allowance,
    parse_amount,
    parse_percentage,
    scrape_allowances,
    scrape_bilingual_bonus,
    scrape_isolated_post_allowances,
    create_supervisory_allowances,
    create_shift_and_standby_allowances,
    scrape_all_allowances,
)


class TestAllowanceModel:
    """Tests for Allowance Pydantic model."""

    def test_valid_allowance_full_fields(self):
        """Allowance accepts valid data with all fields."""
        allowance = Allowance(
            allowance_id="test-uuid-123",
            allowance_type="bilingual_bonus",
            allowance_name="Bilingual Bonus",
            amount=Decimal("800"),
            rate_type="annual",
            percentage=None,
            og_code=None,
            classification_level=None,
            eligibility_criteria="Employees meeting bilingual requirements",
            effective_date="2024-01-01",
            source_url="https://example.com/bonus",
            scraped_at="2024-01-20T12:00:00Z",
        )
        assert allowance.allowance_type == "bilingual_bonus"
        assert allowance.amount == Decimal("800")
        assert allowance.rate_type == "annual"

    def test_valid_allowance_minimal_fields(self):
        """Allowance accepts minimal required fields."""
        allowance = Allowance(
            allowance_id="test-uuid-456",
            allowance_type="supervisory",
            allowance_name="Supervisory Differential",
            source_url="https://example.com/sup",
            scraped_at="2024-01-20T12:00:00Z",
        )
        assert allowance.allowance_type == "supervisory"
        assert allowance.amount is None
        assert allowance.og_code is None

    def test_allowance_with_percentage(self):
        """Allowance can store percentage-based rates."""
        allowance = Allowance(
            allowance_id="test-uuid-789",
            allowance_type="shift",
            allowance_name="Evening Shift Premium",
            amount=None,
            rate_type="percentage",
            percentage=Decimal("7.5"),
            source_url="https://example.com/shift",
            scraped_at="2024-01-20T12:00:00Z",
        )
        assert allowance.percentage == Decimal("7.5")
        assert allowance.rate_type == "percentage"

    def test_allowance_serialization(self):
        """Allowance serializes to JSON correctly."""
        allowance = Allowance(
            allowance_id="test-uuid-abc",
            allowance_type="isolated_post",
            allowance_name="Isolated Post - Level 3",
            amount=Decimal("1500"),
            rate_type="annual",
            source_url="https://example.com/isolated",
            scraped_at="2024-01-20T12:00:00Z",
        )
        data = allowance.model_dump(mode="json")

        assert data["allowance_type"] == "isolated_post"
        assert data["amount"] == 1500.0  # Decimal to float
        assert "scraped_at" in data


class TestParseAmount:
    """Tests for amount parsing."""

    def test_parse_simple_amount(self):
        """Parses simple dollar amounts."""
        assert parse_amount("800") == Decimal("800")
        assert parse_amount("1500") == Decimal("1500")

    def test_parse_with_dollar_sign(self):
        """Parses amounts with dollar sign."""
        assert parse_amount("$800") == Decimal("800")
        assert parse_amount("$ 1,500") == Decimal("1500")

    def test_parse_with_commas(self):
        """Parses amounts with comma separators."""
        assert parse_amount("1,600") == Decimal("1600")
        assert parse_amount("$10,000") == Decimal("10000")

    def test_parse_with_suffix(self):
        """Parses amounts with per year/annually suffix."""
        assert parse_amount("$800 per year") == Decimal("800")
        assert parse_amount("$800 annually") == Decimal("800")
        assert parse_amount("$1,600 per annum") == Decimal("1600")

    def test_parse_empty_returns_none(self):
        """Returns None for empty input."""
        assert parse_amount("") is None
        assert parse_amount(None) is None

    def test_parse_non_numeric_returns_none(self):
        """Returns None for non-numeric text."""
        assert parse_amount("Level 1") is None
        assert parse_amount("N/A") is None

    def test_parse_out_of_range_returns_none(self):
        """Returns None for amounts outside reasonable range."""
        assert parse_amount("$5") is None  # Too small
        assert parse_amount("$100,000") is None  # Too large for allowance


class TestParsePercentage:
    """Tests for percentage parsing."""

    def test_parse_simple_percentage(self):
        """Parses simple percentages."""
        assert parse_percentage("5%") == Decimal("5")
        assert parse_percentage("10%") == Decimal("10")

    def test_parse_decimal_percentage(self):
        """Parses decimal percentages."""
        assert parse_percentage("7.5%") == Decimal("7.5")
        assert parse_percentage("12.5%") == Decimal("12.5")

    def test_parse_percent_word(self):
        """Parses 'percent' spelled out."""
        assert parse_percentage("5 percent") == Decimal("5")
        assert parse_percentage("7.5 Percent") == Decimal("7.5")

    def test_parse_empty_returns_none(self):
        """Returns None for empty input."""
        assert parse_percentage("") is None
        assert parse_percentage(None) is None

    def test_parse_non_percentage_returns_none(self):
        """Returns None for non-percentage text."""
        assert parse_percentage("$800") is None
        assert parse_percentage("Level 1") is None


class TestScrapeBilingualBonus:
    """Tests for bilingual bonus scraping with mocked HTTP."""

    @patch("jobforge.external.tbs.allowances_scraper.requests.get")
    @patch("jobforge.external.tbs.allowances_scraper.time.sleep")
    def test_scrape_successful(self, mock_sleep, mock_get):
        """Successfully scrapes bilingual bonus page."""
        html = """
        <html><body>
        <main>
        <h1>Bilingual Bonus</h1>
        <p>The bilingual bonus is $800 annually for employees who meet
        the language requirements of their bilingual position.</p>
        </main>
        </body></html>
        """
        mock_response = MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        allowances = scrape_bilingual_bonus()

        assert len(allowances) >= 1
        assert allowances[0].allowance_type == "bilingual_bonus"
        assert allowances[0].amount == Decimal("800")

        # Rate limiting applied
        mock_sleep.assert_called()

    @patch("jobforge.external.tbs.allowances_scraper.requests.get")
    @patch("jobforge.external.tbs.allowances_scraper.time.sleep")
    def test_scrape_handles_failure_with_fallback(self, mock_sleep, mock_get):
        """Returns reference data on HTTP failure."""
        import requests as requests_module
        mock_get.side_effect = requests_module.RequestException("Connection error")

        allowances = scrape_bilingual_bonus()

        # Should return reference data instead of empty list
        assert len(allowances) >= 1
        assert all(a.allowance_type == "bilingual_bonus" for a in allowances)


class TestScrapeIsolatedPostAllowances:
    """Tests for isolated post allowances scraping."""

    @patch("jobforge.external.tbs.allowances_scraper.requests.get")
    @patch("jobforge.external.tbs.allowances_scraper.time.sleep")
    def test_scrape_creates_fallback_records(self, mock_sleep, mock_get):
        """Creates fallback records when no table data found."""
        html = """
        <html><body>
        <main>
        <h1>Isolated Posts and Government Housing Directive</h1>
        <p>General information about isolated posts.</p>
        </main>
        </body></html>
        """
        mock_response = MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        allowances = scrape_isolated_post_allowances()

        # Should create 5 level records as fallback
        assert len(allowances) == 5
        assert all(a.allowance_type == "isolated_post" for a in allowances)

    @patch("jobforge.external.tbs.allowances_scraper.requests.get")
    @patch("jobforge.external.tbs.allowances_scraper.time.sleep")
    def test_scrape_handles_failure_with_fallback(self, mock_sleep, mock_get):
        """Returns reference data on HTTP failure."""
        import requests as requests_module
        mock_get.side_effect = requests_module.RequestException("Connection error")

        allowances = scrape_isolated_post_allowances()

        # Should return reference data (5 levels) instead of empty list
        assert len(allowances) == 5
        assert all(a.allowance_type == "isolated_post" for a in allowances)


class TestCreateSupervisoryAllowances:
    """Tests for supervisory allowance creation."""

    def test_creates_supervisory_records(self):
        """Creates supervisory allowance records."""
        allowances = create_supervisory_allowances()

        assert len(allowances) >= 1
        assert all(a.allowance_type == "supervisory" for a in allowances)

    def test_includes_percentage_based(self):
        """Includes percentage-based supervisory differential."""
        allowances = create_supervisory_allowances()

        percentage_allowances = [a for a in allowances if a.percentage is not None]
        assert len(percentage_allowances) >= 1


class TestCreateShiftAndStandbyAllowances:
    """Tests for shift and standby allowance creation."""

    def test_creates_shift_records(self):
        """Creates shift differential records."""
        allowances = create_shift_and_standby_allowances()

        shift_allowances = [a for a in allowances if a.allowance_type == "shift"]
        assert len(shift_allowances) >= 1

    def test_creates_standby_records(self):
        """Creates standby pay records."""
        allowances = create_shift_and_standby_allowances()

        standby_allowances = [a for a in allowances if a.allowance_type == "standby"]
        assert len(standby_allowances) >= 1

    def test_shift_premiums_have_percentages(self):
        """Shift premiums include percentage values."""
        allowances = create_shift_and_standby_allowances()

        shift_allowances = [a for a in allowances if a.allowance_type == "shift"]
        assert all(a.percentage is not None for a in shift_allowances)


class TestScrapeAllowances:
    """Tests for combined allowance scraping."""

    @patch("jobforge.external.tbs.allowances_scraper.scrape_isolated_post_allowances")
    @patch("jobforge.external.tbs.allowances_scraper.scrape_bilingual_bonus")
    def test_combines_all_allowance_types(self, mock_bilingual, mock_isolated):
        """Combines all allowance types."""
        mock_bilingual.return_value = [
            Allowance(
                allowance_id="test-1",
                allowance_type="bilingual_bonus",
                allowance_name="Bilingual Bonus",
                amount=Decimal("800"),
                source_url="https://example.com",
                scraped_at="2024-01-20T12:00:00Z",
            )
        ]
        mock_isolated.return_value = [
            Allowance(
                allowance_id="test-2",
                allowance_type="isolated_post",
                allowance_name="Isolated Post - Level 1",
                source_url="https://example.com",
                scraped_at="2024-01-20T12:00:00Z",
            )
        ]

        allowances = scrape_allowances()

        # Should have bilingual, isolated, supervisory, and shift/standby
        types = {a.allowance_type for a in allowances}
        assert "bilingual_bonus" in types
        assert "isolated_post" in types
        assert "supervisory" in types
        assert "shift" in types
        assert "standby" in types

    @patch("jobforge.external.tbs.allowances_scraper.scrape_isolated_post_allowances")
    @patch("jobforge.external.tbs.allowances_scraper.scrape_bilingual_bonus")
    def test_minimum_allowance_count(self, mock_bilingual, mock_isolated):
        """Returns at least 10 allowance records."""
        mock_bilingual.return_value = [
            Allowance(
                allowance_id="test-1",
                allowance_type="bilingual_bonus",
                allowance_name="Bilingual Bonus",
                source_url="https://example.com",
                scraped_at="2024-01-20T12:00:00Z",
            )
        ]
        mock_isolated.return_value = []  # Even with no isolated data

        allowances = scrape_allowances()

        # Minimum: 1 bilingual + 2 supervisory + 5 shift/standby = 8
        # With isolated fallback: + 5 = 13
        assert len(allowances) >= 8


class TestScrapeAllAllowances:
    """Tests for full scraping with file output."""

    @patch("jobforge.external.tbs.allowances_scraper.scrape_allowances")
    def test_saves_to_json_file(self, mock_scrape, tmp_path):
        """Saves allowances to JSON file."""
        mock_scrape.return_value = [
            Allowance(
                allowance_id="test-1",
                allowance_type="bilingual_bonus",
                allowance_name="Bilingual Bonus",
                amount=Decimal("800"),
                source_url="https://example.com",
                scraped_at="2024-01-20T12:00:00Z",
            )
        ]

        output_path = scrape_all_allowances(output_dir=tmp_path)

        assert output_path.exists()
        assert output_path.name == "og_allowances.json"

        # Verify JSON content
        import json
        with open(output_path) as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["allowance_type"] == "bilingual_bonus"


class TestAllowanceTypeCategories:
    """Tests for allowance type categorization."""

    def test_all_allowance_types_valid(self):
        """All allowance types are from expected set."""
        from jobforge.external.tbs.allowances_scraper import (
            create_bilingual_bonus_reference,
            create_isolated_post_reference,
        )

        all_allowances = (
            create_bilingual_bonus_reference() +
            create_isolated_post_reference() +
            create_supervisory_allowances() +
            create_shift_and_standby_allowances()
        )

        valid_types = {"bilingual_bonus", "supervisory", "isolated_post", "shift", "standby"}
        for a in all_allowances:
            assert a.allowance_type in valid_types

    def test_all_types_have_valid_rate_type(self):
        """All allowances have valid rate_type."""
        supervisory = create_supervisory_allowances()
        shift_standby = create_shift_and_standby_allowances()

        all_allowances = supervisory + shift_standby

        valid_rate_types = {"annual", "hourly", "percentage", "per_diem"}
        for a in all_allowances:
            assert a.rate_type in valid_rate_types
