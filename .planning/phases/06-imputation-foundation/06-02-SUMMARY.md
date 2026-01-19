---
phase: 06-imputation-foundation
plan: 02
title: Attribute Inheritance
subsystem: imputation
tags: [inheritance, provenance, polars, lazyframe]

dependency_graph:
  requires: [06-01]
  provides: [attribute-inheritance, imputation-provenance]
  affects: [06-03, 07-onet-api, 08-job-description-generation]

tech_stack:
  added: []
  patterns: [l5-inheritance, batch-provenance, lazyframe-joins]

key_files:
  created:
    - src/jobforge/imputation/provenance.py
    - src/jobforge/imputation/inheritance.py
    - tests/test_inheritance.py
  modified:
    - src/jobforge/imputation/__init__.py

decisions:
  - id: "06-02-D1"
    decision: "Use 0.85 default confidence for batch inheritance"
    rationale: "64% of UGs are single-label (UG_DOMINANT method); exact confidence requires per-title resolution"
    date: 2026-01-19

metrics:
  tasks_completed: 3
  tests_added: 19
  lines_of_code: ~950
  duration: "8 minutes"
  completed: 2026-01-19
---

# Phase 6 Plan 02: Attribute Inheritance Summary

L5 attribute inheritance with 5 imputation provenance columns (_imputation_source_level, _imputation_source_id, _imputation_provenance, _imputation_confidence, _imputation_at). Supports batch and single-title imputation.

## What Was Built

### Imputation Provenance Utilities (`src/jobforge/imputation/provenance.py`)
- `ImputationProvenanceColumns` - Named constants for 5 provenance columns
- `add_imputation_provenance()` - Add provenance columns to LazyFrame
- `create_imputed_attribute_row()` - Build single row with provenance
- `get_provenance_column_names()` - Get list of all provenance column names

### Attribute Inheritance Logic (`src/jobforge/imputation/inheritance.py`)
- `inherit_attributes_to_job_titles(job_arch, attribute_df, attribute_name, gold_path)` - Batch L5 inheritance via unit_group_id join
- `apply_imputation(job_title, unit_group_id, attribute_tables, gold_path)` - Single title imputation with exact confidence
- `get_imputation_summary(imputed_df)` - Statistics for imputed data

**Inheritance Flow:**
1. Job title inherits from its resolved L5 Unit Group via unit_group_id
2. Left join adds all OASIS attribute columns
3. Provenance columns track source_level=5, provenance="inherited"
4. Batch uses 0.85 default confidence; single-title gets exact resolution confidence

### Validation Tests (`tests/test_inheritance.py`)
- 19 tests covering all inheritance behavior
- Tests for provenance column creation and values
- Tests for batch and single-title imputation
- Tests for summary statistics
- Integration test for end-to-end imputation flow

## Task Completion

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create imputation provenance utilities | `bc4dd05` | provenance.py |
| 2 | Implement attribute inheritance logic | `32220a8` | inheritance.py, __init__.py |
| 3 | Create inheritance validation tests | `880debf` | test_inheritance.py |

## Verification Results

- All imports work: `from jobforge.imputation import inherit_attributes_to_job_titles, apply_imputation, ImputationProvenanceColumns`
- Inheritance connects resolution to attributes: Job title -> unit_group_id -> L5 attributes
- Provenance columns present: All 5 columns verified in test output
- Test suite passes: 19/19 tests pass
- Full test suite passes: 140 tests pass (1 skipped, existing)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed deprecated GroupBy.count API**
- **Found during:** Task 3 test execution
- **Issue:** Polars deprecated `GroupBy.count()` in favor of `GroupBy.len()`
- **Fix:** Changed `.count()` to `.len()` and `"count"` to `"len"` in dict access
- **Files modified:** inheritance.py
- **Commit:** Included in `880debf`

## Decisions Made

1. **Default confidence for batch inheritance** - Used 0.85 (UG_DOMINANT confidence) as default for batch operations since 64% of UGs are single-label. For exact per-title confidence, use `apply_imputation()`.

2. **Provenance column naming** - Followed existing pattern from pipeline provenance (`_source_file`, `_ingested_at`) with `_imputation_` prefix to distinguish imputation provenance from ingestion provenance.

3. **LazyFrame preservation** - All functions preserve Polars LazyFrame laziness; only collect when user explicitly requests via `.collect()` or summary functions.

## Next Phase Readiness

**Blockers:** None

**Ready for:**
- 06-03: Provenance column extension (building on established imputation provenance pattern)
- Phase 7: O*NET/LLM imputation (can extend provenance with different source_levels)
- Phase 8: Job description generation (confidence scores enable quality selection)

## Technical Notes

- Batch inheritance joins on unit_group_id, producing one row per job-title/attribute combination
- Pipeline provenance columns (_source_file, _ingested_at, _batch_id, _layer) excluded from join to avoid duplication
- Single-title imputation returns raw_attributes dict with proficiency scores for downstream use
- Summary function provides statistics for monitoring imputation coverage
