---
phase: 14-og-core
plan: 03
subsystem: database
tags: [polars, parquet, medallion-architecture, occupational-groups, tbs]

# Dependency graph
requires:
  - phase: 14-01
    provides: "Scraped OG JSON files (occupational_groups_en.json, og_subgroups_en.json)"
provides:
  - "dim_og gold table (31 occupational groups)"
  - "dim_og_subgroup gold table (111 subgroups with FK to dim_og)"
  - "ingest_dim_og() and ingest_dim_og_subgroup() pipeline functions"
  - "Catalog metadata for both OG tables"
  - "22 tests for OG ingestion and FK validation"
affects: [14-04, og-concordance, text-to-sql]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Custom JSON loading for nested TBS data structures"
    - "FK validation with orphan removal in silver layer"

key-files:
  created:
    - src/jobforge/ingestion/og.py
    - data/catalog/tables/dim_og.json
    - data/catalog/tables/dim_og_subgroup.json
    - tests/test_og_ingestion.py
  modified: []

key-decisions:
  - "31 unique groups extracted from 217 rows (plan estimated 65)"
  - "111 unique subgroups from 130 records (plan estimated ~200)"
  - "Custom JSON parser for nested occupational_groups_en.json structure"
  - "FK validation removes orphan subgroups with invalid og_code"
  - "Provenance columns include _source_url, _scraped_at, _ingested_at, _batch_id, _layer"

patterns-established:
  - "OG ingestion pattern: load JSON, extract unique, normalize, dedupe, validate"

# Metrics
duration: 16min
completed: 2026-02-05
---

# Phase 14 Plan 03: OG Gold Tables Summary

**Medallion ingestion pipelines for dim_og (31 groups) and dim_og_subgroup (111 subgroups) with FK validation and full provenance**

## Performance

- **Duration:** 16 min
- **Started:** 2026-02-05T06:31:37Z
- **Completed:** 2026-02-05T06:47:04Z
- **Tasks:** 3
- **Files created:** 4

## Accomplishments

- Created ingest_dim_og() pipeline extracting 31 unique occupational groups from TBS JSON
- Created ingest_dim_og_subgroup() pipeline with FK validation against dim_og
- Added catalog metadata files for both tables with relationship definitions
- Implemented 22 tests covering transforms, ingestion, FK validation, and production data

## Task Commits

Each task was committed atomically:

1. **Task 1: Create dim_og ingestion pipeline** - `bb36634` (feat)
2. **Task 2: Create dim_og_subgroup ingestion pipeline** - (included in Task 1 commit)
3. **Task 3: Create catalog metadata and tests** - `0fdcd81` (test)

_Note: Task 2 function was included in the same og.py file as Task 1, so both were committed together._

## Files Created/Modified

- `src/jobforge/ingestion/og.py` - Medallion ingestion pipelines for dim_og and dim_og_subgroup
- `data/catalog/tables/dim_og.json` - Catalog metadata for 31 occupational groups
- `data/catalog/tables/dim_og_subgroup.json` - Catalog metadata for 111 subgroups
- `tests/test_og_ingestion.py` - 22 tests for transforms, ingestion, and FK validation

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| 31 unique groups (not 65) | Actual data had 217 rows with duplicates; only 31 distinct group_abbrev values |
| 111 unique subgroups (not ~200) | Actual og_subgroups_en.json had 130 records with 111 unique subgroup_codes |
| Custom JSON parser | Source JSON has nested structure (rows array with provenance), not NDJSON |
| Clean group names | Remove "(AS)" suffix from "Administrative Services(AS)" for cleaner display |
| FK validation optional | validate_fk=False parameter allows ingestion without dim_og dependency |
| Provenance from source JSON | Extract _source_url and _scraped_at from source metadata |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected row count estimates**
- **Found during:** Task 1 (dim_og creation)
- **Issue:** Plan stated 65 occupational groups; actual data has 31 unique groups
- **Fix:** Updated catalog metadata and tests to reflect actual counts
- **Impact:** None - correct data captured

**2. [Rule 1 - Bug] Corrected subgroup count estimate**
- **Found during:** Task 2 (dim_og_subgroup creation)
- **Issue:** Plan stated ~200 subgroups; actual data has 111 unique subgroups
- **Fix:** Updated catalog metadata and tests to reflect actual counts
- **Impact:** None - correct data captured

**3. [Rule 3 - Blocking] Custom JSON loading for nested structure**
- **Found during:** Task 1 (data loading)
- **Issue:** Source JSON has nested "rows" array with "provenance" objects; scan_ndjson fails
- **Fix:** Created _load_occupational_groups_json() and _load_og_subgroups_json() helpers
- **Impact:** Minimal - follows pattern of handling source-specific structures

---

**Total deviations:** 3 auto-fixed (2 bugs/estimates, 1 blocking)
**Impact on plan:** All deviations were necessary corrections. Data quality is correct.

## Issues Encountered

None - pipeline executed successfully after addressing data structure differences.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- dim_og and dim_og_subgroup tables ready for queries
- FK relationship validated (all subgroup og_codes exist in dim_og)
- Ready for 14-04 (if exists) or future OG-NOC concordance work
- Tables available for text-to-SQL queries via DuckDB

---
*Phase: 14-og-core*
*Completed: 2026-02-05*
