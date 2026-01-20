"""HTML parsing logic for TBS occupational groups pages.

This module handles parsing of the TBS occupational groups table,
validating structure to fail loudly on changes, and extracting
embedded links for follow-up scraping.
"""

from datetime import datetime

from bs4 import BeautifulSoup, Tag

from .models import OccupationalGroupRow, ScrapedProvenance

# Expected column headers in the TBS occupational groups table
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

# Minimum required columns for validation
TBS_REQUIRED_COLUMNS = ["group abbreviation", "code", "occupational group"]


def validate_table_structure(table: Tag) -> bool:
    """Validate that the table has expected column structure.

    Per CONTEXT.md: Fail loudly on page structure changes.

    Args:
        table: BeautifulSoup Tag representing the table element.

    Returns:
        True if structure is valid.

    Raises:
        ValueError: If required columns are missing, indicating page structure change.
    """
    headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]

    # Check required columns are present
    for required_col in TBS_REQUIRED_COLUMNS:
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
) -> list[OccupationalGroupRow]:
    """Parse TBS occupational groups HTML table into structured data.

    Per CONTEXT.md: Fail loudly on structure changes.

    Args:
        html: Raw HTML content of the page.
        source_url: URL from which the HTML was fetched (for provenance).
        scraped_at: UTC timestamp when the page was scraped.

    Returns:
        List of OccupationalGroupRow objects with provenance.

    Raises:
        ValueError: If no table found or structure has changed.
    """
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")

    if not table:
        raise ValueError(
            f"No table found at {source_url}. "
            "TBS page structure may have changed - manual review required."
        )

    # Validate structure before parsing
    validate_table_structure(table)

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
