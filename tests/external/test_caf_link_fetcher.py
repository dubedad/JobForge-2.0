"""Tests for CAF career detail link fetcher.

Tests validate:
- Bilingual content storage (EN/FR in same record)
- Provenance metadata on all records
- No row duplication (single record per career)
- Job family inference
- Link fetcher class functionality
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jobforge.external.caf.link_fetcher import (
    CAFLinkFetcher,
    FetchResult,
    fetch_all_career_details,
    fetch_career_detail,
)
from jobforge.external.caf.models import (
    CAFJobFamily,
    CAFOccupation,
    CAFProvenance,
)


class TestFetchResult:
    """Tests for FetchResult named tuple."""

    def test_successful_result(self):
        """Test creating a successful fetch result."""
        result = FetchResult(
            success=True,
            html="<html></html>",
            content_hash="abc123",
            error_message=None,
        )
        assert result.success is True
        assert result.html == "<html></html>"
        assert result.content_hash == "abc123"
        assert result.error_message is None

    def test_failed_result(self):
        """Test creating a failed fetch result."""
        result = FetchResult(
            success=False,
            html=None,
            content_hash=None,
            error_message="HTTP 404",
        )
        assert result.success is False
        assert result.html is None
        assert result.error_message == "HTTP 404"


class TestCAFLinkFetcher:
    """Tests for CAFLinkFetcher class."""

    @patch("jobforge.external.caf.link_fetcher.httpx.Client")
    def test_fetcher_instantiation(self, mock_client):
        """Test that fetcher can be instantiated."""
        fetcher = CAFLinkFetcher()
        assert fetcher.data_dir == Path("data/caf")
        assert fetcher.delay == 1.5

    @patch("jobforge.external.caf.link_fetcher.httpx.Client")
    def test_fetcher_custom_data_dir(self, mock_client):
        """Test fetcher with custom data directory."""
        fetcher = CAFLinkFetcher(data_dir="custom/path")
        assert fetcher.data_dir == Path("custom/path")

    @patch("jobforge.external.caf.link_fetcher.httpx.Client")
    def test_fetcher_context_manager(self, mock_client_class):
        """Test fetcher as context manager."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        with CAFLinkFetcher() as fetcher:
            assert fetcher is not None

        mock_client.close.assert_called_once()

    @pytest.fixture
    def sample_en_html(self):
        """Sample English career page HTML."""
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <title>Pilot | Canadian Armed Forces</title>
            <meta name="description" content="Pilots fly aircraft in the CAF.">
            <meta name="keywords" content="pilot, aircraft, flying">
        </head>
        <body>
            <h1>Pilot</h1>
            <p class="details">
                <span>OFFICER | </span>
                <span>Full Time, Part Time</span>
            </p>
            <div class="env-icons">
                <img alt="Air Force">
            </div>
            <a class="locale-switcher" href="/fr/carriere/pilote/">FR</a>
            <section id="sec-overview">
                <article>
                    <p>Pilots are responsible for flying aircraft.</p>
                </article>
            </section>
            <h3>Related Civilian Occupations</h3>
            <ul>
                <li>Airline Pilot</li>
                <li>Flight Instructor</li>
            </ul>
        </body>
        </html>
        """

    @pytest.fixture
    def sample_fr_html(self):
        """Sample French career page HTML."""
        return """
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <title>Pilote | Forces armees canadiennes</title>
        </head>
        <body>
            <h1>Pilote</h1>
            <section id="sec-overview">
                <article>
                    <p>Les pilotes sont responsables du pilotage des aeronefs.</p>
                </article>
            </section>
        </body>
        </html>
        """

    @patch("jobforge.external.caf.link_fetcher.httpx.Client")
    def test_fetch_career_page_success(self, mock_client_class, sample_en_html):
        """Test successful career page fetch."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = sample_en_html
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        fetcher = CAFLinkFetcher()
        result = fetcher.fetch_career_page("https://forces.ca/en/career/pilot/")

        assert result.success is True
        assert result.html == sample_en_html
        assert result.content_hash is not None
        assert len(result.content_hash) == 64  # SHA-256 hex

    @patch("jobforge.external.caf.link_fetcher.httpx.Client")
    def test_fetch_career_page_failure(self, mock_client_class):
        """Test failed career page fetch."""
        mock_client = MagicMock()
        # Simulate a generic error that doesn't trigger retry
        mock_client.get.side_effect = Exception("Connection refused")
        mock_client_class.return_value = mock_client

        fetcher = CAFLinkFetcher()
        result = fetcher.fetch_career_page("https://forces.ca/en/career/invalid/")

        assert result.success is False
        assert result.html is None
        assert result.error_message is not None

    @patch("jobforge.external.caf.link_fetcher.httpx.Client")
    def test_extract_fr_url_from_html(self, mock_client_class, sample_en_html):
        """Test French URL extraction from English page."""
        mock_client_class.return_value = MagicMock()

        fetcher = CAFLinkFetcher()
        fr_url = fetcher._extract_fr_url_from_html(sample_en_html)

        assert fr_url == "https://forces.ca/fr/carriere/pilote/"


class TestBilingualStorage:
    """Tests validating bilingual content storage pattern.

    Per CONTEXT.md: Store EN/FR in separate columns, not separate rows.
    """

    @pytest.fixture
    def occupations_path(self):
        """Path to occupations JSON."""
        return Path("data/caf/occupations.json")

    def test_occupations_file_exists(self, occupations_path):
        """Test that occupations file exists."""
        assert occupations_path.exists(), "data/caf/occupations.json should exist"

    def test_no_duplicate_career_ids(self, occupations_path):
        """Test that each career_id appears exactly once (no row duplication)."""
        with open(occupations_path, encoding="utf-8") as f:
            data = json.load(f)

        career_ids = [occ["career_id"] for occ in data["occupations"]]
        unique_ids = set(career_ids)

        assert len(career_ids) == len(unique_ids), "Duplicate career_ids found"

    def test_bilingual_fields_in_same_record(self, occupations_path):
        """Test that EN/FR content is in same record (columns, not rows)."""
        with open(occupations_path, encoding="utf-8") as f:
            data = json.load(f)

        # Check first occupation has both EN and FR fields
        occ = data["occupations"][0]

        # EN fields
        assert "title_en" in occ
        assert "overview_en" in occ
        assert "url_en" in occ

        # FR fields should be present (may be None if not found)
        assert "title_fr" in occ
        assert "overview_fr" in occ

    def test_bilingual_content_not_empty(self, occupations_path):
        """Test that bilingual occupations have content in both languages."""
        with open(occupations_path, encoding="utf-8") as f:
            data = json.load(f)

        bilingual_count = 0
        for occ in data["occupations"]:
            if occ.get("title_fr"):
                bilingual_count += 1
                # If FR title exists, check FR content exists too
                assert occ.get("url_fr"), f"{occ['career_id']} has FR title but no FR URL"

        # Most occupations should be bilingual
        assert bilingual_count > len(data["occupations"]) * 0.5, "Less than 50% bilingual"


class TestProvenanceMetadata:
    """Tests validating provenance tracking on all records."""

    @pytest.fixture
    def occupations_path(self):
        """Path to occupations JSON."""
        return Path("data/caf/occupations.json")

    def test_all_occupations_have_provenance_en(self, occupations_path):
        """Test that all occupations have EN provenance."""
        with open(occupations_path, encoding="utf-8") as f:
            data = json.load(f)

        for occ in data["occupations"]:
            assert "provenance_en" in occ, f"{occ['career_id']} missing provenance_en"
            prov = occ["provenance_en"]
            assert "source_url" in prov, f"{occ['career_id']} missing source_url"
            assert "scraped_at" in prov, f"{occ['career_id']} missing scraped_at"
            assert "content_hash" in prov, f"{occ['career_id']} missing content_hash"

    def test_provenance_content_hash_not_pending(self, occupations_path):
        """Test that content hashes are actual SHA-256 (not 'pending')."""
        with open(occupations_path, encoding="utf-8") as f:
            data = json.load(f)

        for occ in data["occupations"]:
            prov = occ["provenance_en"]
            content_hash = prov["content_hash"]
            assert content_hash != "pending", f"{occ['career_id']} has pending hash"
            assert len(content_hash) == 64, f"{occ['career_id']} has invalid hash length"

    def test_provenance_source_urls_valid(self, occupations_path):
        """Test that source URLs are valid forces.ca URLs."""
        with open(occupations_path, encoding="utf-8") as f:
            data = json.load(f)

        for occ in data["occupations"]:
            url = occ["provenance_en"]["source_url"]
            assert "forces.ca" in url, f"{occ['career_id']} has invalid source URL"
            assert "/career/" in url, f"{occ['career_id']} not a career URL"


class TestJobFamilyInference:
    """Tests for job family inference logic."""

    @pytest.fixture
    def job_families_path(self):
        """Path to job families JSON."""
        return Path("data/caf/job_families.json")

    def test_job_families_file_exists(self, job_families_path):
        """Test that job families file exists."""
        assert job_families_path.exists(), "data/caf/job_families.json should exist"

    def test_job_families_reasonable_count(self, job_families_path):
        """Test that we have a reasonable number of job families (8-15)."""
        with open(job_families_path, encoding="utf-8") as f:
            data = json.load(f)

        family_count = data["family_count"]
        # RESEARCH.md mentioned ~12 families
        assert 8 <= family_count <= 15, f"Unexpected family count: {family_count}"

    def test_job_families_have_careers(self, job_families_path):
        """Test that each family has at least one career."""
        with open(job_families_path, encoding="utf-8") as f:
            data = json.load(f)

        for family in data["families"]:
            assert family["career_count"] > 0, f"{family['family_id']} has no careers"

    def test_job_families_total_matches_occupations(self, job_families_path):
        """Test that total careers across families matches occupation count."""
        occupations_path = Path("data/caf/occupations.json")

        with open(job_families_path, encoding="utf-8") as f:
            families_data = json.load(f)

        with open(occupations_path, encoding="utf-8") as f:
            occupations_data = json.load(f)

        total_in_families = sum(f["career_count"] for f in families_data["families"])
        total_occupations = occupations_data["occupation_count"]

        assert total_in_families == total_occupations, (
            f"Family total ({total_in_families}) != occupation count ({total_occupations})"
        )

    @patch("jobforge.external.caf.link_fetcher.httpx.Client")
    def test_infer_medical_family(self, mock_client_class):
        """Test that medical careers are grouped together."""
        mock_client_class.return_value = MagicMock()

        fetcher = CAFLinkFetcher()

        # Create test occupation with medical title
        occ = CAFOccupation(
            career_id="medical-officer",
            title_en="Medical Officer",
            url_en="https://forces.ca/en/career/medical-officer/",
            provenance_en=CAFProvenance(
                source_url="https://forces.ca/en/career/medical-officer/",
                scraped_at=datetime.now(timezone.utc),
                content_hash="abc123",
            ),
        )

        family_id = fetcher._infer_family_for_occupation(occ)
        assert family_id == "medical-health"

    @patch("jobforge.external.caf.link_fetcher.httpx.Client")
    def test_infer_engineering_family(self, mock_client_class):
        """Test that engineering careers are grouped together."""
        mock_client_class.return_value = MagicMock()

        fetcher = CAFLinkFetcher()

        occ = CAFOccupation(
            career_id="aerospace-engineering-officer",
            title_en="Aerospace Engineering Officer",
            url_en="https://forces.ca/en/career/aerospace-engineering-officer/",
            provenance_en=CAFProvenance(
                source_url="https://forces.ca/en/career/aerospace-engineering-officer/",
                scraped_at=datetime.now(timezone.utc),
                content_hash="abc123",
            ),
        )

        family_id = fetcher._infer_family_for_occupation(occ)
        assert family_id == "engineering-technical"

    @patch("jobforge.external.caf.link_fetcher.httpx.Client")
    def test_infer_combat_family(self, mock_client_class):
        """Test that combat careers are grouped together."""
        mock_client_class.return_value = MagicMock()

        fetcher = CAFLinkFetcher()

        occ = CAFOccupation(
            career_id="infantry-soldier",
            title_en="Infantry Soldier",
            url_en="https://forces.ca/en/career/infantry-soldier/",
            provenance_en=CAFProvenance(
                source_url="https://forces.ca/en/career/infantry-soldier/",
                scraped_at=datetime.now(timezone.utc),
                content_hash="abc123",
            ),
        )

        family_id = fetcher._infer_family_for_occupation(occ)
        assert family_id == "combat-operations"


class TestRelatedCivilianOccupations:
    """Tests for related civilian occupations extraction."""

    @pytest.fixture
    def occupations_path(self):
        """Path to occupations JSON."""
        return Path("data/caf/occupations.json")

    def test_some_occupations_have_related_civilian(self, occupations_path):
        """Test that at least some occupations have related civilian jobs."""
        with open(occupations_path, encoding="utf-8") as f:
            data = json.load(f)

        with_related = sum(
            1 for occ in data["occupations"]
            if occ.get("related_civilian_occupations")
        )

        # At least some occupations should have related civilian jobs
        assert with_related > 0, "No occupations have related civilian occupations"


class TestOccupationContentSections:
    """Tests for occupation content section extraction."""

    @pytest.fixture
    def occupations_path(self):
        """Path to occupations JSON."""
        return Path("data/caf/occupations.json")

    def test_occupations_have_overview(self, occupations_path):
        """Test that most occupations have overview content."""
        with open(occupations_path, encoding="utf-8") as f:
            data = json.load(f)

        with_overview = sum(
            1 for occ in data["occupations"]
            if occ.get("overview_en")
        )

        # Most occupations should have overview
        assert with_overview > len(data["occupations"]) * 0.5, "Less than 50% have overview"


# Integration tests - require network access
class TestCAFLinkFetcherIntegration:
    """Integration tests that make real HTTP requests.

    These tests are marked with pytest.mark.integration and
    should be run separately from unit tests.
    """

    @pytest.mark.integration
    def test_real_single_career_fetch(self):
        """Test fetching a real career page."""
        occupation = fetch_career_detail("https://forces.ca/en/career/pilot/")

        assert occupation is not None
        assert occupation.career_id == "pilot"
        assert occupation.title_en is not None
        assert occupation.provenance_en.content_hash != "pending"

    @pytest.mark.integration
    def test_real_bilingual_fetch(self):
        """Test that bilingual content is fetched correctly."""
        occupation = fetch_career_detail("https://forces.ca/en/career/pilot/")

        assert occupation is not None
        assert occupation.title_en is not None
        assert occupation.title_fr is not None
        assert occupation.url_fr is not None
