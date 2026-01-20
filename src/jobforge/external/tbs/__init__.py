"""TBS (Treasury Board Secretariat) data scraping package.

This package provides tools for scraping occupational group data from
Treasury Board Secretariat pages with full provenance tracking.
Supports both English and French content, and traverses embedded links
to fetch additional metadata.

Usage:
    from jobforge.external.tbs import TBSScraper, scrape_occupational_groups
    from jobforge.external.tbs import LinkMetadataFetcher, fetch_linked_metadata

    # Scrape main pages (EN and FR)
    paths = scrape_occupational_groups()

    # Follow embedded links to get definitions, standards, etc.
    fetch_linked_metadata("data/tbs/occupational_groups_en.json")
"""

from .models import (
    LinkedMetadataCollection,
    LinkedPageContent,
    LinkedPageMetadata,
    OccupationalGroupRow,
    ScrapedPage,
    ScrapedProvenance,
)
from .parser import (
    TBS_EXPECTED_COLUMNS,
    TBS_EXPECTED_COLUMNS_FR,
    TBS_REQUIRED_COLUMNS,
    TBS_REQUIRED_COLUMNS_FR,
    extract_embedded_links,
    parse_occupational_groups_table,
    validate_table_structure,
)
from .scraper import TBS_URLS, TBSScraper, scrape_occupational_groups
from .link_fetcher import LinkMetadataFetcher, fetch_linked_metadata, REQUEST_DELAY_SECONDS

__all__ = [
    # Models
    "ScrapedProvenance",
    "OccupationalGroupRow",
    "ScrapedPage",
    "LinkedPageContent",
    "LinkedPageMetadata",
    "LinkedMetadataCollection",
    # Parser
    "TBS_EXPECTED_COLUMNS",
    "TBS_EXPECTED_COLUMNS_FR",
    "TBS_REQUIRED_COLUMNS",
    "TBS_REQUIRED_COLUMNS_FR",
    "validate_table_structure",
    "parse_occupational_groups_table",
    "extract_embedded_links",
    # Scraper
    "TBS_URLS",
    "TBSScraper",
    "scrape_occupational_groups",
    # Link Fetcher
    "REQUEST_DELAY_SECONDS",
    "LinkMetadataFetcher",
    "fetch_linked_metadata",
]
