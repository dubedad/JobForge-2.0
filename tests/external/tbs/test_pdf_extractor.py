"""Tests for TBS PDF/HTML qualification standard extractor.

Tests cover:
1. QualificationStandardText model validation
2. PDF text extraction (with mock/fixture)
3. HTML extraction from linked_metadata
4. Text length validation
5. Graceful error handling
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from jobforge.external.tbs.pdf_extractor import (
    QualificationStandardText,
    download_qualification_pdf,
    extract_from_scraped_html,
    extract_qualification_standard,
    extract_all_qualification_standards,
    save_qualification_texts,
)


class TestQualificationStandardTextModel:
    """Test QualificationStandardText Pydantic model validation."""

    def test_valid_model_creation(self):
        """Model should accept valid qualification standard data."""
        model = QualificationStandardText(
            og_code="EC",
            full_text="This is the qualification standard for Economics and Social Science Services. " * 5,
            source_url="https://example.com/standards#ec",
            source_file="html",
        )

        assert model.og_code == "EC"
        assert model.subgroup_code is None
        assert model.source_type == "html"
        assert model.page_count == 1
        assert len(model.full_text) > 100

    def test_model_with_subgroup(self):
        """Model should accept subgroup_code."""
        model = QualificationStandardText(
            og_code="CT",
            subgroup_code="CT-FIN",
            full_text="Comptrollership Financial Management qualification standard. " * 5,
            source_url="https://example.com/standards#ct-fin",
            source_file="html",
        )

        assert model.og_code == "CT"
        assert model.subgroup_code == "CT-FIN"

    def test_model_with_tables(self):
        """Model should accept tables as nested lists."""
        model = QualificationStandardText(
            og_code="PM",
            full_text="Programme Administration qualification requirements. " * 5,
            tables=[
                [["Level", "Education"], ["PM-01", "Bachelor's degree"]],
                [["Experience", "Years"], ["Management", "2"]],
            ],
            source_url="https://example.com/standards#pm",
            source_file="html",
        )

        assert len(model.tables) == 2
        assert model.tables[0][0][0] == "Level"

    def test_model_with_pdf_metadata(self):
        """Model should accept PDF metadata dict."""
        model = QualificationStandardText(
            og_code="IT",
            full_text="Information Technology qualification standard content. " * 5,
            source_url="file:///path/to/it_qual.pdf",
            source_file="it_qual.pdf",
            source_type="pdf",
            page_count=5,
            pdf_metadata={
                "Author": "TBS",
                "CreationDate": "2023-01-15",
            },
        )

        assert model.source_type == "pdf"
        assert model.page_count == 5
        assert model.pdf_metadata["Author"] == "TBS"

    def test_model_requires_og_code(self):
        """Model should require og_code field."""
        with pytest.raises(ValidationError):
            QualificationStandardText(
                full_text="Some text",
                source_url="https://example.com",
                source_file="test",
            )

    def test_model_requires_full_text(self):
        """Model should require full_text field."""
        with pytest.raises(ValidationError):
            QualificationStandardText(
                og_code="EC",
                source_url="https://example.com",
                source_file="test",
            )

    def test_extracted_at_default(self):
        """Model should auto-generate extracted_at timestamp."""
        before = datetime.now(timezone.utc)
        model = QualificationStandardText(
            og_code="AS",
            full_text="Administrative Services qualification content. " * 5,
            source_url="https://example.com/standards#as",
            source_file="html",
        )
        after = datetime.now(timezone.utc)

        assert before <= model.extracted_at <= after


class TestExtractQualificationStandard:
    """Test PDF extraction with pdfplumber."""

    def test_file_not_found_raises(self, tmp_path):
        """Should raise FileNotFoundError for missing PDF."""
        fake_path = tmp_path / "nonexistent.pdf"

        with pytest.raises(FileNotFoundError, match="PDF not found"):
            extract_qualification_standard(fake_path)

    @patch("jobforge.external.tbs.pdf_extractor.pdfplumber.open")
    def test_extraction_text_too_short_raises(self, mock_pdfplumber, tmp_path):
        """Should raise ValueError if extracted text < 100 chars."""
        # Create a mock PDF file
        pdf_path = tmp_path / "AI_qual_standard.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test")

        # Mock pdfplumber to return short text
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Short text"
        mock_page.extract_tables.return_value = []
        mock_pdf.pages = [mock_page]
        mock_pdf.metadata = {}
        mock_pdfplumber.return_value.__enter__.return_value = mock_pdf

        with pytest.raises(ValueError, match="text too short"):
            extract_qualification_standard(pdf_path)

    @patch("jobforge.external.tbs.pdf_extractor.pdfplumber.open")
    def test_extraction_extracts_og_code_from_filename(self, mock_pdfplumber, tmp_path):
        """Should extract OG code from filename pattern."""
        pdf_path = tmp_path / "EC_qual_standard.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test")

        # Mock successful extraction
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Economics qualification standard. " * 10
        mock_page.extract_tables.return_value = []
        mock_pdf.pages = [mock_page]
        mock_pdf.metadata = {"Author": "TBS"}
        mock_pdfplumber.return_value.__enter__.return_value = mock_pdf

        result = extract_qualification_standard(pdf_path)

        assert result.og_code == "EC"
        assert result.source_type == "pdf"
        assert result.page_count == 1

    @patch("jobforge.external.tbs.pdf_extractor.pdfplumber.open")
    def test_extraction_handles_tables(self, mock_pdfplumber, tmp_path):
        """Should extract tables from PDF pages."""
        pdf_path = tmp_path / "PM_qual.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test")

        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Programme Administration standard. " * 10
        mock_page.extract_tables.return_value = [
            [["Level", "Education"], ["PM-01", "Degree"]],
        ]
        mock_pdf.pages = [mock_page]
        mock_pdf.metadata = {}
        mock_pdfplumber.return_value.__enter__.return_value = mock_pdf

        result = extract_qualification_standard(pdf_path)

        assert len(result.tables) == 1
        assert result.tables[0][0][0] == "Level"


class TestExtractFromScrapedHtml:
    """Test extraction from linked_metadata HTML data."""

    def test_extracts_from_linked_metadata(self, tmp_path):
        """Should extract qualification standards from linked_metadata JSON."""
        # Create mock linked_metadata
        metadata_file = tmp_path / "linked_metadata_en.json"
        metadata_file.write_text(
            """{
            "language": "en",
            "fetched_at": "2026-01-20T00:00:00Z",
            "total_links": 3,
            "successful_fetches": 3,
            "failed_fetches": 0,
            "metadata": [
                {
                    "group_abbrev": "EC",
                    "link_type": "qualification_standard",
                    "url": "https://example.com/standards#ec",
                    "content": {
                        "title": "Qualification Standards",
                        "main_content": "Economics and Social Science Services qualification standard content here with sufficient length to pass validation. " ,
                        "effective_date": null,
                        "last_modified": "2024-01-01"
                    },
                    "fetch_status": "success",
                    "provenance": {
                        "source_url": "https://example.com/standards#ec",
                        "scraped_at": "2026-01-20T00:00:00Z",
                        "extraction_method": "linked_page_content",
                        "page_title": "Qualification Standards"
                    }
                },
                {
                    "group_abbrev": "AI",
                    "link_type": "definition",
                    "url": "https://example.com/definitions#ai",
                    "content": {"title": "Definitions", "main_content": "Definition content"},
                    "fetch_status": "success",
                    "provenance": {}
                }
            ]
        }"""
        )

        results = extract_from_scraped_html(metadata_file)

        assert len(results) == 1  # Only qualification_standard, not definition
        assert results[0].og_code == "EC"
        assert results[0].source_type == "html"

    def test_skips_failed_fetches(self, tmp_path):
        """Should skip entries with fetch_status != 'success'."""
        metadata_file = tmp_path / "linked_metadata_en.json"
        metadata_file.write_text(
            """{
            "metadata": [
                {
                    "group_abbrev": "EC",
                    "link_type": "qualification_standard",
                    "url": "https://example.com/standards#ec",
                    "content": null,
                    "fetch_status": "failed"
                }
            ]
        }"""
        )

        results = extract_from_scraped_html(metadata_file)

        assert len(results) == 0

    def test_handles_missing_file(self, tmp_path):
        """Should return empty list for missing linked_metadata file."""
        results = extract_from_scraped_html(tmp_path / "nonexistent.json")

        assert results == []

    def test_extracts_subgroup_code(self, tmp_path):
        """Should extract subgroup code from group_abbrev like CT-FIN."""
        metadata_file = tmp_path / "linked_metadata_en.json"
        metadata_file.write_text(
            """{
            "metadata": [
                {
                    "group_abbrev": "CT-FIN",
                    "link_type": "qualification_standard",
                    "url": "https://example.com/standards#ct-fin",
                    "content": {
                        "title": "Qualification Standards",
                        "main_content": "Comptrollership Financial Management qualification standard content that is long enough to pass validation test. "
                    },
                    "fetch_status": "success",
                    "provenance": {
                        "scraped_at": "2026-01-20T00:00:00Z"
                    }
                }
            ]
        }"""
        )

        results = extract_from_scraped_html(metadata_file)

        assert len(results) == 1
        assert results[0].og_code == "CT"
        assert results[0].subgroup_code == "CT-FIN"


class TestDownloadQualificationPdf:
    """Test PDF download functionality."""

    @patch("jobforge.external.tbs.pdf_extractor.httpx.Client")
    def test_skips_existing_file(self, mock_client, tmp_path):
        """Should skip download if file already exists."""
        output_dir = tmp_path / "pdfs"
        output_dir.mkdir()
        existing_file = output_dir / "qual_standard_test.pdf"
        existing_file.write_bytes(b"%PDF-1.4 existing")

        result = download_qualification_pdf(
            "https://example.com/qual_standard_test.pdf",
            output_dir=output_dir,
        )

        assert result == existing_file
        mock_client.assert_not_called()

    @patch("jobforge.external.tbs.pdf_extractor.time.sleep")
    @patch("jobforge.external.tbs.pdf_extractor.httpx.Client")
    def test_downloads_pdf_successfully(self, mock_client_class, mock_sleep, tmp_path):
        """Should download PDF and save to output directory."""
        output_dir = tmp_path / "pdfs"

        # Mock response
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "application/pdf"}
        mock_response.content = b"%PDF-1.4 content"

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client

        result = download_qualification_pdf(
            "https://example.com/test.pdf",
            output_dir=output_dir,
        )

        assert result is not None
        assert result.exists()
        assert result.read_bytes() == b"%PDF-1.4 content"
        mock_sleep.assert_called_once_with(1.5)  # Rate limiting

    @patch("jobforge.external.tbs.pdf_extractor.httpx.Client")
    def test_returns_none_for_non_pdf(self, mock_client_class, tmp_path):
        """Should return None if content is not a PDF."""
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "text/html"}
        mock_response.content = b"<html>Not a PDF</html>"

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client

        result = download_qualification_pdf(
            "https://example.com/page.html",
            output_dir=tmp_path,
        )

        assert result is None


class TestExtractAllQualificationStandards:
    """Test combined extraction from all sources."""

    def test_extracts_html_only(self, tmp_path):
        """Should extract from HTML when no PDF URLs provided."""
        # Create mock linked_metadata
        metadata_file = tmp_path / "linked_metadata_en.json"
        metadata_file.write_text(
            """{
            "metadata": [
                {
                    "group_abbrev": "PM",
                    "link_type": "qualification_standard",
                    "url": "https://example.com/standards#pm",
                    "content": {
                        "title": "Standards",
                        "main_content": "Programme Administration qualification standard with sufficient content length for validation test. "
                    },
                    "fetch_status": "success",
                    "provenance": {"scraped_at": "2026-01-20T00:00:00Z"}
                }
            ]
        }"""
        )

        results = extract_all_qualification_standards(
            pdf_urls=None,
            include_html=True,
            linked_metadata_path=metadata_file,
        )

        assert len(results) == 1
        assert results[0].og_code == "PM"


class TestSaveQualificationTexts:
    """Test saving extracted data to JSON."""

    def test_saves_to_json(self, tmp_path):
        """Should save results to JSON file with correct structure."""
        output_path = tmp_path / "output.json"
        results = [
            QualificationStandardText(
                og_code="EC",
                full_text="Economics qualification standard content that meets minimum length. " * 3,
                source_url="https://example.com/standards#ec",
                source_file="html",
            ),
        ]

        saved_path = save_qualification_texts(results, output_path)

        assert saved_path == output_path
        assert output_path.exists()

        import json

        with open(output_path) as f:
            data = json.load(f)

        assert len(data) == 1
        assert data[0]["og_code"] == "EC"
        assert "extracted_at" in data[0]
        assert "source_url" in data[0]
