"""Tests for TBS Job Evaluation Standards scraper."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jobforge.external.tbs.evaluation_scraper import (
    EvaluationStandard,
    extract_og_code_from_url,
    extract_version_and_date,
    parse_factor_degree_table,
    parse_factor_weighting_table,
    scrape_evaluation_standard,
)


class TestEvaluationStandardModel:
    """Tests for EvaluationStandard Pydantic model."""

    def test_valid_classification_standard(self):
        """EvaluationStandard accepts valid classification standard data."""
        record = EvaluationStandard(
            og_code="IT",
            standard_name="Information Technology Job Evaluation Standard",
            standard_type="classification_standard",
            full_text="This standard defines...",
            source_url="https://example.com/it-standard.html",
            scraped_at="2026-02-05T10:00:00Z",
        )
        assert record.og_code == "IT"
        assert record.standard_type == "classification_standard"
        assert record.factor_name is None

    def test_valid_evaluation_factor(self):
        """EvaluationStandard accepts valid evaluation factor data."""
        record = EvaluationStandard(
            og_code="IT",
            standard_name="Information Technology Job Evaluation Standard",
            standard_type="evaluation_factor",
            factor_name="Technical Knowledge",
            factor_points=300,
            factor_percentage=30.0,
            full_text="Technical Knowledge: 30%, 300 points",
            source_url="https://example.com/it-standard.html",
            scraped_at="2026-02-05T10:00:00Z",
        )
        assert record.factor_name == "Technical Knowledge"
        assert record.factor_points == 300
        assert record.factor_percentage == 30.0

    def test_evaluation_factor_with_level(self):
        """EvaluationStandard accepts factor with level/degree details."""
        record = EvaluationStandard(
            og_code="IT",
            standard_name="Information Technology Job Evaluation Standard",
            standard_type="evaluation_factor",
            factor_name="Critical Thinking",
            factor_level="Degree 3",
            level_points=145,
            level_description="Team Lead level analysis and problem solving",
            full_text="Critical Thinking - Degree 3: 145 points",
            source_url="https://example.com/it-standard.html",
            scraped_at="2026-02-05T10:00:00Z",
        )
        assert record.factor_level == "Degree 3"
        assert record.level_points == 145

    def test_optional_fields_nullable(self):
        """EvaluationStandard allows None for optional fields."""
        record = EvaluationStandard(
            og_code="EC",
            standard_name="EC Job Evaluation Standard",
            standard_type="classification_standard",
            full_text="Standard text...",
            source_url="https://example.com/ec.html",
            scraped_at="2026-02-05T10:00:00Z",
            og_subgroup_code=None,
            factor_name=None,
            factor_description=None,
            factor_points=None,
            factor_percentage=None,
            factor_level=None,
            level_points=None,
            level_description=None,
            effective_date=None,
            version=None,
        )
        assert record.og_subgroup_code is None
        assert record.factor_name is None
        assert record.effective_date is None

    def test_model_serialization(self):
        """EvaluationStandard serializes to JSON correctly."""
        record = EvaluationStandard(
            og_code="FB",
            standard_name="Border Services Job Evaluation Standard",
            standard_type="evaluation_factor",
            factor_name="Knowledge",
            factor_points=200,
            full_text="Knowledge factor...",
            source_url="https://example.com/fb.html",
            scraped_at="2026-02-05T10:00:00Z",
        )
        data = record.model_dump(mode="json")
        assert isinstance(data, dict)
        assert data["og_code"] == "FB"
        assert data["factor_points"] == 200


class TestExtractOgCodeFromUrl:
    """Tests for OG code extraction from URLs."""

    def test_information_technology(self):
        """Extracts IT from information-technology URL."""
        url = "https://www.canada.ca/.../information-technology-job-evaluation-standard.html"
        assert extract_og_code_from_url(url) == "IT"

    def test_economics_social_science(self):
        """Extracts EC from economics-social-science URL."""
        url = "https://www.canada.ca/.../economics-social-science-services-job-evaluation-standard.html"
        assert extract_og_code_from_url(url) == "EC"

    def test_border_services(self):
        """Extracts FB from border-services URL."""
        url = "https://www.canada.ca/.../border-services-group-job-evaluation-standard.html"
        assert extract_og_code_from_url(url) == "FB"

    def test_generic_standard(self):
        """Returns GENERIC for #jes-nee anchor."""
        url = "https://www.canada.ca/.../job-evaluation-standards-public-service-employees.html#jes-nee"
        assert extract_og_code_from_url(url) == "GENERIC"

    def test_unknown_url(self):
        """Returns UNKNOWN for unrecognized URL."""
        url = "https://www.canada.ca/.../some-other-page.html"
        assert extract_og_code_from_url(url) == "UNKNOWN"


class TestExtractVersionAndDate:
    """Tests for version and date extraction."""

    def test_extract_from_amendment_table(self):
        """Extracts effective date from amendment table."""
        from bs4 import BeautifulSoup

        html = """
        <html><body>
        <table>
            <tr><th>Amendment Number</th><th>Date</th><th>Description</th></tr>
            <tr><td>1</td><td>2018-01-15</td><td>Initial version</td></tr>
        </table>
        </body></html>
        """
        soup = BeautifulSoup(html, "lxml")
        version, effective_date = extract_version_and_date(soup)
        assert effective_date == "2018-01-15"

    def test_extract_version_from_text(self):
        """Extracts version from page text."""
        from bs4 import BeautifulSoup

        html = """
        <html><body>
        <p>This standard version: 2.0 was updated in 2020.</p>
        </body></html>
        """
        soup = BeautifulSoup(html, "lxml")
        version, effective_date = extract_version_and_date(soup)
        assert version == "2.0"

    def test_no_version_or_date(self):
        """Returns None when no version or date found."""
        from bs4 import BeautifulSoup

        html = "<html><body><p>Simple content</p></body></html>"
        soup = BeautifulSoup(html, "lxml")
        version, effective_date = extract_version_and_date(soup)
        assert version is None
        assert effective_date is None


class TestParseFactorWeightingTable:
    """Tests for factor weighting table parsing."""

    def test_parse_it_weighting_table(self):
        """Parses IT standard weighting table."""
        from bs4 import BeautifulSoup

        html = """
        <table>
            <tr><th>Element</th><th>Percentage of Total Points</th><th>Maximum Point Value</th></tr>
            <tr><td>Critical Thinking and Analysis</td><td>30.0%</td><td>300</td></tr>
            <tr><td>Leadership and Planning</td><td>14.0%</td><td>140</td></tr>
            <tr><td>Technical Knowledge</td><td>30.0%</td><td>300</td></tr>
        </table>
        """
        soup = BeautifulSoup(html, "lxml")
        table = soup.find("table")

        records = parse_factor_weighting_table(
            table=table,
            og_code="IT",
            standard_name="IT Standard",
            source_url="https://example.com",
            scraped_at="2026-02-05T10:00:00Z",
            version=None,
            effective_date=None,
        )

        assert len(records) == 3
        assert records[0].factor_name == "Critical Thinking and Analysis"
        assert records[0].factor_percentage == 30.0
        assert records[0].factor_points == 300
        assert records[1].factor_name == "Leadership and Planning"
        assert records[1].factor_percentage == 14.0
        assert records[1].factor_points == 140

    def test_skip_total_row(self):
        """Skips 'Total' row in weighting table."""
        from bs4 import BeautifulSoup

        html = """
        <table>
            <tr><th>Element</th><th>Percentage</th><th>Points</th></tr>
            <tr><td>Knowledge</td><td>50%</td><td>500</td></tr>
            <tr><td>Total</td><td>100%</td><td>1000</td></tr>
        </table>
        """
        soup = BeautifulSoup(html, "lxml")
        table = soup.find("table")

        records = parse_factor_weighting_table(
            table, "EC", "EC Standard", "https://example.com", "2026-02-05T10:00:00Z", None, None
        )

        assert len(records) == 1
        assert records[0].factor_name == "Knowledge"


class TestParseFactorDegreeTable:
    """Tests for factor degree/level table parsing."""

    def test_parse_degree_table(self):
        """Parses factor degree table with point values."""
        from bs4 import BeautifulSoup

        html = """
        <table>
            <tr>
                <th>Element</th>
                <th>Degree 1</th>
                <th>Degree 2</th>
                <th>Degree 3</th>
            </tr>
            <tr>
                <td>Critical Thinking</td>
                <td>30 points</td>
                <td>70 points</td>
                <td>145 points</td>
            </tr>
            <tr>
                <td>Leadership</td>
                <td>14 points</td>
                <td>30 points</td>
                <td>60 points</td>
            </tr>
        </table>
        """
        soup = BeautifulSoup(html, "lxml")
        table = soup.find("table")

        records = parse_factor_degree_table(
            table, "IT", "IT Standard", "https://example.com", "2026-02-05T10:00:00Z", None, None
        )

        # 2 factors x 3 degrees = 6 records
        assert len(records) == 6

        # Check first factor's degrees
        critical_thinking = [r for r in records if "Critical" in r.factor_name]
        assert len(critical_thinking) == 3
        assert critical_thinking[0].factor_level == "Degree 1"
        assert critical_thinking[0].level_points == 30
        assert critical_thinking[2].level_points == 145

    def test_handle_na_cells(self):
        """Skips n/a cells in degree table."""
        from bs4 import BeautifulSoup

        html = """
        <table>
            <tr><th>Element</th><th>Degree 1</th><th>Degree 2</th></tr>
            <tr><td>Knowledge</td><td>50 points</td><td>n/a</td></tr>
        </table>
        """
        soup = BeautifulSoup(html, "lxml")
        table = soup.find("table")

        records = parse_factor_degree_table(
            table, "IT", "IT Standard", "https://example.com", "2026-02-05T10:00:00Z", None, None
        )

        assert len(records) == 1
        assert records[0].level_points == 50

    def test_extract_description_from_cell(self):
        """Extracts level description from cell with points and text."""
        from bs4 import BeautifulSoup

        html = """
        <table>
            <tr><th>Element</th><th>Degree 1</th></tr>
            <tr><td>Analysis</td><td>30 points: Basic analysis and problem solving</td></tr>
        </table>
        """
        soup = BeautifulSoup(html, "lxml")
        table = soup.find("table")

        records = parse_factor_degree_table(
            table, "IT", "IT Standard", "https://example.com", "2026-02-05T10:00:00Z", None, None
        )

        assert len(records) == 1
        assert records[0].level_points == 30
        assert "Basic analysis" in records[0].level_description


class TestScrapeEvaluationStandard:
    """Tests for scrape_evaluation_standard with mocked HTTP."""

    @patch("jobforge.external.tbs.evaluation_scraper.fetch_page")
    def test_scrape_creates_overview_record(self, mock_fetch):
        """Scraper creates classification_standard overview record."""
        mock_fetch.return_value = """
        <html>
        <head><title>IT Job Evaluation Standard</title></head>
        <body>
        <main>
            <h1>Information Technology Job Evaluation Standard</h1>
            <p>This standard defines evaluation factors for IT positions.</p>
        </main>
        </body>
        </html>
        """

        url = "https://example.com/information-technology-job-evaluation-standard.html"
        records = scrape_evaluation_standard(url)

        assert len(records) >= 1
        overview = records[0]
        assert overview.standard_type == "classification_standard"
        assert "Information Technology" in overview.standard_name
        assert overview.og_code == "IT"

    @patch("jobforge.external.tbs.evaluation_scraper.fetch_page")
    def test_scrape_extracts_factor_weighting(self, mock_fetch):
        """Scraper extracts factor weighting table."""
        mock_fetch.return_value = """
        <html>
        <body>
        <main>
            <h1>IT Job Evaluation Standard</h1>
            <table>
                <tr><th>Element</th><th>Percentage of Total Points</th><th>Maximum Point Value</th></tr>
                <tr><td>Knowledge</td><td>40%</td><td>400</td></tr>
                <tr><td>Analysis</td><td>30%</td><td>300</td></tr>
            </table>
        </main>
        </body>
        </html>
        """

        url = "https://example.com/information-technology-job-evaluation-standard.html"
        records = scrape_evaluation_standard(url)

        # Should have overview + 2 factors
        assert len(records) >= 3
        factors = [r for r in records if r.standard_type == "evaluation_factor"]
        assert len(factors) == 2

    @patch("jobforge.external.tbs.evaluation_scraper.fetch_page")
    def test_scrape_handles_failure_gracefully(self, mock_fetch):
        """Scraper returns empty list on fetch failure."""
        import requests

        mock_fetch.side_effect = requests.RequestException("Connection error")

        records = scrape_evaluation_standard("https://example.com/bad-url.html")
        assert records == []


class TestIntegration:
    """Integration tests - require source data to exist."""

    def test_occupational_groups_file_exists(self):
        """Verify occupational_groups_en.json exists for URL discovery."""
        og_path = Path("data/tbs/occupational_groups_en.json")
        if not og_path.exists():
            pytest.skip("occupational_groups_en.json not available")

        import json

        with open(og_path) as f:
            data = json.load(f)

        assert "rows" in data
        assert len(data["rows"]) > 0

        # Check for job_eval_standard_url
        has_job_eval = any(r.get("job_eval_standard_url") for r in data["rows"])
        assert has_job_eval, "No job_eval_standard_url found in rows"

    def test_scrape_single_standard_if_available(self):
        """Integration test: scrape one real evaluation standard page.

        Note: This test makes a real HTTP request and may be slow.
        Skip if network not available or to avoid rate limiting.
        """
        pytest.skip(
            "Skipping live scrape test to avoid rate limiting TBS servers. "
            "Run manually with: pytest -k test_scrape_single -s"
        )

        # If running manually:
        # url = "https://www.canada.ca/en/treasury-board-secretariat/services/collective-agreements/job-evaluation/information-technology-job-evaluation-standard.html"
        # records = scrape_evaluation_standard(url)
        # assert len(records) > 0
        # assert records[0].og_code == "IT"
