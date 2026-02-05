"""TBS Collective Agreement scraper with provenance tracking.

This module scrapes collective agreement metadata from the Treasury Board
Secretariat index page. It extracts agreement name, bargaining agent,
signing and expiry dates for each occupational group.

TBS publishes collective agreements at:
https://www.canada.ca/en/treasury-board-secretariat/topics/pay/collective-agreements.html

The index page contains a table with:
- Abbreviation (OG code)
- Group name
- Union (bargaining agent)
- Signing date
- Expiry date
"""

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid5, NAMESPACE_DNS

import requests
import structlog
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

# Index page URL
INDEX_URL = "https://www.canada.ca/en/treasury-board-secretariat/topics/pay/collective-agreements.html"

# Namespace for generating consistent UUIDs from agreement names
AGREEMENT_UUID_NAMESPACE = NAMESPACE_DNS


class CollectiveAgreement(BaseModel):
    """Collective agreement metadata from TBS.

    Captures agreement metadata for linking pay rates to their
    collective bargaining context.
    """

    agreement_id: str = Field(description="Generated UUID from slugified name")
    agreement_name: str = Field(description="Full agreement name (e.g., 'Economics and Social Science Services (EC)')")
    og_code: str = Field(description="Primary occupational group code (FK to dim_og)")
    og_subgroup_codes: list[str] = Field(default_factory=list, description="Subgroup codes covered by this agreement")
    bargaining_agent: str = Field(description="Union/bargaining agent name")
    employer: str = Field(default="Treasury Board of Canada Secretariat", description="Employer signatory")

    signing_date: Optional[str] = Field(default=None, description="Date agreement was signed (YYYY-MM-DD)")
    effective_date: Optional[str] = Field(default=None, description="Date agreement became effective (YYYY-MM-DD)")
    expiry_date: Optional[str] = Field(default=None, description="Date agreement expires (YYYY-MM-DD or null if evergreen)")

    source_url: str = Field(description="URL from which data was scraped")
    scraped_at: str = Field(description="ISO timestamp when scraping occurred")

    class Config:
        """Pydantic config."""
        json_encoders = {
            datetime: lambda v: v.isoformat() if v is not None else None,
        }


def generate_agreement_id(agreement_name: str) -> str:
    """Generate a stable UUID for an agreement based on its name.

    Uses UUID5 with DNS namespace for reproducible IDs.

    Args:
        agreement_name: Full agreement name

    Returns:
        UUID string
    """
    return str(uuid5(AGREEMENT_UUID_NAMESPACE, agreement_name.lower().strip()))


def parse_date_string(date_str: str) -> Optional[str]:
    """Parse date string from TBS table into YYYY-MM-DD format.

    Handles formats like:
    - "2025-12-19" (already formatted)
    - "December 19, 2025"
    - "2025-06-30"

    Args:
        date_str: Date string from table cell

    Returns:
        Date in YYYY-MM-DD format or None if unparseable
    """
    if not date_str:
        return None

    date_str = date_str.strip()

    # Already in YYYY-MM-DD format
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return date_str

    # Try Month Day, Year format
    match = re.match(r"(\w+)\s+(\d{1,2}),?\s*(\d{4})", date_str)
    if match:
        month_name = match.group(1).lower()
        day = match.group(2)
        year = match.group(3)

        months = {
            "january": "01", "february": "02", "march": "03", "april": "04",
            "may": "05", "june": "06", "july": "07", "august": "08",
            "september": "09", "october": "10", "november": "11", "december": "12",
        }

        month_num = months.get(month_name)
        if month_num:
            return f"{year}-{month_num}-{day.zfill(2)}"

    return None


def extract_og_code(abbreviation: str, group_abbr: str) -> str:
    """Extract primary OG code from abbreviation or group abbreviation.

    Args:
        abbreviation: Short abbreviation like "(AI)" or "(CP)(AV)"
        group_abbr: Full group abbreviation like "Air Traffic Control (AI)"

    Returns:
        Primary OG code (e.g., "AI", "CP")
    """
    # Try to extract from abbreviation first - look for first (XX) pattern
    match = re.search(r"\(([A-Z]{2,4})\)", abbreviation)
    if match:
        return match.group(1)

    # Try from group abbreviation
    match = re.search(r"\(([A-Z]{2,4})\)", group_abbr)
    if match:
        return match.group(1)

    # Fallback: clean the abbreviation
    cleaned = re.sub(r"[^A-Z]", "", abbreviation.upper())
    return cleaned[:2] if cleaned else "UNKNOWN"


def extract_subgroup_codes(group_abbr: str) -> list[str]:
    """Extract all subgroup codes from group abbreviation.

    Args:
        group_abbr: Group abbreviation like "Comptrollership (CT [EAV, FIN, IAU])"

    Returns:
        List of subgroup codes (e.g., ["CT", "EAV", "FIN", "IAU"])
    """
    codes = []

    # Find all codes in parentheses and brackets
    # Pattern: (XX) or [XX, YY, ZZ]
    paren_match = re.search(r"\(([A-Z]{2,4})", group_abbr)
    if paren_match:
        codes.append(paren_match.group(1))

    # Find bracketed subgroups
    bracket_match = re.search(r"\[([^\]]+)\]", group_abbr)
    if bracket_match:
        # Split by comma and clean
        bracket_codes = bracket_match.group(1).split(",")
        for code in bracket_codes:
            cleaned = code.strip().upper()
            if re.match(r"^[A-Z]{2,4}$", cleaned):
                codes.append(cleaned)

    return list(set(codes))  # Remove duplicates


def scrape_collective_agreements(
    delay: float = 1.5,
    timeout: int = 30,
) -> list[CollectiveAgreement]:
    """Scrape collective agreement metadata from TBS index page.

    The index page contains a table with all active collective agreements,
    including abbreviation, group name, union, and dates.

    Args:
        delay: Delay between requests in seconds (unused here, single page)
        timeout: HTTP request timeout in seconds

    Returns:
        List of CollectiveAgreement objects
    """
    logger.info("scraping_collective_agreements", url=INDEX_URL)

    try:
        resp = requests.get(INDEX_URL, timeout=timeout)
        resp.raise_for_status()
    except (requests.RequestException, Exception) as e:
        logger.error("collective_agreements_fetch_failed", url=INDEX_URL, error=str(e))
        return []

    scraped_at = datetime.now(timezone.utc).isoformat()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Find the main table with collective agreements
    main = soup.find("main")
    if not main:
        logger.warning("no_main_content_found", url=INDEX_URL)
        return []

    tables = main.find_all("table")
    if not tables:
        logger.warning("no_tables_found", url=INDEX_URL)
        return []

    # The collective agreements table should have headers with:
    # Abbreviation, Group, Group and sub-group abbreviation, Code, Union, Signing date, Expiry date
    agreements: list[CollectiveAgreement] = []

    for table in tables:
        rows = table.find_all("tr")
        if not rows:
            continue

        # Check header row
        header_row = rows[0]
        headers = [cell.get_text().strip().lower() for cell in header_row.find_all(["th", "td"])]

        # Verify this is the collective agreements table
        if not any("union" in h for h in headers):
            continue

        # Map header indices
        header_map = {}
        for i, h in enumerate(headers):
            if "abbreviation" in h and "group" not in h:
                header_map["abbreviation"] = i
            elif "group" in h and "sub-group" in h:
                header_map["group_abbr"] = i
            elif "group" in h:
                header_map["group_name"] = i
            elif "union" in h:
                header_map["union"] = i
            elif "signing" in h:
                header_map["signing_date"] = i
            elif "expiry" in h:
                header_map["expiry_date"] = i

        logger.debug("header_map", header_map=header_map)

        # Process data rows
        for row in rows[1:]:
            cells = row.find_all(["th", "td"])
            if len(cells) < 5:
                continue

            cell_texts = [cell.get_text().strip() for cell in cells]

            # Extract fields
            abbreviation = cell_texts[header_map.get("abbreviation", 0)]
            group_name = cell_texts[header_map.get("group_name", 1)]
            group_abbr = cell_texts[header_map.get("group_abbr", 2)]
            union = cell_texts[header_map.get("union", 4)]
            signing_date_str = cell_texts[header_map.get("signing_date", 5)] if header_map.get("signing_date") else None
            expiry_date_str = cell_texts[header_map.get("expiry_date", 6)] if header_map.get("expiry_date") else None

            # Build agreement name
            agreement_name = f"{group_name} ({abbreviation.replace('(', '').replace(')', '')})"
            agreement_name = re.sub(r"\s+", " ", agreement_name).strip()

            # Extract OG code and subgroups
            og_code = extract_og_code(abbreviation, group_abbr)
            subgroup_codes = extract_subgroup_codes(group_abbr)

            # Parse dates
            signing_date = parse_date_string(signing_date_str) if signing_date_str else None
            expiry_date = parse_date_string(expiry_date_str) if expiry_date_str else None

            # Generate agreement ID
            agreement_id = generate_agreement_id(agreement_name)

            agreement = CollectiveAgreement(
                agreement_id=agreement_id,
                agreement_name=agreement_name,
                og_code=og_code,
                og_subgroup_codes=subgroup_codes,
                bargaining_agent=union,
                employer="Treasury Board of Canada Secretariat",
                signing_date=signing_date,
                effective_date=signing_date,  # Use signing date as effective date
                expiry_date=expiry_date,
                source_url=INDEX_URL,
                scraped_at=scraped_at,
            )

            agreements.append(agreement)

    logger.info(
        "collective_agreements_scraped",
        url=INDEX_URL,
        count=len(agreements),
    )

    return agreements


def scrape_all_collective_agreements(
    output_dir: str | Path = "data/tbs",
    delay: float = 1.5,
    timeout: int = 30,
) -> Path:
    """Scrape all collective agreements and save to JSON.

    Args:
        output_dir: Directory to save collective_agreements.json
        delay: Delay between requests in seconds
        timeout: HTTP request timeout in seconds

    Returns:
        Path to the saved JSON file
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "collective_agreements.json"

    logger.info("scrape_all_collective_agreements_start")

    # Scrape agreements
    agreements = scrape_collective_agreements(delay=delay, timeout=timeout)

    # Convert to dicts for JSON serialization
    data = [a.model_dump(mode="json") for a in agreements]

    # Save to JSON
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info(
        "scrape_all_collective_agreements_complete",
        output_file=str(output_file),
        agreements_count=len(agreements),
    )

    return output_file


if __name__ == "__main__":
    # Quick test
    output = scrape_all_collective_agreements()
    print(f"Saved to: {output}")
