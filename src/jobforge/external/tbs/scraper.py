"""TBS Occupational Groups scraper with provenance tracking.

This module orchestrates the scraping of Treasury Board Secretariat
occupational groups pages, supporting both English and French content.
All scraped data carries full provenance information.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import requests
import structlog

from .link_fetcher import fetch_og_definition
from .models import OGDefinition, OGScrapedData, OGSubgroup, ScrapedPage
from .parser import extract_embedded_links, parse_occupational_groups_table, parse_og_subgroups

logger = structlog.get_logger(__name__)

# TBS Occupational Groups page URLs for both official languages
TBS_URLS = {
    "en": "https://www.canada.ca/en/treasury-board-secretariat/services/collective-agreements/occupational-groups.html",
    "fr": "https://www.canada.ca/fr/secretariat-conseil-tresor/services/conventions-collectives/groupes-professionnels.html",
}


class TBSScraper:
    """TBS Occupational Groups scraper with provenance tracking.

    Supports scraping both English and French pages, with automatic
    provenance tracking for all extracted data.

    Args:
        output_dir: Directory where JSON files will be saved.

    Example:
        scraper = TBSScraper()
        paths = scraper.scrape_and_save()
        # Creates: data/tbs/occupational_groups_en.json
        #          data/tbs/occupational_groups_fr.json
    """

    def __init__(self, output_dir: str | Path = "data/tbs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def scrape_page(self, language: str = "en", timeout: int = 30) -> ScrapedPage:
        """Scrape TBS occupational groups page for given language.

        Per CONTEXT.md: Fail loudly on structure changes.

        Args:
            language: Language code ('en' or 'fr').
            timeout: HTTP request timeout in seconds.

        Returns:
            ScrapedPage with all extracted rows and metadata.

        Raises:
            ValueError: If language not supported or page structure invalid.
            requests.RequestException: If HTTP request fails.
        """
        url = TBS_URLS.get(language)
        if not url:
            raise ValueError(f"Unsupported language: {language}. Use 'en' or 'fr'.")

        logger.info("scraping_tbs_page", url=url, language=language)

        response = requests.get(url, timeout=timeout)
        response.raise_for_status()

        scraped_at = datetime.now(timezone.utc)
        rows = parse_occupational_groups_table(response.text, url, scraped_at)

        links = extract_embedded_links(rows)
        link_count = sum(len(v) for v in links.values())

        logger.info(
            "scraped_tbs_page_success",
            language=language,
            row_count=len(rows),
            link_count=link_count,
        )

        return ScrapedPage(
            url=url,
            language=language,
            title=f"TBS Occupational Groups ({language.upper()})",
            scraped_at=scraped_at,
            rows=rows,
            link_count=link_count,
            row_count=len(rows),
        )

    def scrape_both_languages(self) -> dict[str, ScrapedPage]:
        """Scrape both English and French pages per CONTEXT.md.

        Returns:
            Dictionary with 'en' and 'fr' keys mapping to ScrapedPage objects.
        """
        return {
            "en": self.scrape_page("en"),
            "fr": self.scrape_page("fr"),
        }

    def save_to_json(self, page: ScrapedPage) -> Path:
        """Save scraped page to JSON file with provenance.

        Args:
            page: ScrapedPage to save.

        Returns:
            Path to the saved JSON file.
        """
        filename = f"occupational_groups_{page.language}.json"
        filepath = self.output_dir / filename

        # Convert to JSON-serializable format
        data = page.model_dump(mode="json")

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info("saved_scraped_data", filepath=str(filepath), row_count=page.row_count)
        return filepath

    def scrape_and_save(self) -> dict[str, Path]:
        """Scrape both languages and save to JSON files.

        Convenience method that performs full scrape workflow.

        Returns:
            Dictionary with 'en' and 'fr' keys mapping to saved file paths.
        """
        pages = self.scrape_both_languages()
        return {lang: self.save_to_json(page) for lang, page in pages.items()}

    def scrape_og_complete(self, language: str = "en", timeout: int = 30) -> OGScrapedData:
        """Scrape complete OG data including subgroups and definitions.

        Performs a comprehensive scrape that:
        1. Scrapes the main OG table for groups/rows
        2. Parses subgroup information from rows
        3. Follows unique definition URLs to fetch definition text

        Args:
            language: Language code ('en' or 'fr').
            timeout: HTTP request timeout in seconds.

        Returns:
            OGScrapedData with groups, subgroups, and definitions.

        Note:
            Definition fetching includes rate limiting (1.5s between requests).
            This may take several minutes for a full scrape.
        """
        # Step 1: Scrape main table
        page = self.scrape_page(language=language, timeout=timeout)
        scraped_at = page.scraped_at
        source_url = page.url

        logger.info(
            "scrape_og_complete_main_table",
            language=language,
            row_count=len(page.rows),
        )

        # Step 2: Parse subgroups from rows
        subgroups = parse_og_subgroups(page.rows, source_url, scraped_at)

        logger.info(
            "scrape_og_complete_subgroups_parsed",
            subgroup_count=len(subgroups),
        )

        # Step 3: Fetch definitions from unique URLs
        definitions: list[OGDefinition] = []
        seen_urls: set[str] = set()

        for row in page.rows:
            if row.definition_url and row.definition_url not in seen_urls:
                seen_urls.add(row.definition_url)

                # Determine if this is a subgroup definition
                subgroup_code = None
                if row.subgroup and row.subgroup.strip().upper() != "N/A":
                    # Try to extract subgroup code from subgroup text
                    if "(" in row.subgroup and ")" in row.subgroup:
                        code_start = row.subgroup.rfind("(") + 1
                        code_end = row.subgroup.rfind(")")
                        subgroup_code = row.subgroup[code_start:code_end].strip()

                definition = fetch_og_definition(
                    url=row.definition_url,
                    og_code=row.group_abbrev,
                    subgroup_code=subgroup_code,
                    timeout=timeout,
                )

                if definition:
                    definitions.append(definition)

        logger.info(
            "scrape_og_complete_definitions_fetched",
            definition_count=len(definitions),
            urls_attempted=len(seen_urls),
        )

        return OGScrapedData(
            groups=page.rows,
            subgroups=subgroups,
            definitions=definitions,
            scraped_at=datetime.now(timezone.utc),
            source_url=source_url,
        )

    def save_og_data(self, data: OGScrapedData, language: str = "en") -> dict[str, Path]:
        """Save OG scraped data to JSON files.

        Creates two files:
        - og_subgroups_{lang}.json: List of OGSubgroup objects
        - og_definitions_{lang}.json: List of OGDefinition objects

        Args:
            data: OGScrapedData containing subgroups and definitions.
            language: Language code for filename suffix.

        Returns:
            Dictionary with 'subgroups' and 'definitions' keys mapping to file paths.
        """
        paths = {}

        # Save subgroups
        subgroups_file = self.output_dir / f"og_subgroups_{language}.json"
        subgroups_data = [s.model_dump(mode="json") for s in data.subgroups]
        with open(subgroups_file, "w", encoding="utf-8") as f:
            json.dump(subgroups_data, f, indent=2, ensure_ascii=False)
        paths["subgroups"] = subgroups_file

        logger.info(
            "saved_og_subgroups",
            filepath=str(subgroups_file),
            count=len(data.subgroups),
        )

        # Save definitions
        definitions_file = self.output_dir / f"og_definitions_{language}.json"
        definitions_data = [d.model_dump(mode="json") for d in data.definitions]
        with open(definitions_file, "w", encoding="utf-8") as f:
            json.dump(definitions_data, f, indent=2, ensure_ascii=False)
        paths["definitions"] = definitions_file

        logger.info(
            "saved_og_definitions",
            filepath=str(definitions_file),
            count=len(data.definitions),
        )

        return paths

    def scrape_and_save_complete(self, language: str = "en") -> dict[str, Path]:
        """Scrape complete OG data and save to JSON files.

        Convenience method that performs full OG scrape workflow including
        subgroup parsing and definition fetching.

        Args:
            language: Language code ('en' or 'fr').

        Returns:
            Dictionary with file paths for saved data.

        Note:
            This may take several minutes due to rate limiting on definition fetches.
        """
        data = self.scrape_og_complete(language=language)
        return self.save_og_data(data, language=language)


def scrape_occupational_groups(
    output_dir: str | Path = "data/tbs",
    languages: list[str] | None = None,
) -> dict[str, Path]:
    """Scrape TBS pages and save to JSON.

    Convenience function for quick scraping without instantiating
    the scraper class directly.

    Args:
        output_dir: Directory where JSON files will be saved.
        languages: List of language codes to scrape. Defaults to ['en', 'fr'].

    Returns:
        Dictionary mapping language codes to saved file paths.

    Example:
        paths = scrape_occupational_groups()
        print(paths['en'])  # Path to English JSON file
    """
    scraper = TBSScraper(output_dir)
    languages = languages or ["en", "fr"]

    paths = {}
    for lang in languages:
        page = scraper.scrape_page(lang)
        paths[lang] = scraper.save_to_json(page)

    return paths
