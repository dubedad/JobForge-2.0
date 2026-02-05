"""TBS Job Evaluation Standards scraper with provenance tracking.

This module scrapes Treasury Board Secretariat job evaluation standards pages
for occupational groups. These standards define evaluation factors and point
values used to classify positions.

TBS publishes job evaluation standards at:
https://www.canada.ca/en/treasury-board-secretariat/services/collective-agreements/job-evaluation/

Each standard includes:
- Evaluation factors (e.g., Knowledge, Decision Making, Communication)
- Point values per factor and degree/level
- Factor descriptions and level definitions
"""

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
import structlog
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)

# Rate limiting: respect canada.ca servers
REQUEST_DELAY_SECONDS = 1.5


class EvaluationStandard(BaseModel):
    """Single evaluation standard record from TBS job evaluation pages.

    Represents either a classification standard overview or an individual
    evaluation factor with its point values and level descriptions.
    """

    og_code: str = Field(description="FK to dim_og - occupational group code")
    og_subgroup_code: Optional[str] = Field(
        default=None, description="Optional subgroup code if standard is subgroup-specific"
    )
    standard_name: str = Field(
        description="Name of the job evaluation standard (e.g., 'Information Technology Job Evaluation Standard')"
    )
    standard_type: str = Field(
        description="Type: 'classification_standard' (overview) or 'evaluation_factor' (individual factor)"
    )

    # Evaluation factor details (when standard_type == 'evaluation_factor')
    factor_name: Optional[str] = Field(
        default=None,
        description="Evaluation factor name (e.g., 'Knowledge', 'Decision Making', 'Communication')",
    )
    factor_description: Optional[str] = Field(
        default=None, description="Description of what this factor measures"
    )
    factor_points: Optional[int] = Field(
        default=None, description="Maximum point value for this factor"
    )
    factor_percentage: Optional[float] = Field(
        default=None, description="Percentage of total points (e.g., 30.0 for 30%)"
    )
    factor_level: Optional[str] = Field(
        default=None, description="Level/degree within factor (e.g., 'Degree 1', 'Level 2')"
    )
    level_points: Optional[int] = Field(
        default=None, description="Point value for this specific level"
    )
    level_description: Optional[str] = Field(
        default=None, description="Description of what this level entails"
    )

    # Full text for search capability
    full_text: str = Field(description="Complete text content for full-text search")

    # Temporal tracking
    effective_date: Optional[str] = Field(
        default=None, description="Date standard became effective"
    )
    version: Optional[str] = Field(
        default=None, description="Version identifier (e.g., '2018 version')"
    )

    # Provenance
    source_url: str = Field(description="URL from which data was scraped")
    scraped_at: str = Field(description="ISO timestamp when scraping occurred")

    class Config:
        """Pydantic config."""

        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


def extract_og_code_from_url(url: str) -> str:
    """Extract OG code from job evaluation standard URL.

    URLs follow patterns like:
    - .../information-technology-job-evaluation-standard.html -> IT
    - .../economics-social-science-services-job-evaluation-standard.html -> EC
    - .../border-services-group-job-evaluation-standard.html -> FB

    Args:
        url: Full URL to job evaluation standard page.

    Returns:
        OG code or 'UNKNOWN' if cannot determine.
    """
    # Mapping of URL path segments to OG codes
    url_to_og = {
        "information-technology": "IT",
        "economics-social-science": "EC",
        "border-services": "FB",
        "comptrollership": "FI",  # Financial Management
        "education": "ED",
        "foreign-service": "FS",
        "law-management": "LC",
        "law-practitioner": "LP",
        "meteorology": "MT",
        "nursing": "NU",
        "nutrition-dietetics": "ND",
        "police-operations": "PO",
        "psychology": "PS",
        "social-work": "SW",
        "welfare-programs": "WP",
    }

    url_lower = url.lower()
    for pattern, og_code in url_to_og.items():
        if pattern in url_lower:
            return og_code

    # Fallback: check for anchor fragments like #jes-nee
    if "#jes-nee" in url:
        return "GENERIC"  # Generic job evaluation standard for multiple OGs

    return "UNKNOWN"


def extract_version_and_date(soup: BeautifulSoup) -> tuple[Optional[str], Optional[str]]:
    """Extract version and effective date from page content.

    Args:
        soup: BeautifulSoup parsed page.

    Returns:
        Tuple of (version, effective_date) or (None, None).
    """
    version = None
    effective_date = None

    # Look for amendment table
    amendment_table = None
    for table in soup.find_all("table"):
        headers = table.find_all("th")
        header_text = " ".join(h.get_text() for h in headers).lower()
        if "amendment" in header_text or "date" in header_text:
            amendment_table = table
            break

    if amendment_table:
        rows = amendment_table.find_all("tr")
        for row in rows[1:]:  # Skip header
            cells = row.find_all(["td", "th"])
            if len(cells) >= 2:
                # Date is typically in second column
                date_text = cells[1].get_text().strip()
                # Parse date (format varies: "January 2018", "2018-01-01", etc.)
                date_match = re.search(
                    r"(\d{4}-\d{2}-\d{2})|(\w+\s+\d{4})|(\d{4})", date_text
                )
                if date_match:
                    effective_date = date_match.group(0)
                    break

    # Look for version in text
    main_content = soup.find("main") or soup.find("article") or soup
    text = main_content.get_text()
    version_match = re.search(r"version[:\s]+(\d+\.?\d*|\d{4})", text, re.IGNORECASE)
    if version_match:
        version = version_match.group(1)

    return version, effective_date


def parse_factor_weighting_table(
    table,
    og_code: str,
    standard_name: str,
    source_url: str,
    scraped_at: str,
    version: Optional[str],
    effective_date: Optional[str],
) -> list[EvaluationStandard]:
    """Parse factor weighting table (Element, Percentage, Max Points).

    Args:
        table: BeautifulSoup table element.
        og_code: Occupational group code.
        standard_name: Name of the evaluation standard.
        source_url: Source URL.
        scraped_at: Scrape timestamp.
        version: Version string.
        effective_date: Effective date string.

    Returns:
        List of EvaluationStandard records for each factor.
    """
    records = []
    rows = table.find_all("tr")

    # Skip header row
    for row in rows[1:]:
        cells = row.find_all(["td", "th"])
        if len(cells) < 3:
            continue

        factor_name = cells[0].get_text().strip()
        if not factor_name or factor_name.lower() in ["total", "element"]:
            continue

        # Parse percentage (e.g., "30.0%" -> 30.0)
        percentage_text = cells[1].get_text().strip()
        percentage_match = re.search(r"(\d+\.?\d*)", percentage_text)
        factor_percentage = float(percentage_match.group(1)) if percentage_match else None

        # Parse max points (e.g., "300" -> 300)
        points_text = cells[2].get_text().strip()
        points_match = re.search(r"(\d+)", points_text)
        factor_points = int(points_match.group(1)) if points_match else None

        record = EvaluationStandard(
            og_code=og_code,
            standard_name=standard_name,
            standard_type="evaluation_factor",
            factor_name=factor_name,
            factor_points=factor_points,
            factor_percentage=factor_percentage,
            full_text=f"{factor_name}: {percentage_text}, {points_text}",
            effective_date=effective_date,
            version=version,
            source_url=source_url,
            scraped_at=scraped_at,
        )
        records.append(record)

    return records


def parse_factor_degree_table(
    table,
    og_code: str,
    standard_name: str,
    source_url: str,
    scraped_at: str,
    version: Optional[str],
    effective_date: Optional[str],
) -> list[EvaluationStandard]:
    """Parse factor degree/level table with point values per level.

    Args:
        table: BeautifulSoup table element.
        og_code: Occupational group code.
        standard_name: Name of the evaluation standard.
        source_url: Source URL.
        scraped_at: Scrape timestamp.
        version: Version string.
        effective_date: Effective date string.

    Returns:
        List of EvaluationStandard records for each factor/level combination.
    """
    records = []
    rows = table.find_all("tr")

    if not rows:
        return records

    # Get degree/level headers from first row
    header_cells = rows[0].find_all(["th", "td"])
    degree_headers = []
    for cell in header_cells[1:]:  # Skip first column (factor name)
        header_text = cell.get_text().strip()
        # Extract degree number if present
        degree_match = re.search(r"(?:Degree|Level)\s*(\d+)", header_text, re.IGNORECASE)
        if degree_match:
            degree_headers.append(f"Degree {degree_match.group(1)}")
        elif header_text and header_text not in ["", "n/a"]:
            degree_headers.append(header_text)
        else:
            degree_headers.append(f"Level {len(degree_headers) + 1}")

    # Process data rows
    for row in rows[1:]:
        cells = row.find_all(["td", "th"])
        if len(cells) < 2:
            continue

        factor_name = cells[0].get_text().strip()
        if not factor_name or factor_name.lower() in ["total", "element", ""]:
            continue

        # Process each degree/level column
        for i, cell in enumerate(cells[1:]):
            if i >= len(degree_headers):
                break

            cell_text = cell.get_text().strip()
            if not cell_text or cell_text.lower() == "n/a":
                continue

            degree_level = degree_headers[i]

            # Extract points from cell (format: "30 points" or "30 pts" or just "30")
            points_match = re.search(r"(\d+)\s*(?:points?|pts)?", cell_text, re.IGNORECASE)
            level_points = int(points_match.group(1)) if points_match else None

            # Get description (everything after the points)
            level_description = None
            if points_match:
                desc_start = points_match.end()
                remaining = cell_text[desc_start:].strip()
                # Clean up description
                remaining = re.sub(r"^[:\s]*", "", remaining)
                if remaining and len(remaining) > 5:
                    level_description = remaining[:500]  # Truncate if too long

            record = EvaluationStandard(
                og_code=og_code,
                standard_name=standard_name,
                standard_type="evaluation_factor",
                factor_name=factor_name,
                factor_level=degree_level,
                level_points=level_points,
                level_description=level_description,
                full_text=f"{factor_name} - {degree_level}: {cell_text[:200]}",
                effective_date=effective_date,
                version=version,
                source_url=source_url,
                scraped_at=scraped_at,
            )
            records.append(record)

    return records


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_page(url: str, timeout: int = 30) -> Optional[str]:
    """Fetch URL with retry logic.

    Args:
        url: URL to fetch.
        timeout: Request timeout in seconds.

    Returns:
        Page HTML content or None on failure.
    """
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logger.warning("fetch_failed", url=url, error=str(e))
        raise


def scrape_evaluation_standard(
    url: str, timeout: int = 30
) -> list[EvaluationStandard]:
    """Scrape a single job evaluation standard page.

    Extracts:
    1. Classification standard overview record
    2. Factor weighting records (if available)
    3. Factor degree/level records with points (if available)

    Args:
        url: Full URL to the job evaluation standard page.
        timeout: HTTP request timeout in seconds.

    Returns:
        List of EvaluationStandard records.
    """
    logger.info("scraping_evaluation_standard", url=url)

    try:
        html = fetch_page(url, timeout=timeout)
    except Exception as e:
        logger.warning("scrape_failed", url=url, error=str(e))
        return []

    if not html:
        return []

    scraped_at = datetime.now(timezone.utc).isoformat()
    soup = BeautifulSoup(html, "lxml")

    # Extract standard name from title
    title_elem = soup.find("h1")
    standard_name = (
        title_elem.get_text().strip() if title_elem else "Unknown Standard"
    )

    # Extract OG code from URL
    og_code = extract_og_code_from_url(url)

    # Extract version and effective date
    version, effective_date = extract_version_and_date(soup)

    # Get main content
    main = soup.find("main") or soup.find("article") or soup
    full_text = main.get_text(separator=" ", strip=True)[:10000]  # Truncate

    records: list[EvaluationStandard] = []

    # Create overview record
    overview = EvaluationStandard(
        og_code=og_code,
        standard_name=standard_name,
        standard_type="classification_standard",
        full_text=full_text,
        effective_date=effective_date,
        version=version,
        source_url=url,
        scraped_at=scraped_at,
    )
    records.append(overview)

    # Find and parse tables
    tables = main.find_all("table")

    for table in tables:
        # Get header row to determine table type
        header_row = table.find("tr")
        if not header_row:
            continue

        header_cells = header_row.find_all(["th", "td"])
        header_text = " ".join(c.get_text().lower() for c in header_cells)

        # Check for factor weighting table (Element, Percentage, Points)
        if (
            "element" in header_text
            and "percentage" in header_text
            and "point" in header_text
        ):
            factor_records = parse_factor_weighting_table(
                table,
                og_code,
                standard_name,
                url,
                scraped_at,
                version,
                effective_date,
            )
            records.extend(factor_records)
            logger.debug(
                "parsed_weighting_table", url=url, record_count=len(factor_records)
            )

        # Check for degree/level table (Element, Degree 1, Degree 2, ...)
        elif "element" in header_text and (
            "degree" in header_text or any(f"degree {i}" in header_text for i in range(1, 10))
        ):
            level_records = parse_factor_degree_table(
                table,
                og_code,
                standard_name,
                url,
                scraped_at,
                version,
                effective_date,
            )
            records.extend(level_records)
            logger.debug(
                "parsed_degree_table", url=url, record_count=len(level_records)
            )

    logger.info(
        "scrape_evaluation_standard_complete",
        url=url,
        og_code=og_code,
        record_count=len(records),
    )

    return records


def scrape_evaluation_standards(
    delay: float = REQUEST_DELAY_SECONDS,
) -> list[EvaluationStandard]:
    """Scrape all job evaluation standards from known URLs.

    Discovers URLs from occupational_groups_en.json and scrapes each
    unique job evaluation standard page.

    Args:
        delay: Delay between requests in seconds (default 1.5s).

    Returns:
        List of all EvaluationStandard records.
    """
    # Load occupational groups to get job_eval_standard_urls
    og_path = Path("data/tbs/occupational_groups_en.json")
    if not og_path.exists():
        logger.warning("occupational_groups_not_found", path=str(og_path))
        return []

    with open(og_path, "r", encoding="utf-8") as f:
        og_data = json.load(f)

    # Get unique URLs
    unique_urls: set[str] = set()
    for row in og_data.get("rows", []):
        url = row.get("job_eval_standard_url")
        if url:
            # Normalize URL (remove anchor for base page)
            base_url = url.split("#")[0]
            unique_urls.add(base_url)

    logger.info("discovered_evaluation_urls", count=len(unique_urls))

    all_records: list[EvaluationStandard] = []

    for i, url in enumerate(sorted(unique_urls)):
        records = scrape_evaluation_standard(url)
        all_records.extend(records)

        # Rate limiting
        if i < len(unique_urls) - 1:
            time.sleep(delay)

    logger.info(
        "scrape_evaluation_standards_complete",
        urls_scraped=len(unique_urls),
        total_records=len(all_records),
    )

    return all_records


def scrape_all_evaluation_standards(
    output_dir: Path | str = Path("data/tbs"),
    delay: float = REQUEST_DELAY_SECONDS,
) -> Path:
    """Scrape all evaluation standards and save to JSON.

    Args:
        output_dir: Directory to save og_evaluation_standards.json.
        delay: Delay between requests in seconds.

    Returns:
        Path to the saved JSON file.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "og_evaluation_standards.json"

    logger.info("scrape_all_evaluation_standards_start")

    records = scrape_evaluation_standards(delay=delay)

    # Convert to JSON-serializable format
    data = [r.model_dump(mode="json") for r in records]

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info(
        "scrape_all_evaluation_standards_complete",
        output_file=str(output_file),
        total_records=len(data),
    )

    return output_file


if __name__ == "__main__":
    # Quick test
    output = scrape_all_evaluation_standards()
    print(f"Saved to: {output}")
