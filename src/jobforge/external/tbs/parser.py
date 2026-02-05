"""HTML parsing logic for TBS occupational groups pages.

This module handles parsing of the TBS occupational groups table,
validating structure to fail loudly on changes, and extracting
embedded links for follow-up scraping.
"""

from datetime import datetime

from bs4 import BeautifulSoup, Tag

import re

from .models import OccupationalGroupRow, OGSubgroup, ScrapedProvenance

# Expected column headers in the TBS occupational groups table (English)
# We validate against these to detect page structure changes
TBS_EXPECTED_COLUMNS = [
    "group abbreviation",
    "code",
    "occupational group",
    "group",
    "subgroup",
    "definition",
    "job evaluation standard",
    "qualification standard",
]

# French column headers (for bilingual support)
TBS_EXPECTED_COLUMNS_FR = [
    "abréviation de groupe",
    "code",
    "groupe professionnel",
    "groupe",
    "sous-groupe",
    "définition",
    "norme d'évaluation des emplois",
    "norme de qualification",
]

# Minimum required columns for validation (bilingual)
TBS_REQUIRED_COLUMNS = ["group abbreviation", "code", "occupational group"]
TBS_REQUIRED_COLUMNS_FR = ["abréviation de groupe", "code", "groupe professionnel"]


def validate_table_structure(table: Tag, language: str = "en") -> bool:
    """Validate that the table has expected column structure.

    Per CONTEXT.md: Fail loudly on page structure changes.
    Supports both English and French pages.

    Args:
        table: BeautifulSoup Tag representing the table element.
        language: Language code ('en' or 'fr') to select correct validation headers.

    Returns:
        True if structure is valid.

    Raises:
        ValueError: If required columns are missing, indicating page structure change.
    """
    headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]

    # Select appropriate required columns based on language
    required_cols = TBS_REQUIRED_COLUMNS_FR if language == "fr" else TBS_REQUIRED_COLUMNS

    # Check required columns are present
    for required_col in required_cols:
        if not any(required_col in h for h in headers):
            raise ValueError(
                f"Missing expected column: '{required_col}'. "
                f"Found headers: {headers}. "
                "TBS page structure may have changed - manual review required."
            )

    return True


def parse_occupational_groups_table(
    html: str,
    source_url: str,
    scraped_at: datetime,
    language: str | None = None,
) -> list[OccupationalGroupRow]:
    """Parse TBS occupational groups HTML table into structured data.

    Per CONTEXT.md: Fail loudly on structure changes.
    Supports both English and French pages.

    Args:
        html: Raw HTML content of the page.
        source_url: URL from which the HTML was fetched (for provenance).
        scraped_at: UTC timestamp when the page was scraped.
        language: Language code ('en' or 'fr'). If None, detected from URL.

    Returns:
        List of OccupationalGroupRow objects with provenance.

    Raises:
        ValueError: If no table found or structure has changed.
    """
    # Detect language from URL if not provided
    if language is None:
        language = "fr" if "/fr/" in source_url else "en"

    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")

    if not table:
        raise ValueError(
            f"No table found at {source_url}. "
            "TBS page structure may have changed - manual review required."
        )

    # Validate structure before parsing (with language-aware validation)
    validate_table_structure(table, language)

    # Extract page title for provenance
    title_tag = soup.find("title")
    page_title = title_tag.get_text(strip=True) if title_tag else "Unknown"

    rows: list[OccupationalGroupRow] = []

    # Find all data rows (skip header row)
    table_rows = table.find_all("tr")
    for tr in table_rows[1:]:  # Skip header row
        cells = tr.find_all("td")
        if len(cells) < 6:
            continue  # Skip malformed rows

        # Extract cell values
        group_abbrev = cells[0].get_text(strip=True)
        code = cells[1].get_text(strip=True)
        group_name = cells[2].get_text(strip=True)

        # Group and subgroup may not be present in all table layouts
        group = cells[3].get_text(strip=True) if len(cells) > 3 else None
        subgroup_text = cells[4].get_text(strip=True) if len(cells) > 4 else None
        subgroup = subgroup_text if subgroup_text else None

        def extract_link(cell_idx: int) -> str | None:
            """Extract URL from a cell if it contains a link."""
            if len(cells) > cell_idx:
                link = cells[cell_idx].find("a")
                if link and link.get("href"):
                    href = link["href"]
                    # Make absolute URL if relative
                    if href.startswith("/"):
                        href = "https://www.canada.ca" + href
                    return href
            return None

        rows.append(
            OccupationalGroupRow(
                group_abbrev=group_abbrev,
                group_code=code,
                group_name=group_name,
                subgroup=subgroup,
                definition_url=extract_link(5),
                job_eval_standard_url=extract_link(6),
                qualification_standard_url=extract_link(7),
                provenance=ScrapedProvenance(
                    source_url=source_url,
                    scraped_at=scraped_at,
                    extraction_method="table_cell",
                    page_title=page_title,
                ),
            )
        )

    return rows


def extract_embedded_links(rows: list[OccupationalGroupRow]) -> dict[str, list[str]]:
    """Extract all embedded links by type for follow-up scraping.

    Groups links into categories for batch processing.

    Args:
        rows: List of parsed occupational group rows.

    Returns:
        Dictionary with keys 'definitions', 'job_eval_standards', 'qualification_standards',
        each containing a list of URLs.
    """
    return {
        "definitions": [r.definition_url for r in rows if r.definition_url],
        "job_eval_standards": [r.job_eval_standard_url for r in rows if r.job_eval_standard_url],
        "qualification_standards": [
            r.qualification_standard_url for r in rows if r.qualification_standard_url
        ],
    }


def parse_og_subgroups(
    rows: list[OccupationalGroupRow],
    source_url: str,
    scraped_at: "datetime",
) -> list[OGSubgroup]:
    """Parse subgroup information from occupational group rows.

    Extracts structured subgroup data from rows that have subgroup values.
    Parses subgroup codes and names from the subgroup cell text.

    Args:
        rows: List of OccupationalGroupRow objects from main table scrape.
        source_url: URL from which data was scraped (for provenance).
        scraped_at: UTC timestamp when scraping occurred.

    Returns:
        List of OGSubgroup objects for rows with valid subgroup data.

    Example:
        Row with subgroup="Non-Operational(AI-NOP)" produces:
        OGSubgroup(og_code="AI", subgroup_code="AI-NOP", subgroup_name="Non-Operational", ...)
    """
    subgroups: list[OGSubgroup] = []

    # Pattern to extract name and code from subgroup text like "Non-Operational(AI-NOP)"
    # or "Civil Aviation Inspection(AO-CAI)"
    subgroup_pattern = re.compile(r"^(.+?)\(([A-Z]{2,3}-[A-Z0-9]+)\)$")

    for row in rows:
        # Skip rows without subgroup data or with N/A
        if not row.subgroup or row.subgroup.strip().upper() == "N/A":
            continue

        subgroup_text = row.subgroup.strip()
        match = subgroup_pattern.match(subgroup_text)

        if match:
            subgroup_name = match.group(1).strip()
            subgroup_code = match.group(2).strip()
        else:
            # Fallback: use entire text as name, construct code from parent
            subgroup_name = subgroup_text
            # Try to extract code if it appears after parenthesis
            if "(" in subgroup_text and ")" in subgroup_text:
                code_start = subgroup_text.rfind("(") + 1
                code_end = subgroup_text.rfind(")")
                subgroup_code = subgroup_text[code_start:code_end].strip()
                subgroup_name = subgroup_text[:subgroup_text.rfind("(")].strip()
            else:
                subgroup_code = f"{row.group_abbrev}-{subgroup_text[:3].upper()}"

        subgroups.append(
            OGSubgroup(
                og_code=row.group_abbrev,
                subgroup_code=subgroup_code,
                subgroup_name=subgroup_name,
                definition_url=row.definition_url,
                qualification_standard_url=row.qualification_standard_url,
                rates_of_pay_url=None,  # Not present in main table, could be added later
                source_url=source_url,
                scraped_at=scraped_at,
            )
        )

    return subgroups
