---
phase: 06-imputation-foundation
plan: 01
title: NOC Resolution Service
subsystem: imputation
tags: [noc, resolution, fuzzy-matching, pydantic, rapidfuzz]

dependency_graph:
  requires: [05-gold-layer]
  provides: [noc-resolution-service, imputation-models, confidence-framework]
  affects: [06-02, 06-03, 07-onet-api]

tech_stack:
  added: [rapidfuzz>=3.0.0]
  patterns: [lru_cache-indexing, resolution-cascade, confidence-scoring]

key_files:
  created:
    - src/jobforge/imputation/__init__.py
    - src/jobforge/imputation/models.py
    - src/jobforge/imputation/resolution.py
    - tests/test_noc_resolution.py
  modified:
    - pyproject.toml

decisions:
  - id: "06-01-D1"
    decision: "Use dataclasses for internal types (L6Label, L7ExampleTitle, ResolutionContext)"
    rationale: "Internal-only types don't need Pydantic overhead; dataclasses are lighter"
    date: 2026-01-19

metrics:
  tasks_completed: 3
  tests_added: 21
  lines_of_code: ~850
  duration: "10 minutes"
  completed: 2026-01-19
---

# Phase 6 Plan 01: NOC Resolution Service Summary

NOC resolution service with 5-tier confidence scoring: DIRECT_MATCH (1.00), EXAMPLE_MATCH (0.95), UG_DOMINANT (0.85), LABEL_IMPUTATION (0.60), UG_IMPUTATION (0.40). Uses rapidfuzz WRatio for fuzzy matching with 70 threshold.

## What Was Built

### Imputation Models (`src/jobforge/imputation/models.py`)
- `ResolutionMethodEnum` - 5 resolution methods with mapped confidence scores
- `ProvenanceEnum` - NATIVE/INHERITED/IMPUTED tracking for values
- `NOCResolutionResult` - Pydantic model capturing resolution output with full provenance
- `ImputedValue` - Pydantic model for individual imputed values with source tracking

### Resolution Service (`src/jobforge/imputation/resolution.py`)
- `resolve_job_title(job_title, unit_group_id, gold_path)` - Main resolution function
- `build_resolution_context(unit_group_id, gold_path)` - Loads L5/L6/L7 data for a UG
- `clear_resolution_cache()` - Utility to invalidate cached indexes

**Resolution Algorithm:**
1. Single-label UG optimization (64% of UGs) -> UG_DOMINANT (0.85)
2. Direct L6 Label match (case-insensitive) -> DIRECT_MATCH (1.00)
3. L7 Example Title match (case-insensitive) -> EXAMPLE_MATCH (0.95)
4. Fuzzy L6 Label match (rapidfuzz WRatio >= 70) -> LABEL_IMPUTATION (0.60)
5. Fallback to UG context -> UG_IMPUTATION (0.40)

**Caching:**
- `@lru_cache(maxsize=1)` on index builders for element_labels, element_example_titles, dim_noc
- Indexes keyed by gold_path to support testing with temp directories

### Validation Tests (`tests/test_noc_resolution.py`)
- 21 tests covering all resolution paths
- Tests for each resolution method
- Edge case tests (invalid UG, empty input, None)
- Integration tests for batch resolution
- 397 lines of test code

## Task Completion

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create imputation models module | `64484a4` | models.py, __init__.py |
| 2 | Port NOC resolution service | `4963c1a` | resolution.py, pyproject.toml |
| 3 | Create validation tests | `1a98541` | test_noc_resolution.py |

## Verification Results

- All imports work: `from jobforge.imputation import resolution, models`
- Resolution service connects to gold data: element_labels, element_example_titles, dim_noc
- Test suite passes: 21/21 tests pass
- Confidence scores match prototype: 1.00, 0.95, 0.85, 0.60, 0.40

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed f-string format specifier in fallback rationale**
- **Found during:** Task 2 verification
- **Issue:** `{fuzzy_match.similarity_score:.0f if fuzzy_match else 0}` caused ValueError
- **Fix:** Extract to variable `fuzzy_score = fuzzy_match.similarity_score if fuzzy_match else 0`
- **Files modified:** resolution.py
- **Commit:** Included in `4963c1a`

## Decisions Made

1. **Internal dataclasses vs Pydantic** - Used Python dataclasses for internal types (L6Label, L7ExampleTitle, ResolutionContext, BestMatchResult) since they don't need validation or serialization. Pydantic reserved for API-facing models.

2. **Gold path parameter** - Added `gold_path: Path | None` parameter to resolution functions to support testing with temp directories. Defaults to `PipelineConfig().gold_path()`.

3. **Column name mapping** - Gold data uses "Label" and "Job title text" column names; mapped to internal dataclass fields appropriately.

## Next Phase Readiness

**Blockers:** None

**Ready for:**
- 06-02: Attribute inheritance (will use resolution results to select source level)
- 06-03: Provenance column extension (models ready for provenance tracking)
- Phase 7: O*NET/LLM tiers (confidence framework established)

## Technical Notes

- Single-label UGs are 64.3% of all UGs (332 of 516), matching prototype's ~68%
- rapidfuzz.fuzz.WRatio handles partial matching well for job titles
- Test fixtures use `scope="module"` for expensive data loading
- Cache clearing with `autouse=True` fixture ensures test isolation
