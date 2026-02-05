---
phase: 14-og-core
plan: 06
subsystem: concordance
tags: [rapidfuzz, fuzzy-matching, noc, occupational-groups, bridge-table]

# Dependency graph
requires:
  - phase: 14-03
    provides: dim_og and dim_og_subgroup dimension tables
  - phase: existing
    provides: dim_noc with 516 NOC unit groups
provides:
  - match_noc_to_og() function for NOC-OG fuzzy matching
  - build_bridge_noc_og() for generating bridge table
  - bridge_noc_og.parquet with 2486 ranked mappings
  - Catalog metadata for bridge table
affects: [jd-builder, classification-engine, future-og-lookups]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Fuzzy matching with confidence tiers (exact/high/medium/low)"
    - "Always-return-suggestion pattern for UX"
    - "Source attribution for audit trail"

key-files:
  created:
    - src/jobforge/concordance/__init__.py
    - src/jobforge/concordance/noc_og.py
    - tests/concordance/__init__.py
    - tests/concordance/test_noc_og.py
    - data/gold/bridge_noc_og.parquet
    - data/catalog/tables/bridge_noc_og.json
  modified: []

key-decisions:
  - "Use CT (Comptrollership) and PA (Program and Administrative Services) as test targets - actual TBS OG codes differ from plan assumptions"
  - "Confidence tiers: 1.0=exact (>=0.95), 0.85=high (>=0.90), 0.70=medium (>=0.80), 0.50=low (>=0.70)"
  - "Always return at least one suggestion, even for weak matches (best_guess attribution)"
  - "Bridge table generated on-demand, not committed (parquet gitignored)"

patterns-established:
  - "Concordance module pattern: match_X_to_Y() + build_bridge_X_Y()"
  - "NOCOGMatch Pydantic model with full provenance (source_attribution, rationale, matched_at)"
  - "Fuzzy matching uses max of ratio, token_sort_ratio, WRatio strategies"

# Metrics
duration: 10min
completed: 2026-02-05
---

# Phase 14-06: NOC-OG Concordance Summary

**Rapidfuzz-based NOC-to-OG mapping with confidence scoring, source attribution, and always-return-suggestion guarantee**

## Performance

- **Duration:** 10 min
- **Started:** 2026-02-05T07:12:02Z
- **Completed:** 2026-02-05T07:21:40Z
- **Tasks:** 3
- **Files created:** 6

## Accomplishments

- Created `match_noc_to_og()` function that maps any NOC code to ranked OG groups
- Implemented confidence tiers (exact/high/medium/low) based on fuzzy similarity
- Generated bridge_noc_og.parquet with 2486 rows covering all 516 NOC codes
- Full provenance: source_attribution, rationale text, matched_at timestamp
- Always returns at least one suggestion, even for obscure job titles

## Task Commits

TDD cycle with atomic commits:

1. **Task 1: RED - Write failing tests** - `0329d7f` (test)
2. **Task 2: GREEN - Implement concordance matching** - `6e908fc` (feat)
3. **Task 3: Build bridge table and catalog** - `bed02f1` (feat)

## Files Created/Modified

- `src/jobforge/concordance/__init__.py` - Module exports
- `src/jobforge/concordance/noc_og.py` - Core matching logic with match_noc_to_og() and build_bridge_noc_og()
- `tests/concordance/__init__.py` - Test package init
- `tests/concordance/test_noc_og.py` - 16 tests for matching and bridge table
- `data/gold/bridge_noc_og.parquet` - 2486 rows mapping 516 NOCs to OGs (gitignored, regenerated)
- `data/catalog/tables/bridge_noc_og.json` - Catalog metadata with FK relationships

## Decisions Made

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| CT/PA test targets | Plan assumed FI/AS OG codes, but actual TBS data uses different codes (CT=Comptrollership, PA=Program and Admin) | Tests updated to use real OG codes |
| Confidence tiers | RESEARCH.md specified thresholds for algorithmic matching | 0.95+=exact, 0.90+=high, 0.80+=medium, 0.70+=low |
| Best guess fallback | CONTEXT.md requires always providing suggestion | algorithmic_rapidfuzz_best_guess attribution for weak matches |
| Parquet gitignored | Generated data should be regenerated, not versioned | build_bridge_noc_og() called to regenerate |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test OG code assumptions**
- **Found during:** Task 2 (GREEN phase)
- **Issue:** Plan assumed "FI" and "AS" OG codes, but TBS data uses "CT" and "PA"
- **Fix:** Updated test expectations to match actual OG codes from dim_og.parquet
- **Files modified:** tests/concordance/test_noc_og.py
- **Verification:** All 16 tests now pass
- **Committed in:** 6e908fc (included in GREEN phase commit)

---

**Total deviations:** 1 auto-fixed (1 bug - incorrect test assumptions)
**Impact on plan:** Test data corrected to match reality. No scope creep.

## Issues Encountered

None - plan executed smoothly after fixing test assumptions.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 14 complete. All OG core tables built:
- dim_og (31 groups)
- dim_og_subgroup (111 subgroups)
- dim_og_qualifications (75 qualification standards)
- fact_og_pay_rates (991 pay rates)
- bridge_noc_og (2486 NOC-OG mappings)

Ready for Phase 15 (CAF Core) execution.

---
*Phase: 14-og-core*
*Completed: 2026-02-05*
