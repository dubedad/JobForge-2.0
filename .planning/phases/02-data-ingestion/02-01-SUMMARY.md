---
phase: 02-data-ingestion
plan: 01
subsystem: ingestion
tags: [noc, source-registry, transforms, medallion]

dependency-graph:
  requires: [01-02, 01-03]
  provides: [dim-noc-gold, source-registry, ingestion-transforms]
  affects: [02-02, 02-03, 03-01]

tech-stack:
  added: []
  patterns: [source-registry, transform-functions, bronze-schema]

key-files:
  created:
    - src/jobforge/sources/__init__.py
    - src/jobforge/sources/models.py
    - src/jobforge/sources/registry.py
    - src/jobforge/ingestion/__init__.py
    - src/jobforge/ingestion/noc.py
    - src/jobforge/ingestion/transforms.py
    - data/source/noc_structure_en.csv
    - tests/test_dim_noc_ingestion.py
  modified: []

decisions:
  - id: cast-noc-code-to-utf8
    choice: "Cast noc_code to Utf8 in bronze schema"
    rationale: "Polars infers numeric-looking strings as int64, losing leading zeros"
    alternatives: ["Read CSV with explicit dtypes", "Force string at staged layer"]

metrics:
  duration: ~15 minutes
  completed: 2026-01-18
---

# Phase 2 Plan 01: Source Registry and DIM NOC Ingestion Summary

**One-liner:** Source metadata registry with Pydantic models; DIM NOC ingested through medallion pipeline to gold layer with unit_group_id derived from 5-digit zero-padded NOC codes.

## What Was Built

### 1. Source Registry Module (`src/jobforge/sources/`)

Created a new module for managing data source metadata:

- **BilingualName**: Model for Canadian government bilingual naming (en/fr)
- **SchemaMetadata**: Classification metadata per prototype pattern (source, data_type, subtype)
- **BusinessMetadata**: Business context (purpose, owner, authority level)
- **SourceMetadata**: Complete source metadata combining all above
- **SourceRegistry**: Registry class with `load()`, `get_source()`, `list_sources()` methods

### 2. Ingestion Module (`src/jobforge/ingestion/`)

Created source-specific ingestion logic:

- **filter_unit_groups**: Filters to Level 5 (unit group) rows only
- **derive_unit_group_id**: Creates 5-digit zero-padded unit_group_id from noc_code
- **normalize_noc_code**: Handles OaSIS-style codes with decimal portions
- **derive_noc_element_code**: Extracts 2-digit element code from OaSIS profiles
- **derive_unit_group_from_oasis**: Extracts unit_group_id from OaSIS code format
- **ingest_dim_noc**: Full pipeline ingestion function for DIM NOC table

### 3. DIM NOC Gold Table

Sample data ingested through full pipeline:
- Source: 10 rows (1 broad category, 9 unit groups)
- Gold: 9 rows (Level 5 unit groups only)
- Columns: unit_group_id, noc_code, class_title, class_definition, hierarchical_structure, provenance

### 4. Test Suite (`tests/test_dim_noc_ingestion.py`)

8 tests covering:
- Transform functions (filter, derive, normalize)
- Full ingestion pipeline (gold file creation, filtering, unit_group_id, provenance, columns)

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 60be89c | feat | Create source registry with Pydantic models |
| 1341ee8 | feat | Create NOC ingestion module with transforms |
| 706d2e6 | test | Add DIM NOC ingestion tests and fix transforms |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed regex pattern in normalize_noc_code**
- **Found during:** Task 3 test execution
- **Issue:** Double-escaped backslash `r"\\..*$"` didn't match decimal points
- **Fix:** Changed to single escape `r"\..*$"`
- **Files modified:** src/jobforge/ingestion/transforms.py
- **Commit:** 706d2e6

**2. [Rule 1 - Bug] Fixed NOC code type inference losing leading zeros**
- **Found during:** Task 3 test execution
- **Issue:** Polars inferred "00010" as int64, losing leading zeros
- **Fix:** Added `"noc_code": pl.Utf8` to bronze schema cast
- **Files modified:** src/jobforge/ingestion/noc.py
- **Commit:** 706d2e6

**3. [Rule 3 - Blocking] Fixed sample CSV with comma-separated values**
- **Found during:** Task 2 verification
- **Issue:** CSV values with commas caused parsing errors
- **Fix:** Simplified sample data to avoid commas in unquoted fields
- **Files modified:** data/source/noc_structure_en.csv
- **Commit:** 1341ee8

## Success Criteria Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| SourceRegistry class loads source metadata from JSON | PASS | `SourceRegistry.load()` method with Pydantic validation |
| DIM NOC gold table exists with unit_group_id column | PASS | `data/gold/dim_noc.parquet` with unit_group_id column |
| Only Level 5 rows in gold table | PASS | 9 of 10 rows (filtered from Level 1 category) |
| Provenance columns preserved | PASS | _source_file, _ingested_at, _batch_id, _layer in gold |
| NOC codes are 5-digit zero-padded | PASS | ['00010', '00011', ...] all 5 chars |
| All tests pass | PASS | 8/8 tests pass |

## Next Phase Readiness

**Ready for:** Plan 02-02 (OaSIS Attributes Ingestion)

**Prerequisites delivered:**
- SourceRegistry pattern established for source metadata management
- Transform functions for NOC code normalization ready for reuse
- `derive_unit_group_from_oasis` and `derive_noc_element_code` ready for OaSIS ingestion
- DIM NOC gold table available as join target for attribute tables

**Known issues:** None

## Files Created

```
src/jobforge/sources/
  __init__.py          # Module exports
  models.py            # Pydantic models for source metadata
  registry.py          # SourceRegistry class

src/jobforge/ingestion/
  __init__.py          # Module exports
  noc.py               # DIM NOC ingestion function
  transforms.py        # Reusable transform functions

data/source/
  noc_structure_en.csv # Sample NOC structure (10 rows)

data/gold/
  dim_noc.parquet      # Gold DIM NOC table (9 unit groups)

tests/
  test_dim_noc_ingestion.py  # 8 tests for ingestion
```
