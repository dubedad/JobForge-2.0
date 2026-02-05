"""Pydantic models for CAF scraped data with full provenance.

These models ensure type safety and validation for all data scraped from
Canadian Armed Forces careers pages (forces.ca), including career listings,
job families, and detailed occupation information.

Following TBS scraper pattern per CONTEXT.md and RESEARCH.md.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CAFProvenance(BaseModel):
    """Provenance information for any scraped CAF value.

    Every piece of scraped data must carry its origin information
    for audit and traceability purposes per PROJECT.md core value.
    """

    source_url: str = Field(description="URL from which data was scraped")
    scraped_at: datetime = Field(description="UTC timestamp when scraping occurred")
    content_hash: str = Field(description="SHA-256 hash of raw HTML for integrity verification")
    scraper_version: str = Field(default="CAFScraper-1.0.0", description="Scraper version for audit trail")
    extraction_method: str = Field(
        default="html_parser",
        description="How the value was extracted: 'html_parser', 'sitemap', 'api'",
    )


class CAFCareerListing(BaseModel):
    """Single CAF career listing scraped from forces.ca.

    Represents basic career information extracted from the careers listing
    page or sitemap. Contains enough information to identify the career
    and fetch detailed information in a subsequent scrape.

    Per CONTEXT.md: Capture all available fields from the website.
    """

    # Canonical identifier
    career_id: str = Field(description="Canonical ID derived from URL slug (e.g., 'pilot', 'infantry-officer')")

    # Basic info
    title: str = Field(description="Career title as displayed on forces.ca")
    url: str = Field(description="Full URL to career detail page")

    # Military classification
    environment: list[str] = Field(
        default_factory=list,
        description="Military environments: 'army', 'navy', 'air_force'",
    )
    commission_status: Literal["officer", "ncm", "both", "unknown"] = Field(
        default="unknown",
        description="Officer or Non-Commissioned Member status",
    )
    employment_type: list[str] = Field(
        default_factory=list,
        description="Employment types: 'full_time', 'part_time', 'reserve'",
    )

    # Provenance
    provenance: CAFProvenance = Field(description="Provenance for this listing")


class CAFJobFamily(BaseModel):
    """CAF job family grouping.

    Represents one of the approximately 12 career categories/families
    used to organize CAF occupations. May be inferred from URL patterns
    or career page metadata.

    Per RESEARCH.md open question #1: Exact names may need to be
    discovered through data analysis.
    """

    family_id: str = Field(description="Canonical ID for job family")
    family_name: str = Field(description="Display name of job family")
    description: str | None = Field(default=None, description="Description if available")
    career_count: int = Field(default=0, description="Number of careers in this family")
    source_url: str | None = Field(default=None, description="URL where family was identified")


class CAFOccupation(BaseModel):
    """Detailed CAF occupation information scraped from career detail page.

    Contains full content extracted from an individual career page,
    including overview, training info, entry plans, and related careers.

    Per CONTEXT.md: Capture all available fields, don't filter during scrape.
    """

    # Identity
    career_id: str = Field(description="Canonical ID from URL slug")
    title_en: str = Field(description="Career title in English")
    title_fr: str | None = Field(default=None, description="Career title in French if scraped")

    # Classification
    environment: list[str] = Field(
        default_factory=list,
        description="Military environments: 'army', 'navy', 'air_force'",
    )
    commission_status: Literal["officer", "ncm", "both", "unknown"] = Field(
        default="unknown",
        description="Officer or Non-Commissioned Member status",
    )
    employment_type: list[str] = Field(
        default_factory=list,
        description="Employment types: 'full_time', 'part_time', 'reserve'",
    )

    # Content sections (EN)
    overview_en: str | None = Field(default=None, description="Overview section content in English")
    work_environment_en: str | None = Field(default=None, description="Work environment section in English")
    training_en: str | None = Field(default=None, description="Training section content in English")
    entry_plans_en: str | None = Field(default=None, description="Entry plans section in English")
    part_time_options_en: str | None = Field(default=None, description="Part time options in English")

    # Content sections (FR)
    overview_fr: str | None = Field(default=None, description="Overview section content in French")
    work_environment_fr: str | None = Field(default=None, description="Work environment section in French")
    training_fr: str | None = Field(default=None, description="Training section content in French")
    entry_plans_fr: str | None = Field(default=None, description="Entry plans section in French")
    part_time_options_fr: str | None = Field(default=None, description="Part time options in French")

    # Related data
    related_civilian_occupations: list[str] = Field(
        default_factory=list,
        description="Related civilian occupations listed on career page",
    )
    related_careers: list[str] = Field(
        default_factory=list,
        description="Related CAF careers (career_ids)",
    )

    # Metadata extracted from page
    keywords: list[str] = Field(default_factory=list, description="Keywords from meta tags")
    description_meta: str | None = Field(default=None, description="Meta description from page head")

    # URLs for both languages
    url_en: str = Field(description="English career page URL")
    url_fr: str | None = Field(default=None, description="French career page URL")

    # Provenance
    provenance_en: CAFProvenance = Field(description="Provenance for English scrape")
    provenance_fr: CAFProvenance | None = Field(default=None, description="Provenance for French scrape")


class CAFScrapedPage(BaseModel):
    """Container for a complete CAF scrape result.

    Contains all career listings extracted from a scrape session,
    with metadata about the scrape itself.
    """

    language: str = Field(description="Language code: 'en' or 'fr'")
    scraped_at: datetime = Field(description="UTC timestamp when scraping occurred")
    source: str = Field(
        default="sitemap",
        description="Data source: 'sitemap', 'listing_page', 'individual_pages'",
    )
    careers: list[CAFCareerListing] = Field(description="Extracted career listings")
    career_count: int = Field(description="Number of careers extracted")
    scraper_version: str = Field(default="CAFScraper-1.0.0", description="Scraper version")


# Aliases for backward compatibility and convenience
CareerListing = CAFCareerListing
Occupation = CAFOccupation
Provenance = CAFProvenance
JobFamily = CAFJobFamily
