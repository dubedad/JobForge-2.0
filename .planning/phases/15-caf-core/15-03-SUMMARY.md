---
phase: 15-caf-core
plan: 03
subsystem: ingestion
tags: [caf, gold-tables, medallion, bilingual, provenance, polars]
requires: [15-02]
provides: [dim-caf-occupation, dim-caf-job-family, caf-ingestion-module]
affects: [15-04]
tech-stack:
  added: []
  patterns: [medallion-pipeline, bilingual-columns, fk-relationships]
key-files:
  created:
    - src/jobforge/ingestion/caf.py
    - data/catalog/tables/dim_caf_occupation.json
    - data/catalog/tables/dim_caf_job_family.json
    - tests/ingestion/test_caf.py
  modified: []
decisions:
  - name: JSON array columns for multi-valued fields
    rationale: Polars handles nested JSON well; avoids separate bridge tables for environment/employment_type
    outcome: environment, employment_type, related_civilian_occupations stored as JSON strings
  - name: Job family inference in ingestion module
    rationale: Link fetcher already provides job_families.json; ingestion just validates FK relationship
    outcome: career_id pattern matching mirrors link_fetcher logic for consistency
  - name: Gold files gitignored
    rationale: Generated data should be regenerated, not versioned
    outcome: Parquet files excluded from commits; regenerate with ingest_dim_* functions
metrics:
  duration: 12m 8s
  completed: 2026-02-05
---

# Phase 15 Plan 03: CAF Gold Tables Summary

Medallion pipeline for CAF gold tables; 88 occupations and 11 job families with full bilingual content and provenance; FK relationship validated via job_family_id.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Create dim_caf_occupation ingestion pipeline | 13f9420 | caf.py |
| 2 | Create catalog metadata files | adbda2e | dim_caf_occupation.json, dim_caf_job_family.json |
| 3 | Create tests for CAF ingestion | da526f9 | test_caf.py |

## Implementation Details

### CAF Ingestion Module (caf.py)

Following OG ingestion pattern with medallion transforms:

- **ingest_dim_caf_occupation()**: 88 CAF occupations with bilingual content
- **ingest_dim_caf_job_family()**: 11 job families from inference
- **Bronze**: Load JSON, flatten nested structures, extract provenance
- **Silver**: Normalize codes (lowercase), dedupe, validate required fields
- **Gold**: Final column selection with full provenance

### dim_caf_occupation Gold Table

| Metric | Value |
|--------|-------|
| Rows | 88 |
| Columns | 32 |
| Bilingual columns | 12 (title, overview, work_env, training, entry_plans, part_time) |
| Provenance columns | 9 (_source_url_en/fr, _content_hash_en/fr, _scraped_at, etc.) |
| File size | 389 KB |

**Key columns**:
- career_id (PK)
- title_en, title_fr
- job_family_id (FK to dim_caf_job_family)
- environment (JSON array: army, navy, air_force)
- commission_status (officer, ncm)
- employment_type (JSON array: full_time, part_time)
- related_civilian_occupations (JSON array for career transition mapping)

### dim_caf_job_family Gold Table

| Metric | Value |
|--------|-------|
| Rows | 11 |
| Columns | 10 |
| File size | 5.5 KB |

**Job families** (from 15-02 inference):
- engineering-technical (37 careers)
- medical-health (13 careers)
- combat-operations (10 careers)
- intelligence-signals (10 careers)
- administration-hr (6 careers)
- support-logistics (5 careers)
- police-security (2 careers)
- officer-general (2 careers)
- music (1 career)
- ncm-general (1 career)
- training-development (1 career)

### Catalog Metadata

Created comprehensive catalog files for both tables:
- Column descriptions with example values
- Foreign key relationships defined
- Data owner: Canadian Armed Forces
- Source URL: forces.ca/en/careers/

### Test Coverage

21 tests covering:
- Silver transforms (normalize, dedupe, validate) - 6 tests
- dim_caf_occupation ingestion - 6 tests
- dim_caf_job_family ingestion - 4 tests
- FK integrity validation - 3 tests
- Bilingual storage pattern - 2 tests

## Verification Results

| Check | Status |
|-------|--------|
| `from jobforge.ingestion.caf import ingest_dim_caf_occupation, ingest_dim_caf_job_family` | PASS |
| `pytest tests/ingestion/test_caf.py -v` | 21/21 PASS |
| `ls data/gold/dim_caf*.parquet` - both files exist | PASS |
| `cat data/catalog/tables/dim_caf_occupation.json \| python -m json.tool` | PASS |
| FK relationship valid (all job_family_ids in job_family table) | PASS |
| Bilingual content (88/88 have EN and FR titles) | PASS |

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

### For Plan 04 (CAF Bridge Tables)

- dim_caf_occupation ready with related_civilian_occupations for NOC matching
- career_id available for Job Architecture concordance
- FK relationship to job_family established

### Blockers

None.

### Recommendations

1. Plan 04 should use related_civilian_occupations for NOC fuzzy matching
2. Consider adding environment-based filters for Army/Navy/Air Force career exploration
3. commission_status enables Officer vs NCM career path analysis

---
*Completed: 2026-02-05 13:23 UTC*
*Duration: 12m 8s*
*Tests: 21 passing (785 + 21 = 806 total)*
