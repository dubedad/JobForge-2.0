"""Link fetcher for CAF career detail pages.

This module handles fetching full career details from individual career pages,
following the TBS link_fetcher pattern. Per CONTEXT.md: Store EN/FR in separate
columns, not separate rows.

The fetcher:
1. Reads career URLs from Plan 01 listing scrape (careers_en.json, careers_fr.json)
2. Fetches each EN career page for full content
3. Extracts FR URL from the page and fetches FR content
4. Merges bilingual content into single CAFOccupation records
5. Infers job families from career groupings
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple
from urllib.parse import unquote

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .models import CAFJobFamily, CAFOccupation, CAFProvenance
from .parser import (
    CAF_BASE_URL,
    compute_content_hash,
    extract_career_id_from_url,
    parse_career_detail,
)

logger = structlog.get_logger(__name__)

# Rate limiting: 1.5s between requests (polite scraping)
REQUEST_DELAY_SECONDS = 1.5

# Default timeout for HTTP requests
DEFAULT_TIMEOUT = 30


class FetchResult(NamedTuple):
    """Result of fetching a single career page."""

    success: bool
    html: str | None
    content_hash: str | None
    error_message: str | None


class CAFLinkFetcher:
    """Fetches career details from individual CAF career pages.

    Per CONTEXT.md: Bilingual content stored in same record (EN/FR columns).

    This fetcher follows the TBS link_fetcher pattern:
    - Reads career URLs from listing scrape
    - Fetches each career page with rate limiting and retry
    - Merges EN/FR content into single occupation records
    - Tracks provenance for all scraped data

    Args:
        data_dir: Directory containing careers_*.json and where output will be saved.
        delay: Delay between requests in seconds (default 1.5s).

    Example:
        fetcher = CAFLinkFetcher()
        occupations = fetcher.fetch_all_career_details()
        fetcher.save_occupations(occupations)
    """

    def __init__(
        self,
        data_dir: str | Path = "data/caf",
        delay: float = REQUEST_DELAY_SECONDS,
    ):
        self.data_dir = Path(data_dir)
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

    def fetch_career_page(self, url: str) -> FetchResult:
        """Fetch a single career page with error handling.

        Args:
            url: Career page URL.

        Returns:
            FetchResult with success status, HTML content, and hash.
        """
        try:
            html = self._fetch(url)
            content_hash = compute_content_hash(html)
            return FetchResult(
                success=True,
                html=html,
                content_hash=content_hash,
                error_message=None,
            )
        except httpx.HTTPStatusError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            logger.warning("http_error_fetching_career", url=url, status=status)
            return FetchResult(
                success=False,
                html=None,
                content_hash=None,
                error_message=f"HTTP {status}",
            )
        except httpx.TimeoutException:
            logger.warning("timeout_fetching_career", url=url)
            return FetchResult(
                success=False,
                html=None,
                content_hash=None,
                error_message="Request timeout",
            )
        except Exception as e:
            logger.warning("error_fetching_career", url=url, error=str(e))
            return FetchResult(
                success=False,
                html=None,
                content_hash=None,
                error_message=str(e),
            )

    def load_career_listings(self, language: str = "en") -> list[dict]:
        """Load career listings from JSON file.

        Args:
            language: Language code ('en' or 'fr').

        Returns:
            List of career listing dictionaries.
        """
        filepath = self.data_dir / f"careers_{language}.json"
        if not filepath.exists():
            logger.warning("career_listings_not_found", filepath=str(filepath))
            return []

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data.get("careers", [])

    def _extract_fr_url_from_html(self, html: str) -> str | None:
        """Extract French URL from English career page HTML.

        Args:
            html: HTML content of English career page.

        Returns:
            French career page URL or None if not found.
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")

        # Look for language switcher link
        lang_switcher = soup.find("a", class_="locale-switcher")
        if lang_switcher and lang_switcher.get("href"):
            href = lang_switcher["href"]
            if href.startswith("/"):
                return CAF_BASE_URL + href
            return href

        # Fallback: look for hreflang alternate link
        alt_link = soup.find("link", {"rel": "alternate", "hreflang": "fr"})
        if alt_link and alt_link.get("href"):
            return alt_link["href"]

        return None

    def fetch_career_detail_bilingual(
        self,
        en_url: str,
        scraped_at: datetime,
    ) -> CAFOccupation | None:
        """Fetch career details from both EN and FR pages.

        Fetches the EN page, extracts FR URL, fetches FR page,
        and merges content into a single CAFOccupation record.

        Args:
            en_url: English career page URL.
            scraped_at: Timestamp for provenance.

        Returns:
            CAFOccupation with bilingual content or None if fetch failed.
        """
        # Fetch EN page
        en_result = self.fetch_career_page(en_url)
        if not en_result.success or not en_result.html:
            return None

        # Parse EN content
        en_occupation = parse_career_detail(
            en_result.html, en_url, scraped_at, language="en"
        )

        # Extract FR URL from EN page
        fr_url = self._extract_fr_url_from_html(en_result.html)

        # Rate limit delay before FR fetch
        time.sleep(self.delay)

        # Try to fetch FR page
        fr_occupation = None
        if fr_url:
            fr_result = self.fetch_career_page(fr_url)
            if fr_result.success and fr_result.html:
                fr_occupation = parse_career_detail(
                    fr_result.html, fr_url, scraped_at, language="fr"
                )

        # Merge EN and FR content into single record
        return self._merge_bilingual_occupation(
            en_occupation, fr_occupation, en_result.content_hash, fr_url
        )

    def _merge_bilingual_occupation(
        self,
        en_occ: CAFOccupation,
        fr_occ: CAFOccupation | None,
        en_content_hash: str | None,
        fr_url: str | None,
    ) -> CAFOccupation:
        """Merge English and French occupations into single record.

        Per CONTEXT.md: Store EN/FR in separate columns, not separate rows.

        Args:
            en_occ: English occupation data.
            fr_occ: French occupation data (may be None).
            en_content_hash: Content hash of EN page.
            fr_url: French page URL.

        Returns:
            Merged CAFOccupation with bilingual content.
        """
        # Update EN provenance with actual content hash
        en_provenance = CAFProvenance(
            source_url=en_occ.provenance_en.source_url,
            scraped_at=en_occ.provenance_en.scraped_at,
            content_hash=en_content_hash or en_occ.provenance_en.content_hash,
            scraper_version=en_occ.provenance_en.scraper_version,
            extraction_method="html_parser",
        )

        # Build merged occupation
        merged = CAFOccupation(
            career_id=en_occ.career_id,
            title_en=en_occ.title_en,
            title_fr=fr_occ.title_fr if fr_occ else None,
            environment=en_occ.environment,
            commission_status=en_occ.commission_status,
            employment_type=en_occ.employment_type,
            # EN content
            overview_en=en_occ.overview_en,
            work_environment_en=en_occ.work_environment_en,
            training_en=en_occ.training_en,
            entry_plans_en=en_occ.entry_plans_en,
            part_time_options_en=en_occ.part_time_options_en,
            # FR content (from FR page if available)
            overview_fr=fr_occ.overview_fr if fr_occ else None,
            work_environment_fr=fr_occ.work_environment_fr if fr_occ else None,
            training_fr=fr_occ.training_fr if fr_occ else None,
            entry_plans_fr=fr_occ.entry_plans_fr if fr_occ else None,
            part_time_options_fr=fr_occ.part_time_options_fr if fr_occ else None,
            # Related data (prefer EN source)
            related_civilian_occupations=en_occ.related_civilian_occupations,
            related_careers=en_occ.related_careers,
            keywords=en_occ.keywords,
            description_meta=en_occ.description_meta,
            # URLs
            url_en=en_occ.url_en,
            url_fr=fr_url or (fr_occ.url_fr if fr_occ else None),
            # Provenance
            provenance_en=en_provenance,
            provenance_fr=fr_occ.provenance_fr if fr_occ else None,
        )

        return merged

    def fetch_all_career_details(
        self,
        max_careers: int | None = None,
    ) -> list[CAFOccupation]:
        """Fetch details for all careers from listing.

        Reads EN career listings, fetches each career page,
        and merges bilingual content.

        Args:
            max_careers: Maximum number of careers to fetch (for testing).

        Returns:
            List of CAFOccupation with bilingual content.
        """
        scraped_at = datetime.now(timezone.utc)

        # Load EN career listings
        en_listings = self.load_career_listings("en")
        if not en_listings:
            logger.error("no_career_listings_found")
            return []

        if max_careers:
            en_listings = en_listings[:max_careers]

        logger.info(
            "fetching_career_details",
            career_count=len(en_listings),
            estimated_time_minutes=len(en_listings) * self.delay * 2 / 60,  # EN + FR
        )

        occupations = []
        successful = 0
        failed = 0

        for i, listing in enumerate(en_listings):
            url = listing.get("url")
            career_id = listing.get("career_id", "unknown")

            logger.debug(
                "fetching_career",
                career_id=career_id,
                progress=f"{i+1}/{len(en_listings)}",
            )

            occupation = self.fetch_career_detail_bilingual(url, scraped_at)

            if occupation:
                occupations.append(occupation)
                successful += 1
            else:
                failed += 1

            # Rate limit delay (except for last career)
            if i < len(en_listings) - 1:
                time.sleep(self.delay)

        logger.info(
            "completed_fetching_career_details",
            successful=successful,
            failed=failed,
            total=len(en_listings),
        )

        return occupations

    def infer_job_families(
        self,
        occupations: list[CAFOccupation],
    ) -> list[CAFJobFamily]:
        """Infer job families from occupation data.

        Per RESEARCH.md: Analyze career groupings to infer ~12 job families.
        Uses environment (army/navy/air_force), commission status, and
        career title patterns to group occupations.

        Args:
            occupations: List of CAFOccupation objects.

        Returns:
            List of inferred CAFJobFamily objects.
        """
        # Group by primary characteristics
        families: dict[str, list[str]] = {}

        for occ in occupations:
            # Determine family based on title patterns and environment
            family_id = self._infer_family_for_occupation(occ)
            if family_id not in families:
                families[family_id] = []
            families[family_id].append(occ.career_id)

        # Convert to CAFJobFamily objects
        job_families = []
        for family_id, career_ids in families.items():
            family_name = family_id.replace("-", " ").title()
            job_families.append(
                CAFJobFamily(
                    family_id=family_id,
                    family_name=family_name,
                    description=f"CAF careers in the {family_name} category.",
                    career_count=len(career_ids),
                    source_url=None,  # Inferred, not from single URL
                )
            )

        logger.info(
            "inferred_job_families",
            family_count=len(job_families),
            families=[f.family_id for f in job_families],
        )

        return sorted(job_families, key=lambda f: f.family_id)

    def _infer_family_for_occupation(self, occ: CAFOccupation) -> str:
        """Infer job family for a single occupation.

        Uses title patterns and environment to categorize.

        Args:
            occ: CAFOccupation to categorize.

        Returns:
            Family ID string.
        """
        title_lower = occ.title_en.lower()
        career_id = occ.career_id.lower()

        # Medical/Health careers
        medical_keywords = [
            "medical", "nurse", "physician", "dental", "pharmacy",
            "health", "technologist", "physiotherapy", "bioscience",
        ]
        if any(kw in title_lower or kw in career_id for kw in medical_keywords):
            return "medical-health"

        # Engineering/Technical careers
        engineering_keywords = [
            "engineer", "technician", "systems", "electronics",
            "construction", "electrical", "mechanical", "avionics",
            "aerospace", "weapons", "marine-tech", "aviation",
        ]
        if any(kw in title_lower or kw in career_id for kw in engineering_keywords):
            return "engineering-technical"

        # Combat/Operations careers
        combat_keywords = [
            "infantry", "armour", "artillery", "combat", "gunner",
            "soldier", "warfare", "pilot", "diver",
        ]
        if any(kw in title_lower or kw in career_id for kw in combat_keywords):
            return "combat-operations"

        # Intelligence/Signals careers
        intel_keywords = [
            "intelligence", "signals", "communicator", "cyber",
            "sensor", "operator", "sonar",
        ]
        if any(kw in title_lower or kw in career_id for kw in intel_keywords):
            return "intelligence-signals"

        # Support/Logistics careers
        support_keywords = [
            "logistics", "supply", "traffic", "cook", "steward",
            "postal", "firefighter", "mobile-support",
        ]
        if any(kw in title_lower or kw in career_id for kw in support_keywords):
            return "support-logistics"

        # Administration/HR careers
        admin_keywords = [
            "admin", "human-resources", "financial", "legal",
            "public-affairs", "chaplain", "personnel",
        ]
        if any(kw in title_lower or kw in career_id for kw in admin_keywords):
            return "administration-hr"

        # Aerospace Control careers
        aerospace_keywords = ["aerospace-control", "air-combat-systems"]
        if any(kw in career_id for kw in aerospace_keywords):
            return "aerospace-control"

        # Training/Development careers
        training_keywords = ["training", "instruction", "development-officer"]
        if any(kw in title_lower or kw in career_id for kw in training_keywords):
            return "training-development"

        # Police/Security careers
        police_keywords = ["police", "military-police"]
        if any(kw in title_lower or kw in career_id for kw in police_keywords):
            return "police-security"

        # Imagery/Geomatics careers
        imagery_keywords = ["imagery", "geomatics", "drafting", "survey"]
        if any(kw in title_lower or kw in career_id for kw in imagery_keywords):
            return "imagery-geomatics"

        # Music careers
        if "musician" in title_lower or "musician" in career_id:
            return "music"

        # Default: based on officer/NCM status
        if occ.commission_status == "officer":
            return "officer-general"
        else:
            return "ncm-general"

    def save_occupations(
        self,
        occupations: list[CAFOccupation],
        filename: str = "occupations.json",
    ) -> Path:
        """Save occupations to JSON file with provenance.

        Args:
            occupations: List of CAFOccupation objects.
            filename: Output filename.

        Returns:
            Path to saved file.
        """
        filepath = self.data_dir / filename

        data = {
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "occupation_count": len(occupations),
            "occupations": [occ.model_dump(mode="json") for occ in occupations],
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(
            "saved_occupations",
            filepath=str(filepath),
            occupation_count=len(occupations),
        )

        return filepath

    def save_job_families(
        self,
        families: list[CAFJobFamily],
        filename: str = "job_families.json",
    ) -> Path:
        """Save job families to JSON file.

        Args:
            families: List of CAFJobFamily objects.
            filename: Output filename.

        Returns:
            Path to saved file.
        """
        filepath = self.data_dir / filename

        data = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "family_count": len(families),
            "families": [fam.model_dump(mode="json") for fam in families],
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(
            "saved_job_families",
            filepath=str(filepath),
            family_count=len(families),
        )

        return filepath


def fetch_career_detail(
    url: str,
    scraped_at: datetime | None = None,
) -> CAFOccupation | None:
    """Fetch a single career detail from URL.

    Convenience function for fetching one career page without
    instantiating the full fetcher class.

    Args:
        url: Career page URL.
        scraped_at: Optional timestamp for provenance.

    Returns:
        CAFOccupation or None if fetch failed.
    """
    scraped_at = scraped_at or datetime.now(timezone.utc)

    with CAFLinkFetcher() as fetcher:
        return fetcher.fetch_career_detail_bilingual(url, scraped_at)


def fetch_all_career_details(
    data_dir: str | Path = "data/caf",
    max_careers: int | None = None,
) -> tuple[list[CAFOccupation], list[CAFJobFamily]]:
    """Fetch all career details and infer job families.

    Convenience function for full scrape workflow.

    Args:
        data_dir: Directory containing careers_*.json files.
        max_careers: Optional limit for testing.

    Returns:
        Tuple of (occupations list, job families list).
    """
    with CAFLinkFetcher(data_dir) as fetcher:
        occupations = fetcher.fetch_all_career_details(max_careers)
        families = fetcher.infer_job_families(occupations)

        fetcher.save_occupations(occupations)
        fetcher.save_job_families(families)

    return occupations, families
