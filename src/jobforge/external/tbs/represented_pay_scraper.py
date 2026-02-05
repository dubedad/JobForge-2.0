"""TBS Represented Pay Rates scraper with provenance tracking.

This module scrapes pay rates for represented (unionized) employees from
Treasury Board Secretariat collective agreement pages.

TBS publishes collective agreements at:
https://www.canada.ca/en/treasury-board-secretariat/topics/pay/collective-agreements.html

Each collective agreement page (e.g., /ec.html) contains pay rate tables
in Appendix A with format:
- Table caption: "EC-01 - Annual Rates of Pay (in dollars)"
- Headers: Effective Date | Step 1 | Step 2 | ...
- Rows: $) June 22, 2021 | 55,567 | 57,508 | ...

This follows the same steps-as-columns format as excluded pay rates.
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

# Base URL for collective agreements
BASE_URL = "https://www.canada.ca/en/treasury-board-secretariat/topics/pay/collective-agreements"
INDEX_URL = f"{BASE_URL}.html"

# Request delay to respect server
REQUEST_DELAY_SECONDS = 1.5


class RepresentedPayRate(BaseModel):
    """Represented/unionized pay rate from TBS collective agreements.

    Extends the excluded pay rate pattern with collective agreement linkage.
    """

    og_code: str = Field(description="Occupational group code (e.g., 'EC', 'PA')")
    og_subgroup_code: str = Field(description="Full classification code (e.g., 'EC-01', 'PA-01')")
    classification_level: str = Field(description="Classification level (e.g., 'EC-04', 'PA-02')")
    step: int = Field(description="Pay step within level (typically 1-10)", ge=1)

    annual_rate: Optional[Decimal] = Field(default=None, description="Annual salary rate in CAD")
    hourly_rate: Optional[Decimal] = Field(default=None, description="Hourly rate in CAD if available")
    effective_date: Optional[str] = Field(default=None, description="Date pay rate became effective (YYYY-MM-DD)")

    is_represented: bool = Field(default=True, description="True for unionized employees")
    collective_agreement_id: Optional[str] = Field(default=None, description="FK to dim_collective_agreement")

    # Pay progression type per CONTEXT.md
    pay_progression_type: str = Field(
        default="step",
        description="Pay progression type: 'step', 'performance', or 'hybrid'"
    )

    source_url: str = Field(description="URL from which data was scraped")
    scraped_at: str = Field(description="ISO timestamp when scraping occurred")

    class Config:
        """Pydantic config for JSON serialization."""
        json_encoders = {
            Decimal: lambda v: float(v) if v is not None else None,
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
    if not text or text in ("", "-", "N/A") or "not applicable" in text.lower():
        return None

    # If there's a range (e.g., "100,220 to 114,592"), take the first value
    if " to " in text.lower():
        text = text.lower().split(" to ")[0]

    # Remove dollar signs, commas, spaces, non-breaking spaces
    cleaned = re.sub(r"[$,\s\xa0]", "", text)

    # Must be numeric
    if not cleaned or not re.match(r"^[\d.]+$", cleaned):
        return None

    try:
        value = Decimal(cleaned)
        # Sanity check: TBS salaries are typically 30k-300k range
        if value < 10000 or value > 500000:
            return None
        return value
    except Exception:
        return None


def parse_effective_date(text: str) -> Optional[str]:
    """Extract effective date from table cell text.

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
    date_match = re.search(r"(\w+)\s+(\d{1,2}),?\s*(\d{4})", text)
    if date_match:
        month_name = date_match.group(1)
        day = date_match.group(2)
        year = date_match.group(3)

        months = {
            "january": "01", "february": "02", "march": "03", "april": "04",
            "may": "05", "june": "06", "july": "07", "august": "08",
            "september": "09", "october": "10", "november": "11", "december": "12",
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
    match = re.search(r"step\s*(\d+)", text.lower().replace("\xa0", " "))
    if match:
        return int(match.group(1))
    return None


def extract_classification_from_caption(caption: str) -> Optional[str]:
    """Extract classification level from table caption.

    Args:
        caption: Table caption like "EC-01 - Annual Rates of Pay (in dollars)"

    Returns:
        Classification level (e.g., "EC-01") or None
    """
    if not caption:
        return None

    # Look for XX-NN pattern at start
    match = re.match(r"^([A-Z]{2,4}-\d{1,2})", caption.strip())
    if match:
        return match.group(1)

    return None


def parse_pay_table(
    table,
    og_code: str,
    collective_agreement_id: str,
    source_url: str,
    scraped_at: str,
) -> list[RepresentedPayRate]:
    """Parse a pay rate table from a collective agreement page.

    Tables have format:
    - Caption: "EC-01 - Annual Rates of Pay"
    - Headers: Effective Date | Step 1 | Step 2 | ...
    - Rows: $) June 22, 2021 | 55,567 | 57,508 | ...

    Args:
        table: BeautifulSoup table element
        og_code: Occupational group code
        collective_agreement_id: FK to dim_collective_agreement
        source_url: URL being scraped
        scraped_at: ISO timestamp

    Returns:
        List of RepresentedPayRate objects
    """
    rows_out: list[RepresentedPayRate] = []

    # Extract classification from caption
    caption = table.find("caption")
    if not caption:
        return rows_out

    caption_text = caption.get_text().strip()
    classification = extract_classification_from_caption(caption_text)

    if not classification:
        return rows_out

    # Skip non-pay tables (e.g., "Penological factor allowance")
    if "rates of pay" not in caption_text.lower():
        return rows_out

    # Extract OG code from classification
    og_from_class = classification.split("-")[0] if "-" in classification else og_code

    # Get headers
    header_row = table.find("tr")
    if not header_row:
        return rows_out

    header_cells = header_row.find_all(["th", "td"])
    headers = [c.get_text().strip() for c in header_cells]

    # Find step numbers from headers
    step_numbers = []
    for h in headers:
        step = parse_step_number(h)
        step_numbers.append(step)

    # Process data rows
    data_rows = table.find_all("tr")[1:]
    for tr in data_rows:
        cells = tr.find_all(["th", "td"])
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

            row = RepresentedPayRate(
                og_code=og_from_class,
                og_subgroup_code=og_from_class,
                classification_level=classification,
                step=step,
                annual_rate=rate,
                hourly_rate=None,
                effective_date=effective_date,
                is_represented=True,
                collective_agreement_id=collective_agreement_id,
                pay_progression_type="step",
                source_url=source_url,
                scraped_at=scraped_at,
            )
            rows_out.append(row)

    return rows_out


def scrape_represented_pay_rates(
    og_code: str,
    url: str,
    collective_agreement_id: str,
    timeout: int = 30,
) -> list[RepresentedPayRate]:
    """Scrape pay rates from a single collective agreement page.

    Args:
        og_code: Occupational group code (e.g., 'EC', 'PA')
        url: Full URL to the collective agreement page
        collective_agreement_id: FK to dim_collective_agreement
        timeout: HTTP request timeout in seconds

    Returns:
        List of RepresentedPayRate objects extracted from all tables
    """
    logger.info("scraping_represented_pay_rates", url=url, og_code=og_code)

    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
    except (requests.RequestException, Exception) as e:
        logger.warning("represented_pay_fetch_failed", url=url, error=str(e))
        return []

    scraped_at = datetime.now(timezone.utc).isoformat()
    soup = BeautifulSoup(resp.text, "html.parser")

    main = soup.find("main")
    if not main:
        logger.warning("no_main_content", url=url)
        return []

    # Find all tables with captions
    tables = main.find_all("table")
    all_rows: list[RepresentedPayRate] = []

    for table in tables:
        rows = parse_pay_table(
            table=table,
            og_code=og_code,
            collective_agreement_id=collective_agreement_id,
            source_url=url,
            scraped_at=scraped_at,
        )
        all_rows.extend(rows)

    logger.info(
        "represented_pay_scraped",
        url=url,
        og_code=og_code,
        tables_found=len(tables),
        rows_extracted=len(all_rows),
    )

    return all_rows


def discover_collective_agreement_urls(timeout: int = 30) -> list[dict]:
    """Discover available collective agreement URLs from the index page.

    Args:
        timeout: HTTP request timeout in seconds

    Returns:
        List of dicts with og_code, url, and agreement_name
    """
    logger.info("discovering_collective_agreement_urls", url=INDEX_URL)

    try:
        resp = requests.get(INDEX_URL, timeout=timeout)
        resp.raise_for_status()
    except (requests.RequestException, Exception) as e:
        logger.warning("index_fetch_failed", error=str(e))
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    main = soup.find("main")
    if not main:
        return []

    # Find links to collective agreement pages
    agreements = []
    for link in main.find_all("a", href=True):
        href = link["href"]
        if "/collective-agreements/" in href and href.endswith(".html"):
            # Extract OG code from URL (e.g., /ec.html -> EC)
            page_name = href.split("/")[-1].replace(".html", "")
            og_code = page_name.upper()

            # Skip index page
            if og_code in ("COLLECTIVE-AGREEMENTS", "INDEX"):
                continue

            full_url = href if href.startswith("http") else f"https://www.canada.ca{href}"

            agreements.append({
                "og_code": og_code,
                "url": full_url,
                "agreement_name": link.get_text().strip(),
            })

    # Remove duplicates
    seen = set()
    unique = []
    for a in agreements:
        if a["og_code"] not in seen:
            seen.add(a["og_code"])
            unique.append(a)

    logger.info("collective_agreement_urls_discovered", count=len(unique))
    return unique


def load_collective_agreements(path: str | Path = "data/tbs/collective_agreements.json") -> dict:
    """Load collective agreements mapping OG code to agreement_id.

    Args:
        path: Path to collective_agreements.json

    Returns:
        Dict mapping og_code to agreement_id
    """
    path = Path(path)
    if not path.exists():
        logger.warning("collective_agreements_not_found", path=str(path))
        return {}

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    # Build mapping from og_code to agreement_id
    mapping = {}
    for agreement in data:
        og_code = agreement.get("og_code", "").upper()
        if og_code:
            mapping[og_code] = agreement.get("agreement_id")

    return mapping


def scrape_all_represented_pay_rates(
    output_dir: str | Path = "data/tbs",
    delay: float = REQUEST_DELAY_SECONDS,
    timeout: int = 30,
) -> Path:
    """Scrape pay rates from all collective agreement pages.

    Args:
        output_dir: Directory to save og_represented_pay_rates.json
        delay: Delay between page requests in seconds
        timeout: HTTP request timeout in seconds

    Returns:
        Path to the saved JSON file
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "og_represented_pay_rates.json"

    logger.info("scrape_all_represented_pay_rates_start")

    # Load collective agreements for FK linking
    ca_mapping = load_collective_agreements(output_dir / "collective_agreements.json")

    # Discover collective agreement URLs
    agreements = discover_collective_agreement_urls(timeout=timeout)

    all_rows: list[dict] = []

    for i, agreement in enumerate(agreements):
        og_code = agreement["og_code"]
        url = agreement["url"]

        # Get collective agreement ID for linking
        ca_id = ca_mapping.get(og_code)

        # Scrape pay rates from this agreement
        rows = scrape_represented_pay_rates(
            og_code=og_code,
            url=url,
            collective_agreement_id=ca_id,
            timeout=timeout,
        )

        # Convert to dicts for JSON serialization
        for row in rows:
            row_dict = row.model_dump(mode="json")
            all_rows.append(row_dict)

        # Rate limiting
        if i < len(agreements) - 1:
            time.sleep(delay)

    # Check for regional differentials (per RESEARCH.md Open Question 5)
    regional_codes = [r for r in all_rows if "regional" in str(r.get("classification_level", "")).lower()]
    if not regional_codes:
        logger.info("regional_differentials_not_found", note="TBS pay rates appear nationally uniform")

    # Save to JSON
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_rows, f, indent=2, ensure_ascii=False)

    logger.info(
        "scrape_all_represented_pay_rates_complete",
        output_file=str(output_file),
        agreements_scraped=len(agreements),
        total_rows=len(all_rows),
    )

    return output_file


if __name__ == "__main__":
    output = scrape_all_represented_pay_rates()
    print(f"Saved to: {output}")
