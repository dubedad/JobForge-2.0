# Project State: JobForge 2.0

**Last Updated:** 2026-01-20

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-20)

**Core value:** Auditable provenance from source to output
**Current focus:** v2.1 Orbit Integration - Phase 11

## Current Position

**Milestone:** v2.1 Orbit Integration
**Phase:** 12 of 13 (Schema and Domain Intelligence)
**Plan:** 3 of 3 in current phase
**Status:** Phase 12 COMPLETE
**Last activity:** 2026-01-21 - Completed 12-03-PLAN.md (Source Attribution and Workforce Patterns)

```
v1.0 [####################] 100% SHIPPED 2026-01-19
v2.0 [####################] 100% SHIPPED 2026-01-20
v2.1 [##########          ]  50% IN PROGRESS
```

## Performance Metrics

**v1.0:**
- Plans completed: 13
- Average duration: ~25 min
- Total execution time: ~5.4 hours

**v2.0:**
- Plans completed: 11
- Phases complete: 5 (Phases 6-10)
- Timeline: 2 days (2026-01-19 -> 2026-01-20)

**v2.1:**
- Plans completed: 5
- Phases complete: 2 (Phases 11-12)
- Requirements: 14
- Tests added: 185 (15 + 156 + 7 + 7)

*Updated after each milestone completion*

## Accumulated Context

### Key Decisions

All v1.0 and v2.0 decisions archived in:
- `.planning/milestones/v2.0-ROADMAP.md` (v2.0 decisions)
- `.planning/PROJECT.md` (Key Decisions table with outcomes)

**v2.1 Phase 11 Decisions:**
| Decision | Rationale | Outcome |
|----------|-----------|---------|
| RFC 9457 error format | Standard, interoperable, tool support | ProblemDetail model in errors.py |
| Environment-based CORS | Flexible deployment without code changes | CORS_ORIGINS env var |
| Sanitized error messages | Security: no stack traces to users | Structlog logging + actionable guidance |
| DuckDB information_schema for views | DuckDB doesn't use sqlite_master | Tests use information_schema.tables |
| Intent confidence scoring | More specific patterns override generic matches | "how many tables" routes to metadata |

**v2.1 Phase 12 Decisions:**
| Decision | Rationale | Outcome |
|----------|-----------|---------|
| dim_noc description priority | Specificity: table-specific over generic | Primary key desc vs foreign key desc |
| Workforce dynamic from folder structure | Preserve original bronze semantics | demand/supply taxonomy in catalog |
| Year column templating | Table-specific context for Claude | "Projected {metric} for {year}" |
| Table metadata writes always | Completeness even without column changes | workforce_dynamic written for all COPS |
| DDL comments from catalog | Single source of truth for metadata | COMMENT clauses from JSON files |
| Filter generic descriptions | Avoid cluttering DDL with non-semantic content | Skip "Column of type" placeholders |
| Hard-coded intelligence hints | Simplicity for initial implementation | Demand/supply lists in DDL generator |
| Quoted numeric columns | DuckDB syntax requirement | Year columns as "2023" not 2023 |
| Source attribution from catalog | Provide provenance in query results | Domain metadata maps to friendly source names |
| Workforce pattern hints | Guide Claude on gap/shortage queries | Explicit demand/supply table lists in prompts |
| Entity recognition guidance | Improve text-to-SQL accuracy | NOC codes, occupation names, year hints |
| Orbit DDL enhancement | Consistent schema context | Import generate_schema_ddl with fallback |

### Technical Discoveries

From v2.1 research:
- 85% of Orbit components already built in orbit/ directory from Phase 10
- HTTP adapter pattern: Orbit calls JobForge API, DuckDB stays internal
- Estimated effort: ~5 developer-days
- Key pitfalls: intent pattern collision, text-to-SQL hallucination, CORS config

From Phase 11 execution:
- dim_occupations is TBS occupation groups (not NOC-based, different join keys)
- DuckDB uses information_schema for metadata, not sqlite_master
- 24 gold tables validated and queryable
- Intent classification needs confidence tiering for pattern specificity

From Phase 12 execution:
- 23 catalog tables enriched with 139 columns updated
- Workforce dynamic taxonomy: demand (5 tables) vs supply (3 tables)
- Year columns (2023-2033) vary by table metric
- Description priority matters: table-specific > generic COPS
- DDL with COMMENT clauses improves Claude's text-to-SQL context
- Numeric column names must be quoted in DuckDB DDL
- RELATIONSHIPS section provides FK join hints to Claude
- Source attribution maps domain to friendly names (forecasting→COPS, noc→Statistics Canada NOC)
- Workforce intelligence patterns guide Claude on gap calculations (demand vs supply)
- Entity recognition hints improve NOC code and occupation name handling
- Orbit retriever can import jobforge modules for enhanced DDL with graceful fallback

### Pending Todos

*0 todos pending*

### Open Blockers

None.

## Session Continuity

### Last Session

**Date:** 2026-01-21
**Activity:** Execute Phase 12 Plan 03 - Source Attribution and Workforce Patterns
**Outcome:** 3 tasks completed, Phase 12 complete, query results with source attribution

### Next Session Priorities

1. Execute Phase 13 (Deployment and Documentation)
2. Complete v2.1 Orbit Integration milestone

### Context for Claude

When resuming this project:
- **v1.0 SHIPPED** - 10 requirements, 13 plans (Phases 1-5)
- **v2.0 SHIPPED** - 17 requirements, 11 plans (Phases 6-10)
- **v2.1 IN PROGRESS** - 14 requirements, 3 phases (Phases 11-13)
- Archives in `.planning/milestones/`
- Query API: `jobforge api` starts server on localhost:8000
- Demo web UI: `jobforge demo` starts wizard at localhost:8080
- Orbit adapter: 85% built in orbit/ directory
- Stack: Python 3.11, Polars, DuckDB, Pydantic 2, NetworkX, Rich, rapidfuzz, httpx, tenacity, beautifulsoup4, openai, anthropic, fastapi, uvicorn, starlette, sse-starlette
- **610 tests passing** (440 + 156 from 11-02 + 7 from 12-01 + 7 from 12-02)
- **New:** RFC 9457 error handling in src/jobforge/api/errors.py
- **New:** CORS middleware configured in src/jobforge/api/routes.py
- **New:** Catalog enrichment module in src/jobforge/catalog/enrich.py
- **New:** 23 catalog tables enriched with workforce_dynamic and semantic descriptions
- **New:** DDL generator with COMMENT clauses, RELATIONSHIPS section, and WORKFORCE INTELLIGENCE hints
- **New:** Query results with source attribution (table provenance mapping to friendly source names)
- **New:** System prompts with workforce domain patterns (demand/supply tables, entity recognition)
- **New:** Orbit retriever using enhanced DDL from jobforge with graceful fallback

---
*State updated: 2026-01-21*
*Session count: 35*
*v2.1 Phase 12 COMPLETE*
