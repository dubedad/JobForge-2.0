"""Tests for TBS (Treasury Board Secretariat) scraper package.

This module tests the parser, models, scraper, link fetcher, and schema
extension components for TBS occupational group data.
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jobforge.external.tbs import (
    DIM_OCCUPATIONS_TBS_FIELD_NAMES,
    DIM_OCCUPATIONS_TBS_FIELDS,
    LinkMetadataFetcher,
    LinkedMetadataCollection,
    LinkedPageContent,
    LinkedPageMetadata,
    OccupationalGroupRow,
    REQUEST_DELAY_SECONDS,
    ScrapedPage,
    ScrapedProvenance,
    TBS_EXPECTED_COLUMNS,
    TBS_EXPECTED_COLUMNS_FR,
    TBS_REQUIRED_COLUMNS,
    TBS_REQUIRED_COLUMNS_FR,
    TBS_URLS,
    TBSScraper,
    extract_embedded_links,
    fetch_linked_metadata,
    get_tbs_field_descriptions,
    get_tbs_field_types,
    parse_occupational_groups_table,
    scrape_occupational_groups,
    validate_table_structure,
)

# ==============================================================================
# Test Fixtures
# ==============================================================================

MOCK_TBS_HTML_EN = """
<!DOCTYPE html>
<html>
<head><title>Occupational Groups - Canada.ca</title></head>
<body>
<table>
<tr>
    <th>Group abbreviation</th>
    <th>Code</th>
    <th>Occupational Group</th>
    <th>Group</th>
    <th>Subgroup</th>
    <th>Definition</th>
    <th>Job evaluation standard</th>
    <th>Qualification standard</th>
</tr>
<tr>
    <td>AI</td>
    <td>001</td>
    <td>Air Traffic Control</td>
    <td>AI</td>
    <td></td>
    <td><a href="/en/def/ai">Yes</a></td>
    <td><a href="/en/eval/ai">Yes</a></td>
    <td><a href="/en/qual/ai">Yes</a></td>
</tr>
<tr>
    <td>CR</td>
    <td>002</td>
    <td>Clerical and Regulatory</td>
    <td>PA</td>
    <td>CR</td>
    <td><a href="/en/def/cr">Yes</a></td>
    <td></td>
    <td><a href="/en/qual/cr">Yes</a></td>
</tr>
</table>
</body>
</html>
"""

MOCK_TBS_HTML_FR = """
<!DOCTYPE html>
<html>
<head><title>Groupes professionnels - Canada.ca</title></head>
<body>
<table>
<tr>
    <th>Abréviation de groupe</th>
    <th>Code</th>
    <th>Groupe professionnel</th>
    <th>Groupe</th>
    <th>Sous-groupe</th>
    <th>Définition</th>
    <th>Norme d'évaluation des emplois</th>
    <th>Norme de qualification</th>
</tr>
<tr>
    <td>AI</td>
    <td>001</td>
    <td>Contrôle de la circulation aérienne</td>
    <td>AI</td>
    <td></td>
    <td><a href="/fr/def/ai">Oui</a></td>
    <td><a href="/fr/eval/ai">Oui</a></td>
    <td><a href="/fr/qual/ai">Oui</a></td>
</tr>
</table>
</body>
</html>
"""

MOCK_DEFINITION_HTML = """
<!DOCTYPE html>
<html>
<head><title>AI Group Definition</title></head>
<body>
<h1>Air Traffic Control Group (AI)</h1>
<article>
<p>The Air Traffic Control Group comprises positions that are primarily involved in...</p>
<p>Effective date: 2023-01-01</p>
</article>
<dl id="wb-dtmd"><dd>2023-11-07</dd></dl>
</body>
</html>
"""

MOCK_HTML_NO_TABLE = """
<!DOCTYPE html>
<html>
<head><title>Empty Page</title></head>
<body><p>No table here</p></body>
</html>
"""

MOCK_HTML_WRONG_COLUMNS = """
<!DOCTYPE html>
<html>
<head><title>Wrong Columns</title></head>
<body>
<table>
<tr>
    <th>Wrong Column 1</th>
    <th>Wrong Column 2</th>
</tr>
</table>
</body>
</html>
"""


@pytest.fixture
def mock_scraped_at():
    """Fixed timestamp for testing."""
    return datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)


@pytest.fixture
def mock_provenance(mock_scraped_at):
    """Mock provenance for testing."""
    return ScrapedProvenance(
        source_url="https://example.com/test",
        scraped_at=mock_scraped_at,
        extraction_method="table_cell",
        page_title="Test Page",
    )


# ==============================================================================
# Parser Tests (no network needed)
# ==============================================================================


class TestValidateTableStructure:
    """Tests for validate_table_structure function."""

    def test_validate_table_structure_valid_en(self):
        """Valid English table structure returns True."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(MOCK_TBS_HTML_EN, "lxml")
        table = soup.find("table")
        assert validate_table_structure(table, "en") is True

    def test_validate_table_structure_valid_fr(self):
        """Valid French table structure returns True."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(MOCK_TBS_HTML_FR, "lxml")
        table = soup.find("table")
        assert validate_table_structure(table, "fr") is True

    def test_validate_table_structure_invalid(self):
        """Invalid table structure raises ValueError."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(MOCK_HTML_WRONG_COLUMNS, "lxml")
        table = soup.find("table")
        with pytest.raises(ValueError, match="Missing expected column"):
            validate_table_structure(table, "en")


class TestParseOccupationalGroupsTable:
    """Tests for parse_occupational_groups_table function."""

    def test_parse_valid_html_en(self, mock_scraped_at):
        """Valid English HTML parses correctly."""
        rows = parse_occupational_groups_table(
            MOCK_TBS_HTML_EN,
            "https://example.com/en",
            mock_scraped_at,
        )

        assert len(rows) == 2
        assert rows[0].group_abbrev == "AI"
        assert rows[0].group_code == "001"
        assert rows[0].group_name == "Air Traffic Control"
        assert rows[1].group_abbrev == "CR"
        assert rows[1].subgroup == "CR"

    def test_parse_valid_html_fr(self, mock_scraped_at):
        """Valid French HTML parses correctly with auto-detection."""
        rows = parse_occupational_groups_table(
            MOCK_TBS_HTML_FR,
            "https://example.com/fr/page",
            mock_scraped_at,
        )

        assert len(rows) == 1
        assert rows[0].group_abbrev == "AI"
        assert rows[0].group_name == "Contrôle de la circulation aérienne"

    def test_parse_extracts_links(self, mock_scraped_at):
        """Definition, eval, and qualification URLs are extracted."""
        rows = parse_occupational_groups_table(
            MOCK_TBS_HTML_EN,
            "https://example.com/en",
            mock_scraped_at,
        )

        assert rows[0].definition_url == "https://www.canada.ca/en/def/ai"
        assert rows[0].job_eval_standard_url == "https://www.canada.ca/en/eval/ai"
        assert rows[0].qualification_standard_url == "https://www.canada.ca/en/qual/ai"

    def test_parse_handles_missing_links(self, mock_scraped_at):
        """Missing links return None."""
        rows = parse_occupational_groups_table(
            MOCK_TBS_HTML_EN,
            "https://example.com/en",
            mock_scraped_at,
        )

        # CR row has no job eval standard link
        assert rows[1].job_eval_standard_url is None

    def test_parse_fails_on_missing_table(self, mock_scraped_at):
        """Raises ValueError when no table found."""
        with pytest.raises(ValueError, match="No table found"):
            parse_occupational_groups_table(
                MOCK_HTML_NO_TABLE,
                "https://example.com/en",
                mock_scraped_at,
            )

    def test_parse_fails_on_wrong_columns(self, mock_scraped_at):
        """Raises ValueError when columns don't match expected structure."""
        with pytest.raises(ValueError, match="Missing expected column"):
            parse_occupational_groups_table(
                MOCK_HTML_WRONG_COLUMNS,
                "https://example.com/en",
                mock_scraped_at,
            )


class TestExtractEmbeddedLinks:
    """Tests for extract_embedded_links function."""

    def test_extract_embedded_links(self, mock_scraped_at):
        """Returns dict with link lists by type."""
        rows = parse_occupational_groups_table(
            MOCK_TBS_HTML_EN,
            "https://example.com/en",
            mock_scraped_at,
        )
        links = extract_embedded_links(rows)

        assert "definitions" in links
        assert "job_eval_standards" in links
        assert "qualification_standards" in links
        assert len(links["definitions"]) == 2
        assert len(links["job_eval_standards"]) == 1  # CR has no eval standard
        assert len(links["qualification_standards"]) == 2


# ==============================================================================
# Model Tests
# ==============================================================================


class TestOccupationalGroupRow:
    """Tests for OccupationalGroupRow model."""

    def test_valid_data_creates_model(self, mock_provenance):
        """Valid data creates model successfully."""
        row = OccupationalGroupRow(
            group_abbrev="AI",
            group_code="001",
            group_name="Air Traffic Control",
            subgroup=None,
            definition_url="https://example.com/def",
            job_eval_standard_url=None,
            qualification_standard_url="https://example.com/qual",
            provenance=mock_provenance,
        )
        assert row.group_abbrev == "AI"
        assert row.group_code == "001"
        assert row.subgroup is None

    def test_optional_urls_default_to_none(self, mock_provenance):
        """Optional URL fields default to None."""
        row = OccupationalGroupRow(
            group_abbrev="AI",
            group_code="001",
            group_name="Air Traffic Control",
            provenance=mock_provenance,
        )
        assert row.definition_url is None
        assert row.job_eval_standard_url is None
        assert row.qualification_standard_url is None


class TestScrapedProvenance:
    """Tests for ScrapedProvenance model."""

    def test_required_fields(self):
        """All provenance fields are required."""
        now = datetime.now(timezone.utc)
        prov = ScrapedProvenance(
            source_url="https://example.com",
            scraped_at=now,
            extraction_method="table_cell",
            page_title="Test",
        )
        assert prov.source_url == "https://example.com"
        assert prov.scraped_at == now
        assert prov.extraction_method == "table_cell"
        assert prov.page_title == "Test"


class TestScrapedPage:
    """Tests for ScrapedPage model."""

    def test_row_and_link_counts(self, mock_provenance):
        """row_count and link_count are stored."""
        page = ScrapedPage(
            url="https://example.com",
            language="en",
            title="Test Page",
            scraped_at=datetime.now(timezone.utc),
            rows=[
                OccupationalGroupRow(
                    group_abbrev="AI",
                    group_code="001",
                    group_name="Test",
                    provenance=mock_provenance,
                )
            ],
            link_count=3,
            row_count=1,
        )
        assert page.row_count == 1
        assert page.link_count == 3


class TestLinkedPageMetadata:
    """Tests for LinkedPageMetadata model."""

    def test_success_case_creates_valid_model(self, mock_provenance):
        """Success case with content creates valid model."""
        content = LinkedPageContent(
            title="Test Definition",
            main_content="This is the definition text.",
            effective_date="2023-01-01",
            last_modified="2023-11-07",
        )
        metadata = LinkedPageMetadata(
            group_abbrev="AI",
            link_type="definition",
            url="https://example.com/def",
            content=content,
            fetch_status="success",
            error_message=None,
            provenance=mock_provenance,
        )
        assert metadata.fetch_status == "success"
        assert metadata.content is not None
        assert metadata.content.title == "Test Definition"

    def test_failure_case_stores_error(self, mock_provenance):
        """Failure case stores error message without content."""
        metadata = LinkedPageMetadata(
            group_abbrev="AI",
            link_type="definition",
            url="https://example.com/def",
            content=None,
            fetch_status="failed",
            error_message="HTTP 500",
            provenance=mock_provenance,
        )
        assert metadata.fetch_status == "failed"
        assert metadata.content is None
        assert metadata.error_message == "HTTP 500"


# ==============================================================================
# Scraper Tests (mock network)
# ==============================================================================


class TestTBSScraper:
    """Tests for TBSScraper class."""

    def test_creates_output_dir(self, tmp_path):
        """Output directory created if missing."""
        output_dir = tmp_path / "new_dir"
        scraper = TBSScraper(output_dir)
        assert output_dir.exists()

    @patch("jobforge.external.tbs.scraper.requests.get")
    def test_scraper_saves_json(self, mock_get, tmp_path):
        """JSON file written with correct structure."""
        mock_response = MagicMock()
        mock_response.text = MOCK_TBS_HTML_EN
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        scraper = TBSScraper(tmp_path)
        page = scraper.scrape_page("en")
        path = scraper.save_to_json(page)

        assert path.exists()
        assert path.name == "occupational_groups_en.json"

        import json

        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert "url" in data
        assert "scraped_at" in data
        assert "rows" in data

    @patch("jobforge.external.tbs.scraper.requests.get")
    def test_scraper_bilingual(self, mock_get):
        """Both en and fr URLs are used."""
        # Return appropriate HTML based on URL
        def mock_response_for_url(url, **kwargs):
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            if "/fr/" in url:
                mock_response.text = MOCK_TBS_HTML_FR
            else:
                mock_response.text = MOCK_TBS_HTML_EN
            return mock_response

        mock_get.side_effect = mock_response_for_url

        scraper = TBSScraper()
        scraper.scrape_both_languages()

        # Should have been called with both URLs
        calls = [call[0][0] for call in mock_get.call_args_list]
        assert TBS_URLS["en"] in calls
        assert TBS_URLS["fr"] in calls

    @patch("jobforge.external.tbs.scraper.requests.get")
    def test_scraper_provenance_in_output(self, mock_get, tmp_path):
        """scraped_at timestamp appears in JSON output."""
        mock_response = MagicMock()
        mock_response.text = MOCK_TBS_HTML_EN
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        scraper = TBSScraper(tmp_path)
        page = scraper.scrape_page("en")
        path = scraper.save_to_json(page)

        import json

        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert "scraped_at" in data
        assert data["rows"][0]["provenance"]["scraped_at"] is not None


# ==============================================================================
# Link Fetcher Tests (mock network)
# ==============================================================================


class TestLinkMetadataFetcher:
    """Tests for LinkMetadataFetcher class."""

    def test_parses_content(self):
        """Extracts title and main_content from HTML."""
        fetcher = LinkMetadataFetcher()
        content = fetcher._parse_linked_page(MOCK_DEFINITION_HTML, "https://example.com")

        assert content.title == "Air Traffic Control Group (AI)"
        assert "Air Traffic Control Group comprises" in content.main_content
        assert content.last_modified == "2023-11-07"

    @patch("jobforge.external.tbs.link_fetcher.requests.get")
    def test_handles_404(self, mock_get, mock_provenance):
        """Returns not_found status for 404 errors."""
        from requests.exceptions import HTTPError

        mock_response = MagicMock()
        mock_response.status_code = 404
        error = HTTPError(response=mock_response)
        mock_get.side_effect = error

        fetcher = LinkMetadataFetcher()
        result = fetcher.fetch_single_link(
            url="https://example.com/missing",
            group_abbrev="AI",
            link_type="definition",
        )

        assert result.fetch_status == "not_found"
        assert result.content is None
        assert "404" in result.error_message

    @patch("jobforge.external.tbs.link_fetcher.requests.get")
    def test_handles_timeout(self, mock_get):
        """Returns failed status with error for timeout."""
        from requests.exceptions import Timeout

        mock_get.side_effect = Timeout("Request timed out")

        fetcher = LinkMetadataFetcher()
        result = fetcher.fetch_single_link(
            url="https://example.com/slow",
            group_abbrev="AI",
            link_type="definition",
        )

        assert result.fetch_status == "failed"
        assert result.content is None
        assert "timeout" in result.error_message.lower()

    @patch("jobforge.external.tbs.link_fetcher.requests.get")
    @patch("jobforge.external.tbs.link_fetcher.time.sleep")
    def test_collection_counts(self, mock_sleep, mock_get, mock_provenance):
        """total, successful, and failed counts are correct."""
        # First call succeeds, second fails
        mock_success = MagicMock()
        mock_success.text = MOCK_DEFINITION_HTML
        mock_success.raise_for_status = MagicMock()

        mock_fail = MagicMock()
        mock_fail.raise_for_status.side_effect = Exception("Failed")

        mock_get.side_effect = [mock_success, mock_fail]

        rows = [
            OccupationalGroupRow(
                group_abbrev="AI",
                group_code="001",
                group_name="Test",
                definition_url="https://example.com/def1",
                provenance=mock_provenance,
            ),
            OccupationalGroupRow(
                group_abbrev="CR",
                group_code="002",
                group_name="Test2",
                definition_url="https://example.com/def2",
                provenance=mock_provenance,
            ),
        ]

        fetcher = LinkMetadataFetcher()
        collection = fetcher.fetch_all_links(rows, "en")

        assert collection.total_links == 2
        assert collection.successful_fetches == 1
        assert collection.failed_fetches == 1


# ==============================================================================
# Schema Extension Tests
# ==============================================================================


class TestSchemaExtension:
    """Tests for TBS schema extension fields."""

    def test_dim_occupations_has_tbs_fields(self):
        """DIM Occupations TBS fields are defined."""
        assert len(DIM_OCCUPATIONS_TBS_FIELDS) >= 10

    def test_tbs_field_names_list(self):
        """Field names list contains expected fields."""
        assert "tbs_group_code" in DIM_OCCUPATIONS_TBS_FIELD_NAMES
        assert "tbs_group_abbrev" in DIM_OCCUPATIONS_TBS_FIELD_NAMES
        assert "tbs_group_name" in DIM_OCCUPATIONS_TBS_FIELD_NAMES
        assert "tbs_definition_url" in DIM_OCCUPATIONS_TBS_FIELD_NAMES
        assert "tbs_definition_content" in DIM_OCCUPATIONS_TBS_FIELD_NAMES
        assert "tbs_job_eval_standard_url" in DIM_OCCUPATIONS_TBS_FIELD_NAMES
        assert "tbs_job_eval_content" in DIM_OCCUPATIONS_TBS_FIELD_NAMES
        assert "tbs_qualification_standard_url" in DIM_OCCUPATIONS_TBS_FIELD_NAMES
        assert "tbs_qualification_content" in DIM_OCCUPATIONS_TBS_FIELD_NAMES
        assert "tbs_scraped_at" in DIM_OCCUPATIONS_TBS_FIELD_NAMES

    def test_get_tbs_field_types(self):
        """Field types are TEXT or TIMESTAMP."""
        types = get_tbs_field_types()
        assert types["tbs_group_code"] == "TEXT"
        assert types["tbs_scraped_at"] == "TIMESTAMP"

    def test_get_tbs_field_descriptions(self):
        """Field descriptions are non-empty strings."""
        descriptions = get_tbs_field_descriptions()
        for name, desc in descriptions.items():
            assert isinstance(desc, str)
            assert len(desc) > 0


# ==============================================================================
# Constants Tests
# ==============================================================================


class TestConstants:
    """Tests for module constants."""

    def test_tbs_urls_defined(self):
        """TBS URLs for both languages are defined."""
        assert "en" in TBS_URLS
        assert "fr" in TBS_URLS
        assert "canada.ca" in TBS_URLS["en"]
        assert "canada.ca" in TBS_URLS["fr"]

    def test_expected_columns_defined(self):
        """Expected columns for EN and FR are defined."""
        assert len(TBS_EXPECTED_COLUMNS) > 0
        assert len(TBS_EXPECTED_COLUMNS_FR) > 0
        assert "group abbreviation" in TBS_EXPECTED_COLUMNS
        assert "abréviation de groupe" in TBS_EXPECTED_COLUMNS_FR

    def test_required_columns_defined(self):
        """Required columns for EN and FR are defined."""
        assert len(TBS_REQUIRED_COLUMNS) >= 3
        assert len(TBS_REQUIRED_COLUMNS_FR) >= 3

    def test_request_delay_reasonable(self):
        """Request delay is a reasonable value."""
        assert REQUEST_DELAY_SECONDS >= 0.5
        assert REQUEST_DELAY_SECONDS <= 10.0


# ==============================================================================
# Integration Tests (require network - skip by default)
# ==============================================================================


@pytest.mark.integration
class TestIntegration:
    """Integration tests that require network access.

    Run with: pytest -m integration
    """

    def test_scrape_real_page(self):
        """Actually scrapes TBS page (requires network)."""
        scraper = TBSScraper()
        page = scraper.scrape_page("en")

        assert page.row_count > 0
        assert page.language == "en"
        assert len(page.rows) > 0
        assert page.rows[0].provenance.source_url == TBS_URLS["en"]

    def test_fetch_real_link(self):
        """Actually fetches one definition page (requires network)."""
        fetcher = LinkMetadataFetcher()
        result = fetcher.fetch_single_link(
            url="https://www.canada.ca/en/treasury-board-secretariat/services/collective-agreements/occupational-groups/definitions.html#def-ai",
            group_abbrev="AI",
            link_type="definition",
        )

        assert result.fetch_status == "success"
        assert result.content is not None
        assert len(result.content.main_content) > 0
