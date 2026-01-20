# Project State: JobForge 2.0

**Last Updated:** 2026-01-20

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-19)

**Core value:** Auditable provenance from source to output
**Current focus:** Phase 8 - Description Generation (next)

## Current Position

**Phase:** 8 of 10 (Description Generation)
**Plan:** Not started
**Status:** Ready to plan
**Last activity:** 2026-01-20 — Completed Phase 7 (External Data Integration)

```
v1.0 [####################] 100% SHIPPED
v2.0 [########            ]  45% Phase 7 complete
```

## Performance Metrics

**Velocity (v1.0):**
- Total plans completed: 13
- Average duration: ~25 min
- Total execution time: ~5.4 hours

**v2.0 Progress:**
- Plans completed: 5 of 11
- Phases complete: 2 of 5 (Phase 6, Phase 7)
- Current phase: 07 (3/3 plans complete)

*Updated after each plan completion*

## Accumulated Context

### Key Decisions (v2.0)

| ID | Decision | Rationale | Date |
|----|----------|-----------|------|
| 06-01-D1 | Use dataclasses for internal types | Internal-only types don't need Pydantic overhead | 2026-01-19 |
| 06-02-D1 | Use 0.85 default confidence for batch | 64% of UGs are single-label; exact confidence requires per-title resolution | 2026-01-19 |
| 07-01-D1 | Use Brookfield/thedaisTMU NOC-SOC crosswalk CSV | MIT-licensed, 1,467 validated mappings, covers all 515 NOC unit groups | 2026-01-20 |
| 07-01-D2 | Set ONET_CONFIDENCE=0.5 | Per CONTEXT.md - O*NET is lower precedence than authoritative Canadian sources | 2026-01-20 |
| 07-03-D1 | Use language-aware validation for TBS parser | TBS pages have French column headers; single validation would fail | 2026-01-20 |
| 07-03-D2 | Track unique URLs in link fetcher | Multiple rows may share same definition/standard pages | 2026-01-20 |
| 07-02-D1 | Accept ALL LLM responses regardless of confidence | Per CONTEXT.md - store for downstream filtering | 2026-01-20 |
| 07-02-D2 | Use gpt-4o-2024-08-06 model | Structured Outputs support for guaranteed schema compliance | 2026-01-20 |

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
| TBS bilingual structure | EN/FR pages have different column headers, same data structure |
| TBS link deduplication | 217 rows yield 307 unique links (many shared standards) |

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
**Activity:** Execute 07-02-PLAN.md (LLM Imputation)
**Outcome:** LLM imputation service with Structured Outputs, 26 tests added, 225 total passing

### Next Session Priorities

1. Run `/gsd:discuss-phase 8` or `/gsd:plan-phase 8`
2. Description generation for job titles, families, and functions
3. Multi-source provenance tracking (authoritative vs LLM)

### Context for Claude

When resuming this project:
- **v1.0 SHIPPED** - 10 requirements delivered, 13 plans complete
- **v2.0 Phase 6 COMPLETE** - Imputation Foundation verified
- **v2.0 Phase 7 COMPLETE** - External Data Integration verified
- `jobforge.external.onet` package: crosswalk, client, adapter modules
- `jobforge.external.tbs` package: scraper, parser, link_fetcher, schema modules
- `jobforge.external.llm` package: client, service, prompts modules (NEW)
- LLM imputation: GPT-4o Structured Outputs, accepts all confidence levels
- External data cascade ready: Hierarchical -> O*NET -> LLM (all with provenance)
- Stack: Python 3.11, Polars, DuckDB, Pydantic 2, NetworkX, Rich, rapidfuzz, httpx, tenacity, beautifulsoup4, lxml, openai
- 225 tests total (26 LLM tests added)

---
*State updated: 2026-01-20*
*Session count: 19*
