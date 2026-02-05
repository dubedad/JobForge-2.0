---
status: diagnosed
phase: 14-og-core
source: [14-01-SUMMARY.md, 14-02-SUMMARY.md, 14-03-SUMMARY.md, 14-04-SUMMARY.md, 14-05-SUMMARY.md, 14-06-SUMMARY.md]
started: 2026-02-05T14:30:00Z
updated: 2026-02-05T15:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Query Occupational Groups
expected: Run Python to query dim_og.parquet. Should return 31 TBS occupational groups with columns including og_code, og_name. Example: "PA" = "Program and Administrative Services".
result: pass

### 2. Query Subgroups Linked to Parent Groups
expected: Query dim_og_subgroup.parquet. Should return 111 subgroups with og_code FK linking to parent group.
result: pass

### 3. Query Pay Rates by OG Code
expected: Query fact_og_pay_rates.parquet for a specific OG code (e.g., "PE"). Should return pay rates with step numbers (1-19) and annual_rate values (range $36k-$196k).
result: pass

### 4. Query Qualification Standards with Structured Fields
expected: Query dim_og_qualifications.parquet. Should return 75 records with structured fields: education_requirement, experience_requirement, certification_requirement. Plus full_text column for search.
result: pass

### 5. Look Up NOC-to-OG Mapping
expected: Use match_noc_to_og() function or query bridge_noc_og.parquet. Given a NOC code like "11100" (Financial managers), should return matched OG code(s) with confidence score and rationale.
result: issue
reported: "21231 FAIL - Software developers and programmers mapped to Ship Repair instead of IT"
severity: major

### 6. Verify Provenance on All Tables
expected: Check any OG table has provenance columns: _source_url, _scraped_at or _extracted_at, _ingested_at, _batch_id, _layer. These enable audit trail back to TBS source.
result: pass

## Summary

total: 6
passed: 5
issues: 1
pending: 0
skipped: 0

## Gaps

- truth: "NOC 21231 (Software developers and programmers) should map to IT (Information Technology) as top match"
  status: fixed
  reason: "User reported: 21231 FAIL - Software developers and programmers mapped to Ship Repair instead of IT"
  severity: major
  test: 5
  root_cause: "Pure fuzzy string matching (rapidfuzz WRatio) finds higher similarity for unrelated terms. 'Ship Repair...Production Supervisors' scores 85.5 due to 'pro' matching in programmers/production, while 'Information Technology' scores only 33.4 due to no character overlap."
  fix_plan: "14-07-PLAN.md"
  fix_summary: "14-07-SUMMARY.md"
  verification: "All 23 concordance tests pass. Software developers now maps to IT (0.92 score)."
