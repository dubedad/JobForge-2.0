---
phase: 16-extended-metadata
plan: 02
subsystem: data-pipeline
tags: [scraper, beautifulsoup, polars, pydantic, tbs, job-evaluation, parquet]

# Dependency graph
requires:
  - phase: 14-og-scraping
    provides: TBS scraper patterns and occupational_groups_en.json
provides:
  - TBS job evaluation standards scraper (evaluation_scraper.py)
  - dim_og_job_evaluation_standard gold table with 145 records
  - 16 classification standards + 129 evaluation factors with points
  - Catalog metadata for job evaluation standards
affects: [16-extended-metadata, wiq-schema]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Multi-table parsing (weighting + degree tables)"
    - "OG code extraction from TBS URLs"
    - "Factor points and percentage extraction"

key-files:
  created:
    - src/jobforge/external/tbs/evaluation_scraper.py
    - src/jobforge/ingestion/og_evaluation.py
    - data/tbs/og_evaluation_standards.json
    - data/catalog/tables/dim_og_job_evaluation_standard.json
    - tests/external/tbs/test_evaluation_scraper.py
    - tests/ingestion/test_og_evaluation.py
  modified: []

key-decisions:
  - "Extract OG codes from TBS URLs using pattern mapping (information-technology -> IT)"
  - "Parse both factor weighting tables (max points) and degree tables (level points)"
  - "Soft FK validation - log warnings but preserve all records"
  - "UNKNOWN OG code for generic standards (#jes-nee links)"

patterns-established:
  - "Multi-table HTML parsing: detect table type from headers, dispatch to appropriate parser"
  - "URL-to-OG mapping: pattern-based extraction from TBS job evaluation URLs"

# Metrics
duration: 31min
completed: 2026-02-05
---

# Phase 16 Plan 02: Job Evaluation Standards Summary

**TBS job evaluation standards scraper and gold table with 145 records across 16 OG codes, extracting 129 evaluation factors with numeric points where available**

## Performance

- **Duration:** 31 min
- **Started:** 2026-02-05T16:25:03Z
- **Completed:** 2026-02-05T16:56:00Z
- **Tasks:** 3
- **Files created:** 6

## Accomplishments

- Created evaluation_scraper.py with EvaluationStandard Pydantic model
- Scraped 16 unique TBS job evaluation standard pages
- Extracted 145 records: 16 classification standards + 129 evaluation factors
- Parsed factor weighting tables (percentage, max points)
- Parsed factor degree tables (level descriptions, level points)
- Created medallion ingestion pipeline with soft FK validation
- Added 37 tests (22 scraper + 15 ingestion)
- Per-record source URLs to TBS authority

## Task Commits

Each task was committed atomically:

1. **Task 1: Create job evaluation standards scraper** - `fb10aaa` (feat)
2. **Task 2: Create evaluation standards ingestion pipeline** - `fae7ae9` (feat)
3. **Task 3: Create catalog metadata for evaluation standards** - `7b58b88` (docs)

## Files Created

- `src/jobforge/external/tbs/evaluation_scraper.py` - TBS job evaluation standards scraper
- `src/jobforge/ingestion/og_evaluation.py` - Medallion pipeline for dim_og_job_evaluation_standard
- `data/tbs/og_evaluation_standards.json` - 145 scraped records with provenance
- `data/gold/dim_og_job_evaluation_standard.parquet` - Gold table (gitignored)
- `data/catalog/tables/dim_og_job_evaluation_standard.json` - Catalog metadata
- `tests/external/tbs/test_evaluation_scraper.py` - 22 tests for scraper
- `tests/ingestion/test_og_evaluation.py` - 15 tests for ingestion

## Decisions Made

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| URL-based OG code extraction | TBS URLs follow predictable patterns (e.g., information-technology -> IT) | Mapping dict handles 15+ URL patterns |
| Multi-table parsing | TBS pages have both weighting tables (summary) and degree tables (detail) | Dual parser captures both data types |
| Soft FK validation | Some OG codes (UNKNOWN, GENERIC) not in dim_og | Log warnings, preserve all records |
| Factor points vs level points | Weighting tables have max points, degree tables have level-specific points | Separate columns for each |

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- **Unicode encoding in console output:** Windows cp1252 codec couldn't display some characters. Worked around by setting UTF-8 encoding.
- **Polars schema for nullable columns:** Tests needed explicit schema definition for nullable String columns. Fixed by adding schema parameter to pl.DataFrame().

## Data Statistics

| Metric | Value |
|--------|-------|
| Total records | 145 |
| Classification standards | 16 |
| Evaluation factors | 129 |
| Unique OG codes | 16 |
| Factors with max points | 46 |
| TBS pages scraped | 16 |

**OG codes covered:** EC, ED, FB, FI, FS, IT, LC, LP, MT, ND, NU, PO, PS, SW, UNKNOWN, WP

## Next Phase Readiness

- dim_og_job_evaluation_standard.parquet ready for WiQ schema integration
- Catalog metadata enables query routing
- Per-record _source_url enables provenance queries
- Tests passing (37 total)

---
*Phase: 16-extended-metadata*
*Plan: 02*
*Completed: 2026-02-05*
