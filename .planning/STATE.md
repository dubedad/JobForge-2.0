# Project State: JobForge 2.0

**Last Updated:** 2026-01-20

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-19)

**Core value:** Auditable provenance from source to output
**Current focus:** Phase 9 - Demo Infrastructure (next)

## Current Position

**Phase:** 9 of 10 (Demo Infrastructure)
**Plan:** Not started
**Status:** Ready to plan
**Last activity:** 2026-01-20 — Completed Phase 8 (Description Generation)

```
v1.0 [####################] 100% SHIPPED
v2.0 [############        ]  60% Phase 8 complete
```

## Performance Metrics

**Velocity (v1.0):**
- Total plans completed: 13
- Average duration: ~25 min
- Total execution time: ~5.4 hours

**v2.0 Progress:**
- Plans completed: 7 of 11
- Phases complete: 3 of 5 (Phase 6, Phase 7, Phase 8)
- Current phase: 09 (0/2 plans complete)

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
| 08-01-D1 | DescriptionProvenance.precedence as property | Maps source_type to SourcePrecedence dynamically | 2026-01-20 |
| 08-01-D2 | lru_cache for lead statements | Single cache for 900 entries; cleared only when gold updates | 2026-01-20 |

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
| Lead statement count | 900 entries in element_lead_statement.parquet indexed by OASIS code |

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
**Activity:** Execute Phase 8 (Description Generation)
**Outcome:** Description generation service with NOC-style prompts, 73 new tests, 298 total passing

### Next Session Priorities

1. Run `/gsd:discuss-phase 9` or `/gsd:plan-phase 9`
2. Port MCP configuration from prototype
3. Live demo with Power BI + narration UI

### Context for Claude

When resuming this project:
- **v1.0 SHIPPED** - 10 requirements delivered, 13 plans complete
- **v2.0 Phase 6 COMPLETE** - Imputation Foundation verified
- **v2.0 Phase 7 COMPLETE** - External Data Integration verified
- **v2.0 Phase 8 COMPLETE** - Description Generation verified
- `jobforge.description` package: models, sources, prompts, service modules
- `jobforge.external.onet` package: crosswalk, client, adapter modules
- `jobforge.external.tbs` package: scraper, parser, link_fetcher, schema modules
- `jobforge.external.llm` package: client, service, prompts modules
- Description cascade: AUTHORITATIVE (900 NOC lead statements) -> LLM fallback with boundary words
- Stack: Python 3.11, Polars, DuckDB, Pydantic 2, NetworkX, Rich, rapidfuzz, httpx, tenacity, beautifulsoup4, lxml, openai
- 298 tests total (73 description tests)

---
*State updated: 2026-01-20*
*Session count: 22*
