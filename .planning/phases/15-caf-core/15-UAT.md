---
status: complete
phase: 15-caf-core
source: [15-01-SUMMARY.md, 15-02-SUMMARY.md, 15-03-SUMMARY.md, 15-04-SUMMARY.md, 15-05-SUMMARY.md, 15-06-SUMMARY.md]
started: 2026-02-05T15:00:00Z
updated: 2026-02-05T15:10:00Z
---

## Current Test

[testing complete]

## Tests

### 1. CAF Career Scraping Data Exists
expected: `data/caf/careers_en.json` and `data/caf/careers_fr.json` exist with bilingual career listings (~50KB each, 80+ careers)
result: pass
verified: Both files exist (50KB EN, 52KB FR)

### 2. CAF Occupations with Full Content
expected: `data/caf/occupations.json` contains 88 occupations with bilingual fields (title_en, title_fr, overview_en, etc.)
result: pass
verified: 88 occupations with title_en, title_fr, overview_en fields present

### 3. CAF Job Families Inferred
expected: `data/caf/job_families.json` contains 11 job families (engineering-technical, medical-health, combat-operations, etc.)
result: pass
verified: 11 job families in families array

### 4. dim_caf_occupation Gold Table
expected: `data/gold/dim_caf_occupation.parquet` exists with 88 rows, bilingual columns, and provenance fields (_source_url, _content_hash, _scraped_at)
result: pass
verified: 88 rows, 32 cols, _source_url_en and _content_hash_en present

### 5. dim_caf_job_family Gold Table
expected: `data/gold/dim_caf_job_family.parquet` exists with 11 rows, one per job family
result: pass
verified: 11 rows, 10 columns

### 6. CAF-NOC Bridge Table
expected: `data/gold/bridge_caf_noc.parquet` contains 880 mappings (10 per CAF occupation) with confidence_score, match_method, and rationale columns
result: pass
verified: 880 rows, 15 cols with confidence_score, match_method, rationale

### 7. CAF-NOC Human Review File
expected: `data/reference/caf_noc_mappings.json` exists for human verification of automated matches
result: pass
verified: 426.6 KB reference file exists

### 8. CAF-JA Bridge Table
expected: `data/gold/bridge_caf_ja.parquet` contains 880 mappings with JA context columns (ja_job_function_en, ja_job_family_en)
result: pass
verified: 880 rows, 17 cols with ja_job_function_en and ja_job_family_en

### 9. CAF-JA Human Review File
expected: `data/reference/caf_ja_mappings.json` exists for human verification of JA matches
result: pass
verified: 477.4 KB reference file exists

### 10. CLI caf status Command
expected: `jobforge caf status` displays CAF table row counts and reference file status
result: pass
verified: Shows 4 tables (88, 11, 880, 880 rows) and 2 reference files with sizes

### 11. CLI caf refresh Command
expected: `jobforge caf refresh --help` shows options for --scrape and --match flags
result: pass
verified: Shows --scrape/--no-scrape and --match/--no-match options

### 12. WiQ Schema Contains CAF Tables
expected: `data/catalog/schemas/wiq_schema.json` includes 4 CAF tables (dim_caf_occupation, dim_caf_job_family, bridge_caf_noc, bridge_caf_ja) with FK relationships
result: pass
verified: 4 CAF tables in 28 total tables, 27 relationships

### 13. Integration Tests Pass
expected: `pytest tests/test_caf_integration.py -v` runs 47 tests covering all Phase 15 success criteria
result: pass
verified: 47 passed in 8.24s

## Summary

total: 13
passed: 13
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
