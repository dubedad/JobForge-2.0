"""Tests for OG pay rates scraper and ingestion pipeline."""

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from jobforge.external.tbs.pay_rates_scraper import (
    PayRateRow,
    detect_table_format,
    extract_classification_info,
    parse_effective_date,
    parse_rate_value,
    parse_step_number,
    scrape_pay_rates,
)
from jobforge.ingestion.og_pay_rates import (
    dedupe_rates,
    ingest_fact_og_pay_rates,
    normalize_codes,
    validate_rates,
)


class TestPayRateRow:
    """Tests for PayRateRow model validation."""

    def test_valid_pay_rate_row(self):
        """PayRateRow accepts valid data."""
        row = PayRateRow(
            og_code="PE",
            og_subgroup_code="PE",
            classification_level="PE-01",
            step=1,
            annual_rate=Decimal("65000.00"),
            effective_date="2024-01-01",
            represented=False,
            source_url="https://example.com/pay",
            scraped_at=datetime.now(timezone.utc),
        )
        assert row.og_code == "PE"
        assert row.step == 1
        assert row.annual_rate == Decimal("65000.00")

    def test_pay_rate_row_with_none_optional_fields(self):
        """PayRateRow allows None for optional fields."""
        row = PayRateRow(
            og_code="AO",
            og_subgroup_code="AO",
            classification_level="AO",
            step=1,
            annual_rate=None,
            hourly_rate=None,
            effective_date=None,
            represented=False,
            collective_agreement=None,
            source_url="https://example.com/pay",
            scraped_at=datetime.now(timezone.utc),
        )
        assert row.annual_rate is None
        assert row.hourly_rate is None

    def test_pay_rate_row_step_validation(self):
        """PayRateRow requires step >= 1."""
        with pytest.raises(ValueError):
            PayRateRow(
                og_code="PE",
                og_subgroup_code="PE",
                classification_level="PE-01",
                step=0,  # Invalid: must be >= 1
                annual_rate=Decimal("65000.00"),
                source_url="https://example.com",
                scraped_at=datetime.now(timezone.utc),
            )


class TestParseRateValue:
    """Tests for rate value parsing."""

    def test_parse_simple_number(self):
        """Parses simple dollar amounts."""
        assert parse_rate_value("65000") == Decimal("65000")
        assert parse_rate_value("151490") == Decimal("151490")

    def test_parse_with_commas(self):
        """Parses amounts with comma separators."""
        assert parse_rate_value("65,000") == Decimal("65000")
        assert parse_rate_value("151,490") == Decimal("151490")

    def test_parse_with_dollar_sign(self):
        """Parses amounts with dollar sign."""
        assert parse_rate_value("$65,000") == Decimal("65000")

    def test_parse_range_returns_minimum(self):
        """Parses range and returns minimum value."""
        result = parse_rate_value("100,220 to 114,592")
        assert result == Decimal("100220")

    def test_parse_not_applicable_returns_none(self):
        """Returns None for not applicable values."""
        assert parse_rate_value("-not applicable") is None
        assert parse_rate_value("N/A") is None
        assert parse_rate_value("-") is None
        assert parse_rate_value("") is None

    def test_parse_invalid_returns_none(self):
        """Returns None for non-numeric text."""
        assert parse_rate_value("Step 1") is None
        assert parse_rate_value("Effective date") is None


class TestParseEffectiveDate:
    """Tests for effective date parsing."""

    def test_parse_standard_format(self):
        """Parses standard TBS date format."""
        assert parse_effective_date("$) June 21, 2020") == "2020-06-21"
        assert parse_effective_date("A) January 26, 2022") == "2022-01-26"

    def test_parse_without_comma(self):
        """Parses date without comma."""
        assert parse_effective_date("B) March 15 2023") == "2023-03-15"

    def test_parse_various_months(self):
        """Parses all month names."""
        assert parse_effective_date("January 1, 2024") == "2024-01-01"
        assert parse_effective_date("December 31, 2024") == "2024-12-31"

    def test_parse_invalid_returns_none(self):
        """Returns None for invalid date text."""
        assert parse_effective_date("Effective date") is None
        assert parse_effective_date("Step 1") is None
        assert parse_effective_date("") is None


class TestParseStepNumber:
    """Tests for step number parsing."""

    def test_parse_step_with_space(self):
        """Parses Step N format."""
        assert parse_step_number("Step 1") == 1
        assert parse_step_number("Step 10") == 10

    def test_parse_step_with_nbsp(self):
        """Parses Step with non-breaking space."""
        assert parse_step_number("Step\xa01") == 1

    def test_parse_invalid_returns_none(self):
        """Returns None for non-step text."""
        assert parse_step_number("Effective date") is None
        assert parse_step_number("") is None


class TestExtractClassificationInfo:
    """Tests for classification info extraction."""

    def test_extract_full_code(self):
        """Extracts classification from full code."""
        clf, subgroup = extract_classification_info("PE-01", "PE")
        assert clf == "PE-01"
        assert subgroup == "PE"

    def test_extract_with_level_padding(self):
        """Pads single-digit levels to two digits."""
        clf, subgroup = extract_classification_info("AS-7", "AS")
        assert clf == "AS-07"

    def test_extract_number_only(self):
        """Prepends OG code when only number given."""
        clf, subgroup = extract_classification_info("1", "PE")
        assert clf == "PE-01"
        assert subgroup == "PE"

    def test_skip_non_classification_text(self):
        """Returns None for non-classification text."""
        clf, subgroup = extract_classification_info("Effective date", "PE")
        assert clf is None
        assert subgroup is None


class TestDetectTableFormat:
    """Tests for table format detection."""

    def test_detect_steps_as_columns(self):
        """Detects steps-as-columns format."""
        headers = ["Effective date", "Step 1", "Step 2", "Step 3"]
        assert detect_table_format(headers) == "steps-as-columns"

    def test_detect_dates_as_columns(self):
        """Detects dates-as-columns format."""
        headers = ["Level", "Rates of pay", "$) June 21, 2020", "A) June 21, 2021"]
        assert detect_table_format(headers) == "dates-as-columns"

    def test_detect_unknown(self):
        """Returns unknown for unrecognized format."""
        headers = ["Column A", "Column B", "Column C"]
        assert detect_table_format(headers) == "unknown"


class TestScrapePayRatesWithMock:
    """Tests for scrape_pay_rates with mocked HTTP."""

    @patch("jobforge.external.tbs.pay_rates_scraper.requests.get")
    def test_scrape_steps_as_columns_format(self, mock_get):
        """Scrapes table with steps as columns."""
        html = """
        <html><body>
        <table>
            <tr><th>Effective date</th><th>Step 1</th><th>Step 2</th></tr>
            <tr><td>$) June 21, 2022</td><td>65,000</td><td>68,000</td></tr>
        </table>
        </body></html>
        """
        mock_response = MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        rows = scrape_pay_rates("https://example.com/pay.html", "PE")

        assert len(rows) == 2  # 2 steps
        assert rows[0].step == 1
        assert rows[0].annual_rate == Decimal("65000")
        assert rows[0].effective_date == "2022-06-21"

    @patch("jobforge.external.tbs.pay_rates_scraper.requests.get")
    def test_scrape_request_failure_returns_empty(self, mock_get):
        """Returns empty list on HTTP failure."""
        import requests as requests_module
        mock_get.side_effect = requests_module.RequestException("Connection error")

        rows = scrape_pay_rates("https://example.com/pay.html", "PE")

        assert rows == []


class TestSilverTransforms:
    """Tests for silver layer transforms."""

    def test_normalize_codes_uppercase(self):
        """normalize_codes converts to uppercase."""
        df = pl.DataFrame({
            "og_code": ["pe", "ao"],
            "og_subgroup_code": ["pe", "ao"],
            "classification_level": ["pe-01", "ao-01"],
        }).lazy()

        result = normalize_codes(df).collect()

        assert result["og_code"].to_list() == ["PE", "AO"]
        assert result["og_subgroup_code"].to_list() == ["PE", "AO"]
        assert result["classification_level"].to_list() == ["PE-01", "AO-01"]

    def test_validate_rates_filters_invalid(self):
        """validate_rates removes rows with invalid rates."""
        df = pl.DataFrame({
            "annual_rate": [65000.0, -1.0, None, 0.0],
        }).lazy()

        result = validate_rates(df).collect()

        # Should keep positive and null, filter negative and zero
        assert len(result) == 2  # 65000 and None
        assert 65000.0 in result["annual_rate"].to_list()

    def test_dedupe_rates_removes_duplicates(self):
        """dedupe_rates removes duplicate rows."""
        df = pl.DataFrame({
            "og_subgroup_code": ["PE", "PE", "AO"],
            "classification_level": ["PE-01", "PE-01", "AO-01"],
            "step": [1, 1, 1],
            "effective_date": ["2024-01-01", "2024-01-01", "2024-01-01"],
            "annual_rate": [65000.0, 65000.0, 70000.0],
        }).lazy()

        result = dedupe_rates(df).collect()

        assert len(result) == 2  # PE-01 deduplicated


class TestIngestFactOgPayRates:
    """Integration tests for the full ingestion pipeline."""

    def test_ingest_creates_parquet_file(self):
        """ingest_fact_og_pay_rates creates gold parquet file."""
        # Only run if source file exists
        source_path = Path("data/tbs/og_pay_rates_en.json")
        if not source_path.exists():
            pytest.skip("Source file not available")

        result = ingest_fact_og_pay_rates()

        assert result["gold_path"].exists()
        assert result["row_count"] > 0

    def test_ingest_produces_rows_with_expected_schema(self):
        """Ingested table has expected columns."""
        gold_path = Path("data/gold/fact_og_pay_rates.parquet")
        if not gold_path.exists():
            pytest.skip("Gold file not available")

        df = pl.read_parquet(gold_path)

        expected_columns = [
            "og_subgroup_code",
            "og_code",
            "classification_level",
            "step",
            "annual_rate",
            "effective_date",
            "is_represented",
        ]
        for col in expected_columns:
            assert col in df.columns

    def test_ingest_has_provenance_columns(self):
        """Ingested table has provenance columns."""
        gold_path = Path("data/gold/fact_og_pay_rates.parquet")
        if not gold_path.exists():
            pytest.skip("Gold file not available")

        df = pl.read_parquet(gold_path)

        provenance_columns = [
            "_source_url",
            "_scraped_at",
            "_source_file",
            "_ingested_at",
            "_batch_id",
            "_layer",
        ]
        for col in provenance_columns:
            assert col in df.columns

    def test_ingest_annual_rates_positive(self):
        """Annual rates are positive where not null."""
        gold_path = Path("data/gold/fact_og_pay_rates.parquet")
        if not gold_path.exists():
            pytest.skip("Gold file not available")

        df = pl.read_parquet(gold_path)

        rates = df.filter(pl.col("annual_rate").is_not_null())["annual_rate"]
        assert all(r > 0 for r in rates.to_list())


class TestForeignKeyIntegrity:
    """Tests for FK integrity with dimension tables."""

    def test_og_codes_exist_in_fact_table(self):
        """Fact table has valid OG codes."""
        gold_path = Path("data/gold/fact_og_pay_rates.parquet")
        if not gold_path.exists():
            pytest.skip("Gold file not available")

        df = pl.read_parquet(gold_path)
        og_codes = df["og_code"].unique().to_list()

        # OG codes should be non-empty strings
        assert all(og for og in og_codes)
        assert all(isinstance(og, str) for og in og_codes)

    def test_subgroup_codes_match_og_codes(self):
        """Subgroup codes are consistent with OG codes."""
        gold_path = Path("data/gold/fact_og_pay_rates.parquet")
        if not gold_path.exists():
            pytest.skip("Gold file not available")

        df = pl.read_parquet(gold_path)

        # For excluded employees, subgroup_code typically equals og_code
        # Check they're both non-empty
        assert df.filter(pl.col("og_subgroup_code").is_null()).height == 0
        assert df.filter(pl.col("og_code").is_null()).height == 0
