---
phase: 14-og-core
plan: 07
subsystem: concordance
tags: [rapidfuzz, keyword-boosting, semantic-matching, noc-og]

# Dependency graph
requires:
  - phase: 14-06
    provides: NOC-OG concordance matching
provides:
  - Keyword-based semantic boosting for NOC-OG matching
  - Improved IT mapping for software-related NOCs
  - 7 new tests for keyword boosting
affects: [bridge_noc_og, jd-builder]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Keyword boosting for semantic matching gaps"
    - "Additive boost capped at 1.0"

key-files:
  created: []
  modified:
    - src/jobforge/concordance/noc_og.py
    - tests/concordance/test_noc_og.py

key-decisions:
  - "0.6 boost for IT keywords (software, developer, programmer, etc.)"
  - "0.5 boost for UT keywords (professor, lecturer, university)"
  - "0.4 boost for CT/HM keywords (financial, HR-related)"

patterns-established:
  - "KEYWORD_BOOSTS dict for semantic keyword -> OG code mapping"
  - "_get_keyword_boost() helper for clean separation"

# Metrics
duration: 5min
completed: 2026-02-05
---

# Phase 14 Plan 07: Keyword Boosting Fix Summary

**Added semantic keyword boosting to NOC-OG concordance to fix software developers mapping to Ship Repair instead of IT**

## Performance

- **Duration:** 5 min
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- Added KEYWORD_BOOSTS dict with semantic mappings for IT, CT, HM, UT, EC, TR, FS
- Created _get_keyword_boost() function for clean boost lookup
- Modified _compute_similarity() to apply additive boosting capped at 1.0
- Added 7 tests for keyword boosting functionality
- Rebuilt bridge_noc_og.parquet with improved mappings (2487 rows)

## Task Commits

1. **Task 1: Add keyword boosting** - `f3da24c` (feat)
2. **Task 2: Add tests** - `1d11392` (test)
3. **Task 3: Rebuild bridge table** - (regenerated, gitignored)

## Gap Closed

| Before | After |
|--------|-------|
| Software developers → Ship Repair (0.85) | Software developers → IT (0.92) |
| Pure fuzzy matching | Fuzzy + keyword boosting |

## Verification

All 23 concordance tests pass:
- 16 existing tests still pass
- 7 new keyword boosting tests pass

---
*Phase: 14-og-core*
*Completed: 2026-02-05*
