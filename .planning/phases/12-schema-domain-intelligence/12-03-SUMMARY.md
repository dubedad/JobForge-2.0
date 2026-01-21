---
phase: 12-schema-domain-intelligence
plan: 03
subsystem: api
tags: [text-to-sql, source-attribution, workforce-analytics, ddl, duckdb, orbit]

# Dependency graph
requires:
  - phase: 12-02-enhanced-ddl
    provides: Enhanced DDL generator with COMMENT clauses and relationship hints
  - phase: 12-01-catalog-enrichment
    provides: Enriched catalog with domain metadata
provides:
  - DataQueryResult with source_tables and source_attribution fields
  - Source attribution mapping tables to friendly source names (COPS, NOC, OaSIS, etc.)
  - System prompts with WORKFORCE INTELLIGENCE PATTERNS section
  - System prompts with ENTITY RECOGNITION hints
  - Orbit DuckDBRetriever using enhanced DDL from catalog
affects: [13-orbit-integration, query-api, text-to-sql]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Source attribution pattern: Load catalog metadata to map tables to friendly source names"
    - "Domain mapping: forecasting→COPS, noc→Statistics Canada NOC, oasis→OaSIS, job_architecture→TBS"
    - "System prompt enhancement: WORKFORCE INTELLIGENCE PATTERNS and ENTITY RECOGNITION sections"
    - "Orbit integration: Import jobforge modules for DDL generation, fallback to basic DDL"

key-files:
  created: []
  modified:
    - src/jobforge/api/data_query.py
    - orbit/retrievers/duckdb.py

key-decisions:
  - "Source attribution from catalog: Load domain metadata from catalog JSON to provide provenance"
  - "Workforce pattern hints: Explicit demand/supply table lists in system prompts"
  - "Entity recognition guidance: NOC codes, occupation names, year ranges in prompts"
  - "Orbit DDL enhancement: Import generate_schema_ddl for catalog-based DDL with graceful fallback"

patterns-established:
  - "Attribution helper pattern: _build_source_attribution() method"
  - "Domain source mapping: Hard-coded mapping from domain to friendly name"
  - "Shared DDL generation: Both JobForge API and Orbit use same enhanced DDL"
  - "Fallback DDL: _generate_basic_ddl() when catalog unavailable"

# Metrics
duration: 52min
completed: 2026-01-21
---

# Phase 12 Plan 03: Source Attribution and Workforce Patterns Summary

**Query results enhanced with source attribution showing table provenance, system prompts updated with workforce domain patterns for gap analysis, Orbit retriever using enriched DDL**

## Performance

- **Duration:** 52 min
- **Started:** 2026-01-21T01:22:14Z
- **Completed:** 2026-01-21T02:14:04Z
- **Tasks:** 3
- **Files modified:** 2 (data_query.py, duckdb.py)

## Accomplishments

- DataQueryResult model extended with source_tables and source_attribution fields
- Source attribution automatically built from catalog metadata (e.g., "Source: cops_employment (COPS Open Canada)")
- System prompts enhanced with WORKFORCE INTELLIGENCE PATTERNS section listing demand/supply tables
- System prompts enhanced with ENTITY RECOGNITION section for NOC codes, occupations, years
- Orbit DuckDBRetriever now uses enhanced DDL generator from jobforge (same catalog-based DDL as API)
- Graceful fallback to basic DDL when jobforge imports unavailable
- Both JobForge API and Orbit adapter use identical enhanced schema context

## Task Commits

Each task was committed atomically:

1. **Task 1: Add source attribution to DataQueryResult** - `3f8287e` (feat)
2. **Task 2: Enhance system prompts with workforce domain patterns** - (included in 3d6cdd3)
3. **Task 3: Enhance Orbit DuckDBRetriever with catalog-based DDL** - `2ceecb5` (feat)

## Files Created/Modified

**Modified:**

- `src/jobforge/api/data_query.py` - Enhanced query service
  - Added `source_tables` and `source_attribution` fields to DataQueryResult model
  - Added `_build_source_attribution()` helper method to map tables to friendly source names
  - Load catalog metadata to extract domain (forecasting, noc, oasis, job_architecture)
  - Map domain to user-facing source name (COPS Open Canada, Statistics Canada NOC, OaSIS, TBS Job Architecture)
  - Updated `query()` method to populate source fields from sql_result.tables_used
  - Enhanced SYSTEM_PROMPT with WORKFORCE INTELLIGENCE PATTERNS section:
    - demand tables: cops_employment, cops_employment_growth, cops_retirements, cops_retirement_rates, cops_other_replacement
    - supply tables: cops_immigration, cops_school_leavers, cops_other_seekers
    - Shortage/gap query guidance: compare demand vs supply
    - Year column quoting requirement: SELECT "2025" not SELECT 2025
  - Enhanced SYSTEM_PROMPT with ENTITY RECOGNITION section:
    - NOC codes: 5-digit numbers like 21232, 41200, 00010
    - Occupation names: "Software Engineers", "Financial Managers", etc.
    - Years: 2023-2033 (projection period)

- `orbit/retrievers/duckdb.py` - Enhanced Orbit retriever
  - Added imports: sys, Path from pathlib
  - Import generate_schema_ddl from jobforge.api.schema_ddl
  - Import PipelineConfig from jobforge.pipeline.config
  - Updated `initialize()` method to use generate_schema_ddl() from jobforge
  - Added `_generate_basic_ddl()` fallback method when jobforge unavailable
  - Updated SYSTEM_PROMPT to match DataQueryService (same WORKFORCE INTELLIGENCE PATTERNS and ENTITY RECOGNITION sections)
  - Ensures Orbit uses same enriched DDL with COMMENT clauses as JobForge API

## Decisions Made

1. **Source attribution from catalog**: Load domain metadata from catalog JSON files to provide provenance in query results, enabling users to trace data back to source (COPS, NOC, OaSIS, etc.).

2. **Workforce pattern hints in prompts**: Explicitly list demand tables (employment, growth, retirements) and supply tables (immigration, school leavers, seekers) in system prompts to guide Claude on gap/shortage query patterns.

3. **Entity recognition guidance**: Add NOC code format hints (5-digit), occupation name examples, and year range (2023-2033) to system prompts to improve Claude's entity extraction and query generation.

4. **Orbit DDL enhancement**: Import jobforge generate_schema_ddl() in Orbit retriever to ensure both API and Orbit use identical enriched DDL, with graceful fallback to basic DDL if imports fail.

## Deviations from Plan

None - plan executed exactly as written.

Tasks 1 and 3 committed as specified. Task 2 system prompt changes were already applied in a prior commit (3d6cdd3) but were documented here as they were part of this plan's scope.

## Issues Encountered

None - implementation was straightforward with enriched catalog and enhanced DDL generator from prior plans.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for Phase 13 (Deployment and Documentation):
- Query results include source attribution showing table provenance
- System prompts provide workforce domain guidance for gap/shortage queries
- Entity recognition hints improve Claude's NOC code and occupation name handling
- Both JobForge API and Orbit retriever use identical enhanced DDL with semantic comments
- Catalog-based DDL provides rich schema context for text-to-SQL
- Graceful fallback ensures Orbit can operate independently if needed

Foundation complete for workforce intelligence queries with full provenance tracking. Next steps: deployment infrastructure and integration documentation.

---
*Phase: 12-schema-domain-intelligence*
*Completed: 2026-01-21*
