# Project State: JobForge 2.0

**Last Updated:** 2026-01-20

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-20)

**Core value:** Auditable provenance from source to output
**Current focus:** v2.1 Orbit Integration - Phase 11

## Current Position

**Milestone:** v2.1 Orbit Integration
**Phase:** 11 of 13 (Validation and Hardening)
**Plan:** 2 of 2 in current phase
**Status:** Phase 11 COMPLETE
**Last activity:** 2026-01-20 - Completed 11-02-PLAN.md (DuckDB and Intent Routing Validation)

```
v1.0 [####################] 100% SHIPPED 2026-01-19
v2.0 [####################] 100% SHIPPED 2026-01-20
v2.1 [######              ]  33% IN PROGRESS
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
- Plans completed: 2
- Phases complete: 1 (Phase 11)
- Requirements: 14
- Tests added: 171 (15 + 156)

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

### Pending Todos

*0 todos pending*

### Open Blockers

None.

## Session Continuity

### Last Session

**Date:** 2026-01-20
**Activity:** Execute Phase 11 Plan 02 - DuckDB and Intent Routing Validation
**Outcome:** 3 tasks completed, 156 tests added (table coverage, intent routing, adapter config)

### Next Session Priorities

1. Execute Phase 12 Plan 01 (Schema and Domain Intelligence)
2. Continue through Phase 12-13
3. Complete v2.1 Orbit Integration

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
- **596 tests passing** (440 + 156 new from 11-02)
- **New:** RFC 9457 error handling in src/jobforge/api/errors.py
- **New:** CORS middleware configured in src/jobforge/api/routes.py
- **New:** 83 table coverage tests, 40 intent routing tests, 33 adapter config tests

---
*State updated: 2026-01-20*
*Session count: 32*
*v2.1 Phase 11 COMPLETE*
