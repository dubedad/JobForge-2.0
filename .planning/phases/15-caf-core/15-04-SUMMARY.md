---
phase: 15-caf-core
plan: 04
subsystem: concordance
tags: [caf, noc, fuzzy-matching, bridge-table, rapidfuzz, audit-trail]
requires: [15-03]
provides: [bridge-caf-noc, caf-noc-matcher]
affects: []
tech-stack:
  added: []
  patterns: [fuzzy-matching, confidence-scoring, audit-trail]
key-files:
  created:
    - src/jobforge/external/caf/matchers.py
    - data/catalog/tables/bridge_caf_noc.json
    - data/reference/caf_noc_mappings.json
    - tests/external/test_caf_matchers.py
  modified:
    - src/jobforge/external/caf/__init__.py
    - src/jobforge/ingestion/caf.py
decisions:
  - name: Hybrid matching strategy
    rationale: related_civilian_occupations more reliable than title-only matching
    outcome: related_civilian matches get same confidence but prioritized in sorting
  - name: 10 matches per CAF occupation
    rationale: Provide comprehensive options for career transition planning
    outcome: 880 total mappings for 88 CAF occupations
  - name: JSON for human review
    rationale: Enable manual verification and correction of automated matches
    outcome: caf_noc_mappings.json groups matches by CAF occupation
metrics:
  duration: 25m 31s
  completed: 2026-02-05
---

# Phase 15 Plan 04: CAF-NOC Bridge Table Summary

CAF-to-NOC bridge table with fuzzy matching using rapidfuzz; 880 mappings across 88 CAF occupations with full audit trail including confidence scores, match methods, and rationale.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Create CAF-NOC matcher module | 086a481 | matchers.py, __init__.py |
| 2 | Generate bridge table and reference mappings | 2675331 | caf.py, bridge_caf_noc.parquet, caf_noc_mappings.json |
| 3 | Create catalog and tests for bridge | 7123237 | bridge_caf_noc.json, test_caf_matchers.py |

## Implementation Details

### CAFNOCMatcher (matchers.py)

Following existing concordance/noc_og.py patterns:

- **Hybrid matching**: Uses related_civilian_occupations first, then falls back to title matching
- **rapidfuzz token_sort_ratio**: Best score from multiple strategies (ratio, token_sort, WRatio)
- **Confidence tiers**: 1.0=exact (>=0.95), 0.85=high (>=0.90), 0.70=medium (>=0.80), 0.50=low (<0.80)
- **Best guess fallback**: Always returns at least one match per CONTEXT.md requirement

### CAFNOCMapping Model

Full audit trail per plan requirements:
- `confidence_score`: Confidence tier (0.0-1.0)
- `match_method`: related_civilian, title_fuzzy, or best_guess
- `algorithm_version`: caf_matcher_v1.0
- `fuzzy_score`: Raw similarity score from rapidfuzz
- `matched_text`: The text that was matched
- `rationale`: Human-readable explanation

### Bridge Table (bridge_caf_noc.parquet)

| Metric | Value |
|--------|-------|
| Rows | 880 |
| CAF occupations | 88 |
| Matches per occupation | ~10 (ranked by confidence) |
| Columns | 15 |
| File size | 37.8 KB |

### Reference JSON (caf_noc_mappings.json)

Human-reviewable format for verification workflow:
- Grouped by CAF occupation
- Each occupation shows ranked NOC matches
- Includes confidence, method, and rationale for each

### Test Coverage

27 tests covering:
- Helper functions (similarity, confidence tiers) - 9 tests
- CAFNOCMapping model - 2 tests
- CAFNOCMatcher class - 9 tests
- Convenience function - 2 tests
- FK relationships - 2 tests
- Confidence scoring - 2 tests
- Integration test - 1 test

## Verification Results

| Check | Status |
|-------|--------|
| `from jobforge.external.caf import CAFNOCMatcher, match_caf_to_noc` | PASS |
| `pytest tests/external/test_caf_matchers.py -v` | 27/27 PASS |
| `ls data/gold/bridge_caf_noc.parquet` | EXISTS (37.8 KB) |
| Audit trail columns (confidence_score, match_method, algorithm_version, rationale) | ALL PRESENT |
| caf_noc_mappings.json for human review | EXISTS (426.6 KB) |

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

### For Future Plans

- bridge_caf_noc enables CAF-to-civilian career pathway queries
- caf_noc_mappings.json available for human verification workflow
- Pattern established for future bridge tables (CAF-JA)

### Blockers

None.

### Recommendations

1. Consider adding human-verified flag to distinguish manual corrections
2. Bridge table enables queries like "Find civilian jobs for Infantry Officer"
3. Confidence filtering allows users to tune precision/recall tradeoff

---
*Completed: 2026-02-05 13:58 UTC*
*Duration: 25m 31s*
*Tests: 27 passing (806 + 27 = 833 total)*
