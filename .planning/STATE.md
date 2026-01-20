# Project State: JobForge 2.0

**Last Updated:** 2026-01-20

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-19)

**Core value:** Auditable provenance from source to output
**Current focus:** Phase 10 - Governance and Conversational Interface

## Current Position

**Phase:** 10 of 10 (Governance and Conversational)
**Plan:** 2 of 3 complete
**Status:** In progress
**Last activity:** 2026-01-20 - Completed 10-02-PLAN.md (Query HTTP Endpoints)

```
v1.0 [####################] 100% SHIPPED
v2.0 [###################-]  95% Phase 10 in progress
```

## Performance Metrics

**Velocity (v1.0):**
- Total plans completed: 13
- Average duration: ~25 min
- Total execution time: ~5.4 hours

**v2.0 Progress:**
- Plans completed: 11 of 12
- Phases complete: 4 of 5 (Phase 6, Phase 7, Phase 8, Phase 9)
- Current phase: 10 in progress (2/3 plans complete)

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
| 09-01-D1 | Narration-only orchestrator | Does NOT call MCP; reads schema, yields events only | 2026-01-20 |
| 09-01-D2 | SSE streaming with visual delays | 0.05-0.1s delays between events for smooth progression | 2026-01-20 |
| 09-02-D1 | GC FIP colors via CSS custom properties | Easy theming, dark mode support | 2026-01-20 |
| 09-02-D2 | Half-screen width support | UI optimized for side-by-side with Power BI Desktop | 2026-01-20 |
| 09-02-D3 | data-i18n attributes for bilingual text | Declarative approach for EN/FR switching | 2026-01-20 |
| 10-01-D1 | Use RTM pattern for compliance logs | Industry-standard format mapping requirements to evidence artifacts | 2026-01-20 |
| 10-01-D2 | Mark DADM 6.1, 6.5, 6.6 as NOT_APPLICABLE | WiQ is decision-SUPPORT tool, not decision-MAKING system | 2026-01-20 |
| 10-01-D3 | Mark DAMA Security and Document as NOT_APPLICABLE | WiQ uses only public data (no PII), focuses on structured data | 2026-01-20 |
| 10-02-D1 | Use Claude claude-sonnet-4-20250514 with structured outputs for SQL | Guarantees valid JSON response matching SQLQuery schema | 2026-01-20 |
| 10-02-D2 | Extend LineageQueryEngine with catalogue patterns | Reuse existing rule-based engine, add describe/columns/count patterns | 2026-01-20 |
| 10-02-D3 | Register gold parquet as DuckDB views | Memory-efficient, leverages DuckDB parquet scanning | 2026-01-20 |

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
| Gold DDL generation | DuckDB DESCRIBE on parquet views provides column types for schema DDL |

### v2.0 Prototype Assets

Reference implementations in `/JobForge/` sibling directory:
- description_imputation_service.py (160+ lines)
- noc_resolution_service.py (420 lines) - PORTED in 06-01
- onet_adapter.py (393 lines) - PORTED in 07-01
- llm_service.py (199 lines)

### Pending Todos

| Todo | Area | Created | Status |
|------|------|---------|--------|
| DADM traceability log | governance | 2026-01-19 | DONE (10-01) |
| DAMA traceability log | governance | 2026-01-19 | DONE (10-01) |
| Job classification log | governance | 2026-01-19 | DONE (10-01) |

*0 todos pending*

### Open Blockers

None.

## Session Continuity

### Last Session

**Date:** 2026-01-20
**Activity:** Execute Phase 10 Plan 2 (Query HTTP Endpoints)
**Outcome:** FastAPI endpoints for conversational data/metadata queries, Claude text-to-SQL, 36 API tests

### Next Session Priorities

1. Execute Phase 10 Plan 3 (Orbit Integration) if planned
2. Final testing and documentation
3. Ship v2.0

### Context for Claude

When resuming this project:
- **v1.0 SHIPPED** - 10 requirements delivered, 13 plans complete
- **v2.0 Phase 6 COMPLETE** - Imputation Foundation verified
- **v2.0 Phase 7 COMPLETE** - External Data Integration verified
- **v2.0 Phase 8 COMPLETE** - Description Generation verified
- **v2.0 Phase 9 COMPLETE** - Demo Infrastructure (backend + UI)
- **v2.0 Phase 10 Plan 1 COMPLETE** - Compliance Traceability Logs
- **v2.0 Phase 10 Plan 2 COMPLETE** - Query HTTP Endpoints
- Query API: `jobforge api` starts server on localhost:8000
- Endpoints: /api/query/data, /api/query/metadata, /api/compliance/{framework}
- Requires ANTHROPIC_API_KEY for data queries
- Compliance logs: `jobforge compliance {dadm|dama|classification}`
- Demo web UI: 4-step wizard at http://localhost:8080
- Static files in src/jobforge/demo/static/ (HTML, CSS, JS, locales)
- Bilingual EN/FR with localStorage persistence
- GC FIP color palette with dark mode
- SSE narration connects to /api/deploy/stream
- CLI: `jobforge demo` starts web server
- `/stagegold` command triggers actual deployment in Claude Code
- Stack: Python 3.11, Polars, DuckDB, Pydantic 2, NetworkX, Rich, rapidfuzz, httpx, tenacity, beautifulsoup4, lxml, openai, anthropic, fastapi, uvicorn, starlette, sse-starlette
- 425 tests total (36 API tests, 59 governance tests)

---
*State updated: 2026-01-20*
*Session count: 26*
