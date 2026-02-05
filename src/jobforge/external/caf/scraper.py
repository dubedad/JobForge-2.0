"""CAF Careers scraper with provenance tracking.

This module orchestrates the scraping of Canadian Armed Forces
careers pages from forces.ca, supporting both English and French content.
All scraped data carries full provenance information.

Following TBS scraper pattern per CONTEXT.md and RESEARCH.md.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .models import CAFCareerListing, CAFScrapedPage
from .parser import (
    CAF_BASE_URL,
    CAF_SITEMAP_URL,
    parse_career_page,
    parse_careers_listing,
    parse_sitemap_career_urls,
)

logger = structlog.get_logger(__name__)

# Rate limiting: 1.5s between requests (polite scraping)
REQUEST_DELAY_SECONDS = 1.5

# Default timeout for HTTP requests
DEFAULT_TIMEOUT = 30


class CAFScraper:
    """CAF Careers scraper with provenance tracking.

    Supports scraping both English and French pages, with automatic
    provenance tracking for all extracted data. Uses sitemap.xml
    for URL discovery per RESEARCH.md recommendation.

    Args:
        output_dir: Directory where JSON files will be saved.
        delay: Delay between requests in seconds (default 1.5s).

    Example:
        scraper = CAFScraper()
        paths = scraper.scrape_and_save()
        # Creates: data/caf/careers_en.json
        #          data/caf/careers_fr.json
    """

    def __init__(
        self,
        output_dir: str | Path = "data/caf",
        delay: float = REQUEST_DELAY_SECONDS,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.delay = delay
        self.client = httpx.Client(
            timeout=DEFAULT_TIMEOUT,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=5),
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1.5, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException)),
    )
    def _fetch(self, url: str) -> str:
        """Fetch URL with retry and exponential backoff.

        Per RESEARCH.md: Use tenacity for resilient HTTP requests.

        Args:
            url: URL to fetch.

        Returns:
            Response text content.

        Raises:
            httpx.HTTPStatusError: If request fails after retries.
        """
        response = self.client.get(url)
        response.raise_for_status()
        return response.text

    def fetch_sitemap(self) -> dict[str, list[str]]:
        """Fetch and parse sitemap.xml to get career URLs.

        Per RESEARCH.md: Extract URLs from sitemap rather than constructing.

        Returns:
            Dictionary with 'en' and 'fr' keys mapping to career URLs.
        """
        logger.info("fetching_sitemap", url=CAF_SITEMAP_URL)

        xml_content = self._fetch(CAF_SITEMAP_URL)
        urls = parse_sitemap_career_urls(xml_content)

        logger.info(
            "sitemap_parsed",
            en_count=len(urls["en"]),
            fr_count=len(urls["fr"]),
        )

        return urls

    def scrape_career_listings(
        self,
        language: str = "en",
        urls: list[str] | None = None,
        fetch_details: bool = False,
    ) -> list[CAFCareerListing]:
        """Scrape career listings for a given language.

        If urls is not provided, fetches from sitemap.
        If fetch_details is True, fetches each career page for more info.

        Args:
            language: Language code ('en' or 'fr').
            urls: Optional list of career URLs to scrape.
            fetch_details: Whether to fetch individual career pages.

        Returns:
            List of CAFCareerListing objects.
        """
        scraped_at = datetime.now(timezone.utc)

        if urls is None:
            sitemap_urls = self.fetch_sitemap()
            urls = sitemap_urls.get(language, [])

        if not urls:
            logger.warning("no_career_urls_found", language=language)
            return []

        logger.info("scraping_career_listings", language=language, url_count=len(urls))

        if fetch_details:
            # Fetch each career page for detailed info
            listings = []
            for i, url in enumerate(urls):
                try:
                    logger.debug("fetching_career_page", url=url, progress=f"{i+1}/{len(urls)}")
                    html = self._fetch(url)
                    listing = parse_career_page(html, url, scraped_at, language)
                    listings.append(listing)

                    # Rate limiting
                    if i < len(urls) - 1:
                        time.sleep(self.delay)

                except Exception as e:
                    logger.error("career_page_fetch_failed", url=url, error=str(e))
                    # Continue with basic listing
                    listings.append(
                        CAFCareerListing(
                            career_id=url.rstrip("/").split("/")[-1],
                            title=url.rstrip("/").split("/")[-1].replace("-", " ").title(),
                            url=url,
                            provenance=CAFCareerListing.model_fields["provenance"].default_factory()
                            if callable(CAFCareerListing.model_fields["provenance"].default_factory)
                            else CAFCareerListing(
                                career_id="temp",
                                title="temp",
                                url=url,
                                provenance=type(
                                    "Provenance",
                                    (),
                                    {
                                        "source_url": url,
                                        "scraped_at": scraped_at,
                                        "content_hash": "failed",
                                        "extraction_method": "failed",
                                    },
                                )(),
                            ).provenance,
                        )
                    )
            return listings
        else:
            # Create listings from URLs without fetching pages
            return parse_careers_listing(urls, language, scraped_at)

    def scrape_page(self, language: str = "en") -> CAFScrapedPage:
        """Scrape career listings for a language and return as CAFScrapedPage.

        This is the main entry point following the TBS scraper pattern.

        Args:
            language: Language code ('en' or 'fr').

        Returns:
            CAFScrapedPage containing all career listings with provenance.
        """
        scraped_at = datetime.now(timezone.utc)

        # Get URLs from sitemap
        sitemap_urls = self.fetch_sitemap()
        urls = sitemap_urls.get(language, [])

        # Create listings
        listings = parse_careers_listing(urls, language, scraped_at)

        logger.info(
            "scraped_caf_listings",
            language=language,
            career_count=len(listings),
        )

        return CAFScrapedPage(
            language=language,
            scraped_at=scraped_at,
            source="sitemap",
            careers=listings,
            career_count=len(listings),
        )

    def scrape_both_languages(self) -> dict[str, CAFScrapedPage]:
        """Scrape both English and French career listings.

        Returns:
            Dictionary with 'en' and 'fr' keys mapping to CAFScrapedPage objects.
        """
        scraped_at = datetime.now(timezone.utc)

        # Fetch sitemap once for both languages
        sitemap_urls = self.fetch_sitemap()

        results = {}
        for language in ["en", "fr"]:
            urls = sitemap_urls.get(language, [])
            listings = parse_careers_listing(urls, language, scraped_at)

            results[language] = CAFScrapedPage(
                language=language,
                scraped_at=scraped_at,
                source="sitemap",
                careers=listings,
                career_count=len(listings),
            )

            logger.info(
                "scraped_caf_listings",
                language=language,
                career_count=len(listings),
            )

        return results

    def save_to_json(self, page: CAFScrapedPage) -> Path:
        """Save scraped page to JSON file with provenance.

        Args:
            page: CAFScrapedPage to save.

        Returns:
            Path to the saved JSON file.
        """
        filename = f"careers_{page.language}.json"
        filepath = self.output_dir / filename

        # Convert to JSON-serializable format
        data = page.model_dump(mode="json")

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(
            "saved_caf_data",
            filepath=str(filepath),
            career_count=page.career_count,
        )

        return filepath

    def scrape_and_save(self) -> dict[str, Path]:
        """Scrape both languages and save to JSON files.

        Convenience method that performs full scrape workflow.

        Returns:
            Dictionary with 'en' and 'fr' keys mapping to saved file paths.
        """
        pages = self.scrape_both_languages()
        return {lang: self.save_to_json(page) for lang, page in pages.items()}


def scrape_caf_careers(
    output_dir: str | Path = "data/caf",
    languages: list[str] | None = None,
) -> dict[str, Path]:
    """Scrape CAF careers and save to JSON files.

    Convenience function for quick scraping without instantiating
    the scraper class directly.

    Args:
        output_dir: Directory where JSON files will be saved.
        languages: List of language codes to scrape. Defaults to ['en', 'fr'].

    Returns:
        Dictionary mapping language codes to saved file paths.

    Example:
        paths = scrape_caf_careers()
        print(paths['en'])  # Path to English JSON file
    """
    languages = languages or ["en", "fr"]

    with CAFScraper(output_dir) as scraper:
        paths = {}
        for lang in languages:
            page = scraper.scrape_page(lang)
            paths[lang] = scraper.save_to_json(page)

    return paths
