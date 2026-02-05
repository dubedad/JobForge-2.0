"""HTML parsing logic for CAF careers pages.

This module handles parsing of forces.ca career pages,
extracting career listings and detailed occupation information.

Per CONTEXT.md: Capture all available fields, don't filter during scrape.
"""

import hashlib
import re
from datetime import datetime

from bs4 import BeautifulSoup

from .models import CAFCareerListing, CAFOccupation, CAFProvenance

# Base URLs for forces.ca
CAF_BASE_URL = "https://forces.ca"
CAF_SITEMAP_URL = "https://forces.ca/sitemap.xml"

# URL patterns for career pages
CAREER_URL_PATTERN_EN = re.compile(r"https://(?:www\.)?forces\.ca/en/career/([^/]+)/?")
CAREER_URL_PATTERN_FR = re.compile(r"https://(?:www\.)?forces\.ca/fr/carriere/([^/]+)/?")


def compute_content_hash(html: str) -> str:
    """Compute SHA-256 hash of HTML content for integrity verification.

    Per RESEARCH.md: Use SHA-256 for data integrity and legal defensibility.

    Args:
        html: Raw HTML content.

    Returns:
        SHA-256 hexdigest of the content.
    """
    return hashlib.sha256(html.encode("utf-8")).hexdigest()


def extract_career_id_from_url(url: str) -> str | None:
    """Extract canonical career ID from forces.ca career URL.

    Args:
        url: Full URL to career page.

    Returns:
        Career ID (slug) or None if URL doesn't match expected pattern.

    Examples:
        >>> extract_career_id_from_url("https://forces.ca/en/career/pilot/")
        'pilot'
        >>> extract_career_id_from_url("https://www.forces.ca/fr/carriere/pilote/")
        'pilote'
    """
    for pattern in [CAREER_URL_PATTERN_EN, CAREER_URL_PATTERN_FR]:
        match = pattern.match(url)
        if match:
            return match.group(1)
    return None


def parse_sitemap_career_urls(xml_content: str) -> dict[str, list[str]]:
    """Parse sitemap.xml to extract career page URLs.

    Per RESEARCH.md: Extract URLs from sitemap rather than constructing them.

    Args:
        xml_content: Raw XML content of sitemap.

    Returns:
        Dictionary with 'en' and 'fr' keys mapping to lists of career URLs.
    """
    soup = BeautifulSoup(xml_content, "lxml-xml")
    urls = {"en": [], "fr": []}

    for loc in soup.find_all("loc"):
        url = loc.get_text(strip=True)

        if CAREER_URL_PATTERN_EN.match(url):
            urls["en"].append(url)
        elif CAREER_URL_PATTERN_FR.match(url):
            urls["fr"].append(url)

    return urls


def parse_careers_listing(
    urls: list[str],
    language: str,
    scraped_at: datetime,
    content_hashes: dict[str, str] | None = None,
) -> list[CAFCareerListing]:
    """Create career listings from a list of URLs.

    This is a simple conversion from URLs to CAFCareerListing objects,
    typically used after extracting URLs from sitemap.

    Args:
        urls: List of career page URLs.
        language: Language code ('en' or 'fr').
        scraped_at: UTC timestamp when data was gathered.
        content_hashes: Optional mapping of URL to content hash.

    Returns:
        List of CAFCareerListing objects with basic information.
    """
    listings = []
    content_hashes = content_hashes or {}

    for url in urls:
        career_id = extract_career_id_from_url(url)
        if not career_id:
            continue

        # Create title from career_id (human-readable)
        title = career_id.replace("-", " ").title()

        listings.append(
            CAFCareerListing(
                career_id=career_id,
                title=title,
                url=url,
                provenance=CAFProvenance(
                    source_url=url,
                    scraped_at=scraped_at,
                    content_hash=content_hashes.get(url, "pending"),
                    extraction_method="sitemap",
                ),
            )
        )

    return listings


def parse_career_page(
    html: str,
    url: str,
    scraped_at: datetime,
    language: str = "en",
) -> CAFCareerListing:
    """Parse a CAF career listing page for basic information.

    Extracts career listing data from the career page HTML.
    This is used for initial scraping; detailed content parsing
    is done by parse_career_detail().

    Args:
        html: Raw HTML content of career page.
        url: URL that was scraped.
        scraped_at: UTC timestamp when scraping occurred.
        language: Language code ('en' or 'fr').

    Returns:
        CAFCareerListing with basic career information and provenance.
    """
    content_hash = compute_content_hash(html)
    soup = BeautifulSoup(html, "lxml")

    career_id = extract_career_id_from_url(url)
    if not career_id:
        career_id = url.rstrip("/").split("/")[-1]

    # Extract title from h1
    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else career_id.replace("-", " ").title()

    # Extract environment from icons
    environment = _extract_environment(soup)

    # Extract commission status (Officer vs NCM)
    commission_status = _extract_commission_status(soup)

    # Extract employment type
    employment_type = _extract_employment_type(soup)

    return CAFCareerListing(
        career_id=career_id,
        title=title,
        url=url,
        environment=environment,
        commission_status=commission_status,
        employment_type=employment_type,
        provenance=CAFProvenance(
            source_url=url,
            scraped_at=scraped_at,
            content_hash=content_hash,
            extraction_method="html_parser",
        ),
    )


def parse_career_detail(
    html: str,
    url: str,
    scraped_at: datetime,
    language: str = "en",
) -> CAFOccupation:
    """Parse full career detail from a CAF career page.

    Extracts complete career information including overview,
    training, entry plans, and related careers.

    Per CONTEXT.md: Capture all available fields.

    Args:
        html: Raw HTML content of career page.
        url: URL that was scraped.
        scraped_at: UTC timestamp when scraping occurred.
        language: Language code ('en' or 'fr').

    Returns:
        CAFOccupation with detailed career information and provenance.
    """
    content_hash = compute_content_hash(html)
    soup = BeautifulSoup(html, "lxml")

    career_id = extract_career_id_from_url(url)
    if not career_id:
        career_id = url.rstrip("/").split("/")[-1]

    # Extract title
    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else career_id.replace("-", " ").title()

    # Extract meta description and keywords
    meta_desc = None
    meta_desc_tag = soup.find("meta", {"name": "description"})
    if meta_desc_tag and meta_desc_tag.get("content"):
        meta_desc = meta_desc_tag["content"]

    keywords = []
    keywords_tag = soup.find("meta", {"name": "keywords"})
    if keywords_tag and keywords_tag.get("content"):
        keywords = [k.strip() for k in keywords_tag["content"].split(",")]

    # Extract content sections
    overview = _extract_section_content(soup, "overview")
    work_env = _extract_section_content(soup, "work environment")
    training = _extract_section_content(soup, "training")
    entry_plans = _extract_section_content(soup, "entry")
    part_time = _extract_section_content(soup, "part time")

    # Extract environment, commission status, employment type
    environment = _extract_environment(soup)
    commission_status = _extract_commission_status(soup)
    employment_type = _extract_employment_type(soup)

    # Extract related civilian occupations
    related_civilian = _extract_related_civilian(soup)

    # Extract related careers
    related_careers = _extract_related_careers(soup, language)

    # Extract French URL if available
    url_fr = _extract_alternate_language_url(soup, language)

    # Build occupation model based on language
    if language == "en":
        return CAFOccupation(
            career_id=career_id,
            title_en=title,
            title_fr=None,
            environment=environment,
            commission_status=commission_status,
            employment_type=employment_type,
            overview_en=overview,
            work_environment_en=work_env,
            training_en=training,
            entry_plans_en=entry_plans,
            part_time_options_en=part_time,
            related_civilian_occupations=related_civilian,
            related_careers=related_careers,
            keywords=keywords,
            description_meta=meta_desc,
            url_en=url,
            url_fr=url_fr,
            provenance_en=CAFProvenance(
                source_url=url,
                scraped_at=scraped_at,
                content_hash=content_hash,
                extraction_method="html_parser",
            ),
        )
    else:
        return CAFOccupation(
            career_id=career_id,
            title_en="",  # Will be populated from EN page
            title_fr=title,
            environment=environment,
            commission_status=commission_status,
            employment_type=employment_type,
            overview_fr=overview,
            work_environment_fr=work_env,
            training_fr=training,
            entry_plans_fr=entry_plans,
            part_time_options_fr=part_time,
            related_civilian_occupations=related_civilian,
            related_careers=related_careers,
            keywords=keywords,
            description_meta=meta_desc,
            url_en="",  # Will be populated from EN page
            url_fr=url,
            provenance_en=CAFProvenance(
                source_url=url,
                scraped_at=scraped_at,
                content_hash=content_hash,
                extraction_method="html_parser",
            ),
            provenance_fr=CAFProvenance(
                source_url=url,
                scraped_at=scraped_at,
                content_hash=content_hash,
                extraction_method="html_parser",
            ),
        )


def _extract_environment(soup: BeautifulSoup) -> list[str]:
    """Extract military environment(s) from career page."""
    environments = []

    # Look for environment icons
    env_icons = soup.find_all("img", alt=True)
    for img in env_icons:
        alt_text = img.get("alt", "").lower()
        if "army" in alt_text:
            environments.append("army")
        elif "navy" in alt_text:
            environments.append("navy")
        elif "air" in alt_text:
            environments.append("air_force")

    # Also check for text indicators
    page_text = soup.get_text().lower()
    if not environments:
        if "army" in page_text and "army" not in environments:
            environments.append("army")
        if "navy" in page_text and "navy" not in environments:
            environments.append("navy")
        if "air force" in page_text and "air_force" not in environments:
            environments.append("air_force")

    return list(set(environments))


def _extract_commission_status(soup: BeautifulSoup) -> str:
    """Extract officer/NCM commission status from career page."""
    details = soup.find("p", class_="details")
    if details:
        text = details.get_text().lower()
        if "officer" in text and "non-commissioned" not in text:
            return "officer"
        elif "non-commissioned" in text or "ncm" in text:
            return "ncm"

    # Fallback: search page text
    page_text = soup.get_text().lower()
    if "non-commissioned member" in page_text:
        return "ncm"
    elif "officer" in page_text:
        return "officer"

    return "unknown"


def _extract_employment_type(soup: BeautifulSoup) -> list[str]:
    """Extract employment types from career page."""
    employment = []

    details = soup.find("p", class_="details")
    if details:
        text = details.get_text().lower()
        if "full time" in text or "full-time" in text:
            employment.append("full_time")
        if "part time" in text or "part-time" in text:
            employment.append("part_time")
        if "reserve" in text:
            employment.append("reserve")

    return employment


def _extract_section_content(soup: BeautifulSoup, section_name: str) -> str | None:
    """Extract content from a named section of the career page."""
    # Try to find section by ID
    section_ids = [
        f"sec-{section_name.replace(' ', '-').lower()}",
        f"sec-{section_name.replace(' ', '').lower()}",
        section_name.replace(" ", "-").lower(),
    ]

    for section_id in section_ids:
        section = soup.find("section", id=section_id)
        if section:
            # Get article content within section
            article = section.find("article")
            if article:
                # Remove script and style tags
                for tag in article.find_all(["script", "style"]):
                    tag.decompose()
                return article.get_text(separator="\n", strip=True)

            # Fall back to section text
            return section.get_text(separator="\n", strip=True)

    # Try to find by heading text
    for heading in soup.find_all(["h2", "h3", "h4"]):
        if section_name.lower() in heading.get_text().lower():
            # Get next siblings until next heading
            content_parts = []
            for sibling in heading.find_next_siblings():
                if sibling.name in ["h2", "h3", "h4"]:
                    break
                content_parts.append(sibling.get_text(separator="\n", strip=True))
            if content_parts:
                return "\n".join(content_parts)

    return None


def _extract_related_civilian(soup: BeautifulSoup) -> list[str]:
    """Extract related civilian occupations from career page."""
    occupations = []

    # Look for the Related Civilian Occupations section
    for heading in soup.find_all(["h2", "h3", "h4"]):
        if "related civilian" in heading.get_text().lower():
            # Look for list items
            next_list = heading.find_next("ul")
            if next_list:
                for li in next_list.find_all("li"):
                    text = li.get_text(strip=True)
                    if text:
                        occupations.append(text)

            # Also check for comma-separated text
            if not occupations:
                next_p = heading.find_next("p")
                if next_p:
                    text = next_p.get_text(strip=True)
                    if text and "no direct related" not in text.lower():
                        occupations = [o.strip() for o in text.split(",")]

    return occupations


def _extract_related_careers(soup: BeautifulSoup, language: str) -> list[str]:
    """Extract related career IDs from career page."""
    careers = []

    # Find related careers section
    related_section = soup.find("section", id="sec-related")
    if related_section:
        for link in related_section.find_all("a", href=True):
            href = link["href"]
            career_id = extract_career_id_from_url(CAF_BASE_URL + href if href.startswith("/") else href)
            if career_id:
                careers.append(career_id)

    return careers


def _extract_alternate_language_url(soup: BeautifulSoup, current_language: str) -> str | None:
    """Extract URL for alternate language version of the page."""
    # Look for language switcher link
    lang_switcher = soup.find("a", class_="locale-switcher")
    if lang_switcher and lang_switcher.get("href"):
        href = lang_switcher["href"]
        if href.startswith("/"):
            return CAF_BASE_URL + href
        return href

    return None
