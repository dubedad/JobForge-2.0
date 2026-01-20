# Research Summary: Orbit Integration (v2.1)

**Synthesized:** 2026-01-20
**Overall Confidence:** MEDIUM-HIGH

---

## Executive Summary

Orbit integration for JobForge 2.0 is a **low-risk, high-value milestone** because the existing codebase already contains 85% of the required components. The `orbit/` directory has a working DuckDBRetriever implementation, HTTP adapter configuration, and domain-specific intent templates. The v2.1 milestone should focus on **productionizing and hardening** what exists rather than building from scratch. The HTTP adapter pattern is the correct approach: Orbit acts as a conversational gateway that routes queries to JobForge's existing FastAPI endpoints, keeping all DuckDB logic in JobForge and treating Orbit as a UI/routing layer only.

The primary technical challenge is **text-to-SQL accuracy**, not infrastructure. Research indicates that well-documented schemas with column descriptions and relationship hints can push accuracy from the 70-85% baseline to 90%+. The existing Claude Structured Outputs integration (Nov 2025) provides schema-guaranteed SQL generation without needing additional frameworks like LangChain or Vanna. The key pitfalls center on intent pattern collision, schema DDL drift after updates, and potential memory leaks in async environments using DuckDB.

Stack changes are minimal: the only optional addition is `schmitech-orbit-client==1.1.6` for CLI testing. All core dependencies (DuckDB 1.4+, anthropic 0.43+, FastAPI, httpx) are already in the project. Deployment uses Docker with the `schmitech/orbit:basic` image. The estimated effort is **5 developer-days** to complete v2.1, making this an efficient milestone with clear deliverables.

---

## Key Findings

### From STACK.md

- **No new dependencies required** - DuckDB, anthropic, FastAPI, httpx already installed
- **HTTP adapter pattern recommended** over custom DuckDBRetriever inside Orbit (2ms latency vs. maintenance burden)
- **Claude Structured Outputs** (Nov 2025 beta) provides schema-guaranteed SQL - no LangChain needed
- **Orbit v2.3.0** available via Docker (`schmitech/orbit:basic`) or local install
- **Python 3.11 for JobForge**, Python 3.12+ for Orbit server (runs separately in Docker)
- Optional CLI client: `schmitech-orbit-client==1.1.6` for testing without full UI

### From FEATURES.md

- **Table stakes 85% complete** - DuckDBRetriever working, intent routing configured, schema context generated
- **Remaining work is polish**: error handling improvements, deployment documentation
- **Differentiators already configured**: entity recognition for NOC codes, TEER levels, broad categories
- **Anti-features clear**: no vector embeddings (v3.0 scope), no multi-turn conversation, no custom fine-tuned model
- **Estimated effort: 5 developer-days**

### From ARCHITECTURE.md

- **Additive integration** - does not modify existing Power BI deployment path
- **Both paths read same gold layer** - changes to parquet propagate to both consumers
- **Three routing options**: DATA_QUERY (DuckDB), METADATA_QUERY (lineage API), COMPLIANCE_QUERY (DADM API)
- **DuckDBRetriever uses in-memory DuckDB** with lazy initialization
- **Build order**: DuckDBRetriever first, then Orbit configuration, then documentation/testing

### From PITFALLS.md

- **C1: Intent Pattern Collision** - "how many tables contain NOC" matches both data and metadata patterns
- **P1: Memory Leak in Async** - musl malloc (Alpine) + DuckDB can cause RSS creep; use jemalloc
- **I1: Column Hallucination** - LLM generates plausible but wrong column names; add descriptions to DDL
- **I3: Conflicting Interfaces** - JobForge has DataQueryService AND new DuckDBRetriever; avoid duplication
- **D4: CORS Not Configured** - React UI on 3000 cannot reach API on 8000 without middleware

---

## Recommended Stack

**Additions for v2.1:**

| Package | Version | Purpose | Required? |
|---------|---------|---------|-----------|
| schmitech-orbit-client | 1.1.6 | CLI testing interface | Optional |

**Already Present (No Changes):**

| Package | Version | Role in Orbit Integration |
|---------|---------|---------------------------|
| duckdb | >=1.4.0 | SQL on gold Parquet files |
| anthropic | >=0.43.0 | Claude Structured Outputs for text-to-SQL |
| fastapi | >=0.115.0 | HTTP API endpoints for Orbit HTTP adapter |
| httpx | >=0.27.0 | Async HTTP client |
| pydantic | >=2.12.0 | SQLQuery response model |

**Deployment:**

```bash
# Orbit via Docker (recommended)
docker pull schmitech/orbit:basic
docker run -d --name orbit -p 5173:5173 -p 3000:3000 \
  -v $(pwd)/orbit/config:/orbit/config schmitech/orbit:basic
```

---

## Feature Scope

### Table Stakes (Must Ship)

| Feature | Status | Notes |
|---------|--------|-------|
| DuckDBRetriever working with 24 gold tables | COMPLETE | `orbit/retrievers/duckdb.py` exists |
| Intent routing for data queries | COMPLETE | `jobforge.yaml` configured |
| Schema DDL context for LLM | COMPLETE | Generated dynamically from parquet |
| SELECT-only enforcement | COMPLETE | System prompt enforces |
| Error handling (user-friendly) | PARTIAL | Needs improvement |
| Basic deployment documentation | TODO | Required for milestone completion |

### Differentiators (Should Ship)

| Feature | Value | Build in v2.1? |
|---------|-------|----------------|
| Domain entity recognition (NOC, TEER) | Already configured | YES - validate |
| Query explanation surfacing | Already generated | YES - expose |
| Metadata query pathway | Already built | YES - wire up |

### Anti-Features (Do Not Build)

| Feature | Why Avoid |
|---------|-----------|
| Vector embeddings | RAG-03 is v3.0 scope |
| Multi-turn conversation | Requires session state |
| Custom fine-tuned model | Claude Structured Outputs sufficient |
| Query builder UI | JDB-01 through JDB-05 are v3.0 |
| Auto-visualization | Different product |

---

## Architecture Approach

### Integration Pattern

```
User Question
     |
     v
+------------------+
|  Orbit Gateway   |  <-- Intent classification, UI, conversation history
|  localhost:3000  |
+--------+---------+
         |
    HTTP calls to JobForge API (or direct DuckDB)
         |
         v
+------------------+
|  JobForge API    |  <-- Claude text-to-SQL, DuckDB queries
|  localhost:8000  |
+--------+---------+
         |
         v
+------------------+
|  Gold Parquet    |  <-- 24 tables, star schema
|  data/gold/*.parquet
+------------------+
```

### Key Architectural Decisions

1. **HTTP adapter over custom retriever** - Keeps DuckDB logic in JobForge; Orbit is pure UI
2. **Single source of truth** - DuckDBRetriever should delegate to DataQueryService (avoid parallel implementations)
3. **In-memory DuckDB** - Clean isolation per session; lazy initialization
4. **Same gold layer** - Both Power BI and Orbit read from `data/gold/*.parquet`

### New Components

| Component | Location | Purpose |
|-----------|----------|---------|
| DuckDBRetriever | `orbit/retrievers/duckdb.py` | EXISTS - validate |
| jobforge.yaml | `orbit/config/adapters/` | EXISTS - validate |
| wiq_intents.yaml | `orbit/config/intents/` | EXISTS - validate |
| orbit-integration.md | `docs/` | TODO - create |

---

## Critical Pitfalls

### 1. Intent Pattern Collision (CRITICAL)

**Risk:** "How many tables contain NOC?" matches both data ("how many") and metadata ("tables contain") intents.

**Prevention:**
- Design mutually exclusive patterns
- Add priority ordering (metadata checked before data)
- Include negative patterns in data_query

### 2. Column Hallucination (HIGH)

**Risk:** LLM generates `job_title` when actual column is `class_title`.

**Prevention:**
- Add column descriptions to schema DDL:
  ```sql
  class_title VARCHAR,  -- Official occupation title (not "job_title")
  ```
- Validate SQL against actual schema before execution
- Log failed queries for schema improvement

### 3. Memory Leak in Async (MEDIUM)

**Risk:** DuckDB + musl malloc (Alpine) causes RSS creep in async FastAPI.

**Prevention:**
- Use jemalloc allocator in production Docker images
- Monitor memory trends over time
- Set memory limits with buffer

### 4. CORS Not Configured (HIGH for deployment)

**Risk:** React UI on port 3000 cannot reach API on port 8000.

**Prevention:**
- Add CORS middleware to FastAPI:
  ```python
  app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"])
  ```

### 5. Schema DDL Drift (MEDIUM)

**Risk:** Gold tables updated but Orbit not restarted; LLM uses stale schema.

**Prevention:**
- Document that Orbit restart required after schema changes
- Consider schema DDL TTL (regenerate periodically)

---

## Roadmap Implications

### Suggested Phase Structure

Based on dependency analysis and architecture patterns, v2.1 should be structured as:

#### Phase 1: Validation and Hardening (1-2 days)

**Deliverables:**
- Validate existing DuckDBRetriever works with all 24 gold tables
- Validate intent routing handles ambiguous queries correctly
- Test entity recognition patterns (NOC codes, TEER levels)

**Features from FEATURES.md:** Table stakes validation
**Pitfalls to avoid:** C1 (intent collision), I1 (column hallucination)
**Research needed:** NO - patterns well-documented

#### Phase 2: Error Handling and API Polish (1 day)

**Deliverables:**
- User-friendly error messages (not raw SQL errors)
- CORS configuration for cross-origin requests
- API health check validates credentials at startup

**Features from FEATURES.md:** Error handling improvement
**Pitfalls to avoid:** I5 (error exposure), D4 (CORS), C3 (missing API key)
**Research needed:** NO - standard FastAPI patterns

#### Phase 3: Deployment Configuration (1 day)

**Deliverables:**
- Docker Compose for Orbit + JobForge
- Environment variable configuration (not hardcoded localhost)
- Port conflict resolution

**Features from FEATURES.md:** Deployment configuration
**Pitfalls to avoid:** C2 (hardcoded localhost), D1 (port conflicts), D2 (version mismatch)
**Research needed:** NO - Docker patterns standard

#### Phase 4: Documentation and Testing (1 day)

**Deliverables:**
- `docs/orbit-integration.md` with architecture diagram, quick start, troubleshooting
- End-to-end test from question to answer
- Manual verification checklist

**Features from FEATURES.md:** Basic deployment documentation
**Pitfalls to avoid:** D3 (retriever not registered)
**Research needed:** NO

### Research Flags

| Phase | Needs `/gsd:research-phase`? | Rationale |
|-------|------------------------------|-----------|
| Phase 1 | NO | Existing code provides patterns |
| Phase 2 | NO | Standard FastAPI middleware |
| Phase 3 | NO | Docker Compose well-documented |
| Phase 4 | NO | Documentation task |

**Conclusion:** v2.1 requires NO additional research phases. All patterns are well-documented and existing code provides implementation guidance.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verified via PyPI; minimal additions needed |
| Features | MEDIUM-HIGH | Existing implementation provides grounding; Orbit docs sparse |
| Architecture | HIGH | HTTP adapter pattern well-documented; existing code validates |
| Pitfalls | MEDIUM | DuckDB/text-to-SQL well-documented; Orbit-specific patterns inferred |

### Gaps to Address During Planning

1. **Orbit retriever registration process** - Documentation unclear on exact factory registration steps
2. **Intent pattern testing methodology** - Need systematic test suite for ambiguous queries
3. **Memory monitoring baseline** - Establish RSS baseline before deployment to detect leaks

### Overall Assessment

**Confidence: MEDIUM-HIGH**

The integration is well-scoped with minimal unknowns. The primary risk is text-to-SQL accuracy, which is a known challenge with documented mitigations (column descriptions, relationship hints, SQL validation). The existing codebase provides strong implementation guidance.

---

## Sources

### Stack Research (HIGH Confidence)
- [PyPI - DuckDB 1.4.3](https://pypi.org/project/duckdb/)
- [Anthropic Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
- [schmitech/orbit GitHub](https://github.com/schmitech/orbit)
- [schmitech-orbit-client on Libraries.io](https://libraries.io/pypi/schmitech-orbit-client)

### Features Research (MEDIUM Confidence)
- [Google Cloud - Techniques for improving text-to-SQL](https://cloud.google.com/blog/products/databases/techniques-for-improving-text-to-sql)
- [Text to SQL: Ultimate Guide 2025](https://medium.com/@ayushgs/text-to-sql-the-ultimate-guide-for-2025-3fa4e78cbdf9)
- [DuckDB Information Schema](https://duckdb.org/docs/stable/sql/meta/information_schema)

### Architecture Research (HIGH Confidence)
- [Orbit Adapters Documentation](https://github.com/schmitech/orbit/blob/main/docs/adapters/adapters.md)
- [Orbit Docker README](https://github.com/schmitech/orbit/blob/main/docker/README.md)
- [MotherDuck - Semantic Layer with DuckDB](https://motherduck.com/blog/semantic-layer-duckdb-tutorial/)

### Pitfalls Research (MEDIUM Confidence)
- [BetterUp - Async FastAPI Memory Leak with jemalloc](https://build.betterup.com/chasing-a-memory-leak-in-our-async-fastapi-service-how-jemalloc-fixed-our-rss-creep/)
- [K2View - LLM text-to-SQL challenges](https://www.k2view.com/blog/llm-text-to-sql/)
- [Six Failures of Text-to-SQL](https://medium.com/google-cloud/the-six-failures-of-text-to-sql-and-how-to-fix-them-with-agents-ef5fd2b74b68)
- [DuckDB Issue #18031 - Memory leak](https://github.com/duckdb/duckdb/issues/18031)
