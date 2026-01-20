---
phase: 08-description-generation
plan: 02
subsystem: description
tags: [pydantic, openai, prompts, source-cascade, provenance]

# Dependency graph
requires:
  - phase: 08-01
    provides: DescriptionSource, DescriptionProvenance, GeneratedDescription models
  - phase: 06-imputation-foundation
    provides: resolve_job_title function for OASIS resolution
  - phase: 07-external-data
    provides: LLMClient for structured outputs
provides:
  - DescriptionGenerationService with generate methods for title/family/function
  - NOC-style prompt templates with boundary words
  - Source cascade: AUTHORITATIVE lead statement -> LLM fallback
  - Full provenance on all generated descriptions
affects: [08-03, description-output, job-architecture]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - NOC boundary words as prompt context
    - Source cascade with provenance tracking
    - Formal third-person voice matching NOC style

key-files:
  created:
    - src/jobforge/description/prompts.py
    - src/jobforge/description/service.py
    - tests/test_description_service.py
  modified:
    - src/jobforge/description/__init__.py

key-decisions:
  - "No new decisions - implemented per plan specification"

patterns-established:
  - "Description generation: resolve -> lead statement lookup -> LLM fallback"
  - "NOC boundary words: include unit group title, definition, labels in LLM prompts"
  - "Aggregate descriptions: family/function use LLM with member titles as context"

# Metrics
duration: 15min
completed: 2026-01-20
---

# Phase 8 Plan 2: Description Generation Service Summary

**DescriptionGenerationService with NOC-style prompts, source cascade from authoritative lead statements to LLM fallback, and full provenance tracking**

## Performance

- **Duration:** 15 min
- **Started:** 2026-01-20T05:01:11Z
- **Completed:** 2026-01-20T05:16:20Z
- **Tasks:** 3/3
- **Files created:** 3
- **Files modified:** 1

## Accomplishments

- Created NOC-style prompt templates with boundary words for semantic anchoring
- Implemented DescriptionGenerationService with source cascade logic
- AUTHORITATIVE path uses resolution + lead statement lookup (no API calls)
- LLM fallback includes unit group title, definition, and labels as context
- Family/function descriptions use member titles for aggregate context
- 44 tests added for prompts, service, and provenance (298 total passing)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create description prompts** - `2758085` (feat)
2. **Task 2: Create DescriptionGenerationService** - `76ae744` (feat)
3. **Task 3: Add service tests** - `752407f` (test)

## Files Created/Modified

- `src/jobforge/description/prompts.py` - DESCRIPTION_SYSTEM_PROMPT, build_title_description_prompt, build_aggregate_description_prompt, DescriptionResponse
- `src/jobforge/description/service.py` - DescriptionGenerationService, generate_description convenience function
- `src/jobforge/description/__init__.py` - Updated exports for new modules
- `tests/test_description_service.py` - 44 tests for prompts, service, provenance

## Decisions Made

None - followed plan as specified.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all tasks completed successfully.

## User Setup Required

None - no external service configuration required.

LLM functionality requires OPENAI_API_KEY environment variable, but authoritative path (lead statements) works without API key.

## Next Phase Readiness

- DescriptionGenerationService ready for integration
- Source cascade: AUTHORITATIVE when lead statement exists, LLM otherwise
- Family/function descriptions always use LLM with member context
- Full provenance tracking on all descriptions
- Ready for 08-03 (batch processing and output)

---
*Phase: 08-description-generation*
*Completed: 2026-01-20*
