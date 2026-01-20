# Requirements: JobForge 2.0 v2.1

**Defined:** 2026-01-20
**Core Value:** Auditable provenance from source to output

## v2.1 Requirements

Requirements for Orbit integration milestone. Each maps to roadmap phases.

### Core Integration

- [ ] **ORB-01**: HTTP adapter configuration routes Orbit queries to JobForge API endpoints
- [ ] **ORB-02**: Intent configuration classifies queries (data, metadata, compliance, lineage)
- [ ] **ORB-03**: DuckDBRetriever validated with all 24 gold tables
- [ ] **ORB-04**: Error responses are user-friendly with actionable guidance

### Schema Enhancement

- [ ] **ORB-05**: Schema DDL includes column descriptions for improved SQL accuracy
- [ ] **ORB-06**: Relationship hints in DDL for multi-table joins

### Domain Intelligence

- [ ] **ORB-07**: Domain-specific intent patterns for workforce intelligence queries
- [ ] **ORB-08**: Entity recognition for NOC codes, occupational groups, job titles
- [ ] **ORB-09**: Provenance-aware responses include source attribution

### Deployment

- [ ] **ORB-10**: Docker Compose configuration for Orbit + JobForge stack
- [ ] **ORB-11**: Environment variables for API URLs, ports, credentials
- [ ] **ORB-12**: CORS middleware configured for cross-origin Orbit requests

### Documentation

- [ ] **ORB-13**: Orbit integration guide with architecture diagram
- [ ] **ORB-14**: Intent configuration reference for extending patterns

## Future Requirements (v3.0+)

Deferred to future milestones. Tracked but not in current roadmap.

### Semantic Search

- **RAG-01**: Vector database for semantic similarity search
- **RAG-02**: RAG pipeline for context-aware LLM responses
- **RAG-03**: Knowledge graph enhancement

### Job Description Builder

- **JDB-01**: Manager-facing web UI for job description creation
- **JDB-02**: NOC-aware form with auto-populated fields

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| PostgreSQL migration | DuckDB + Parquet works; HTTP adapter pattern abstracts database |
| Vector embeddings | v3.0 scope (RAG milestone) |
| Multi-turn conversation | Complexity; single-query pattern sufficient for v2.1 |
| Auto-visualization | Orbit handles this; not JobForge responsibility |
| Query builder UI | Users interact via natural language, not SQL builder |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| ORB-01 | Phase 11 | Pending |
| ORB-02 | Phase 11 | Pending |
| ORB-03 | Phase 11 | Pending |
| ORB-04 | Phase 11 | Pending |
| ORB-05 | Phase 12 | Pending |
| ORB-06 | Phase 12 | Pending |
| ORB-07 | Phase 12 | Pending |
| ORB-08 | Phase 12 | Pending |
| ORB-09 | Phase 12 | Pending |
| ORB-10 | Phase 13 | Pending |
| ORB-11 | Phase 13 | Pending |
| ORB-12 | Phase 13 | Pending |
| ORB-13 | Phase 13 | Pending |
| ORB-14 | Phase 13 | Pending |

**Coverage:**
- v2.1 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0

---
*Requirements defined: 2026-01-20*
*Last updated: 2026-01-20 after roadmap creation*
