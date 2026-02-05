---
phase: 16-extended-metadata
plan: 01
subsystem: ingestion
tags: [pydantic, regex, polars, parquet, qualification-standards, bilingual, security-clearance]

# Dependency graph
requires:
  - phase: 14-03
    provides: dim_og and dim_og_subgroup gold tables for FK validation
  - phase: 14-05
    provides: og_qualification_text.json source data
provides:
  - Enhanced qualification parser (20+ structured fields from text)
  - dim_og_qualification_standard gold table (75 rows, 27 columns)
  - EnhancedQualification Pydantic model
  - Catalog metadata with FK relationships
affects: [16-02, 16-03, jd-builder]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Keyword extraction with regex fallback to full text"
    - "Soft FK validation with warning logs"
    - "Standardized enum extraction (education_level, security_clearance)"

key-files:
  created:
    - src/jobforge/external/tbs/qualification_parser.py
    - src/jobforge/ingestion/og_qualification_standards.py
    - data/catalog/tables/dim_og_qualification_standard.json
    - tests/external/tbs/test_qualification_parser.py
    - tests/ingestion/test_og_qualification_standards.py
  modified: []

key-decisions:
  - "Full text fallback for education level detection when section extraction fails"
  - "Soft FK validation (warnings only) to preserve all records"
  - "7 standardized education levels: high_school, certificate, diploma, bachelors, masters, phd, professional_degree"

patterns-established:
  - "EnhancedQualification model as contract between parser and ingestion"
  - "Separate extraction functions for each structured field type"
  - "Boolean flags for conditions of employment and operational requirements"

# Metrics
duration: 18min
completed: 2026-02-05
---

# Phase 16 Plan 01: Enhanced Qualification Standards Summary

**Enhanced qualification parser with 20+ structured fields extracting education levels, bilingual profiles, security clearance, and employment conditions from TBS qualification text**

## Performance

- **Duration:** 18 min
- **Started:** 2026-02-05T16:13:26Z
- **Completed:** 2026-02-05T16:31:00Z
- **Tasks:** 3
- **Files created:** 5

## Accomplishments

- EnhancedQualification Pydantic model with 20+ CONTEXT.md structured fields
- Parser extracts education_level (100%), security_clearance (100%), equivalency, certification
- dim_og_qualification_standard.parquet: 75 rows, 27 columns
- 72 tests covering parser extractors and ingestion pipeline
- Catalog metadata with column descriptions and FK relationships

## Task Commits

Each task was committed atomically:

1. **Task 1: Create enhanced qualification parser module** - `937c63c` (feat)
2. **Task 2: Create enhanced qualification ingestion pipeline** - `306b25e` (feat)
3. **Task 3: Create catalog metadata for enhanced qualifications** - `d2f3089` (docs)

## Files Created/Modified

- `src/jobforge/external/tbs/qualification_parser.py` - EnhancedQualification model and extraction functions
- `src/jobforge/ingestion/og_qualification_standards.py` - Medallion pipeline for dim_og_qualification_standard
- `data/catalog/tables/dim_og_qualification_standard.json` - Catalog metadata with 27 column descriptions
- `tests/external/tbs/test_qualification_parser.py` - 53 parser tests
- `tests/ingestion/test_og_qualification_standards.py` - 19 ingestion tests

## Decisions Made

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Full text fallback for education level | Section extraction sometimes gets wrong text due to regex | 100% education_level extraction rate |
| 7 standardized education levels | Cover TBS qualification range from high_school to phd | Enum-like filtering capability |
| Soft FK validation | Preserve all records even if og_code orphaned | All 75 records preserved with warnings |
| Boolean flags for conditions | Enable simple filtering | requires_travel, shift_work, physical_demands, etc. |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed education level extraction when section extraction fails**
- **Found during:** Task 1 (parser testing)
- **Issue:** Regex for education section sometimes captured equivalency statement instead of education content
- **Fix:** Added fallback to scan full text for education keywords when section doesn't contain expected terms
- **Files modified:** src/jobforge/external/tbs/qualification_parser.py
- **Verification:** test_parses_real_tbs_sample passes
- **Committed in:** 937c63c

**2. [Rule 1 - Bug] Fixed certification extraction for licence patterns**
- **Found during:** Task 1 (AI sample testing)
- **Issue:** "Possession of an Air Traffic Controller Licence" not matched by existing patterns
- **Fix:** Added regex pattern for standalone "Possession of ... Licence" statements
- **Files modified:** src/jobforge/external/tbs/qualification_parser.py
- **Verification:** test_ai_sample_certification passes
- **Committed in:** 937c63c

---

**Total deviations:** 2 auto-fixed (2 bugs in regex patterns)
**Impact on plan:** Both fixes essential for correct extraction. No scope creep.

## Issues Encountered

- min_years_experience and bilingual_levels extract 0 values from TBS qualification standards. This is expected - TBS standards don't typically specify exact years or bilingual profiles; those appear in job postings, not standards. The columns exist for future use with job posting data.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- dim_og_qualification_standard ready for JD Builder queries
- Parser can be reused for job posting text extraction
- Future plans can add additional extraction patterns as needed

---
*Phase: 16-extended-metadata*
*Completed: 2026-02-05*
