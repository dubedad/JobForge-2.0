---
phase: 14-og-core
plan: 02
subsystem: external-data
tags: [pdfplumber, pdf-extraction, tbs, qualification-standards, pydantic, httpx]

# Dependency graph
requires:
  - phase: 14-og-core-01
    provides: TBS occupational groups scraped data (linked_metadata_en.json)
provides:
  - pdfplumber dependency for PDF text extraction
  - QualificationStandardText Pydantic model with provenance
  - PDF download and extraction functions
  - HTML extraction from existing scraped data
  - 75 qualification standards extracted to og_qualification_text.json
affects: [14-og-core-03, gold-tables, text-search]

# Tech tracking
tech-stack:
  added: [pdfplumber>=0.11.0]
  patterns: [dual-source-extraction, unified-provenance-model]

key-files:
  created:
    - src/jobforge/external/tbs/pdf_extractor.py
    - data/tbs/og_qualification_text.json
    - tests/external/tbs/test_pdf_extractor.py
  modified:
    - pyproject.toml

key-decisions:
  - "TBS publishes HTML not PDFs - adapted to extract from linked_metadata"
  - "Unified QualificationStandardText model supports both PDF and HTML sources"
  - "75 qualification standards covering 31 unique occupational groups"

patterns-established:
  - "Dual-source extraction: Module supports both PDF (pdfplumber) and HTML (scraped data)"
  - "Provenance preservation: source_url, source_type, extracted_at, pdf_metadata tracked"
  - "Text validation: Extraction requires >= 100 chars to detect failures"

# Metrics
duration: 15min
completed: 2026-02-05
---

# Phase 14 Plan 02: PDF Extractor Summary

**pdfplumber-based PDF extraction module with 75 TBS qualification standards extracted from HTML scraped data**

## Performance

- **Duration:** 15 min
- **Started:** 2026-02-05T06:03:51Z
- **Completed:** 2026-02-05T06:18:39Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Added pdfplumber>=0.11.0 dependency for PDF text extraction with table detection
- Created pdf_extractor.py with QualificationStandardText model and extraction functions
- Extracted 75 qualification standards covering 31 unique OG codes from HTML data
- Added 20 comprehensive tests with 100% pass rate

## Task Commits

Each task was committed atomically:

1. **Task 1: Add pdfplumber dependency** - `df942f2` (chore)
2. **Task 2: Create PDF extractor module** - `a272d8e` (feat)
3. **Task 3: Run extraction and add tests** - `cc12079` (feat)

## Files Created/Modified

- `pyproject.toml` - Added pdfplumber>=0.11.0,<0.12.0 dependency
- `src/jobforge/external/tbs/pdf_extractor.py` - PDF/HTML extraction module (389 lines)
  - QualificationStandardText Pydantic model with full provenance
  - download_qualification_pdf() with rate limiting
  - extract_qualification_standard() for pdfplumber extraction
  - extract_from_scraped_html() for HTML data
  - extract_all_qualification_standards() for combined extraction
  - save_qualification_texts() for JSON persistence
- `data/tbs/og_qualification_text.json` - 75 extracted qualification standards (1,634 lines)
- `tests/external/tbs/test_pdf_extractor.py` - 20 tests covering all functionality

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| TBS publishes HTML not PDFs | Plan assumed PDFs; actual TBS core.html has qualification standards as HTML sections |
| Unified model for both sources | QualificationStandardText works with source_type "pdf" or "html" for flexibility |
| Extract from existing linked_metadata | Leverage already-scraped HTML data instead of re-scraping |
| Text validation >= 100 chars | Detect extraction failures early; real standards are much longer |

## Deviations from Plan

### Adaptation Applied

**1. [Rule 3 - Blocking] TBS qualification standards are HTML, not PDFs**
- **Found during:** Task 2 analysis
- **Issue:** Plan specified PDF extraction, but TBS publishes qualification standards as HTML sections at core.html#<og-code>, not as separate PDF files
- **Fix:** Adapted module to support both PDF (for future use) and HTML extraction, leveraging existing linked_metadata_en.json scraped data
- **Files modified:** src/jobforge/external/tbs/pdf_extractor.py (added extract_from_scraped_html function)
- **Verification:** 75 qualification standards successfully extracted from HTML data
- **Impact:** No data loss; HTML extraction provides complete qualification text with provenance

---

**Total deviations:** 1 adaptation (data format discovery)
**Impact on plan:** Adaptation improved coverage - extracted from existing scraped data immediately rather than attempting PDF downloads that would fail

## Issues Encountered

- textract package dependency warnings (unrelated legacy package with incompatible beautifulsoup4 version) - safely ignored, does not affect pdfplumber functionality

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 75 qualification standards ready for gold table ingestion
- QualificationStandardText model provides structured data with provenance
- Full text searchable for qualification criteria queries ("find OGs requiring Master's degree")
- PDF extraction capability ready if TBS publishes PDFs in future

---
*Phase: 14-og-core*
*Completed: 2026-02-05*
