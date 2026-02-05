"""PDF and HTML extraction for TBS qualification standards.

This module handles extraction of qualification standard text from both:
1. PDF documents (using pdfplumber for text and table extraction)
2. HTML pages (leveraging existing linked_metadata scraped data)

The TBS qualification standards are primarily published as HTML pages at
https://www.canada.ca/en/treasury-board-secretariat/services/staffing/qualification-standards/core.html
but some specific standards may be available as PDFs.

All extracted data includes full provenance for audit trails.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import pdfplumber
import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

# Rate limiting for PDF downloads
REQUEST_DELAY_SECONDS = 1.5


class QualificationStandardText(BaseModel):
    """Extracted qualification standard with full provenance.

    Contains the qualification requirements for an occupational group,
    extracted from either PDF or HTML sources.
    """

    og_code: str = Field(description="Occupational group code (e.g., 'AI', 'EC')")
    subgroup_code: str | None = Field(
        default=None, description="Subgroup code if applicable (e.g., 'CT-FIN')"
    )
    full_text: str = Field(description="Full extracted text with layout preserved")
    tables: list[list[list[str]]] = Field(
        default_factory=list, description="Extracted tables as nested lists"
    )
    page_count: int = Field(default=1, description="Number of pages (1 for HTML)")
    source_url: str = Field(description="Original URL of the qualification standard")
    source_file: str = Field(description="Local filename or 'html' for web content")
    source_type: str = Field(
        default="html", description="Source type: 'pdf' or 'html'"
    )
    extracted_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when extraction occurred",
    )
    pdf_metadata: dict[str, Any] = Field(
        default_factory=dict, description="PDF metadata (empty for HTML sources)"
    )


def download_qualification_pdf(
    url: str,
    output_dir: str | Path = "data/tbs/og_qualifications",
    timeout: int = 60,
) -> Path | None:
    """Download a qualification standard PDF from TBS.

    Downloads the PDF and saves it locally with a descriptive filename.
    Implements rate limiting to avoid overwhelming canada.ca servers.

    Args:
        url: URL of the PDF to download.
        output_dir: Directory to save downloaded PDFs.
        timeout: HTTP request timeout in seconds.

    Returns:
        Path to downloaded file, or None if download failed.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Extract filename from URL or generate one
    url_path = url.split("/")[-1].split("?")[0]
    if url_path.endswith(".pdf"):
        filename = url_path
    else:
        # Generate filename from URL hash
        import hashlib

        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        filename = f"qual_standard_{url_hash}.pdf"

    output_path = output_dir / filename

    # Skip if already downloaded
    if output_path.exists():
        logger.info("pdf_already_exists", path=str(output_path))
        return output_path

    try:
        logger.info("downloading_pdf", url=url)
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()

            # Verify it's actually a PDF
            content_type = response.headers.get("content-type", "")
            if "pdf" not in content_type.lower() and not response.content[:5] == b"%PDF-":
                logger.warning(
                    "not_a_pdf",
                    url=url,
                    content_type=content_type,
                )
                return None

            output_path.write_bytes(response.content)
            logger.info("pdf_downloaded", path=str(output_path), size=len(response.content))

            # Rate limiting
            time.sleep(REQUEST_DELAY_SECONDS)

            return output_path

    except httpx.HTTPStatusError as e:
        logger.warning("pdf_download_http_error", url=url, status=e.response.status_code)
        return None
    except httpx.TimeoutException:
        logger.warning("pdf_download_timeout", url=url)
        return None
    except Exception as e:
        logger.warning("pdf_download_error", url=url, error=str(e))
        return None


def extract_qualification_standard(
    pdf_path: Path,
    source_url: str | None = None,
) -> QualificationStandardText:
    """Extract qualification standard text from a PDF file.

    Uses pdfplumber to extract text with layout preservation and tables.

    Args:
        pdf_path: Path to the PDF file.
        source_url: Original URL (for provenance).

    Returns:
        QualificationStandardText with extracted content.

    Raises:
        ValueError: If extraction fails or text too short (< 100 chars).
        FileNotFoundError: If PDF file doesn't exist.
    """
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    # Extract OG code from filename (e.g., "AI_qual_standard.pdf" -> "AI")
    stem = pdf_path.stem
    og_code = stem.split("_")[0].upper() if "_" in stem else stem.upper()

    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        all_tables: list[list[list[str]]] = []

        for page in pdf.pages:
            # Extract text preserving layout
            page_text = page.extract_text(layout=True)
            if page_text:
                full_text += page_text + "\n\n"

            # Extract tables
            page_tables = page.extract_tables()
            for table in page_tables:
                # Clean up table cells
                cleaned_table = [
                    [str(cell) if cell is not None else "" for cell in row]
                    for row in table
                ]
                all_tables.append(cleaned_table)

        # Validate extraction
        text_length = len(full_text.strip())
        if text_length < 100:
            raise ValueError(
                f"Extraction likely failed: text too short ({text_length} chars). "
                f"Expected >= 100 chars for qualification standard."
            )

        return QualificationStandardText(
            og_code=og_code,
            subgroup_code=None,  # Extracted from content if needed
            full_text=full_text.strip(),
            tables=all_tables,
            page_count=len(pdf.pages),
            source_url=source_url or f"file://{pdf_path.absolute()}",
            source_file=pdf_path.name,
            source_type="pdf",
            extracted_at=datetime.now(timezone.utc),
            pdf_metadata=dict(pdf.metadata) if pdf.metadata else {},
        )


def extract_from_scraped_html(
    linked_metadata_path: str | Path = "data/tbs/linked_metadata_en.json",
) -> list[QualificationStandardText]:
    """Extract qualification standards from already-scraped HTML data.

    The TBS qualification standards at core.html have already been scraped
    and stored in linked_metadata_en.json. This function extracts and
    structures that data.

    Args:
        linked_metadata_path: Path to linked_metadata JSON file.

    Returns:
        List of QualificationStandardText objects with HTML-sourced content.
    """
    linked_metadata_path = Path(linked_metadata_path)

    if not linked_metadata_path.exists():
        logger.warning("linked_metadata_not_found", path=str(linked_metadata_path))
        return []

    with open(linked_metadata_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    results: list[QualificationStandardText] = []
    seen_urls: set[str] = set()

    for item in data.get("metadata", []):
        # Only process qualification_standard links
        if item.get("link_type") != "qualification_standard":
            continue

        url = item.get("url", "")
        if url in seen_urls:
            continue
        seen_urls.add(url)

        # Skip failed fetches
        if item.get("fetch_status") != "success":
            continue

        content = item.get("content")
        if not content:
            continue

        og_code = item.get("group_abbrev", "UNKNOWN")
        main_content = content.get("main_content", "")

        if len(main_content) < 100:
            logger.warning(
                "html_content_too_short",
                og_code=og_code,
                length=len(main_content),
            )
            continue

        # Extract subgroup if present in og_code (e.g., "CT-FIN")
        subgroup_code = None
        if "-" in og_code:
            subgroup_code = og_code

        provenance = item.get("provenance", {})
        scraped_at_str = provenance.get("scraped_at")
        scraped_at = (
            datetime.fromisoformat(scraped_at_str.replace("Z", "+00:00"))
            if scraped_at_str
            else datetime.now(timezone.utc)
        )

        result = QualificationStandardText(
            og_code=og_code.split("-")[0] if "-" in og_code else og_code,
            subgroup_code=subgroup_code,
            full_text=main_content,
            tables=[],  # HTML content doesn't have structured tables
            page_count=1,
            source_url=url,
            source_file="html",
            source_type="html",
            extracted_at=scraped_at,
            pdf_metadata={
                "page_title": content.get("title", ""),
                "effective_date": content.get("effective_date"),
                "last_modified": content.get("last_modified"),
            },
        )
        results.append(result)

    logger.info(
        "extracted_from_html",
        count=len(results),
        source=str(linked_metadata_path),
    )

    return results


def extract_all_qualification_standards(
    pdf_urls: list[str] | None = None,
    include_html: bool = True,
    pdf_output_dir: str | Path = "data/tbs/og_qualifications",
    linked_metadata_path: str | Path = "data/tbs/linked_metadata_en.json",
) -> list[QualificationStandardText]:
    """Extract qualification standards from all available sources.

    Combines PDF downloads and HTML scrape data to get comprehensive
    qualification standard coverage.

    Args:
        pdf_urls: List of PDF URLs to download and extract (optional).
        include_html: Whether to include HTML-scraped qualification standards.
        pdf_output_dir: Directory to save downloaded PDFs.
        linked_metadata_path: Path to linked_metadata JSON file.

    Returns:
        List of QualificationStandardText objects from all sources.
    """
    results: list[QualificationStandardText] = []

    # Extract from HTML scraped data first
    if include_html:
        html_results = extract_from_scraped_html(linked_metadata_path)
        results.extend(html_results)
        logger.info("html_extraction_complete", count=len(html_results))

    # Download and extract PDFs
    if pdf_urls:
        pdf_output_dir = Path(pdf_output_dir)
        pdf_count = 0
        failed_count = 0

        for url in pdf_urls:
            pdf_path = download_qualification_pdf(url, pdf_output_dir)

            if pdf_path:
                try:
                    pdf_result = extract_qualification_standard(pdf_path, source_url=url)
                    results.append(pdf_result)
                    pdf_count += 1
                except ValueError as e:
                    logger.warning("pdf_extraction_failed", url=url, error=str(e))
                    failed_count += 1
                except Exception as e:
                    logger.warning("pdf_extraction_error", url=url, error=str(e))
                    failed_count += 1
            else:
                failed_count += 1

        logger.info(
            "pdf_extraction_complete",
            downloaded=pdf_count,
            failed=failed_count,
        )

    logger.info("all_extraction_complete", total=len(results))
    return results


def save_qualification_texts(
    results: list[QualificationStandardText],
    output_path: str | Path = "data/tbs/og_qualification_text.json",
) -> Path:
    """Save extracted qualification texts to JSON with provenance.

    Args:
        results: List of QualificationStandardText objects.
        output_path: Path to save the JSON file.

    Returns:
        Path to saved file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = [r.model_dump(mode="json") for r in results]

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info(
        "saved_qualification_texts",
        path=str(output_path),
        count=len(results),
    )

    return output_path
