"""TBS Rates of Pay scraper with provenance tracking.

This module scrapes Treasury Board Secretariat rates of pay pages
for excluded/unrepresented employees across occupational groups.

TBS publishes pay rates at:
https://www.canada.ca/en/treasury-board-secretariat/services/pay/rates-pay/
rates-pay-unrepresented-senior-excluded-employees.html

Each OG has a dedicated page with tables showing pay rates by level and step
across effective dates.

Two common table formats:
1. Steps-as-columns: Effective date rows x Step columns (AO, CX, etc.)
2. Dates-as-columns: Level rows x Effective date columns (AS, ED, etc.)
"""

import json
import re
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional

import requests
import structlog
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

# Base URL for excluded/unrepresented pay rates
BASE_URL = "https://www.canada.ca/en/treasury-board-secretariat/services/pay/rates-pay/rates-pay-unrepresented-senior-excluded-employees"
INDEX_URL = f"{BASE_URL}.html"

# Known OG codes with dedicated pay rate pages
# Discovered from the index page
KNOWN_OG_PAY_PAGES = [
    "AO", "AS", "CO-RCMP", "CT", "CX", "DS", "ED", "EX", "FR", "HR",
    "IS", "LC", "MD", "MT", "NU", "OM", "PE", "PG", "PI", "PM",
    "SG", "SO", "SRW", "TR", "UT", "WP"
]


class PayRateRow(BaseModel):
    """Single pay rate row from TBS rates of pay tables.

    Captures pay rate for a specific classification level and step,
    with full provenance tracking.
    """

    og_code: str = Field(description="Parent occupational group code (e.g., 'AS', 'PM')")
    og_subgroup_code: str = Field(description="Full classification code (e.g., 'AS-01', 'PM-01')")
    classification_level: str = Field(description="Classification level (e.g., 'AS-07', 'PM-01')")
    step: int = Field(description="Pay step within level (typically 1-10)", ge=1)
    annual_rate: Optional[Decimal] = Field(default=None, description="Annual salary rate in CAD")
    hourly_rate: Optional[Decimal] = Field(default=None, description="Hourly rate in CAD if available")
    effective_date: Optional[str] = Field(default=None, description="Date pay rate became effective")
    represented: bool = Field(default=False, description="True if unionized/represented, False if excluded")
    collective_agreement: Optional[str] = Field(default=None, description="Collective agreement name if represented")
    source_url: str = Field(description="URL from which data was scraped")
    scraped_at: datetime = Field(description="UTC timestamp when scraping occurred")

    class Config:
        """Pydantic config for JSON serialization."""
        json_encoders = {
            Decimal: lambda v: float(v) if v is not None else None,
            datetime: lambda v: v.isoformat() if v is not None else None,
        }


def parse_rate_value(text: str) -> Optional[Decimal]:
    """Parse a dollar amount from table cell text.

    Handles formats like:
    - "$100,220"
    - "100,220"
    - "100220"
    - "$100,220 to $114,592" (returns minimum)
    - "-not applicable"

    Args:
        text: Raw text from table cell

    Returns:
        Decimal value or None if unparseable
    """
    if not text:
        return None

    text = text.strip()

    # Skip non-applicable values
    if not text or text in ('', '-', 'N/A') or 'not applicable' in text.lower():
        return None

    # If there's a range (e.g., "100,220 to 114,592"), take the first value
    if ' to ' in text.lower():
        text = text.lower().split(' to ')[0]

    # Remove dollar signs, commas, spaces, non-breaking spaces
    cleaned = re.sub(r'[$,\s\xa0]', '', text)

    # Must be numeric
    if not cleaned or not re.match(r'^[\d.]+$', cleaned):
        return None

    # Try to parse as decimal
    try:
        value = Decimal(cleaned)
        # Sanity check: TBS salaries are typically 30k-300k range
        if value < 10000 or value > 500000:
            return None
        return value
    except Exception:
        return None


def parse_effective_date(text: str) -> Optional[str]:
    """Extract effective date from table cell or header text.

    Handles formats like:
    - "$) June 21, 2020"
    - "A) June 21, 2021"
    - "$) January 26, 2022"

    Args:
        text: Raw text

    Returns:
        Date string in YYYY-MM-DD format or None
    """
    if not text:
        return None

    # Extract date portion - looking for Month Day, Year pattern
    date_match = re.search(r'(\w+)\s+(\d{1,2}),?\s*(\d{4})', text)
    if date_match:
        month_name = date_match.group(1)
        day = date_match.group(2)
        year = date_match.group(3)

        # Convert month name to number
        months = {
            'january': '01', 'february': '02', 'march': '03', 'april': '04',
            'may': '05', 'june': '06', 'july': '07', 'august': '08',
            'september': '09', 'october': '10', 'november': '11', 'december': '12'
        }
        month_num = months.get(month_name.lower())
        if month_num:
            return f"{year}-{month_num}-{day.zfill(2)}"

    return None


def parse_step_number(text: str) -> Optional[int]:
    """Extract step number from header text.

    Handles formats like:
    - "Step 1" or "Step\xa01"
    - "Step 10"

    Args:
        text: Header text

    Returns:
        Step number (1-10 typically) or None
    """
    if not text:
        return None

    # Look for "Step N" pattern
    match = re.search(r'step\s*(\d+)', text.lower().replace('\xa0', ' '))
    if match:
        return int(match.group(1))
    return None


def extract_classification_info(text: str, og_code: str) -> tuple[Optional[str], Optional[str]]:
    """Extract classification level and subgroup code from text.

    Args:
        text: Text that might contain classification info
        og_code: Parent OG code for context

    Returns:
        Tuple of (classification_level, og_subgroup_code) or (None, None)
    """
    if not text:
        return None, None

    text = text.strip().upper()

    # Skip non-classification text
    skip_patterns = ['EFFECTIVE', 'RATES', 'PAY', 'STEP', 'NOTE', 'LEGEND']
    if any(pat in text for pat in skip_patterns):
        return None, None

    # Look for OG-NN pattern (e.g., AS-07, PM-01)
    match = re.match(r'^([A-Z]{2,4})-(\d{1,2})\b', text)
    if match:
        prefix = match.group(1)
        level = match.group(2)
        classification = f"{prefix}-{level.zfill(2)}"
        return classification, prefix

    # If it's just a number, prepend OG code
    num_match = re.match(r'^(\d{1,2})\b', text)
    if num_match:
        level = int(num_match.group(1))
        classification = f"{og_code}-{level:02d}"
        return classification, og_code

    return None, None


def detect_table_format(headers: list[str]) -> str:
    """Detect the table format based on headers.

    Args:
        headers: List of header cell texts

    Returns:
        "steps-as-columns" or "dates-as-columns"
    """
    # Check if headers contain "Step" - indicates steps-as-columns format
    for h in headers:
        if 'step' in h.lower().replace('\xa0', ' '):
            return "steps-as-columns"

    # Check if headers contain date patterns - indicates dates-as-columns format
    for h in headers:
        if parse_effective_date(h):
            return "dates-as-columns"

    return "unknown"


def parse_table_steps_as_columns(
    table,
    og_code: str,
    source_url: str,
    scraped_at: datetime,
    classification_context: Optional[str] = None,
) -> list[PayRateRow]:
    """Parse table with steps as columns (AO, CX style).

    Format:
    | Effective date    | Step 1  | Step 2  | ... |
    | $) Jan 26, 2022   | 151,490 | 155,615 | ... |

    Args:
        table: BeautifulSoup table element
        og_code: Occupational group code
        source_url: URL being scraped
        scraped_at: Scrape timestamp
        classification_context: Classification level from preceding h2/h3

    Returns:
        List of PayRateRow objects
    """
    rows_out: list[PayRateRow] = []

    # Get headers
    header_row = table.find('tr')
    if not header_row:
        return rows_out

    header_cells = header_row.find_all(['th', 'td'])
    headers = [c.get_text().strip() for c in header_cells]

    # Find step numbers from headers
    step_numbers = []
    for h in headers:
        step = parse_step_number(h)
        step_numbers.append(step)

    # Process data rows
    data_rows = table.find_all('tr')[1:]
    for tr in data_rows:
        cells = tr.find_all(['th', 'td'])
        if len(cells) < 2:
            continue

        # First cell should contain effective date
        first_cell_text = cells[0].get_text().strip()
        effective_date = parse_effective_date(first_cell_text)
        if not effective_date:
            continue

        # Process rate values (columns after first)
        for col_idx, cell in enumerate(cells[1:], start=1):
            if col_idx >= len(step_numbers):
                break

            step = step_numbers[col_idx]
            if step is None:
                continue

            rate = parse_rate_value(cell.get_text())
            if rate is None:
                continue

            # Use classification from context or default to OG code
            classification = classification_context or og_code

            row = PayRateRow(
                og_code=og_code,
                og_subgroup_code=og_code,
                classification_level=classification,
                step=step,
                annual_rate=rate,
                hourly_rate=None,
                effective_date=effective_date,
                represented=False,
                collective_agreement=None,
                source_url=source_url,
                scraped_at=scraped_at,
            )
            rows_out.append(row)

    return rows_out


def parse_table_dates_as_columns(
    table,
    og_code: str,
    source_url: str,
    scraped_at: datetime,
) -> list[PayRateRow]:
    """Parse table with dates as columns (AS, ED style).

    Format:
    | Level | Rates of pay | $) June 21, 2020 | A) June 21, 2021 | ... |
    | AS-07 | 100,220 to.. | 101,723 to ...   | ...              | ... |

    Args:
        table: BeautifulSoup table element
        og_code: Occupational group code
        source_url: URL being scraped
        scraped_at: Scrape timestamp

    Returns:
        List of PayRateRow objects
    """
    rows_out: list[PayRateRow] = []

    # Get headers
    header_row = table.find('tr')
    if not header_row:
        return rows_out

    header_cells = header_row.find_all(['th', 'td'])
    headers = [c.get_text().strip() for c in header_cells]

    # Find effective dates from headers (skip first 1-2 columns which are usually labels)
    effective_dates = []
    for h in headers:
        eff_date = parse_effective_date(h)
        effective_dates.append(eff_date)

    # Process data rows
    data_rows = table.find_all('tr')[1:]
    for tr in data_rows:
        cells = tr.find_all(['th', 'td'])
        if len(cells) < 3:
            continue

        # First cell should be classification level
        first_cell_text = cells[0].get_text().strip()
        classification, subgroup = extract_classification_info(first_cell_text, og_code)
        if not classification:
            continue

        # Process rate values (find columns with effective dates)
        for col_idx, cell in enumerate(cells):
            if col_idx >= len(effective_dates):
                break

            if effective_dates[col_idx] is None:
                continue

            rate = parse_rate_value(cell.get_text())
            if rate is None:
                continue

            row = PayRateRow(
                og_code=og_code,
                og_subgroup_code=subgroup or og_code,
                classification_level=classification,
                step=1,  # Dates-as-columns tables typically show single/range rates
                annual_rate=rate,
                hourly_rate=None,
                effective_date=effective_dates[col_idx],
                represented=False,
                collective_agreement=None,
                source_url=source_url,
                scraped_at=scraped_at,
            )
            rows_out.append(row)

    return rows_out


def scrape_pay_rates(url: str, og_code: str, timeout: int = 30) -> list[PayRateRow]:
    """Scrape pay rates from a single TBS rates of pay page.

    Handles multiple table formats by detecting structure automatically.

    Args:
        url: Full URL to the pay rates page
        og_code: Occupational group code (e.g., 'AS', 'PM')
        timeout: HTTP request timeout in seconds

    Returns:
        List of PayRateRow objects extracted from all tables on the page
    """
    logger.info("scraping_pay_rates_page", url=url, og_code=og_code)

    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.warning("pay_rates_fetch_failed", url=url, error=str(e))
        return []

    scraped_at = datetime.now(timezone.utc)
    soup = BeautifulSoup(resp.text, 'html.parser')

    # Find all tables on the page
    tables = soup.find_all('table')
    if not tables:
        logger.warning("no_tables_found", url=url)
        return []

    all_rows: list[PayRateRow] = []

    # Track classification context from preceding headers
    classification_context = None

    for element in soup.find_all(['h2', 'h3', 'table']):
        if element.name in ('h2', 'h3'):
            # Check if header contains classification info
            header_text = element.get_text().strip()
            clf, _ = extract_classification_info(header_text, og_code)
            if clf:
                classification_context = clf
            continue

        if element.name != 'table':
            continue

        table = element

        # Get headers for format detection
        header_row = table.find('tr')
        if not header_row:
            continue

        header_cells = header_row.find_all(['th', 'td'])
        headers = [c.get_text().strip() for c in header_cells]

        if len(headers) < 2:
            continue

        # Detect and parse based on format
        table_format = detect_table_format(headers)

        if table_format == "steps-as-columns":
            rows = parse_table_steps_as_columns(
                table, og_code, url, scraped_at, classification_context
            )
            all_rows.extend(rows)
        elif table_format == "dates-as-columns":
            rows = parse_table_dates_as_columns(
                table, og_code, url, scraped_at
            )
            all_rows.extend(rows)

    logger.info(
        "pay_rates_scraped",
        url=url,
        og_code=og_code,
        tables_found=len(tables),
        rows_extracted=len(all_rows),
    )

    return all_rows


def discover_og_pay_pages(timeout: int = 30) -> list[str]:
    """Discover available OG pay rate pages from the index page.

    Args:
        timeout: HTTP request timeout in seconds

    Returns:
        List of OG codes that have dedicated pay rate pages
    """
    logger.info("discovering_og_pay_pages", url=INDEX_URL)

    try:
        resp = requests.get(INDEX_URL, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.warning("index_fetch_failed", error=str(e))
        return KNOWN_OG_PAY_PAGES

    soup = BeautifulSoup(resp.text, 'html.parser')

    # Find all links to individual OG pay pages
    og_codes = set()
    base_path = '/en/treasury-board-secretariat/services/pay/rates-pay/rates-pay-unrepresented-senior-excluded-employees/'

    for link in soup.find_all('a', href=True):
        href = link['href']
        if base_path in href:
            suffix = href.split(base_path)[-1]
            page = suffix.split('#')[0].replace('.html', '').upper()
            if page and page != '':
                og_codes.add(page)

    if not og_codes:
        logger.warning("no_og_pages_discovered_using_known_list")
        return KNOWN_OG_PAY_PAGES

    logger.info("og_pay_pages_discovered", count=len(og_codes))
    return sorted(og_codes)


def scrape_all_pay_rates(
    output_dir: str | Path = "data/tbs",
    delay: float = 1.5,
    timeout: int = 30,
) -> Path:
    """Scrape pay rates from all available OG pages and save to JSON.

    Args:
        output_dir: Directory to save og_pay_rates_en.json
        delay: Delay between page requests in seconds
        timeout: HTTP request timeout in seconds

    Returns:
        Path to the saved JSON file
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "og_pay_rates_en.json"

    logger.info("scrape_all_pay_rates_start")

    # Discover available OG pages
    og_codes = discover_og_pay_pages(timeout=timeout)

    all_rows: list[dict] = []

    for i, og_code in enumerate(og_codes):
        # Build URL for this OG's pay rates page
        url = f"{BASE_URL}/{og_code.lower()}.html"

        # Scrape the page
        rows = scrape_pay_rates(url, og_code, timeout=timeout)

        # Convert to dicts for JSON serialization
        for row in rows:
            row_dict = row.model_dump(mode='json')
            all_rows.append(row_dict)

        # Rate limiting
        if i < len(og_codes) - 1:
            time.sleep(delay)

    # Save to JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_rows, f, indent=2, ensure_ascii=False)

    logger.info(
        "scrape_all_pay_rates_complete",
        output_file=str(output_file),
        og_pages_scraped=len(og_codes),
        total_rows=len(all_rows),
    )

    return output_file


if __name__ == "__main__":
    # Quick test
    output = scrape_all_pay_rates()
    print(f"Saved to: {output}")
