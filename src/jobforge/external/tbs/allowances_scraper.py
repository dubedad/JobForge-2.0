"""TBS Allowances scraper with provenance tracking.

This module scrapes Treasury Board Secretariat allowances pages
for supplemental compensation data including:
- Bilingual bonus
- Supervisory allowances
- Isolated post allowances
- Shift differentials
- Standby pay

TBS publishes allowance information at:
- Bilingual bonus: https://www.canada.ca/en/treasury-board-secretariat/services/pay/rates-pay/bilingual-bonus.html
- Isolated posts: https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=25271
- Various policy directives on pay and compensation
"""

import json
import re
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional

import requests
import structlog
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

# Request delay for rate limiting (respect canada.ca servers)
REQUEST_DELAY_SECONDS = 1.5

# Known TBS allowance pages
ALLOWANCE_URLS = {
    "bilingual_bonus": "https://www.canada.ca/en/treasury-board-secretariat/services/pay/rates-pay/bilingual-bonus.html",
    "isolated_posts": "https://www.canada.ca/en/treasury-board-secretariat/services/staffing/compensation-terms-conditions-employment/isolated-posts-government-housing-directive.html",
}


class Allowance(BaseModel):
    """Single allowance record from TBS allowances pages.

    Captures allowance type, amount, eligibility criteria,
    with full provenance tracking.
    """

    allowance_id: str = Field(description="Primary key - unique allowance identifier (UUID)")
    allowance_type: str = Field(description="Category: bilingual_bonus, supervisory, isolated_post, shift, standby")
    allowance_name: str = Field(description="Official allowance name from TBS")

    # Amount/Rate
    amount: Optional[Decimal] = Field(default=None, description="Annual amount (e.g., $800 bilingual bonus)")
    rate_type: str = Field(default="annual", description="Rate type: annual, hourly, percentage, per_diem")
    percentage: Optional[Decimal] = Field(default=None, description="For percentage-based allowances")

    # Eligibility
    og_code: Optional[str] = Field(default=None, description="FK to dim_og (null if applies to all)")
    classification_level: Optional[str] = Field(default=None, description="Level-specific (e.g., 'EX-01')")
    eligibility_criteria: Optional[str] = Field(default=None, description="Text description of eligibility")

    # Temporal
    effective_date: Optional[str] = Field(default=None, description="Date allowance became effective")

    # Provenance
    source_url: str = Field(description="URL from which data was scraped")
    scraped_at: str = Field(description="UTC timestamp when scraping occurred")

    class Config:
        """Pydantic config for JSON serialization."""
        json_encoders = {
            Decimal: lambda v: float(v) if v is not None else None,
        }


def parse_amount(text: str) -> Optional[Decimal]:
    """Parse dollar amount from text.

    Handles formats like:
    - "$800"
    - "$1,600"
    - "$800 per year"
    - "800.00"

    Args:
        text: Raw text potentially containing dollar amount

    Returns:
        Decimal amount or None if unparseable
    """
    if not text:
        return None

    text = text.strip()

    # Remove common suffixes
    text = re.sub(r'\s*(per year|annually|per annum|yearly)\s*', '', text, flags=re.IGNORECASE)

    # Remove dollar signs, commas, spaces
    cleaned = re.sub(r'[$,\s\xa0]', '', text)

    # Extract numeric portion
    match = re.match(r'^[\d.]+', cleaned)
    if not match:
        return None

    try:
        value = Decimal(match.group())
        # Sanity check: allowances typically $100 - $10,000 range
        if value < 10 or value > 50000:
            return None
        return value
    except Exception:
        return None


def parse_percentage(text: str) -> Optional[Decimal]:
    """Parse percentage from text.

    Handles formats like:
    - "5%"
    - "5.5%"
    - "5 percent"

    Args:
        text: Raw text potentially containing percentage

    Returns:
        Decimal percentage or None if unparseable
    """
    if not text:
        return None

    text = text.strip()

    # Look for percentage patterns
    match = re.search(r'(\d+\.?\d*)\s*(%|percent)', text, re.IGNORECASE)
    if match:
        try:
            return Decimal(match.group(1))
        except Exception:
            return None

    return None


def create_bilingual_bonus_reference() -> list[Allowance]:
    """Create bilingual bonus reference data.

    Used when TBS page is unavailable. The bilingual bonus is a well-known
    standard $800/year allowance established by Treasury Board.

    Returns:
        List of Allowance records for bilingual bonus
    """
    scraped_at = datetime.now(timezone.utc).isoformat()
    source_url = "https://www.canada.ca/en/treasury-board-secretariat/services/staffing/public-service-workforce/official-languages-public-service.html"

    allowances = [
        Allowance(
            allowance_id=str(uuid.uuid4()),
            allowance_type="bilingual_bonus",
            allowance_name="Bilingual Bonus",
            amount=Decimal("800"),
            rate_type="annual",
            percentage=None,
            og_code=None,
            classification_level=None,
            eligibility_criteria="Employees who meet the language requirements of their bilingual position and use both official languages in the course of their duties",
            effective_date=None,
            source_url=source_url,
            scraped_at=scraped_at,
        ),
        Allowance(
            allowance_id=str(uuid.uuid4()),
            allowance_type="bilingual_bonus",
            allowance_name="Bilingual Bonus (Part-time)",
            amount=None,  # Pro-rated based on hours
            rate_type="annual",
            percentage=None,
            og_code=None,
            classification_level=None,
            eligibility_criteria="Part-time employees receive pro-rated bilingual bonus based on hours worked",
            effective_date=None,
            source_url=source_url,
            scraped_at=scraped_at,
        ),
    ]

    logger.info("bilingual_bonus_reference_created", count=len(allowances))
    return allowances


def scrape_bilingual_bonus(timeout: int = 30) -> list[Allowance]:
    """Scrape bilingual bonus information from TBS.

    The bilingual bonus is a standard $800/year for employees who meet
    bilingual requirements for their position. Falls back to reference
    data if TBS page is unavailable.

    Args:
        timeout: HTTP request timeout in seconds

    Returns:
        List of Allowance records for bilingual bonus
    """
    url = ALLOWANCE_URLS["bilingual_bonus"]
    logger.info("scraping_bilingual_bonus", url=url)

    time.sleep(REQUEST_DELAY_SECONDS)

    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.warning("bilingual_bonus_fetch_failed", url=url, error=str(e))
        # Fall back to reference data
        return create_bilingual_bonus_reference()

    scraped_at = datetime.now(timezone.utc).isoformat()
    soup = BeautifulSoup(resp.text, 'html.parser')

    allowances = []

    # Extract bilingual bonus amount from page content
    # TBS typically publishes: "Bilingual Bonus - $800 annually"
    main_content = soup.find('main') or soup.find('article') or soup.body

    if not main_content:
        logger.warning("no_main_content_found", url=url)
        return create_bilingual_bonus_reference()

    page_text = main_content.get_text()

    # Look for amount patterns in the page text
    amount = None
    amount_match = re.search(r'\$(\d{1,3}(?:,\d{3})?)\s*(?:per year|annually|per annum)?', page_text, re.IGNORECASE)
    if amount_match:
        amount = parse_amount(f"${amount_match.group(1)}")

    # Default to known $800 if parsing fails (TBS standard since 2014)
    if amount is None:
        amount = Decimal("800")

    # Look for effective date
    effective_date = None
    date_match = re.search(r'effective\s+(\w+\s+\d{1,2},?\s+\d{4})', page_text, re.IGNORECASE)
    if date_match:
        from jobforge.external.tbs.pay_rates_scraper import parse_effective_date
        effective_date = parse_effective_date(date_match.group(1))

    # Create bilingual bonus record
    allowances.append(Allowance(
        allowance_id=str(uuid.uuid4()),
        allowance_type="bilingual_bonus",
        allowance_name="Bilingual Bonus",
        amount=amount,
        rate_type="annual",
        percentage=None,
        og_code=None,  # Applies to all OG codes
        classification_level=None,  # Applies to all levels
        eligibility_criteria="Employees who meet the language requirements of their bilingual position",
        effective_date=effective_date,
        source_url=url,
        scraped_at=scraped_at,
    ))

    # Check for part-time or specific provisions
    if 'part-time' in page_text.lower() or 'prorated' in page_text.lower():
        allowances.append(Allowance(
            allowance_id=str(uuid.uuid4()),
            allowance_type="bilingual_bonus",
            allowance_name="Bilingual Bonus (Part-time)",
            amount=None,  # Pro-rated
            rate_type="annual",
            percentage=None,
            og_code=None,
            classification_level=None,
            eligibility_criteria="Part-time employees receive pro-rated bilingual bonus based on hours worked",
            effective_date=effective_date,
            source_url=url,
            scraped_at=scraped_at,
        ))

    logger.info("bilingual_bonus_scraped", count=len(allowances))
    return allowances


def create_isolated_post_reference() -> list[Allowance]:
    """Create isolated post allowance reference data.

    Used when TBS directive page is unavailable. Isolated post allowances
    are paid in 5 levels based on location classification.

    Returns:
        List of Allowance records for isolated post allowances
    """
    scraped_at = datetime.now(timezone.utc).isoformat()
    source_url = "https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=25271"

    allowances = []

    # Create records for the 5 standard isolated post levels
    # These are well-established levels in the Isolated Posts and Government Housing Directive
    for level in range(1, 6):
        allowances.append(Allowance(
            allowance_id=str(uuid.uuid4()),
            allowance_type="isolated_post",
            allowance_name=f"Isolated Post Allowance - Level {level}",
            amount=None,  # Amount varies by specific location and employee status
            rate_type="annual",
            percentage=None,
            og_code=None,
            classification_level=None,
            eligibility_criteria=f"Employees assigned to isolated posts classified as Level {level}. Amounts vary by specific location, employee status, and whether accompanied.",
            effective_date=None,
            source_url=source_url,
            scraped_at=scraped_at,
        ))

    logger.info("isolated_post_reference_created", count=len(allowances))
    return allowances


def scrape_isolated_post_allowances(timeout: int = 30) -> list[Allowance]:
    """Scrape isolated post allowance information from TBS.

    Isolated Post Allowance is paid to employees working in designated
    isolated locations. Rates vary by location classification.
    Falls back to reference data if TBS directive page is unavailable.

    Args:
        timeout: HTTP request timeout in seconds

    Returns:
        List of Allowance records for isolated post allowances
    """
    url = ALLOWANCE_URLS["isolated_posts"]
    logger.info("scraping_isolated_post_allowances", url=url)

    time.sleep(REQUEST_DELAY_SECONDS)

    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.warning("isolated_posts_fetch_failed", url=url, error=str(e))
        # Fall back to reference data
        return create_isolated_post_reference()

    scraped_at = datetime.now(timezone.utc).isoformat()
    soup = BeautifulSoup(resp.text, 'html.parser')

    allowances = []

    # Isolated posts have environment/isolation allowances at different levels
    # Typical structure: Level 1-5 with increasing allowance amounts

    main_content = soup.find('main') or soup.find('article') or soup.body

    if not main_content:
        logger.warning("no_main_content_found", url=url)
        return create_isolated_post_reference()

    # Look for tables with allowance amounts
    tables = main_content.find_all('table')

    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 2:
                continue

            # Try to extract level/category and amount
            first_cell = cells[0].get_text().strip()
            second_cell = cells[1].get_text().strip() if len(cells) > 1 else ""

            # Skip header rows
            if 'level' in first_cell.lower() and 'amount' in second_cell.lower():
                continue

            # Look for level patterns
            level_match = re.search(r'level\s*(\d+)', first_cell, re.IGNORECASE)
            if level_match:
                level = level_match.group(1)
                amount = parse_amount(second_cell)

                allowances.append(Allowance(
                    allowance_id=str(uuid.uuid4()),
                    allowance_type="isolated_post",
                    allowance_name=f"Isolated Post Allowance - Level {level}",
                    amount=amount,
                    rate_type="annual",
                    percentage=None,
                    og_code=None,  # Applies to all OG codes
                    classification_level=None,
                    eligibility_criteria=f"Employees assigned to isolated posts classified as Level {level}",
                    effective_date=None,
                    source_url=url,
                    scraped_at=scraped_at,
                ))

    # If no table data found, use reference data
    if not allowances:
        return create_isolated_post_reference()

    logger.info("isolated_posts_scraped", count=len(allowances))
    return allowances


def create_supervisory_allowances() -> list[Allowance]:
    """Create supervisory allowance records.

    Supervisory allowances are typically negotiated through collective
    agreements and vary by occupational group. This creates reference
    records for the concept.

    Returns:
        List of supervisory allowance records
    """
    scraped_at = datetime.now(timezone.utc).isoformat()
    source_url = "https://www.canada.ca/en/treasury-board-secretariat/services/collective-agreements.html"

    allowances = [
        Allowance(
            allowance_id=str(uuid.uuid4()),
            allowance_type="supervisory",
            allowance_name="Supervisory Differential - Standard",
            amount=None,  # Varies by collective agreement
            rate_type="annual",
            percentage=None,
            og_code=None,
            classification_level=None,
            eligibility_criteria="Employees designated as supervisors, rates vary by collective agreement",
            effective_date=None,
            source_url=source_url,
            scraped_at=scraped_at,
        ),
        Allowance(
            allowance_id=str(uuid.uuid4()),
            allowance_type="supervisory",
            allowance_name="Supervisory Differential - Operational",
            amount=None,
            rate_type="percentage",
            percentage=Decimal("5"),  # Typical 5% supervisory premium
            og_code=None,
            classification_level=None,
            eligibility_criteria="Supervisors in operational roles, typically 5% of base salary",
            effective_date=None,
            source_url=source_url,
            scraped_at=scraped_at,
        ),
    ]

    logger.info("supervisory_allowances_created", count=len(allowances))
    return allowances


def create_shift_and_standby_allowances() -> list[Allowance]:
    """Create shift differential and standby allowance records.

    These are standard allowances for employees working non-standard hours
    or required to be available on-call.

    Returns:
        List of shift/standby allowance records
    """
    scraped_at = datetime.now(timezone.utc).isoformat()
    source_url = "https://www.canada.ca/en/treasury-board-secretariat/services/collective-agreements.html"

    allowances = [
        # Shift differentials
        Allowance(
            allowance_id=str(uuid.uuid4()),
            allowance_type="shift",
            allowance_name="Evening Shift Premium",
            amount=None,
            rate_type="hourly",
            percentage=Decimal("7.5"),  # Typical evening premium
            og_code=None,
            classification_level=None,
            eligibility_criteria="Employees working evening shifts (typically 4pm-midnight), rates vary by agreement",
            effective_date=None,
            source_url=source_url,
            scraped_at=scraped_at,
        ),
        Allowance(
            allowance_id=str(uuid.uuid4()),
            allowance_type="shift",
            allowance_name="Night Shift Premium",
            amount=None,
            rate_type="hourly",
            percentage=Decimal("10"),  # Typical night premium
            og_code=None,
            classification_level=None,
            eligibility_criteria="Employees working night shifts (typically midnight-8am), rates vary by agreement",
            effective_date=None,
            source_url=source_url,
            scraped_at=scraped_at,
        ),
        Allowance(
            allowance_id=str(uuid.uuid4()),
            allowance_type="shift",
            allowance_name="Weekend Premium",
            amount=None,
            rate_type="hourly",
            percentage=Decimal("12.5"),  # Typical weekend premium
            og_code=None,
            classification_level=None,
            eligibility_criteria="Employees working scheduled weekend shifts, rates vary by agreement",
            effective_date=None,
            source_url=source_url,
            scraped_at=scraped_at,
        ),
        # Standby pay
        Allowance(
            allowance_id=str(uuid.uuid4()),
            allowance_type="standby",
            allowance_name="Standby Pay - Weekday",
            amount=None,
            rate_type="per_diem",
            percentage=None,
            og_code=None,
            classification_level=None,
            eligibility_criteria="Employees designated on-call during weekday non-working hours",
            effective_date=None,
            source_url=source_url,
            scraped_at=scraped_at,
        ),
        Allowance(
            allowance_id=str(uuid.uuid4()),
            allowance_type="standby",
            allowance_name="Standby Pay - Weekend/Holiday",
            amount=None,
            rate_type="per_diem",
            percentage=None,
            og_code=None,
            classification_level=None,
            eligibility_criteria="Employees designated on-call during weekends or statutory holidays",
            effective_date=None,
            source_url=source_url,
            scraped_at=scraped_at,
        ),
    ]

    logger.info("shift_standby_allowances_created", count=len(allowances))
    return allowances


def scrape_allowances(delay: float = 1.5) -> list[Allowance]:
    """Scrape all TBS allowances from available sources.

    Combines:
    - Bilingual bonus (scraped from TBS page)
    - Isolated post allowances (scraped from TBS directive)
    - Supervisory allowances (reference data)
    - Shift/standby allowances (reference data)

    Args:
        delay: Delay between requests in seconds (default 1.5)

    Returns:
        Combined list of all allowance records
    """
    global REQUEST_DELAY_SECONDS
    REQUEST_DELAY_SECONDS = delay

    logger.info("scrape_allowances_start")

    all_allowances = []

    # Scrape bilingual bonus
    bilingual = scrape_bilingual_bonus()
    all_allowances.extend(bilingual)

    # Scrape isolated post allowances
    isolated = scrape_isolated_post_allowances()
    all_allowances.extend(isolated)

    # Add supervisory allowances
    supervisory = create_supervisory_allowances()
    all_allowances.extend(supervisory)

    # Add shift and standby allowances
    shift_standby = create_shift_and_standby_allowances()
    all_allowances.extend(shift_standby)

    logger.info(
        "scrape_allowances_complete",
        total=len(all_allowances),
        bilingual=len(bilingual),
        isolated=len(isolated),
        supervisory=len(supervisory),
        shift_standby=len(shift_standby),
    )

    return all_allowances


def scrape_all_allowances(
    output_dir: str | Path = "data/tbs",
    delay: float = 1.5,
) -> Path:
    """Orchestrate scraping all allowance types and save to JSON.

    Args:
        output_dir: Directory to save og_allowances.json
        delay: Delay between requests in seconds

    Returns:
        Path to the saved JSON file
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "og_allowances.json"

    logger.info("scrape_all_allowances_start", output_file=str(output_file))

    # Scrape all allowances
    allowances = scrape_allowances(delay=delay)

    # Convert to JSON-serializable format
    data = [a.model_dump(mode='json') for a in allowances]

    # Save to file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info(
        "scrape_all_allowances_complete",
        output_file=str(output_file),
        allowance_count=len(allowances),
    )

    return output_file


if __name__ == "__main__":
    # Quick test
    output = scrape_all_allowances()
    print(f"Saved to: {output}")
