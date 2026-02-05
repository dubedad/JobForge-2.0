---
phase: 14-og-core
plan: 05
subsystem: ingestion
tags: [polars, qualification-standards, tbs, regex-parsing, full-text-search, gold-tables]

# Dependency graph
requires:
  - phase: 14-og-core-02
    provides: TBS qualification text data (og_qualification_text.json)
provides:
  - dim_og_qualifications gold table with structured and full-text fields
  - parse_qualification_text() for extracting structured qualification fields
  - Catalog metadata for dim_og_qualifications
affects: [jd-builder-lite, text-search, qualification-queries]

# Tech tracking
tech-stack:
  added: []
  patterns: [structured-text-extraction, soft-fk-validation, explicit-schema-typing]

key-files:
  created:
    - src/jobforge/ingestion/og_qualifications.py
    - data/catalog/tables/dim_og_qualifications.json
    - tests/test_og_qualifications_ingestion.py
  modified: []

key-decisions:
  - "Soft FK validation - log warnings but preserve all records"
  - "Explicit DataFrame schema for nullable column handling"
  - "100% structured extraction success from TBS text"

patterns-established:
  - "Structured text extraction with regex patterns"
  - "Preserve full_text alongside parsed fields for full-text search"
  - "Soft FK validation when parent table may not exist yet"

# Metrics
duration: 24min
completed: 2026-02-05
---

# Phase 14 Plan 05: Qualification Standards Summary

**dim_og_qualifications gold table with 75 records - structured fields extracted + full text for search**

## Performance

- **Duration:** 24 min
- **Started:** 2026-02-05T06:34:01Z
- **Completed:** 2026-02-05T06:58:09Z
- **Tasks:** 3
- **Files created:** 3

## Accomplishments

- Created parse_qualification_text() with regex patterns for TBS qualification sections
- Built ingest_dim_og_qualifications() medallion pipeline
- Extracted structured fields from 75/75 records (100% success rate)
- Created catalog metadata with column descriptions and FK relationships
- Added 23 comprehensive tests covering parsing, transforms, and ingestion

## Task Commits

Each task was committed atomically:

1. **Task 1: Create qualification text parser** - `de45cc0` (feat)
2. **Task 2: Create dim_og_qualifications ingestion pipeline** - (verification only, code in Task 1)
3. **Task 3: Create catalog metadata and tests** - `fd333aa` (feat)

## Files Created

- `src/jobforge/ingestion/og_qualifications.py` - Qualification parsing and ingestion module (407 lines)
  - parse_qualification_text() - Extract education, experience, certification, language requirements
  - normalize_qualification_codes() - Handle null subgroup codes gracefully
  - validate_og_exists() - Soft FK validation with warning logging
  - ingest_dim_og_qualifications() - Full medallion pipeline
- `data/catalog/tables/dim_og_qualifications.json` - Catalog metadata with FK relationships
- `tests/test_og_qualifications_ingestion.py` - 23 tests for parser and ingestion

## Data Output

- `data/gold/dim_og_qualifications.parquet` - 75 rows, 15 columns
- Structured fields extracted:
  - education_requirement (populated in all 75 records)
  - experience_requirement (populated in all 75 records)
  - certification_requirement (populated in all 75 records)
  - language_requirement (available when present in source)
  - other_requirements (available when present in source)
- full_text preserved for full-text search capability
- Provenance columns: _source_url, _source_file, _extracted_at, _ingested_at, _batch_id, _layer

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Soft FK validation | Allow ingestion even if dim_og not yet created; log warnings for orphan og_codes |
| Explicit DataFrame schema | Polars requires explicit String type when all values may be null |
| 100% structured extraction | Regex patterns successfully extract common TBS qualification sections |
| Preserve full_text always | Enables full-text search for queries like "find OGs requiring Master's degree" |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Null handling in normalize_qualification_codes**
- **Found during:** Task 3 testing
- **Issue:** Polars string operations fail when column has all null values
- **Fix:** Use pl.when().then().otherwise() for conditional string operations
- **Files modified:** src/jobforge/ingestion/og_qualifications.py
- **Commit:** fd333aa

**2. [Rule 1 - Bug] DataFrame schema inference with nulls**
- **Found during:** Task 3 testing
- **Issue:** Polars infers Null type when all column values are None
- **Fix:** Specify explicit schema with pl.Utf8 types when creating DataFrame
- **Files modified:** src/jobforge/ingestion/og_qualifications.py
- **Commit:** fd333aa

---

**Total deviations:** 2 bug fixes (Polars null handling)
**Impact on plan:** None - fixes enable correct operation

## FK Validation Results

During ingestion:
- 1 og_code orphan detected: SR (not in dim_og)
- Warning logged but record preserved (soft validation)
- This is expected - the qualification data references more OG codes than are in the current dim_og

## Issues Encountered

None - execution proceeded smoothly after null handling fixes.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- dim_og_qualifications ready for JD Builder Lite queries
- Full-text search capability via full_text column
- Structured fields enable filtering (e.g., "OGs requiring Master's degree")
- FK relationship to dim_og documented in catalog

---
*Phase: 14-og-core*
*Completed: 2026-02-05*
