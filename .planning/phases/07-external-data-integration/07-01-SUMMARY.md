---
phase: "07"
plan: "01"
subsystem: external-data
tags: ["onet", "crosswalk", "api-client", "provenance"]
dependency-graph:
  requires: ["06-01", "06-02"]
  provides: ["O*NET integration", "NOC-SOC crosswalk", "external attribute fetching"]
  affects: ["07-02", "08-*"]
tech-stack:
  added: ["httpx>=0.27.0", "tenacity>=8.2.0"]
  patterns: ["Adapter pattern", "Async API client", "1:N mapping aggregation"]
key-files:
  created:
    - src/jobforge/external/models.py
    - src/jobforge/external/onet/crosswalk.py
    - src/jobforge/external/onet/client.py
    - src/jobforge/external/onet/adapter.py
    - data/crosswalk/noc2021_onet26.csv
    - tests/test_onet.py
  modified:
    - src/jobforge/external/__init__.py
    - src/jobforge/external/onet/__init__.py
    - pyproject.toml
decisions:
  - id: "07-01-D1"
    decision: "Use Brookfield/thedaisTMU NOC-SOC crosswalk CSV"
    rationale: "MIT-licensed, 1,467 validated mappings, covers all 515 NOC unit groups"
  - id: "07-01-D2"
    decision: "Set ONET_CONFIDENCE=0.5 for all O*NET attributes"
    rationale: "Per CONTEXT.md - O*NET is lower precedence than authoritative Canadian sources"
metrics:
  duration: "~19 min"
  completed: "2026-01-20"
---

# Phase 7 Plan 1: O*NET Integration Summary

**One-liner:** NOC-SOC crosswalk with 1,467 mappings and async O*NET API client for fetching skills, abilities, and knowledge with provenance tracking.

## What Was Built

### External Package Structure
Created `jobforge.external` package with O*NET subpackage providing:
- **NOCSOCCrosswalk**: Loads Brookfield CSV, handles 1:N cardinality, cached lookups
- **ONetClient**: Async HTTP client with X-API-Key auth, tenacity retry logic, rate limit handling
- **ONetAdapter**: Converts O*NET API responses to WiQ schema with provenance

### Pydantic Models
- **ONetAttribute**: Single attribute with element_id, importance_score, source_soc, source_noc, confidence=0.5
- **ONetAttributeSet**: Collection grouped by SOC code with skills, abilities, knowledge lists
- **SourcePrecedence**: Enum defining LLM < ONET < AUTHORITATIVE precedence hierarchy

### Key Capabilities
1. **NOC to SOC mapping**: `crosswalk.noc_to_soc("21211")` returns `["15-1221.00", "15-2051.00", "15-2051.01"]`
2. **Async attribute fetching**: `await adapter.get_attributes_for_noc("21211")` aggregates from all mapped SOCs
3. **Convenience function**: `await get_attributes_for_noc("21211")` for simple one-liner usage
4. **Coverage stats**: 1,467 mappings, 515 unique NOC codes, 995 unique SOC codes

## Technical Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| 07-01-D1 | Use Brookfield/thedaisTMU crosswalk CSV | MIT-licensed, 1,467 validated mappings, NOC 2021 to O*NET 26 |
| 07-01-D2 | ONET_CONFIDENCE = 0.5 | Per CONTEXT.md - lower than authoritative Canadian sources |
| 07-01-D3 | Aggregate all SOCs for 1:N mappings | Don't lose attributes when NOC maps to multiple SOCs |

## Commits

| Hash | Type | Description |
|------|------|-------------|
| f7f4d5f | feat | Create external package with O*NET crosswalk loader |
| 0f62724 | feat | Create O*NET API client and adapter |
| 2eca8f8 | test | Add O*NET integration tests (25 tests) |

## Test Coverage

**25 tests added** (all passing):
- 11 crosswalk tests (CSV loading, 1:N mapping, coverage stats)
- 3 client availability tests (with/without API key)
- 9 adapter tests (mocked API, confidence, provenance, aggregation)
- 2 model tests (ONetAttribute, ONetAttributeSet)
- 2 live API tests (skipped without ONET_API_KEY)

## Deviations from Plan

### [Rule 3 - Blocking] Fixed GitHub repository URL
- **Found during:** Task 1
- **Issue:** Brookfield repo moved to `thedaisTMU` organization
- **Fix:** Used correct URL `https://raw.githubusercontent.com/thedaisTMU/NOC_ONet_Crosswalk/master/noc2021_onet26.csv`
- **Files affected:** data/crosswalk/noc2021_onet26.csv

## Files Created/Modified

### Created
```
src/jobforge/external/models.py          # ONetAttribute, ONetAttributeSet, SourcePrecedence
src/jobforge/external/onet/crosswalk.py  # NOCSOCCrosswalk class
src/jobforge/external/onet/client.py     # ONetClient async API client
src/jobforge/external/onet/adapter.py    # ONetAdapter + get_attributes_for_noc
data/crosswalk/noc2021_onet26.csv        # Brookfield NOC-SOC crosswalk (1,467 rows)
tests/test_onet.py                       # 25 tests for O*NET integration
```

### Modified
```
src/jobforge/external/__init__.py        # Export models
src/jobforge/external/onet/__init__.py   # Export ONetClient, ONetAdapter, get_attributes_for_noc
pyproject.toml                           # Added httpx>=0.27.0, tenacity>=8.2.0
```

## Verification Results

| Check | Result |
|-------|--------|
| Package structure imports | PASS |
| Crosswalk coverage >= 1400 | PASS (1,467) |
| pytest tests/test_onet.py | 25 passed, 2 skipped |
| pytest (full suite) | 165 passed, 3 skipped |

## Success Criteria Checklist

- [x] NOCSOCCrosswalk loads Brookfield CSV with 1,467 mappings
- [x] ONetClient connects to O*NET API v2 with X-API-Key auth
- [x] ONetAdapter converts O*NET attributes to WiQ schema with provenance
- [x] 1:N NOC-SOC cardinality handled (aggregates attributes from all mapped SOCs)
- [x] All attributes tagged with source_type="ONET", confidence=0.5
- [x] Tests pass without requiring real API key (mocked)

## Next Phase Readiness

**Ready for 07-02 (LLM Imputation):**
- External package structure established
- SourcePrecedence enum ready for LLM integration
- Provenance model patterns can be reused

**API Key Setup Required:**
To use live O*NET API, set environment variable:
```bash
export ONET_API_KEY="your-key-here"
# Get key from: https://services.onetcenter.org/developer/
```

---
*Plan completed: 2026-01-20*
*Duration: ~19 minutes*
*Tests: 25 new (165 total passing)*
