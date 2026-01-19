---
phase: 02-data-ingestion
plan: 02
subsystem: ingestion
tags: [oasis, element, noc-attributes, proficiency-scores, text-descriptions]

dependency-graph:
  requires: [02-01]
  provides: [oasis-ingestion, element-ingestion, noc-attributes]
  affects: [02-03, 03-01]

tech-stack:
  added: []
  patterns: [float-to-string-reconstruction, multi-row-tables]

key-files:
  created:
    - src/jobforge/ingestion/oasis.py
    - src/jobforge/ingestion/element.py
    - data/source/skills_oasis_sample.csv
    - data/source/main_duties_element_sample.csv
    - tests/test_noc_attributes_ingestion.py
  modified:
    - src/jobforge/ingestion/__init__.py

decisions:
  - id: float-reconstruction-for-oasis-codes
    choice: "Reconstruct OaSIS codes from Polars float inference"
    rationale: "Polars infers 00010.00 as f64 (10.0), losing leading zeros and decimal format"
    alternatives: ["Read CSV with explicit string dtype at staged layer", "Pre-process CSV before ingestion"]

metrics:
  duration: ~10 minutes
  completed: 2026-01-18
---

# Phase 2 Plan 02: NOC Attributes Ingestion Summary

**One-liner:** OASIS proficiency-scored tables and Element text description tables ingestion with unit_group_id/noc_element_code derivation, handling Polars float inference through numeric reconstruction.

## What Was Built

### 1. OASIS Attribute Ingestion (`src/jobforge/ingestion/oasis.py`)

Created ingestion for proficiency-scored attribute tables:

- **OASIS_TABLES**: List of 6 table types (skills, abilities, personal_attributes, knowledges, workactivities, workcontext)
- **ingest_oasis_table()**: Full pipeline function for single OASIS table
- **ingest_all_oasis_tables()**: Batch processing for all OASIS tables in a directory

Key features:
- Handles Polars float inference by reconstructing XXXXX.YY format from float
- Derives `unit_group_id` (5-digit zero-padded from integer part)
- Derives `noc_element_code` (2-digit zero-padded from decimal part)
- Preserves all proficiency columns (scores 1-5)
- Column reordering to put FK columns first

### 2. Element Attribute Ingestion (`src/jobforge/ingestion/element.py`)

Created ingestion for text description tables:

- **ELEMENT_TABLES**: List of 8 table types (labels, lead_statement, workplaces_employers, example_titles, main_duties, employment_requirements, additional_information, exclusions)
- **ingest_element_table()**: Full pipeline function for single Element table
- **ingest_all_element_tables()**: Batch processing for all Element tables

Key features:
- Supports multi-row tables (multiple duties/requirements per occupation)
- Same FK derivation pattern as OASIS (unit_group_id, noc_element_code)
- Preserves all text description columns

### 3. Sample Data Files

Created sample CSVs for testing:
- **skills_oasis_sample.csv**: 5 occupations with 5 proficiency columns
- **main_duties_element_sample.csv**: 8 duty statements across 3 occupations

### 4. Test Suite (`tests/test_noc_attributes_ingestion.py`)

12 tests covering:
- OASIS table list completeness
- Gold file creation for both table types
- unit_group_id derivation and format (5-digit)
- noc_element_code derivation and format (2-digit)
- Proficiency column preservation (OASIS)
- Multi-row preservation (Element)
- Provenance columns (Element)
- FK format validation

## Commits

| Hash | Type | Description |
|------|------|-------------|
| c1d4492 | feat | Add OASIS attribute table ingestion |
| 023a642 | feat | Add Element attribute table ingestion |
| 91229c2 | test | Add NOC attributes ingestion tests and exports |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed Polars float inference for OaSIS codes**
- **Found during:** Task 1 verification
- **Issue:** Polars inferred "00010.00" as f64 (10.0), losing leading zeros and decimal format
- **Fix:** Reconstruct proper format from float using floor/modulo operations
- **Details:** `floor(10.0)` -> "00010", `(10.01 - floor(10.01)) * 100` -> "01"
- **Files modified:** src/jobforge/ingestion/oasis.py, src/jobforge/ingestion/element.py
- **Commits:** c1d4492, 023a642

## Success Criteria Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| ingest_oasis_table() ingests proficiency-scored tables | PASS | Function created and tested |
| ingest_element_table() ingests text description tables | PASS | Function created and tested |
| Both derive unit_group_id (5-digit zero-padded) | PASS | `test_oasis_has_unit_group_id`, `test_element_has_unit_group_id` |
| Both derive noc_element_code (2-digit) | PASS | `test_oasis_has_noc_element_code` with "00" and "01" variants |
| OASIS tables preserve all proficiency columns | PASS | `test_oasis_preserves_proficiency_columns` |
| Element tables preserve multiple rows per occupation | PASS | `test_element_preserves_multiple_rows` (2 rows for 00010) |
| All tests pass | PASS | 12/12 tests pass |

## Technical Discovery

**Polars Float Inference for Decimal Codes:**

The OaSIS code format "XXXXX.YY" is interpreted by Polars as a floating-point number:
- Input: "00010.00"
- Polars infers: 10.0 (f64)
- Lost: leading zeros, decimal portion precision

**Solution:** Reconstruct the original format from the float value:
```python
# unit_group_id: integer part, 5-digit zero-padded
pl.col("oasis_code").floor().cast(pl.Int64).cast(pl.Utf8).str.zfill(5)

# noc_element_code: decimal part * 100, 2-digit zero-padded
((pl.col("oasis_code") - pl.col("oasis_code").floor()) * 100)
.round(0).cast(pl.Int64).cast(pl.Utf8).str.zfill(2)
```

This pattern is reusable for any OaSIS-formatted code column.

## Next Phase Readiness

**Ready for:** Plan 02-03 (COPS and Additional Sources)

**Prerequisites delivered:**
- OASIS ingestion pattern established for proficiency tables
- Element ingestion pattern established for text tables
- Float-to-string reconstruction pattern for OaSIS codes documented
- All attribute tables have unit_group_id linking to DIM NOC

**Known issues:** None

## Files Created

```
src/jobforge/ingestion/
  oasis.py              # OASIS attribute ingestion
  element.py            # Element attribute ingestion
  __init__.py           # Updated with OASIS/Element exports

data/source/
  skills_oasis_sample.csv         # Sample OASIS skills data
  main_duties_element_sample.csv  # Sample Element duties data

tests/
  test_noc_attributes_ingestion.py  # 12 tests for attribute ingestion
```
