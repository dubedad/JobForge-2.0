---
phase: 02-data-ingestion
plan: 03
subsystem: ingestion
tags: [cops, job-architecture, dim-occupations, forecasting, medallion]

dependency-graph:
  requires: [02-01]
  provides: [cops-ingestion, job-architecture-gold, dim-occupations-gold]
  affects: [03-01, 03-02]

tech-stack:
  added: []
  patterns: [flexible-schema, aggregate-filtering, dimension-extraction]

key-files:
  created:
    - src/jobforge/ingestion/cops.py
    - src/jobforge/ingestion/job_architecture.py
    - data/source/employment_cops_sample.csv
    - data/source/job_architecture_sample.csv
    - tests/test_cops_ingestion.py
    - tests/test_job_architecture_ingestion.py
  modified:
    - src/jobforge/ingestion/__init__.py

decisions:
  - id: filter-00000-aggregate
    choice: "Exclude 00000 code in unit_group_id derivation"
    rationale: "00000 is 'All occupations' aggregate, not a valid unit group"
    alternatives: ["Use NOC dimension lookup", "Filter by string prefix"]
  - id: flexible-column-rename
    choice: "Filter rename dict to only existing columns"
    rationale: "Job Architecture CSVs may have varying column sets"
    alternatives: ["Strict schema validation", "Optional columns with nulls"]

metrics:
  duration: ~20 minutes
  completed: 2026-01-18
---

# Phase 2 Plan 03: COPS and Job Architecture Ingestion Summary

**One-liner:** COPS forecasting tables with 10-year projections and aggregate filtering; Job Architecture with NOC mappings and derived DIM Occupations dimension.

## What Was Built

### 1. COPS Ingestion Module (`src/jobforge/ingestion/cops.py`)

Created COPS (Canadian Occupational Projection System) ingestion:

- **COPS_SUPPLY_TABLES**: List of supply tables (school_leavers, immigration, etc.)
- **COPS_DEMAND_TABLES**: List of demand tables (employment, job_openings, etc.)
- **COPS_SUMMARY_TABLES**: List of assessment tables (summary, flmc, rlmc)
- **ingest_cops_table()**: Full pipeline ingestion with aggregate filtering
- **ingest_all_cops_tables()**: Batch ingestion from directory

Key features:
- Filters aggregate rows (00000, TEER_*, NOC1_*) by default
- Preserves 10-year projection columns (2023-2033)
- Derives unit_group_id for valid 5-digit NOC codes
- Bilingual occupation names (English/French)

### 2. Job Architecture Ingestion Module (`src/jobforge/ingestion/job_architecture.py`)

Created Job Architecture and DIM Occupations ingestion:

- **ingest_job_architecture()**: Full pipeline for job title mappings
- **extract_dim_occupations()**: Derives unique job families/functions
- **ingest_job_architecture_with_dim_occupations()**: Combined ingestion

Key features:
- Derives unit_group_id from 2021_NOC_UID with zero-padding
- Flexible schema handles varying column sets gracefully
- Bilingual columns for job titles, functions, families
- DIM Occupations creates unique family/function combinations with hash IDs

### 3. Sample Data Files

- **employment_cops_sample.csv**: 5 rows (2 aggregates, 3 unit groups)
- **job_architecture_sample.csv**: 5 rows with full column set

### 4. Test Suites

**test_cops_ingestion.py** (6 tests):
- COPS table lists complete
- Gold file creation
- Aggregate filtering
- Aggregate preservation option
- Projection columns preserved
- Bilingual names preserved

**test_job_architecture_ingestion.py** (8 tests):
- Gold file creation
- unit_group_id derivation
- Bilingual columns preserved
- All rows preserved
- DIM Occupations file creation
- Unique families extraction
- Combined ingestion
- FK format validation

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 3b4aa98 | feat | Create COPS forecasting table ingestion |
| cfdb81f | feat | Create Job Architecture and DIM Occupations ingestion |
| 3379b67 | test | Add COPS and Job Architecture ingestion tests |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed 00000 aggregate not being filtered**
- **Found during:** Task 1 verification
- **Issue:** 00000 matched the 5-digit regex but is "All occupations" aggregate
- **Fix:** Added explicit exclusion `& (pl.col("code") != "00000")`
- **Files modified:** src/jobforge/ingestion/cops.py
- **Commit:** 3b4aa98

**2. [Rule 1 - Bug] Fixed column rename failing on missing columns**
- **Found during:** Task 3 test execution
- **Issue:** BronzeLayer failed when renaming columns that don't exist in source
- **Fix:** Filter rename dict to only include columns present in source CSV
- **Files modified:** src/jobforge/ingestion/job_architecture.py
- **Commit:** 3379b67

**3. [Rule 1 - Bug] Fixed test comparing int64 with string**
- **Found during:** Task 3 test execution
- **Issue:** jt_id inferred as int64, test compared with string "2"
- **Fix:** Cast jt_id to Utf8 before comparison in test
- **Files modified:** tests/test_job_architecture_ingestion.py
- **Commit:** 3379b67

## Success Criteria Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| ingest_cops_table() ingests forecasting tables | PASS | Function created with year projection handling |
| COPS tables filter aggregates by default | PASS | 5 rows -> 3 rows (00000, TEER_0 filtered) |
| COPS tables have unit_group_id for valid codes | PASS | 00010, 00011, 10010 all have unit_group_id |
| ingest_job_architecture() ingests job titles | PASS | Function created with NOC mapping |
| extract_dim_occupations() derives families | PASS | Extracts unique job family/function combos |
| Job Architecture has unit_group_id | PASS | Derived from 2021_NOC_UID with zero-padding |
| All gold tables have provenance columns | PASS | _source_file, _ingested_at, _batch_id, _layer |
| All tests pass | PASS | 40/40 tests pass (14 new for this plan) |

## Next Phase Readiness

**Ready for:** Phase 3 (WiQ Semantic Model)

**Prerequisites delivered:**
- COPS forecasting tables provide supply/demand projections by NOC
- Job Architecture provides job title to NOC mappings
- DIM Occupations provides job family/function hierarchy
- All tables have unit_group_id FK for relationship to DIM NOC
- Aggregate filtering ensures only valid unit groups in gold layer

**Known issues:** None

## Files Created

```
src/jobforge/ingestion/
  cops.py               # COPS forecasting ingestion
  job_architecture.py   # Job Architecture and DIM Occupations ingestion

data/source/
  employment_cops_sample.csv    # Sample COPS data (5 rows)
  job_architecture_sample.csv   # Sample Job Architecture (5 rows)

tests/
  test_cops_ingestion.py              # 6 tests for COPS
  test_job_architecture_ingestion.py  # 8 tests for Job Architecture
```

## Phase 2 Completion Status

With Plan 03 complete, Phase 2 (Data Ingestion) is now complete:

| Plan | Description | Status |
|------|-------------|--------|
| 02-01 | Source Registry and DIM NOC | Complete |
| 02-02 | OaSIS and Element Attributes | Complete |
| 02-03 | COPS and Job Architecture | Complete |

**Gold layer now contains:**
- dim_noc.parquet (NOC dimension)
- oasis_skills.parquet (and other OaSIS tables)
- element_skills.parquet (and other Element tables)
- cops_employment.parquet (forecasting)
- job_architecture.parquet (job titles)
- dim_occupations.parquet (job families)

All tables have unit_group_id for FK relationships to DIM NOC.
