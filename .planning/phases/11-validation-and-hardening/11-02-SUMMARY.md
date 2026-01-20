---
phase: 11-validation-and-hardening
plan: 02
completed: 2026-01-20
duration: 33m
subsystem: testing
tags: [pytest, validation, orbit, duckdb, intent-classification]
dependency_graph:
  requires: [10-03]
  provides: [table-coverage-tests, intent-routing-tests, adapter-config-tests]
  affects: [11-02, 12-01]
tech_stack:
  added: []
  patterns: [parametrized-tests, yaml-validation, intent-classification]
key_files:
  created:
    - tests/api/test_table_coverage.py
    - tests/api/test_intent_routing.py
    - tests/orbit/__init__.py
    - tests/orbit/test_adapter_config.py
  modified: []
decisions:
  - id: DEC-11-02-01
    title: "Use DuckDB information_schema for view discovery"
    choice: "Query information_schema.tables instead of sqlite_master"
    rationale: "DuckDB uses information_schema for metadata, not SQLite's sqlite_master"
  - id: DEC-11-02-02
    title: "Intent classification uses confidence scoring"
    choice: "More specific patterns get higher confidence to override generic matches"
    rationale: "Ensures 'how many tables' routes to metadata, not data"
metrics:
  tests_added: 156
  test_files_created: 4
  lines_of_test_code: 797
---

# Phase 11 Plan 02: DuckDB and Intent Routing Validation Summary

Parametrized table coverage tests, intent classification validation, and HTTP adapter config tests for Orbit integration.

## What Was Built

### Task 1: Parametrized Table Coverage Tests (83 tests)

Created `tests/api/test_table_coverage.py` with comprehensive validation:

**Gold Table Discovery Tests:**
- Verify exactly 24 gold tables exist
- Validate dim_*, cops_*, oasis_*, element_* table groups present
- Confirm job_architecture table exists

**DuckDB Registration Tests:**
- Test all 24 tables registered as views in DuckDB
- Verify view count matches parquet file count

**Table Queryability Tests (parametrized x 24):**
- Each table accessible via DataQueryService
- Each table has rows (count >= 0)
- Each table has column definitions

**SQL Execution Tests:**
- COUNT queries work correctly
- SELECT with LIMIT works
- JOIN queries between tables work

### Task 2: Intent Classification Validation Tests (40 tests)

Created `tests/api/test_intent_routing.py` with IntentClassifier:

**Data Intent Tests (9 parametrized):**
- "How many", "count of", "list all", "show me" patterns
- High confidence (0.90) for clear data queries

**Metadata Intent Tests (10 parametrized):**
- "Where does...come from", "lineage", "what columns" patterns
- Specific patterns like "how many tables" override generic "how many"

**Compliance Intent Tests (5 parametrized):**
- "DADM compliance", "DAMA compliant", "governance status" patterns

**Lineage Tests (4 parametrized):**
- Validate lineage queries route to metadata endpoint

**Edge Cases:**
- Ambiguous queries default to data with low confidence
- Empty/random text defaults appropriately
- Pattern priority ensures specific patterns win

### Task 3: HTTP Adapter Configuration Tests (33 tests)

Created `tests/orbit/test_adapter_config.py`:

**JobForge Adapter Tests (16 tests):**
- Required fields: name, description, enabled, type, http
- HTTP config: base_url, timeout, endpoints
- Endpoint validation: data, metadata, compliance
- Intent routing validation
- LLM fallback config

**WiQ Intents Config Tests (15 tests):**
- Domain identification (workforce_intelligence)
- Entity definitions: noc_code, teer_level, broad_category
- Entity patterns compile as valid regex
- Intent categories: occupation, forecast, lineage, compliance
- Fallback strategy defined

**Config Consistency Tests (2 tests):**
- Adapter intents match intent categories
- LLM model specification valid

## Verification Results

```
156 tests passed in 204.93s

Test breakdown:
- Table coverage: 83 tests (24 tables x 3 tests + discovery + SQL)
- Intent routing: 40 tests (across all intent categories)
- Adapter config: 33 tests (YAML validation)
```

## Key Technical Decisions

### DEC-11-02-01: DuckDB Metadata Schema
**Choice:** Use `information_schema.tables` for view discovery
**Context:** DuckDB doesn't use SQLite's `sqlite_master`
**Impact:** Tests correctly validate view registration

### DEC-11-02-02: Intent Classification Confidence
**Choice:** Specific patterns get higher confidence scores
**Context:** "How many tables" (metadata) must win over "how many" (data)
**Impact:** Intent routing works correctly for all query types

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed JOIN test query**
- **Found during:** Task 1 verification
- **Issue:** Original test used `dim_occupations.noc_code` which doesn't exist
- **Fix:** Changed to join `dim_noc` with `cops_employment` on `unit_group_id`
- **Files modified:** tests/api/test_table_coverage.py
- **Commit:** e158903

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| tests/api/test_table_coverage.py | 228 | Parametrized tests for all 24 gold tables |
| tests/api/test_intent_routing.py | 274 | Intent classification validation |
| tests/orbit/__init__.py | 1 | Package marker |
| tests/orbit/test_adapter_config.py | 295 | YAML config validation |

## Commits

| Hash | Type | Description |
|------|------|-------------|
| e158903 | test | Add parametrized table coverage tests |
| 48b8b24 | test | Add intent classification validation tests |
| d3fb7fc | test | Add HTTP adapter configuration tests |

## Success Criteria Met

- [x] `tests/api/test_table_coverage.py` exists with parametrized tests for all 24 tables
- [x] `tests/api/test_intent_routing.py` exists with tests for data/metadata/compliance/lineage intents
- [x] `tests/orbit/test_adapter_config.py` exists with YAML validation tests
- [x] All 24 gold tables pass queryability test
- [x] Intent classification matches expected routing for sample queries
- [x] Adapter config has all required endpoints (data, metadata, compliance)
- [x] All new tests pass (156 total)

## Next Phase Readiness

**Ready for:**
- Phase 11-01: Error response validation (already exists)
- Phase 12: Schema and domain intelligence

**No blockers identified.**
