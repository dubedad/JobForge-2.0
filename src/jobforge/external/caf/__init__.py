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

    # Fetch full career details with bilingual content
    from jobforge.external.caf import CAFLinkFetcher, fetch_career_detail
    with CAFLinkFetcher() as fetcher:
        occupations = fetcher.fetch_all_career_details()

    # Match CAF occupations to NOC codes
    from jobforge.external.caf import CAFNOCMatcher, match_caf_to_noc
    matches = match_caf_to_noc("infantry-officer")
"""

from .link_fetcher import CAFLinkFetcher, fetch_all_career_details, fetch_career_detail
from .matchers import CAFNOCMapping, CAFNOCMatcher, match_caf_to_noc
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
    # Link fetcher
    "CAFLinkFetcher",
    "fetch_career_detail",
    "fetch_all_career_details",
    # Matchers
    "CAFNOCMapping",
    "CAFNOCMatcher",
    "match_caf_to_noc",
]
