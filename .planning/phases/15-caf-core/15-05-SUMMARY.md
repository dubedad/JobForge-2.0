---
phase: 15-caf-core
plan: 05
subsystem: concordance
tags: [caf, job-architecture, fuzzy-matching, rapidfuzz, bridge-table, provenance]
requires:
  - phase: 15-03
    provides: dim_caf_occupation with related_civilian_occupations
provides:
  - CAFJAMatcher with two-level matching
  - bridge_caf_ja.parquet with JA context columns
  - caf_ja_mappings.json for human review
affects: [15-06, caf-query-api]
tech-stack:
  added: []
  patterns: [two-level-fuzzy-matching, ja-context-capture, audit-trail]
key-files:
  created:
    - src/jobforge/external/caf/matchers.py (JA section)
    - data/gold/bridge_caf_ja.parquet
    - data/reference/caf_ja_mappings.json
    - data/catalog/tables/bridge_caf_ja.json
    - tests/external/test_caf_ja_matcher.py
  modified:
    - src/jobforge/external/caf/__init__.py
    - src/jobforge/ingestion/caf.py
key-decisions:
  - "Optional JA context fields - job_function/job_family can be null in source data"
  - "Unified matchers.py for both NOC and JA matching"
patterns-established:
  - "Two-level matching: related_civilian first, then title_fuzzy"
  - "JA context capture (job_function, job_family) for filtering"
  - "Full audit trail with match_method, rationale, fuzzy_score"
metrics:
  duration: 21m
  completed: 2026-02-05
---

# Phase 15 Plan 05: CAF-JA Bridge Table Summary

**CAF-to-Job Architecture bridge with fuzzy matching, confidence scoring, and JA context (job_function, job_family) for career transition filtering**

## Performance

- **Duration:** 21 min
- **Started:** 2026-02-05T13:33:50Z
- **Completed:** 2026-02-05T13:55:00Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments
- CAFJAMatcher with two-level matching (related_civilian + title_fuzzy)
- 880 CAF-JA mappings across 88 CAF occupations with full audit trail
- JA context columns (job_function_en, job_family_en) for context filtering
- 19 tests for matcher, confidence scoring, FK relationships

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend/create matchers.py with JA matching** - `e0db79b` (feat)
2. **Task 2: Generate JA bridge table** - `3a32ec3` (feat)
3. **Task 3: Create catalog and tests for JA bridge** - `0e79dfb` (test)

## Files Created/Modified
- `src/jobforge/external/caf/matchers.py` - Added CAFJAMatcher, CAFJAMapping, match_caf_to_ja
- `src/jobforge/external/caf/__init__.py` - Export JA matcher classes
- `src/jobforge/ingestion/caf.py` - Added ingest_bridge_caf_ja function
- `data/gold/bridge_caf_ja.parquet` - 880 rows, 17 columns with JA context
- `data/reference/caf_ja_mappings.json` - Human-reviewable mapping file
- `data/catalog/tables/bridge_caf_ja.json` - Catalog metadata with FK relationships
- `tests/external/test_caf_ja_matcher.py` - 19 tests for JA matcher

## Decisions Made
| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Optional JA context fields | job_function/job_family can be None in JA table | Model allows Optional[str] |
| Unified matchers.py | Both NOC and JA matching in same file | Shared helpers, consistent patterns |
| Two-level matching | related_civilian occupations are more specific than CAF titles | Higher confidence from civilian match |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed pydantic validation for None JA context**
- **Found during:** Task 2 (bridge table generation)
- **Issue:** ja_job_function_en and ja_job_family_en can be None in job_architecture table
- **Fix:** Changed CAFJAMapping fields to Optional[str] = None
- **Files modified:** src/jobforge/external/caf/matchers.py
- **Committed in:** 3a32ec3 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Bug fix necessary for correctness with actual JA data. No scope creep.

## Issues Encountered
- 15-04 (CAF-NOC bridge) running in parallel modified __init__.py with NOC exports, requiring coordination
- Resolved by extending matchers.py with both NOC and JA sections

## Next Phase Readiness

### For Plan 06 (Integration Tests)
- bridge_caf_ja.parquet ready with FK relationships
- JA context columns enable filtering by job_function/job_family
- Full audit trail supports human review workflow

### Blockers
None.

### Recommendations
1. Plan 06 should validate FK integrity between bridge_caf_ja and dim_caf_occupation/job_architecture
2. Consider adding human-verified flag for reviewed mappings
3. JA context filtering enables career path analysis (e.g., "show me healthcare careers")

---
*Completed: 2026-02-05 13:55 UTC*
*Duration: 21m*
*Tests: 19 passing (806 + 19 = 825 total)*
