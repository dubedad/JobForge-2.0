"""CAF (Canadian Armed Forces) careers data scraping package.

This package provides tools for scraping career data from forces.ca
with full provenance tracking. Supports bilingual content (EN/FR)
and follows the established TBS scraper pattern.

Usage:
    from jobforge.external.caf import CAFScraper, scrape_caf_careers
    from jobforge.external.caf.models import CAFCareerListing, CAFOccupation

    # Scrape career listings (EN and FR)
    paths = scrape_caf_careers()

    # Or use the scraper class directly
    scraper = CAFScraper()
    listings_en = scraper.scrape_career_listings("en")
"""

from .models import (
    CAFCareerListing,
    CAFJobFamily,
    CAFOccupation,
    CAFProvenance,
    CAFScrapedPage,
)
from .scraper import CAFScraper, scrape_caf_careers

__all__ = [
    # Models
    "CAFProvenance",
    "CAFCareerListing",
    "CAFJobFamily",
    "CAFOccupation",
    "CAFScrapedPage",
    # Scraper
    "CAFScraper",
    "scrape_caf_careers",
]
