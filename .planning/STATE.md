# Project State: JobForge 2.0

**Last Updated:** 2026-02-05

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-20)

**Core value:** Auditable provenance from source to output
**Current focus:** v3.0 Data Layer Expansion

## Current Position

**Milestone:** v3.0 Data Layer Expansion
**Phase:** 14-og-core (OG Core Tables)
**Plan:** 02 of 3 complete
**Status:** In progress
**Last activity:** 2026-02-05 - Completed 14-02-PLAN.md (PDF Extractor Module)

```
v1.0 [####################] 100% SHIPPED 2026-01-19
v2.0 [####################] 100% SHIPPED 2026-01-20
v2.1 [####################] 100% SHIPPED 2026-01-21
v3.0 [##                  ]  10% IN PROGRESS
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
- Plans completed: 7
- Phases complete: 3 (Phases 11-13)
- Requirements: 14 (all complete)
- Tests added: 185 (15 + 156 + 7 + 7)
- Documentation pages: 3 (1,493 lines)
- Timeline: 2 days (2026-01-20 -> 2026-01-21)

**Quick Tasks:**
- 001: User-facing landing page (23m 40s) - 2026-01-21

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

**v2.1 Phase 13 Decisions:**
| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python 3.11-slim base image | Multi-architecture support (ARM64 + AMD64) | Smaller image size, cross-platform compatibility |
| Editable install | Development workflow in container | pip install -e . enables live updates |
| Healthcheck-based startup | Reliable service ordering | Demo waits for API health before starting |
| Volume mount for data | Updates without rebuild | ./data:/app/data mounted as volume |
| Environment variable ports | Configuration without code changes | ${API_PORT:-8000} and ${DEMO_PORT:-8080} |
| Cross-platform browser launch | Seamless user experience | OS detection in start.sh (darwin/msys/Linux) |
| Mermaid graph TB syntax | Renders in GitHub/VS Code/most viewers | Architecture diagram shows complete topology |
| Domain-organized examples | Users find relevant queries quickly | 5 categories with 30+ curl examples |
| Step-by-step tutorial format | Scenario-based learning more effective | Certification query walkthrough |
| Curl examples throughout | Portable, no dependencies, copy-paste ready | Immediate API testing without clients |

**Quick Task 001 Decisions:**
| Decision | Rationale | Outcome |
|----------|-----------|---------|
| FileResponse vs StaticFiles | StaticFiles mount at "/" conflicts with API routes | Explicit FileResponse for index.html only |
| Automatic metadata fallback | Questions about metadata/lineage don't need data query | JS tries /api/query/data first, falls back on 4xx |
| Vanilla HTML/CSS/JS | Zero build dependencies, immediate deployment | 601 lines including styles, fully functional |
| Business use case organization | Users think in business domains | 4 categories (Forecasting, Skills, Compliance, Lineage) |

**v3.0 Phase 14-01 Decisions:**
| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Transform existing data | TBS already scraped; re-scraping would take hours | Instant generation from prior JSON files |
| Regex pattern for subgroup codes | Consistent "Name(OG-CODE)" format | Clean extraction of AI-NOP, AO-CAI patterns |
| 130 subgroups (not 200+) | Actual unique subgroups fewer than estimate | Correct count from 217 table rows |
| 10k char cap on definitions | Prevent oversized JSON | Consistent file sizes |

**v3.0 Phase 14-02 Decisions:**
| Decision | Rationale | Outcome |
|----------|-----------|---------|
| TBS publishes HTML not PDFs | Plan assumed PDFs; actual core.html has HTML sections | Adapted to extract from linked_metadata |
| Unified model for both sources | Flexibility for future PDF sources | QualificationStandardText with source_type field |
| Extract from existing linked_metadata | Leverage already-scraped HTML data | 75 qualification standards instantly available |
| Text validation >= 100 chars | Detect extraction failures early | Real standards are much longer; catches errors |

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

From Phase 13 execution:
- Docker Compose v2 does not require version field (deprecated)
- Healthcheck polling in startup scripts ensures services ready before browser launch
- Docker layer caching: Copy pyproject.toml first, then install, then copy code
- Exec form CMD required for proper signal handling in containers
- Volume mounts enable data updates without container rebuilds

### Pending Todos

*0 todos pending*

### Open Blockers

None.

## Session Continuity

### Last Session

**Date:** 2026-02-05
**Activity:** Executed 14-02-PLAN.md (PDF Extractor Module)
**Outcome:** Added pdfplumber dependency, created pdf_extractor.py with dual PDF/HTML extraction, extracted 75 qualification standards with provenance

### Next Session Priorities

1. Continue v3.0 Phase 14 — execute 14-03-PLAN.md (OG Gold Tables and NOC Concordance)
2. Create dim_og and dim_og_subgroup gold tables from extracted data
3. Add NOC-OG concordance bridge table with confidence scoring

### Context for Claude

When resuming this project:
- **v1.0 SHIPPED** - 10 requirements, 13 plans (Phases 1-5)
- **v2.0 SHIPPED** - 17 requirements, 11 plans (Phases 6-10)
- **v2.1 SHIPPED** - 14 requirements, 7 plans (Phases 11-13)
- Archives in `.planning/milestones/`
- Query API: `jobforge api` starts server on localhost:8000
- Demo web UI: `jobforge demo` starts wizard at localhost:8080
- Orbit adapter: 85% built in orbit/ directory
- Stack: Python 3.11, Polars, DuckDB, Pydantic 2, NetworkX, Rich, rapidfuzz, httpx, tenacity, beautifulsoup4, openai, anthropic, fastapi, uvicorn, starlette, sse-starlette
- **630 tests passing** (610 + 20 from 14-02)
- **New:** RFC 9457 error handling in src/jobforge/api/errors.py
- **New:** CORS middleware configured in src/jobforge/api/routes.py
- **New:** Catalog enrichment module in src/jobforge/catalog/enrich.py
- **New:** 23 catalog tables enriched with workforce_dynamic and semantic descriptions
- **New:** DDL generator with COMMENT clauses, RELATIONSHIPS section, and WORKFORCE INTELLIGENCE hints
- **New:** Query results with source attribution (table provenance mapping to friendly source names)
- **New:** System prompts with workforce domain patterns (demand/supply tables, entity recognition)
- **New:** Orbit retriever using enhanced DDL from jobforge with graceful fallback
- **New:** Docker Compose stack with API and demo services
- **New:** Healthcheck-based service orchestration (demo waits for API health)
- **New:** Cross-platform startup scripts (start.sh, start.bat) with browser auto-open
- **New:** Environment-based configuration (.env.example with API key and port settings)
- **New:** Complete documentation suite (docs/architecture.md, docs/integration-guide.md, docs/extending-intents.md)
- **New:** Mermaid architecture diagram showing Docker stack topology and data flow
- **New:** 30+ example queries organized by domain (supply/demand, occupation, skills, trends, compliance)
- **New:** Step-by-step intent extension tutorial with certification query example
- **New:** User-facing landing page at http://localhost:8000/ with query UI and example queries
- **New:** Automatic fallback from data query to metadata query on client errors (4xx)

- **New:** pdfplumber>=0.11.0 for PDF text extraction with table detection
- **New:** src/jobforge/external/tbs/pdf_extractor.py - PDF/HTML qualification extraction
- **New:** data/tbs/og_qualification_text.json - 75 qualification standards with provenance
- **New:** QualificationStandardText model supporting both PDF and HTML sources

---
*State updated: 2026-02-05*
*Session count: 41*
*v3.0 Phase 14-02 COMPLETE - 2026-02-05*
