---
phase: 15-caf-core
verified: 2026-02-05T14:45:00Z
status: passed
score: 6/6 must-haves verified
---

# Phase 15: CAF Core Verification Report

**Phase Goal:** CAF Careers data scraped and loaded into gold tables with bridges to NOC and Job Architecture
**Verified:** 2026-02-05T14:45:00Z
**Status:** PASSED

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Query 88 CAF occupations with full metadata | VERIFIED | dim_caf_occupation.parquet: 88 rows, 32 columns |
| 2 | Query 11 job families | VERIFIED | dim_caf_job_family.parquet: 11 rows |
| 3 | Look up civilian equivalents | VERIFIED | related_civilian_occupations: 76/88 populated |
| 4 | Find NOC codes for CAF occupations | VERIFIED | bridge_caf_noc.parquet: 880 rows |
| 5 | Find JA matches with confidence scores | VERIFIED | bridge_caf_ja.parquet: 880 rows, confidence 0.5-1.0 |
| 6 | Full provenance on all tables | VERIFIED | _source_url, _content_hash, _scraped_at, algorithm_version |

**Score:** 6/6 truths verified

## Key Artifacts Verified

| Artifact | Status | Details |
|----------|--------|--------|
| src/jobforge/external/caf/models.py | VERIFIED (173 lines) | CAFProvenance, CAFCareerListing, CAFOccupation models |
| src/jobforge/external/caf/scraper.py | VERIFIED (337 lines) | CAFScraper with sitemap parsing, rate limiting |
| src/jobforge/external/caf/link_fetcher.py | VERIFIED (643 lines) | CAFLinkFetcher with bilingual merge |
| src/jobforge/external/caf/matchers.py | VERIFIED (375 lines) | CAFNOCMatcher, CAFJAMatcher with confidence |
| src/jobforge/ingestion/caf.py | VERIFIED (723 lines) | Full ingestion pipeline |
| data/gold/dim_caf_occupation.parquet | VERIFIED (88 rows) | 32 columns, bilingual content |
| data/gold/dim_caf_job_family.parquet | VERIFIED (11 rows) | 10 columns with career counts |
| data/gold/bridge_caf_noc.parquet | VERIFIED (880 rows) | 15 columns with audit trail |
| data/gold/bridge_caf_ja.parquet | VERIFIED (880 rows) | 17 columns with JA context |

## FK Integrity

| Relationship | Status | Orphans |
|-------------|--------|--------|
| dim_caf_occupation -> dim_caf_job_family | WIRED | 0 |
| bridge_caf_noc -> dim_caf_occupation | WIRED | 0 |
| bridge_caf_noc -> dim_noc | WIRED | 0 |
| bridge_caf_ja -> dim_caf_occupation | WIRED | 0 |
| bridge_caf_ja -> job_architecture | WIRED | 0 |

## Test Summary

| Suite | Tests | Status |
|-------|-------|--------|
| test_caf_integration.py | 47 | ALL PASS |
| test_caf_scraper.py | 36 | ALL PASS |
| test_caf_link_fetcher.py | 24 | ALL PASS |
| test_caf_matchers.py | 27 | ALL PASS |
| test_caf_ja_matcher.py | 19 | ALL PASS |
| test_caf.py (ingestion) | 21 | ALL PASS |
| **Total** | **174** | **ALL PASS** |

## Anti-Patterns: None found

## Summary

Phase 15 goal achieved. All 6 success criteria verified:

1. **88 CAF occupations** queryable with full metadata (32 columns, bilingual)
2. **11 job families** queryable with career counts
3. **Civilian equivalents** via related_civilian_occupations (76/88 populated)
4. **NOC codes** via bridge_caf_noc (880 mappings)
5. **JA matches** with confidence scores via bridge_caf_ja (0.5-1.0)
6. **Full provenance** on all tables

All FK relationships verified with 0 orphans. 174 tests passing. No stub patterns.

**Note:** ROADMAP.md mentions 107 occupations/12 families but forces.ca sitemap yields 88/11.

---
*Verified: 2026-02-05T14:45:00Z*
*Verifier: Claude (gsd-verifier)*
