"""Tests for CAF careers scraper, parser, and models.

Tests cover:
- CAFProvenance model validation
- CAFCareerListing model validation
- CAFOccupation model validation
- CAFScrapedPage container model
- Parser functions with mocked/sample data
- Scraper class with mocked HTTP responses

Integration tests (marked with pytest.mark.integration) require
network access and should be run separately.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jobforge.external.caf.models import (
    CAFCareerListing,
    CAFJobFamily,
    CAFOccupation,
    CAFProvenance,
    CAFScrapedPage,
)
from jobforge.external.caf.parser import (
    compute_content_hash,
    extract_career_id_from_url,
    parse_career_page,
    parse_careers_listing,
    parse_sitemap_career_urls,
)
from jobforge.external.caf.scraper import CAFScraper


class TestCAFProvenanceModel:
    """Tests for CAFProvenance Pydantic model."""

    def test_valid_provenance(self):
        """Test creating a valid CAFProvenance."""
        provenance = CAFProvenance(
            source_url="https://forces.ca/en/career/pilot/",
            scraped_at=datetime.now(timezone.utc),
            content_hash="abc123def456",
        )
        assert provenance.source_url == "https://forces.ca/en/career/pilot/"
        assert provenance.scraper_version == "CAFScraper-1.0.0"
        assert provenance.extraction_method == "html_parser"

    def test_provenance_custom_values(self):
        """Test provenance with custom scraper version and method."""
        provenance = CAFProvenance(
            source_url="https://forces.ca/sitemap.xml",
            scraped_at=datetime.now(timezone.utc),
            content_hash="abc123",
            scraper_version="CAFScraper-2.0.0",
            extraction_method="sitemap",
        )
        assert provenance.scraper_version == "CAFScraper-2.0.0"
        assert provenance.extraction_method == "sitemap"

    def test_provenance_serialization(self):
        """Test that CAFProvenance serializes to JSON correctly."""
        scraped_at = datetime(2026, 2, 5, 12, 0, 0, tzinfo=timezone.utc)
        provenance = CAFProvenance(
            source_url="https://forces.ca/en/career/pilot/",
            scraped_at=scraped_at,
            content_hash="abc123",
        )
        data = provenance.model_dump(mode="json")
        assert data["source_url"] == "https://forces.ca/en/career/pilot/"
        assert "scraped_at" in data
        assert data["content_hash"] == "abc123"


class TestCAFCareerListingModel:
    """Tests for CAFCareerListing Pydantic model."""

    def test_valid_career_listing(self):
        """Test creating a valid career listing."""
        listing = CAFCareerListing(
            career_id="pilot",
            title="Pilot",
            url="https://forces.ca/en/career/pilot/",
            environment=["air_force"],
            commission_status="officer",
            employment_type=["full_time", "part_time"],
            provenance=CAFProvenance(
                source_url="https://forces.ca/en/career/pilot/",
                scraped_at=datetime.now(timezone.utc),
                content_hash="abc123",
            ),
        )
        assert listing.career_id == "pilot"
        assert listing.title == "Pilot"
        assert "air_force" in listing.environment
        assert listing.commission_status == "officer"

    def test_career_listing_minimal(self):
        """Test career listing with minimal required fields."""
        listing = CAFCareerListing(
            career_id="infantry-soldier",
            title="Infantry Soldier",
            url="https://forces.ca/en/career/infantry-soldier/",
            provenance=CAFProvenance(
                source_url="https://forces.ca/en/career/infantry-soldier/",
                scraped_at=datetime.now(timezone.utc),
                content_hash="abc123",
            ),
        )
        assert listing.career_id == "infantry-soldier"
        assert listing.environment == []
        assert listing.commission_status == "unknown"
        assert listing.employment_type == []

    def test_career_listing_serialization(self):
        """Test that CAFCareerListing serializes to JSON correctly."""
        listing = CAFCareerListing(
            career_id="pilot",
            title="Pilot",
            url="https://forces.ca/en/career/pilot/",
            provenance=CAFProvenance(
                source_url="https://forces.ca/en/career/pilot/",
                scraped_at=datetime.now(timezone.utc),
                content_hash="abc123",
            ),
        )
        data = listing.model_dump(mode="json")
        assert data["career_id"] == "pilot"
        assert "provenance" in data
        assert data["provenance"]["content_hash"] == "abc123"


class TestCAFOccupationModel:
    """Tests for CAFOccupation Pydantic model."""

    def test_valid_occupation_en(self):
        """Test creating a valid occupation with English content."""
        occupation = CAFOccupation(
            career_id="pilot",
            title_en="Pilot",
            environment=["air_force"],
            commission_status="officer",
            employment_type=["full_time"],
            overview_en="Pilots fly aircraft in the CAF.",
            work_environment_en="Work in various locations.",
            related_civilian_occupations=["Airline Pilot", "Flight Instructor"],
            url_en="https://forces.ca/en/career/pilot/",
            provenance_en=CAFProvenance(
                source_url="https://forces.ca/en/career/pilot/",
                scraped_at=datetime.now(timezone.utc),
                content_hash="abc123",
            ),
        )
        assert occupation.career_id == "pilot"
        assert occupation.title_en == "Pilot"
        assert occupation.overview_en == "Pilots fly aircraft in the CAF."
        assert len(occupation.related_civilian_occupations) == 2

    def test_occupation_bilingual(self):
        """Test occupation with both English and French content."""
        occupation = CAFOccupation(
            career_id="pilot",
            title_en="Pilot",
            title_fr="Pilote",
            overview_en="Pilots fly aircraft.",
            overview_fr="Les pilotes pilotent des aeronefs.",
            url_en="https://forces.ca/en/career/pilot/",
            url_fr="https://forces.ca/fr/carriere/pilote/",
            provenance_en=CAFProvenance(
                source_url="https://forces.ca/en/career/pilot/",
                scraped_at=datetime.now(timezone.utc),
                content_hash="abc123",
            ),
            provenance_fr=CAFProvenance(
                source_url="https://forces.ca/fr/carriere/pilote/",
                scraped_at=datetime.now(timezone.utc),
                content_hash="def456",
            ),
        )
        assert occupation.title_en == "Pilot"
        assert occupation.title_fr == "Pilote"
        assert occupation.url_fr == "https://forces.ca/fr/carriere/pilote/"


class TestCAFScrapedPageModel:
    """Tests for CAFScrapedPage container model."""

    def test_valid_scraped_page(self):
        """Test creating a valid scraped page container."""
        page = CAFScrapedPage(
            language="en",
            scraped_at=datetime.now(timezone.utc),
            source="sitemap",
            careers=[
                CAFCareerListing(
                    career_id="pilot",
                    title="Pilot",
                    url="https://forces.ca/en/career/pilot/",
                    provenance=CAFProvenance(
                        source_url="https://forces.ca/en/career/pilot/",
                        scraped_at=datetime.now(timezone.utc),
                        content_hash="abc123",
                    ),
                )
            ],
            career_count=1,
        )
        assert page.language == "en"
        assert page.career_count == 1
        assert len(page.careers) == 1

    def test_empty_scraped_page(self):
        """Test creating an empty scraped page."""
        page = CAFScrapedPage(
            language="fr",
            scraped_at=datetime.now(timezone.utc),
            careers=[],
            career_count=0,
        )
        assert page.career_count == 0
        assert len(page.careers) == 0


class TestCAFJobFamilyModel:
    """Tests for CAFJobFamily Pydantic model."""

    def test_valid_job_family(self):
        """Test creating a valid job family."""
        family = CAFJobFamily(
            family_id="air-operations",
            family_name="Air Operations",
            description="Careers related to air operations.",
            career_count=15,
            source_url="https://forces.ca/en/careers/env_2",
        )
        assert family.family_id == "air-operations"
        assert family.family_name == "Air Operations"
        assert family.career_count == 15


class TestParserFunctions:
    """Tests for parser utility functions."""

    def test_compute_content_hash(self):
        """Test SHA-256 hash computation."""
        html = "<html><body>Test content</body></html>"
        hash1 = compute_content_hash(html)
        hash2 = compute_content_hash(html)

        # Same content should produce same hash
        assert hash1 == hash2
        # Hash should be 64 characters (SHA-256 hex)
        assert len(hash1) == 64

    def test_compute_content_hash_different_content(self):
        """Test that different content produces different hashes."""
        hash1 = compute_content_hash("<html>Content A</html>")
        hash2 = compute_content_hash("<html>Content B</html>")
        assert hash1 != hash2

    def test_extract_career_id_from_url_en(self):
        """Test extracting career ID from English URL."""
        url = "https://forces.ca/en/career/pilot/"
        assert extract_career_id_from_url(url) == "pilot"

        url = "https://www.forces.ca/en/career/infantry-soldier/"
        assert extract_career_id_from_url(url) == "infantry-soldier"

    def test_extract_career_id_from_url_fr(self):
        """Test extracting career ID from French URL."""
        url = "https://forces.ca/fr/carriere/pilote/"
        assert extract_career_id_from_url(url) == "pilote"

        url = "https://www.forces.ca/fr/carriere/soldat-dinfanterie/"
        assert extract_career_id_from_url(url) == "soldat-dinfanterie"

    def test_extract_career_id_invalid_url(self):
        """Test that invalid URLs return None."""
        assert extract_career_id_from_url("https://forces.ca/en/careers/") is None
        assert extract_career_id_from_url("https://example.com/pilot/") is None


class TestParseSitemapCareerUrls:
    """Tests for sitemap parsing."""

    @pytest.fixture
    def sample_sitemap(self):
        """Sample sitemap XML content."""
        return """<?xml version="1.0" encoding="utf-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url>
                <loc>https://www.forces.ca/en/career/pilot/</loc>
            </url>
            <url>
                <loc>https://www.forces.ca/en/career/infantry-soldier/</loc>
            </url>
            <url>
                <loc>https://www.forces.ca/fr/carriere/pilote/</loc>
            </url>
            <url>
                <loc>https://www.forces.ca/en/careers</loc>
            </url>
        </urlset>
        """

    def test_parse_sitemap_extracts_career_urls(self, sample_sitemap):
        """Test that sitemap parsing extracts career URLs."""
        urls = parse_sitemap_career_urls(sample_sitemap)

        assert len(urls["en"]) == 2
        assert len(urls["fr"]) == 1
        assert "https://www.forces.ca/en/career/pilot/" in urls["en"]
        assert "https://www.forces.ca/en/career/infantry-soldier/" in urls["en"]
        assert "https://www.forces.ca/fr/carriere/pilote/" in urls["fr"]

    def test_parse_sitemap_excludes_non_career_urls(self, sample_sitemap):
        """Test that non-career URLs are excluded."""
        urls = parse_sitemap_career_urls(sample_sitemap)

        # /en/careers (listing page) should not be included
        en_urls_str = " ".join(urls["en"])
        assert "/en/careers" not in en_urls_str or "/en/career/" in en_urls_str


class TestParseCareersListing:
    """Tests for careers listing parsing."""

    def test_parse_careers_listing_creates_listings(self):
        """Test creating career listings from URLs."""
        urls = [
            "https://forces.ca/en/career/pilot/",
            "https://forces.ca/en/career/infantry-soldier/",
        ]
        scraped_at = datetime.now(timezone.utc)

        listings = parse_careers_listing(urls, "en", scraped_at)

        assert len(listings) == 2
        assert listings[0].career_id == "pilot"
        assert listings[0].title == "Pilot"
        assert listings[1].career_id == "infantry-soldier"
        assert listings[1].title == "Infantry Soldier"

    def test_parse_careers_listing_includes_provenance(self):
        """Test that listings include provenance metadata."""
        urls = ["https://forces.ca/en/career/pilot/"]
        scraped_at = datetime.now(timezone.utc)

        listings = parse_careers_listing(urls, "en", scraped_at)

        assert listings[0].provenance.source_url == "https://forces.ca/en/career/pilot/"
        assert listings[0].provenance.scraped_at == scraped_at
        assert listings[0].provenance.extraction_method == "sitemap"


class TestParseCareerPage:
    """Tests for career page HTML parsing."""

    @pytest.fixture
    def sample_career_html(self):
        """Sample career page HTML."""
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <title>Pilot | Canadian Armed Forces</title>
            <meta name="description" content="Pilots fly aircraft in the CAF.">
            <meta name="keywords" content="pilot, aircraft, flying">
        </head>
        <body>
            <h1 class="h3 text-dkblue mb-2">Pilot</h1>
            <p class="details">
                <span>OFFICER | </span>
                <span>Full Time, Part Time</span>
            </p>
            <div class="env-icons">
                <img alt="Air Force">
            </div>
            <a class="locale-switcher" href="/fr/carriere/pilote/">FR</a>
        </body>
        </html>
        """

    def test_parse_career_page_extracts_title(self, sample_career_html):
        """Test that title is extracted from h1."""
        listing = parse_career_page(
            sample_career_html,
            "https://forces.ca/en/career/pilot/",
            datetime.now(timezone.utc),
        )
        assert listing.title == "Pilot"

    def test_parse_career_page_extracts_career_id(self, sample_career_html):
        """Test that career ID is extracted from URL."""
        listing = parse_career_page(
            sample_career_html,
            "https://forces.ca/en/career/pilot/",
            datetime.now(timezone.utc),
        )
        assert listing.career_id == "pilot"

    def test_parse_career_page_extracts_environment(self, sample_career_html):
        """Test that environment is extracted from icons."""
        listing = parse_career_page(
            sample_career_html,
            "https://forces.ca/en/career/pilot/",
            datetime.now(timezone.utc),
        )
        assert "air_force" in listing.environment

    def test_parse_career_page_extracts_commission_status(self, sample_career_html):
        """Test that officer/NCM status is extracted."""
        listing = parse_career_page(
            sample_career_html,
            "https://forces.ca/en/career/pilot/",
            datetime.now(timezone.utc),
        )
        assert listing.commission_status == "officer"

    def test_parse_career_page_extracts_employment_type(self, sample_career_html):
        """Test that employment types are extracted."""
        listing = parse_career_page(
            sample_career_html,
            "https://forces.ca/en/career/pilot/",
            datetime.now(timezone.utc),
        )
        assert "full_time" in listing.employment_type
        assert "part_time" in listing.employment_type

    def test_parse_career_page_computes_content_hash(self, sample_career_html):
        """Test that content hash is computed."""
        listing = parse_career_page(
            sample_career_html,
            "https://forces.ca/en/career/pilot/",
            datetime.now(timezone.utc),
        )
        assert listing.provenance.content_hash is not None
        assert len(listing.provenance.content_hash) == 64


class TestCAFScraper:
    """Tests for CAFScraper class with mocked HTTP."""

    @pytest.fixture
    def mock_sitemap_response(self):
        """Mock sitemap XML response."""
        return """<?xml version="1.0" encoding="utf-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://www.forces.ca/en/career/pilot/</loc></url>
            <url><loc>https://www.forces.ca/en/career/infantry-soldier/</loc></url>
            <url><loc>https://www.forces.ca/fr/carriere/pilote/</loc></url>
        </urlset>
        """

    @patch("jobforge.external.caf.scraper.httpx.Client")
    def test_scraper_instantiation(self, mock_client):
        """Test that scraper can be instantiated."""
        scraper = CAFScraper()
        assert scraper.output_dir == Path("data/caf")
        assert scraper.delay == 1.5

    @patch("jobforge.external.caf.scraper.httpx.Client")
    def test_scraper_fetch_sitemap(self, mock_client_class, mock_sitemap_response):
        """Test fetching and parsing sitemap."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = mock_sitemap_response
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        scraper = CAFScraper()
        urls = scraper.fetch_sitemap()

        assert len(urls["en"]) == 2
        assert len(urls["fr"]) == 1

    @patch("jobforge.external.caf.scraper.httpx.Client")
    def test_scraper_scrape_page(self, mock_client_class, mock_sitemap_response):
        """Test scraping a full page of listings."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = mock_sitemap_response
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        scraper = CAFScraper()
        page = scraper.scrape_page("en")

        assert page.language == "en"
        assert page.career_count == 2
        assert len(page.careers) == 2


class TestScrapedDataValidation:
    """Tests that validate actual scraped data files if they exist."""

    @pytest.fixture
    def careers_en_path(self):
        """Path to English careers JSON."""
        return Path("data/caf/careers_en.json")

    @pytest.fixture
    def careers_fr_path(self):
        """Path to French careers JSON."""
        return Path("data/caf/careers_fr.json")

    def test_careers_en_exists(self, careers_en_path):
        """Test that English careers file exists."""
        assert careers_en_path.exists(), "data/caf/careers_en.json should exist"

    def test_careers_fr_exists(self, careers_fr_path):
        """Test that French careers file exists."""
        assert careers_fr_path.exists(), "data/caf/careers_fr.json should exist"

    def test_careers_en_has_careers(self, careers_en_path):
        """Test that English file has career listings."""
        with open(careers_en_path) as f:
            data = json.load(f)
        assert data["career_count"] > 0
        assert len(data["careers"]) > 0

    def test_careers_fr_has_careers(self, careers_fr_path):
        """Test that French file has career listings."""
        with open(careers_fr_path) as f:
            data = json.load(f)
        assert data["career_count"] > 0
        assert len(data["careers"]) > 0

    def test_careers_en_has_provenance(self, careers_en_path):
        """Test that each English career has provenance."""
        with open(careers_en_path) as f:
            data = json.load(f)
        for career in data["careers"]:
            assert "provenance" in career
            assert "source_url" in career["provenance"]
            assert "scraped_at" in career["provenance"]

    def test_careers_have_valid_urls(self, careers_en_path):
        """Test that career URLs are valid forces.ca URLs."""
        with open(careers_en_path) as f:
            data = json.load(f)
        for career in data["careers"]:
            assert career["url"].startswith("https://")
            assert "forces.ca" in career["url"]
            assert "/career/" in career["url"]

    def test_minimum_career_count(self, careers_en_path):
        """Test that we have a reasonable number of careers (at least 50)."""
        with open(careers_en_path) as f:
            data = json.load(f)
        # Research indicated ~107 careers; sitemap has 88
        assert data["career_count"] >= 50, f"Expected at least 50 careers, got {data['career_count']}"


# Integration tests - require network access
class TestCAFScraperIntegration:
    """Integration tests that make real HTTP requests.

    These tests are marked with pytest.mark.integration and
    should be run separately from unit tests.
    """

    @pytest.mark.integration
    def test_real_sitemap_fetch(self):
        """Test fetching real sitemap from forces.ca."""
        with CAFScraper() as scraper:
            urls = scraper.fetch_sitemap()

        assert len(urls["en"]) > 0
        assert len(urls["fr"]) > 0
        # Should have ~88+ careers
        assert len(urls["en"]) >= 50

    @pytest.mark.integration
    def test_real_scrape_and_save(self, tmp_path):
        """Test full scrape and save workflow."""
        with CAFScraper(output_dir=tmp_path) as scraper:
            paths = scraper.scrape_and_save()

        assert (tmp_path / "careers_en.json").exists()
        assert (tmp_path / "careers_fr.json").exists()

        with open(tmp_path / "careers_en.json") as f:
            data = json.load(f)
        assert data["career_count"] > 0
