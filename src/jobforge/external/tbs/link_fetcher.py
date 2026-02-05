"""Link fetcher for traversing embedded TBS URLs.

This module handles the "two levels deep" traversal per CONTEXT.md,
fetching metadata from definition, evaluation, and qualification
standard pages linked from the main occupational groups table.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
import structlog
from bs4 import BeautifulSoup

from .models import (
    LinkedMetadataCollection,
    LinkedPageContent,
    LinkedPageMetadata,
    OccupationalGroupRow,
    OGDefinition,
    ScrapedProvenance,
)

logger = structlog.get_logger(__name__)

# Polite delay between requests to avoid hammering canada.ca
REQUEST_DELAY_SECONDS = 1.0


class LinkMetadataFetcher:
    """Fetches and parses metadata from embedded TBS links.

    Per CONTEXT.md: Traverse two levels deep from main page.
    This fetcher follows links from the scraped table to extract
    definition content, qualification standards, and job evaluation
    standards for each occupational group.

    Args:
        output_dir: Directory where linked metadata JSON files will be saved.
    """

    def __init__(self, output_dir: str | Path = "data/tbs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _parse_linked_page(self, html: str, url: str) -> LinkedPageContent:
        """Extract structured content from a linked page.

        TBS pages typically have:
        - h1 for title
        - main content in article or main tag
        - dates in metadata or visible text

        Args:
            html: Raw HTML content of the page.
            url: URL that was fetched (for logging).

        Returns:
            LinkedPageContent with extracted title, content, and dates.
        """
        soup = BeautifulSoup(html, "lxml")

        # Extract title
        title_tag = soup.find("h1") or soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else "Unknown"

        # Extract main content - try article, main, or content div
        content_tag = (
            soup.find("article")
            or soup.find("main")
            or soup.find("div", {"class": "mwsgeneric-base-html"})
            or soup.find("div", {"id": "content"})
        )

        if content_tag:
            # Get text from paragraphs and list items, clean up whitespace
            paragraphs = content_tag.find_all(["p", "li"])
            main_content = "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
        else:
            # Fallback: get body text
            main_content = soup.get_text(separator="\n", strip=True)[:5000]

        # Try to find dates
        effective_date = None
        last_modified = None

        # Look for "Date modified" pattern common on canada.ca
        date_dl = soup.find("dl", {"id": "wb-dtmd"})
        if date_dl:
            dd = date_dl.find("dd")
            if dd:
                last_modified = dd.get_text(strip=True)

        # Also try time element in dateModified section
        time_tag = soup.find("time", {"property": "dateModified"})
        if time_tag:
            last_modified = time_tag.get("datetime") or time_tag.get_text(strip=True)

        # Look for "Effective date" in content
        for text in soup.stripped_strings:
            text_lower = text.lower()
            if ("effective" in text_lower or "date" in text_lower) and any(c.isdigit() for c in text):
                # Only capture if it looks like a date line
                if len(text) < 100:
                    effective_date = text
                    break

        return LinkedPageContent(
            title=title,
            main_content=main_content[:10000],  # Cap content length
            effective_date=effective_date,
            last_modified=last_modified,
        )

    def fetch_single_link(
        self,
        url: str,
        group_abbrev: str,
        link_type: str,
        timeout: int = 30,
    ) -> LinkedPageMetadata:
        """Fetch and parse a single linked page.

        Handles HTTP errors gracefully, recording failure status
        rather than raising exceptions.

        Args:
            url: URL to fetch.
            group_abbrev: Parent group abbreviation (for metadata).
            link_type: Type of link ('definition', 'job_eval_standard', 'qualification_standard').
            timeout: HTTP request timeout in seconds.

        Returns:
            LinkedPageMetadata with content or error information.
        """
        scraped_at = datetime.now(timezone.utc)
        provenance = ScrapedProvenance(
            source_url=url,
            scraped_at=scraped_at,
            extraction_method="linked_page_content",
            page_title="",  # Will be updated after fetch
        )

        try:
            logger.debug("fetching_linked_page", url=url, link_type=link_type)
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()

            content = self._parse_linked_page(response.text, url)
            provenance = ScrapedProvenance(
                source_url=url,
                scraped_at=scraped_at,
                extraction_method="linked_page_content",
                page_title=content.title,
            )

            return LinkedPageMetadata(
                group_abbrev=group_abbrev,
                link_type=link_type,
                url=url,
                content=content,
                fetch_status="success",
                error_message=None,
                provenance=provenance,
            )

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            logger.warning("http_error_fetching_link", url=url, status=status)
            return LinkedPageMetadata(
                group_abbrev=group_abbrev,
                link_type=link_type,
                url=url,
                content=None,
                fetch_status="not_found" if status == 404 else "failed",
                error_message=f"HTTP {status}",
                provenance=provenance,
            )

        except requests.exceptions.Timeout:
            logger.warning("timeout_fetching_link", url=url)
            return LinkedPageMetadata(
                group_abbrev=group_abbrev,
                link_type=link_type,
                url=url,
                content=None,
                fetch_status="failed",
                error_message="Request timeout",
                provenance=provenance,
            )

        except Exception as e:
            logger.warning("error_fetching_link", url=url, error=str(e))
            return LinkedPageMetadata(
                group_abbrev=group_abbrev,
                link_type=link_type,
                url=url,
                content=None,
                fetch_status="failed",
                error_message=str(e),
                provenance=provenance,
            )

    def fetch_all_links(
        self,
        rows: list[OccupationalGroupRow],
        language: str = "en",
    ) -> LinkedMetadataCollection:
        """Fetch metadata from all embedded links in scraped rows.

        Per CONTEXT.md: Traverse two levels deep from main page.
        This is level 2 - following links from the main table.

        Uses polite delays between requests to avoid overwhelming canada.ca.

        Args:
            rows: List of OccupationalGroupRow objects from main table scrape.
            language: Language code ('en' or 'fr') for logging.

        Returns:
            LinkedMetadataCollection with results for all links.
        """
        logger.info(
            "fetching_linked_metadata",
            language=language,
            row_count=len(rows),
        )

        all_metadata: list[LinkedPageMetadata] = []
        successful = 0
        failed = 0

        # Track unique URLs to avoid duplicate fetches
        seen_urls: set[str] = set()

        for row in rows:
            # Fetch each link type if present and not already fetched
            links_to_fetch = [
                (row.definition_url, "definition"),
                (row.job_eval_standard_url, "job_eval_standard"),
                (row.qualification_standard_url, "qualification_standard"),
            ]

            for url, link_type in links_to_fetch:
                if not url or url in seen_urls:
                    continue

                seen_urls.add(url)

                metadata = self.fetch_single_link(
                    url=url,
                    group_abbrev=row.group_abbrev,
                    link_type=link_type,
                )
                all_metadata.append(metadata)

                if metadata.fetch_status == "success":
                    successful += 1
                else:
                    failed += 1

                # Polite delay between requests
                time.sleep(REQUEST_DELAY_SECONDS)

        logger.info(
            "completed_fetching_linked_metadata",
            language=language,
            total=len(all_metadata),
            successful=successful,
            failed=failed,
        )

        return LinkedMetadataCollection(
            language=language,
            fetched_at=datetime.now(timezone.utc),
            total_links=len(all_metadata),
            successful_fetches=successful,
            failed_fetches=failed,
            metadata=all_metadata,
        )

    def save_to_json(self, collection: LinkedMetadataCollection) -> Path:
        """Save linked metadata to JSON file.

        Args:
            collection: LinkedMetadataCollection to save.

        Returns:
            Path to the saved JSON file.
        """
        filename = f"linked_metadata_{collection.language}.json"
        filepath = self.output_dir / filename

        data = collection.model_dump(mode="json")

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(
            "saved_linked_metadata",
            filepath=str(filepath),
            total=collection.total_links,
            successful=collection.successful_fetches,
        )
        return filepath


def fetch_linked_metadata(
    scraped_data_path: str | Path,
    output_dir: str | Path = "data/tbs",
) -> Path:
    """Fetch metadata from all links in a scraped occupational groups file.

    Convenience function that loads an existing scrape result and
    follows all embedded links to fetch additional metadata.

    Args:
        scraped_data_path: Path to occupational_groups_{lang}.json file.
        output_dir: Where to save linked_metadata_{lang}.json.

    Returns:
        Path to saved linked metadata file.

    Example:
        path = fetch_linked_metadata("data/tbs/occupational_groups_en.json")
        print(path)  # data/tbs/linked_metadata_en.json
    """
    scraped_data_path = Path(scraped_data_path)

    with open(scraped_data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Reconstruct rows from JSON
    rows = [OccupationalGroupRow(**r) for r in data["rows"]]
    language = data["language"]

    fetcher = LinkMetadataFetcher(output_dir)
    collection = fetcher.fetch_all_links(rows, language)
    return fetcher.save_to_json(collection)


def fetch_og_definition(
    url: str,
    og_code: str,
    subgroup_code: str | None = None,
    timeout: int = 30,
) -> OGDefinition | None:
    """Fetch and extract definition from a TBS definition page.

    Makes an HTTP request to the definition URL and extracts the
    definition text content with provenance tracking.

    Args:
        url: URL of the definition page.
        og_code: Parent occupational group code (e.g., "AI", "AS").
        subgroup_code: Subgroup code if this is a subgroup definition, None for parent OG.
        timeout: HTTP request timeout in seconds.

    Returns:
        OGDefinition object with extracted text, or None if fetch failed.

    Note:
        Includes 1.5 second delay after request to respect rate limits.
        Handles 404 errors gracefully by returning None.
    """
    scraped_at = datetime.now(timezone.utc)

    try:
        logger.debug("fetching_og_definition", url=url, og_code=og_code, subgroup_code=subgroup_code)
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        # Extract page title
        title_tag = soup.find("h1") or soup.find("title")
        page_title = title_tag.get_text(strip=True) if title_tag else "Unknown"

        # Extract definition content
        # TBS definition pages typically have content in article/main tags
        # or in a div with mwsgeneric-base-html class
        content_tag = (
            soup.find("article")
            or soup.find("main")
            or soup.find("div", {"class": "mwsgeneric-base-html"})
            or soup.find("div", {"id": "content"})
        )

        if content_tag:
            # Get text from paragraphs and list items
            paragraphs = content_tag.find_all(["p", "li"])
            definition_text = "\n\n".join(
                p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)
            )
        else:
            # Fallback: get body text
            definition_text = soup.get_text(separator="\n", strip=True)[:10000]

        # Rate limit delay
        time.sleep(1.5)

        return OGDefinition(
            og_code=og_code,
            subgroup_code=subgroup_code,
            definition_text=definition_text[:10000],  # Cap at 10k chars
            page_title=page_title,
            source_url=url,
            scraped_at=scraped_at,
        )

    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "unknown"
        logger.warning("http_error_fetching_definition", url=url, status=status)
        time.sleep(1.5)  # Still delay on error to be polite
        return None

    except requests.exceptions.Timeout:
        logger.warning("timeout_fetching_definition", url=url)
        time.sleep(1.5)
        return None

    except Exception as e:
        logger.warning("error_fetching_definition", url=url, error=str(e))
        time.sleep(1.5)
        return None
