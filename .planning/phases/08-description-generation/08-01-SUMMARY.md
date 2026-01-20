---
phase: 08-description-generation
plan: 01
subsystem: description
tags: [pydantic, polars, provenance, lead-statements, source-cascade]

# Dependency graph
requires:
  - phase: 06-imputation-foundation
    provides: SourcePrecedence enum for conflict resolution
  - phase: 07-external-data
    provides: External models pattern for datetime handling
provides:
  - DescriptionSource enum (AUTHORITATIVE/ONET/LLM)
  - DescriptionProvenance model with precedence mapping
  - GeneratedDescription model for titles/families/functions
  - Lead statement lookup functions with caching
  - Source cascade logic for description determination
affects: [08-02, 08-03, description-service]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Lead statement caching with lru_cache
    - Source cascade pattern (authoritative first, LLM fallback)
    - Provenance-aware models with precedence mapping

key-files:
  created:
    - src/jobforge/description/__init__.py
    - src/jobforge/description/models.py
    - src/jobforge/description/sources.py
    - tests/test_description_models.py
  modified: []

key-decisions:
  - "Provenance.precedence property maps to SourcePrecedence for conflict resolution"
  - "Lead statements cached with lru_cache for efficiency across multiple lookups"

patterns-established:
  - "Description provenance: Every description has source_type, confidence, timestamp, and optional resolution context"
  - "Source cascade: Check authoritative lead statement first, fall back to LLM"

# Metrics
duration: 13min
completed: 2026-01-20
---

# Phase 8 Plan 1: Description Models and Sources Summary

**Pydantic models for description provenance with SourcePrecedence mapping and cached lead statement lookup from 900 OASIS codes**

## Performance

- **Duration:** 13 min
- **Started:** 2026-01-20T04:44:27Z
- **Completed:** 2026-01-20T04:57:20Z
- **Tasks:** 3/3
- **Files created:** 4

## Accomplishments

- Created `jobforge.description` package with models and source cascade logic
- DescriptionProvenance model with precedence property mapping to SourcePrecedence enum
- Lead statement loader caches 900 entries from element_lead_statement.parquet
- Source cascade: AUTHORITATIVE when lead statement exists, LLM otherwise
- Comprehensive test coverage with 29 tests (254 total passing)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create description models** - `279811c` (feat)
2. **Task 2: Create source cascade logic** - `b4c5f08` (feat)
3. **Task 3: Add model and source tests** - `c6e6aa6` (test)

## Files Created

- `src/jobforge/description/__init__.py` - Package exports for models and sources
- `src/jobforge/description/models.py` - DescriptionSource, DescriptionProvenance, GeneratedDescription
- `src/jobforge/description/sources.py` - Lead statement lookup and source cascade functions
- `tests/test_description_models.py` - 29 tests for models and source logic

## Decisions Made

1. **DescriptionProvenance.precedence as property** - Maps source_type to SourcePrecedence dynamically rather than storing redundant data
2. **lru_cache for lead statements** - Single cache for all 900 entries; cleared only when gold layer updates

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all tasks completed successfully.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Models ready for DescriptionGenerationService (08-02)
- Lead statement lookup available for authoritative descriptions
- Source cascade logic ready for integration
- Full test coverage ensures safe extension

---
*Phase: 08-description-generation*
*Completed: 2026-01-20*
