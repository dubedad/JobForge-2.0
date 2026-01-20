---
phase: "07"
plan: "03"
subsystem: external-data
tags: [tbs, scraper, provenance, bilingual, link-traversal]

dependency-graph:
  requires: []
  provides:
    - TBS scraper with bilingual support
    - Link fetcher for two-level deep traversal
    - DIM Occupations TBS schema extension
    - Scraped baseline data (EN/FR)
  affects:
    - 07-04 (LLM imputation may reference TBS metadata)
    - 08-xx (Gold layer will consume TBS fields)

tech-stack:
  added:
    - beautifulsoup4 (HTML parsing)
    - lxml (parser backend)
    - requests (HTTP client)
  patterns:
    - Pydantic models with full provenance
    - Bilingual validation (EN/FR column headers)
    - Polite scraping with REQUEST_DELAY_SECONDS
    - Error isolation (failures tracked, not raised)

key-files:
  created:
    - src/jobforge/external/__init__.py
    - src/jobforge/external/tbs/__init__.py
    - src/jobforge/external/tbs/models.py
    - src/jobforge/external/tbs/parser.py
    - src/jobforge/external/tbs/scraper.py
    - src/jobforge/external/tbs/link_fetcher.py
    - src/jobforge/external/tbs/schema.py
    - tests/test_tbs_scraper.py
    - data/tbs/occupational_groups_en.json
    - data/tbs/occupational_groups_fr.json
    - data/tbs/linked_metadata_en.json
    - data/tbs/linked_metadata_fr.json
  modified:
    - pyproject.toml (added dependencies)

decisions:
  - id: 07-03-D1
    decision: Use language-aware validation with separate column header lists
    rationale: TBS pages have French column headers; single validation would fail
  - id: 07-03-D2
    decision: Track unique URLs in link fetcher to avoid duplicate fetches
    rationale: Multiple rows may share same definition/standard pages
  - id: 07-03-D3
    decision: Store TBS fields as schema extension module, not in gold layer yet
    rationale: Gold layer is introspected from actual data; fields added when merged

metrics:
  duration: ~88 min
  completed: 2026-01-20
---

# Phase 07 Plan 03: TBS Scraper with Link Traversal Summary

**One-liner:** Bilingual TBS scraper with two-level deep link traversal extracting 217 occupational groups and 307 linked pages per language with full provenance.

## What Was Built

1. **TBS Package (`jobforge.external.tbs`)**
   - `models.py`: Pydantic models for scraped data with provenance
   - `parser.py`: HTML table parser with bilingual column validation
   - `scraper.py`: TBSScraper class with EN/FR support
   - `link_fetcher.py`: LinkMetadataFetcher for two-level traversal
   - `schema.py`: DIM Occupations TBS field definitions

2. **Scraped Data Files**
   - `occupational_groups_en.json`: 217 rows, 621 embedded links
   - `occupational_groups_fr.json`: 217 rows, 621 embedded links
   - `linked_metadata_en.json`: 307 unique pages fetched, 0 failures
   - `linked_metadata_fr.json`: 307 unique pages fetched, 0 failures

3. **Test Suite**
   - 32 tests covering parser, models, scraper, link fetcher, schema
   - All tests pass without network (mocked HTTP)
   - Integration tests available with `pytest -m integration`

## Provenance Implementation

Every scraped value carries:
- `source_url`: Where the data came from
- `scraped_at`: UTC timestamp
- `extraction_method`: How it was extracted (table_cell, linked_page_content)
- `page_title`: Title of the source page

## Schema Extension

10 fields defined for DIM_Occupations:
- `tbs_group_code`, `tbs_group_abbrev`, `tbs_group_name`
- `tbs_definition_url`, `tbs_definition_content`
- `tbs_job_eval_standard_url`, `tbs_job_eval_content`
- `tbs_qualification_standard_url`, `tbs_qualification_content`
- `tbs_scraped_at`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] French page validation failure**
- **Found during:** Task 2
- **Issue:** Parser used English column headers for French pages
- **Fix:** Added TBS_REQUIRED_COLUMNS_FR and language-aware validation
- **Files modified:** parser.py
- **Commit:** Part of 0f62724 (prior session)

## Commits

| Commit | Description |
|--------|-------------|
| ead24df | feat(07-03): create TBS models and HTML parser |
| 0f62724 | (included) TBS scraper and baseline data |
| 958d3c7 | feat(07-03): create link fetcher for embedded URL traversal |
| 7a880a3 | feat(07-03): add DIM Occupations TBS schema extension and tests |

## Verification Results

- [x] TBSScraper fetches EN and FR pages from canada.ca
- [x] Parser validates table structure and fails loudly on changes
- [x] All scraped values carry provenance (URL, timestamp, method)
- [x] Embedded links extracted (definitions, job eval, qualifications)
- [x] Embedded links FOLLOWED to fetch actual content (requirement SRC-02)
- [x] Linked page content parsed (title, main text, dates)
- [x] JSON files saved with full provenance metadata
- [x] DIM_Occupations schema extended with TBS fields including content
- [x] Tests pass with mocked HTML (no network dependency for CI)

## Next Phase Readiness

**Ready for:** 07-04 (LLM Imputation)
- TBS metadata available for context enrichment
- Provenance infrastructure established for LLM outputs
- No blockers identified

---
*Generated: 2026-01-20*
