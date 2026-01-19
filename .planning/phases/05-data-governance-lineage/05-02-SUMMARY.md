---
phase: 05-data-governance-lineage
plan: 02
subsystem: governance
tags: [catalogue, metadata, DAMA-DMBOK, parquet]

dependency-graph:
  requires:
    - "01-03: CatalogManager and TableMetadata models"
    - "03-01: WiQ schema definition (wiq_schema.json)"
  provides:
    - "CatalogueGenerator class"
    - "generate_catalogue() function"
    - "24 table catalogue JSON files"
  affects:
    - "05-03: Data Catalogue will feed into governance dashboards"

tech-stack:
  added: []
  patterns:
    - "Schema-driven metadata generation"
    - "Parquet file introspection via Polars"

key-files:
  created:
    - src/jobforge/governance/__init__.py
    - src/jobforge/governance/catalogue.py
    - tests/test_catalogue.py
    - data/catalog/tables/*.json (24 files)
  modified:
    - src/jobforge/pipeline/catalog.py

decisions:
  - id: "DIM_TYPE_MAPPING"
    choice: "Map 'dimension' to 'reference' domain"
    reason: "WiQ schema uses 'dimension' not 'dim' for table_type"
  - id: "UTF8_ENCODING"
    choice: "Explicit UTF-8 encoding for all JSON file I/O"
    reason: "Windows defaults to locale encoding, causing French character corruption"

metrics:
  duration: "~15 minutes"
  completed: "2026-01-19"
---

# Phase 05 Plan 02: Data Catalogue Generation Summary

**One-liner:** CatalogueGenerator reads WiQ schema + parquet metadata to produce 24 per-table JSON catalogues with column types, FK relationships, and sample values.

## What Was Built

### CatalogueGenerator Class
Created `src/jobforge/governance/catalogue.py` with:
- `CatalogueGenerator` class that reads WiQ schema and physical parquet files
- `generate()` method producing comprehensive TableMetadata for all tables
- `_load_wiq_schema()` for schema JSON parsing
- `_generate_table_metadata()` for per-table catalogue creation
- `_map_column_metadata()` for column-level documentation with FK tracking
- `generate_catalogue()` convenience function for CLI/script usage

### Table Catalogues Generated
24 JSON files in `data/catalog/tables/`:
- **Fact tables (8):** cops_employment, cops_employment_growth, cops_immigration, cops_other_replacement, cops_other_seekers, cops_retirement_rates, cops_retirements, cops_school_leavers
- **Dimension tables (2):** dim_noc, dim_occupations
- **Element tables (8):** element_additional_information, element_employment_requirements, element_example_titles, element_exclusions, element_labels, element_lead_statement, element_main_duties, element_workplaces_employers
- **Other (6):** job_architecture, oasis_abilities, oasis_knowledges, oasis_skills, oasis_workactivities, oasis_workcontext

### Test Coverage
14 tests in `tests/test_catalogue.py`:
- Schema loading (2 tests)
- Metadata generation (4 tests)
- File output (2 tests)
- Edge cases (1 test)
- Convenience function (2 tests)
- Domain mapping (2 tests)
- Source system (1 test)

## Key Implementation Details

### Metadata Captured
Each catalogue JSON includes:
- **Table identification:** table_name, layer (gold), domain, file_path
- **Physical metadata:** row_count, column_count, file_size_bytes (from parquet)
- **Business metadata:** description, business_purpose, data_owner
- **Column-level:** name, data_type, nullable, description, source_columns, example_values

### Domain Mapping
```python
TABLE_TYPE_DOMAINS = {
    "fact": "forecasting",
    "dimension": "reference",
    "bridge": "relationship",
}
```

### Source System
All tables identified as: `"JobForge WiQ Pipeline"`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed dimension table_type mapping**
- **Found during:** Task 2
- **Issue:** WiQ schema uses "dimension" not "dim" for table_type
- **Fix:** Added "dimension" as key in TABLE_TYPE_* mappings
- **Files modified:** src/jobforge/governance/catalogue.py
- **Commit:** bdd1116

**2. [Rule 1 - Bug] Fixed UTF-8 encoding for Windows**
- **Found during:** Task 3 (test failures)
- **Issue:** `write_text()` without encoding on Windows uses locale encoding, corrupting French characters in sample values
- **Fix:** Added `encoding="utf-8"` to all `read_text()` and `write_text()` calls in CatalogManager
- **Files modified:** src/jobforge/pipeline/catalog.py
- **Commit:** 2c9f424

## Verification Results

| Check | Result |
|-------|--------|
| Module imports | OK |
| Catalogue files created | 24/24 |
| Source system in all files | 24/24 |
| Tests pass | 14/14 |

## Sample Catalogue Entry

```json
{
  "table_name": "dim_noc",
  "layer": "gold",
  "domain": "reference",
  "row_count": 516,
  "column_count": 5,
  "data_owner": "JobForge WiQ Pipeline",
  "columns": [
    {
      "name": "unit_group_id",
      "data_type": "VARCHAR",
      "nullable": false,
      "description": "Primary key",
      "example_values": ["00010", "00011", "00012"]
    }
  ]
}
```

## Next Phase Readiness

**Ready for Phase 05-03:** Data Catalogue is complete and can be used for:
- Governance compliance dashboards
- DADM/DAMA traceability reporting
- Business glossary enrichment
- Column-level lineage visualization
