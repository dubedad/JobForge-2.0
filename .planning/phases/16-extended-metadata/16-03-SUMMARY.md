---
phase: 16-extended-metadata
plan: 03
subsystem: database
tags: [polars, pydantic, beautifulsoup, scraping, pay-rates, collective-agreements]

# Dependency graph
requires:
  - phase: 14-og-core
    provides: fact_og_pay_rates.parquet with excluded employee pay rates
provides:
  - dim_collective_agreement.parquet - 28 collective agreements with metadata
  - Extended fact_og_pay_rates.parquet - 6,765 pay rates (excluded + represented)
  - Collective agreement FK linking represented rates to agreements
  - is_represented flag distinguishing unionized vs excluded employees
affects: [16-extended-metadata, wiq-queries, pay-intelligence]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Collective agreement metadata scraping from TBS index table
    - Pay rate extraction from collective agreement annexes (steps-as-columns format)
    - Medallion pipeline extension (merge excluded + represented)

key-files:
  created:
    - src/jobforge/external/tbs/represented_pay_scraper.py
    - src/jobforge/ingestion/og_represented_pay.py
    - data/catalog/tables/dim_collective_agreement.json
    - data/tbs/og_represented_pay_rates.json
    - tests/external/tbs/test_represented_pay_scraper.py
    - tests/ingestion/test_og_represented_pay.py
  modified:
    - data/catalog/tables/fact_og_pay_rates.json

key-decisions:
  - "Scrape collective agreement metadata from TBS index table (not individual pages)"
  - "Extract pay rates from table captions containing classification levels (e.g., EC-01)"
  - "Cast _ingested_at to string to align excluded and represented schemas before concat"
  - "28 collective agreements (TBS publishes fewer than estimated 30)"

patterns-established:
  - "Table caption extraction: Classification levels in <caption> elements"
  - "Schema alignment: Cast mismatched Datetime/String columns before polars concat"

# Metrics
duration: 58min
completed: 2026-02-05
---

# Phase 16 Plan 03: Represented Pay Rates Summary

**Extended fact_og_pay_rates with 5,774 represented (unionized) pay rates from 28 collective agreements, linked via FK to new dim_collective_agreement dimension table**

## Performance

- **Duration:** 58 min
- **Started:** 2026-02-05T16:09:37Z
- **Completed:** 2026-02-05T19:07:03Z
- **Tasks:** 3 (Task 1 already done in prior session)
- **Files created:** 6
- **Files modified:** 1

## Accomplishments

- Scraped 28 collective agreements with metadata (name, bargaining agent, signing/expiry dates)
- Extracted 9,174 raw represented pay rates from collective agreement annexes
- Extended fact_og_pay_rates to 6,765 unique rows (991 excluded + 5,774 represented after dedup)
- Linked all represented rates to collective agreements via FK
- Added is_represented flag to distinguish excluded vs unionized employees
- Added pay_progression_type column for step/performance/hybrid progression
- Captured 126 unique effective dates (full historical coverage)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create collective agreement scraper** - `2044f0f` (already done in prior session as part of 16-04)
2. **Task 2: Create represented pay rates scraper** - `9e520e1` (feat)
3. **Task 3: Extend fact_og_pay_rates and create dim_collective_agreement** - `61a0152` (feat)

## Files Created/Modified

- `src/jobforge/external/tbs/represented_pay_scraper.py` - Scrape pay rates from collective agreement pages
- `src/jobforge/ingestion/og_represented_pay.py` - Medallion pipeline for dim_collective_agreement and extending fact_og_pay_rates
- `data/catalog/tables/dim_collective_agreement.json` - Catalog metadata for collective agreements dimension
- `data/catalog/tables/fact_og_pay_rates.json` - Updated with new columns (collective_agreement_id, pay_progression_type)
- `data/tbs/og_represented_pay_rates.json` - 9,174 scraped represented pay rates
- `tests/external/tbs/test_represented_pay_scraper.py` - 26 tests for represented pay scraper
- `tests/ingestion/test_og_represented_pay.py` - 12 tests for ingestion pipeline

## Decisions Made

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Scrape collective agreements from index table | TBS index page has all metadata (bargaining agent, dates) in single HTML table | 28 agreements extracted without following individual agreement links |
| Extract classification from table captions | EC-01 style levels appear in `<caption>` elements, not headers | Reliable extraction of classification levels |
| Cast _ingested_at to string | Excluded parquet has Datetime, represented has String; Polars concat requires matching schemas | Concat works, preserves all provenance data |
| 28 collective agreements (not 30+) | TBS publishes 28 collective agreements in current index | Adjusted expectation from plan's "30+" estimate |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed schema mismatch between excluded and represented DataFrames**
- **Found during:** Task 3 (Extend fact_og_pay_rates)
- **Issue:** Polars concat failed due to _ingested_at being Datetime in excluded but String in represented
- **Fix:** Cast _ingested_at to String in excluded_df before concat
- **Files modified:** src/jobforge/ingestion/og_represented_pay.py
- **Verification:** Ingestion completes successfully, all 6,765 rows preserved
- **Committed in:** 61a0152

**2. [Rule 3 - Blocking] Fixed step column type mismatch (Int64 vs Int32)**
- **Found during:** Task 3 (Extend fact_og_pay_rates)
- **Issue:** Excluded parquet has step as Int32, represented DataFrame has Int64
- **Fix:** Cast step to Int32 in represented_df before concat
- **Files modified:** src/jobforge/ingestion/og_represented_pay.py
- **Verification:** Concat succeeds without type errors
- **Committed in:** 61a0152

---

**Total deviations:** 2 auto-fixed (both blocking issues)
**Impact on plan:** Minor schema alignment required. No scope creep.

## Issues Encountered

- Some collective agreement pages have no pay rate tables (0 rows extracted) - these are operational agreements without pay annexes
- Regional pay differentials not found in TBS data - pay rates appear nationally uniform per RESEARCH.md Open Question 5

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for:**
- Phase 16-04 (OG Allowances) - already has collective agreement context
- Phase 16-05 (CAF Training) - independent of pay rates
- WiQ queries combining excluded and represented pay data

**Data available:**
- 28 collective agreements with bargaining agents and expiry dates
- 6,765 pay rates (both excluded and represented)
- Full historical rates (126 effective dates)
- FK from pay rates to collective agreements

**Blockers/concerns:**
- None

---
*Phase: 16-extended-metadata*
*Completed: 2026-02-05*
