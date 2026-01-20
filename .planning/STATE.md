# Project State: JobForge 2.0

**Last Updated:** 2026-01-20

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-19)

**Core value:** Auditable provenance from source to output
**Current focus:** Phase 7 - External Data Integration

## Current Position

**Phase:** 7 of 10 (External Data Integration)
**Plan:** 1 of 3 complete
**Status:** In progress
**Last activity:** 2026-01-20 - Completed 07-01-PLAN.md (O*NET Integration)

```
v1.0 [####################] 100% SHIPPED
v2.0 [#####               ]  27% Plan 07-01 complete
```

## Performance Metrics

**Velocity (v1.0):**
- Total plans completed: 13
- Average duration: ~25 min
- Total execution time: ~5.4 hours

**v2.0 Progress:**
- Plans completed: 3 of 11
- Phases complete: 1 of 5 (Phase 6)
- Current phase: 07 (1/3 plans complete)

*Updated after each plan completion*

## Accumulated Context

### Key Decisions (v2.0)

| ID | Decision | Rationale | Date |
|----|----------|-----------|------|
| 06-01-D1 | Use dataclasses for internal types | Internal-only types don't need Pydantic overhead | 2026-01-19 |
| 06-02-D1 | Use 0.85 default confidence for batch | 64% of UGs are single-label; exact confidence requires per-title resolution | 2026-01-19 |
| 07-01-D1 | Use Brookfield/thedaisTMU NOC-SOC crosswalk CSV | MIT-licensed, 1,467 validated mappings, covers all 515 NOC unit groups | 2026-01-20 |
| 07-01-D2 | Set ONET_CONFIDENCE=0.5 | Per CONTEXT.md - O*NET is lower precedence than authoritative Canadian sources | 2026-01-20 |

### Key Decisions (v1.0)

All decisions documented in PROJECT.md with outcomes marked "Good".

### Technical Discoveries (v1.0)

| Discovery | Details |
|-----------|---------|
| Pydantic field naming | Cannot use `_source_file` as field name; use serialization_alias |
| Polars CSV type inference | Numeric-looking strings cast as int64; must cast to Utf8 |
| NetworkX DAG efficiency | 123 logs deduplicate to 106 nodes, 79 edges |

### Technical Discoveries (v2.0)

| Discovery | Details |
|-----------|---------|
| Single-label UGs | 64.3% of UGs (332/516) have single label; enables UG_DOMINANT optimization |
| Gold column names | element_labels uses "Label", element_example_titles uses "Job title text" |
| NOC-SOC cardinality | 1:N mapping - one NOC maps to avg 2.85 SOCs (max 37) |
| Brookfield repo moved | Repository now at thedaisTMU/NOC_ONet_Crosswalk (was BrookfieldIIE) |

### v2.0 Prototype Assets

Reference implementations in `/JobForge/` sibling directory:
- description_imputation_service.py (160+ lines)
- noc_resolution_service.py (420 lines) - PORTED in 06-01
- onet_adapter.py (393 lines) - PORTED in 07-01
- llm_service.py (199 lines)

### Pending Todos

| Todo | Area | Created |
|------|------|---------|
| DADM traceability log | governance | 2026-01-19 |
| DAMA traceability log | governance | 2026-01-19 |
| Job classification log | governance | 2026-01-19 |

*3 todos pending in `.planning/todos/pending/`*

### Open Blockers

None.

## Session Continuity

### Last Session

**Date:** 2026-01-20
**Activity:** Execute 07-01-PLAN.md (O*NET Integration)
**Outcome:** O*NET crosswalk + client + adapter, 25 tests added, 165 total passing

### Next Session Priorities

1. Execute 07-02-PLAN.md (LLM Imputation)
2. Execute 07-03-PLAN.md (TBS Scraping)
3. Complete Phase 7 External Data Integration

### Context for Claude

When resuming this project:
- **v1.0 SHIPPED** - 10 requirements delivered, 13 plans complete
- **v2.0 Phase 6 COMPLETE** - Imputation Foundation verified
- **v2.0 Plan 07-01 COMPLETE** - O*NET Integration verified
- `jobforge.external.onet` package: crosswalk, client, adapter modules
- NOCSOCCrosswalk loads 1,467 mappings from Brookfield CSV
- ONetClient uses async httpx with tenacity retry logic
- ONetAdapter converts O*NET to WiQ schema with confidence=0.5
- Stack: Python 3.11, Polars, DuckDB, Pydantic 2, NetworkX, Rich, rapidfuzz, httpx, tenacity
- 165 tests total (25 O*NET tests added)

---
*State updated: 2026-01-20*
*Session count: 17*
