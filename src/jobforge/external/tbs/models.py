"""Pydantic models for TBS scraped data with full provenance.

These models ensure type safety and validation for all data scraped from
Treasury Board Secretariat pages, including occupational group tables
and linked metadata pages.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ScrapedProvenance(BaseModel):
    """Provenance information for any scraped value.

    Every piece of scraped data must carry its origin information
    for audit and traceability purposes.
    """

    source_url: str = Field(description="URL from which data was scraped")
    scraped_at: datetime = Field(description="UTC timestamp when scraping occurred")
    extraction_method: str = Field(
        description="How the value was extracted: 'table_cell', 'link_href', 'link_text', 'linked_page_content'"
    )
    page_title: str = Field(description="Title of the source page")


class OccupationalGroupRow(BaseModel):
    """Single row from TBS occupational groups table.

    Represents one occupational group with its metadata and links
    to definition, evaluation, and qualification standard pages.
    """

    group_abbrev: str = Field(description="Group abbreviation (e.g., 'AI', 'CR')")
    group_code: str = Field(description="Numeric code for the group")
    group_name: str = Field(description="Full occupational group name")
    subgroup: str | None = Field(default=None, description="Subgroup if applicable")
    definition_url: str | None = Field(default=None, description="Link to definition page")
    job_eval_standard_url: str | None = Field(
        default=None, description="Link to job evaluation standard"
    )
    qualification_standard_url: str | None = Field(
        default=None, description="Link to qualification standard"
    )
    provenance: ScrapedProvenance = Field(description="Provenance for this row")


class ScrapedPage(BaseModel):
    """Container for complete page scrape result.

    Contains all rows extracted from the occupational groups table
    plus metadata about the scrape itself.
    """

    url: str = Field(description="URL that was scraped")
    language: str = Field(description="Language code: 'en' or 'fr'")
    title: str = Field(description="Page title")
    scraped_at: datetime = Field(description="UTC timestamp when scraping occurred")
    rows: list[OccupationalGroupRow] = Field(description="Extracted table rows")
    link_count: int = Field(description="Number of embedded links found")
    row_count: int = Field(description="Number of data rows extracted")


class LinkedPageContent(BaseModel):
    """Content extracted from a linked page (definition, qual standard, etc.).

    TBS pages typically contain structured content with titles, main body text,
    and metadata about effective dates and modifications.
    """

    title: str = Field(description="Page title (from h1 or title tag)")
    main_content: str = Field(description="Primary content text (definition, standard text)")
    effective_date: str | None = Field(default=None, description="Effective date if present")
    last_modified: str | None = Field(default=None, description="Page last modified date")


class LinkedPageMetadata(BaseModel):
    """Metadata fetched from an embedded link.

    Tracks the result of following a link from the main table,
    including success/failure status and extracted content.
    """

    group_abbrev: str = Field(description="Parent group abbreviation")
    link_type: str = Field(
        description="Type of link: 'definition', 'job_eval_standard', 'qualification_standard'"
    )
    url: str = Field(description="URL that was fetched")
    content: LinkedPageContent | None = Field(
        default=None, description="Extracted content, None if fetch failed"
    )
    fetch_status: str = Field(description="Status: 'success', 'failed', or 'not_found'")
    error_message: str | None = Field(default=None, description="Error message if fetch failed")
    provenance: ScrapedProvenance = Field(description="Provenance for this fetch")


class LinkedMetadataCollection(BaseModel):
    """Collection of all linked page metadata for a language.

    Aggregates results from following all embedded links in the
    occupational groups table, with summary statistics.
    """

    language: str = Field(description="Language code: 'en' or 'fr'")
    fetched_at: datetime = Field(description="UTC timestamp when fetching completed")
    total_links: int = Field(description="Total number of links attempted")
    successful_fetches: int = Field(description="Number of successful fetches")
    failed_fetches: int = Field(description="Number of failed fetches")
    metadata: list[LinkedPageMetadata] = Field(description="Results for each link")


# Alias for backward compatibility
OGRow = OccupationalGroupRow


class OGSubgroup(BaseModel):
    """Structured subgroup data parsed from TBS occupational groups table.

    Represents a single subgroup within an occupational group with
    its code, name, and related URLs. Separated from OGRow for
    cleaner data modeling and downstream processing.
    """

    og_code: str = Field(description="Parent group abbreviation (e.g., 'AS', 'AI')")
    subgroup_code: str = Field(description="Full subgroup code (e.g., 'AS-01', 'AI-NOP')")
    subgroup_name: str = Field(description="Subgroup name extracted from parentheses")
    definition_url: str | None = Field(default=None, description="Link to subgroup definition page")
    qualification_standard_url: str | None = Field(
        default=None, description="Link to qualification standard"
    )
    rates_of_pay_url: str | None = Field(default=None, description="Link to pay rates page")
    source_url: str = Field(description="TBS page URL from which data was scraped")
    scraped_at: datetime = Field(description="UTC timestamp when scraping occurred")


class OGDefinition(BaseModel):
    """Definition text extracted from a TBS linked page.

    Contains the definition content for an occupational group or
    subgroup, with full provenance tracking.
    """

    og_code: str = Field(description="Parent group abbreviation (e.g., 'AS', 'AI')")
    subgroup_code: str | None = Field(
        default=None, description="Subgroup code if this is a subgroup definition, None for parent OG"
    )
    definition_text: str = Field(description="Full definition text extracted from linked page")
    page_title: str = Field(description="Title of the source page")
    source_url: str = Field(description="URL of the definition page")
    scraped_at: datetime = Field(description="UTC timestamp when definition was fetched")


class OGScrapedData(BaseModel):
    """Container for complete OG scrape result including subgroups and definitions.

    Aggregates all occupational group data from a full scrape session,
    including groups, subgroups, and fetched definitions with provenance.
    """

    groups: list[OccupationalGroupRow] = Field(description="All rows from main OG table")
    subgroups: list[OGSubgroup] = Field(description="Parsed subgroup data")
    definitions: list[OGDefinition] = Field(description="Fetched definition content")
    scraped_at: datetime = Field(description="UTC timestamp when scrape completed")
    source_url: str = Field(description="Main TBS page URL")
