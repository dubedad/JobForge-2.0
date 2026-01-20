# Features Research: Orbit Integration (v2.1)

**Domain:** Text-to-SQL gateway for workforce intelligence data
**Researched:** 2026-01-20
**Confidence:** MEDIUM (existing implementation provides grounding; Orbit documentation sparse)

---

## Executive Summary

JobForge 2.0 already has most of the hard work done. The existing `orbit/` directory contains:
- A working DuckDBRetriever implementation (`orbit/retrievers/duckdb.py`)
- An HTTP adapter configuration (`orbit/config/adapters/jobforge.yaml`)
- Domain-specific intent configuration (`orbit/config/intents/wiq_intents.yaml`)

The v2.1 milestone should focus on **productionizing and hardening** what exists, not building from scratch. Orbit (schmitech/orbit) is an open-source inference gateway that routes natural language queries to appropriate backends via intent classification.

---

## Table Stakes (Must Have)

Features every Orbit deployment needs to be considered functional.

| Feature | Why Expected | Complexity | Existing Coverage | Notes |
|---------|--------------|------------|-------------------|-------|
| **Working retriever** | Core functionality - query data via NL | High | COMPLETE | `DuckDBRetriever` in `orbit/retrievers/duckdb.py` |
| **Intent routing** | Route questions to correct endpoint | Medium | COMPLETE | `jobforge.yaml` has data/metadata/compliance intents |
| **Schema context** | LLM needs schema for accurate SQL | Medium | COMPLETE | DDL generated dynamically from parquet files |
| **Error handling** | Users need clear feedback on failures | Low | PARTIAL | Basic try/catch exists; needs user-friendly messages |
| **Query result formatting** | Return structured, usable results | Low | COMPLETE | Returns list of dicts from DuckDB |
| **SELECT-only enforcement** | Security - prevent data modification | Low | COMPLETE | System prompt enforces SELECT only |
| **Intent fallback strategy** | Handle ambiguous queries gracefully | Low | COMPLETE | `wiq_intents.yaml` has fallback to metadata_first |

**Assessment:** Table stakes are 85% complete. Remaining work is polish and hardening.

---

## Differentiators

Features that would make this integration stand out compared to generic text-to-SQL deployments.

| Feature | Value Proposition | Complexity | Build in v2.1? | Notes |
|---------|-------------------|------------|----------------|-------|
| **Domain-specific entity recognition** | Understand "21232", "TEER 1", "broad category 2" | Medium | YES | Already configured in `wiq_intents.yaml` - needs testing |
| **Metadata query pathway** | Answer "where does X come from?" without SQL | Low | YES | Existing FastAPI `/api/query/metadata` endpoint |
| **Compliance reporting** | Show DADM/DAMA compliance on demand | Low | YES | Existing `/api/compliance/{framework}` endpoint |
| **Multi-intent classification** | Handle compound questions | High | NO | Future enhancement - single intent is fine for v2.1 |
| **Query explanation** | Show SQL + explain what it does | Low | YES | Already in `SQLQuery` model - surface to users |
| **Rich column descriptions** | Domain context in schema DDL | Medium | MAYBE | Would improve SQL accuracy; investigate ROI |
| **Confidence scoring** | Tell users when LLM is uncertain | High | NO | Nice to have but adds complexity |
| **Query history/caching** | Avoid re-running identical queries | Medium | NO | Optimization for v2.2+ |
| **Semantic similarity examples** | Few-shot examples matched to user query | High | NO | RAG enhancement for v3.0 scope |

**Recommended differentiators for v2.1:**
1. Entity recognition patterns (already configured)
2. Query explanation surfacing (already generated, just expose)
3. Metadata pathway integration (already built)

---

## Anti-Features (Out of Scope for v2.1)

Features to deliberately NOT build. Some are distractions; others belong in future milestones.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Vector embeddings for retrieval** | RAG-03 is v3.0 scope; adds complexity without proportional value for structured data | Use schema-based text-to-SQL only |
| **Custom fine-tuned model** | DuckDB-NSQL exists but Claude structured outputs work well already | Stick with Claude Sonnet 4 |
| **Multi-turn conversation** | Requires session state, history management | Single-shot queries only for v2.1 |
| **Auto-visualization** | Chart generation is a different product | Return data; let downstream tools visualize |
| **Query builder UI** | JDB-01 through JDB-05 are v3.0 scope | CLI/API only for v2.1 |
| **Cross-database joins** | Only one database (WiQ) | Don't architect for multi-DB |
| **Real-time data sync** | Out of scope per PROJECT.md | Manual export/import workflow |
| **User authentication in retriever** | Orbit handles auth at gateway level | Trust Orbit's API key system |
| **Billing/usage tracking** | Not needed for internal deployment | Defer unless GC requires chargeback |

**Rationale:** v2.1 is about proving Orbit works for WiQ. Keep scope tight.

---

## Complexity Assessment

| Feature Area | Complexity | Effort (days) | Risk | Notes |
|--------------|------------|---------------|------|-------|
| **DuckDBRetriever completion** | Low | 0.5 | Low | Already implemented; needs integration test |
| **Intent routing validation** | Low | 0.5 | Low | Test all intent patterns work correctly |
| **Entity recognition testing** | Medium | 1 | Medium | Regex patterns need validation against real queries |
| **Error message improvement** | Low | 0.5 | Low | Map exceptions to user-friendly messages |
| **Deployment configuration** | Medium | 1 | Medium | Docker compose, env vars, secrets management |
| **End-to-end testing** | Medium | 1 | Low | User journey from question to answer |
| **Documentation** | Low | 0.5 | Low | How to deploy, configure, use |

**Total estimated effort:** 5 developer-days for v2.1

---

## Feature Dependencies

```
Existing JobForge v2.0 Features
        |
        v
+-------------------+
| Gold Parquet      |  <-- DuckDBRetriever reads from here
| (24 tables)       |
+-------------------+
        |
        v
+-------------------+
| Schema DDL Gen    |  <-- schema_ddl.py generates DDL for LLM context
| (api/schema_ddl)  |
+-------------------+
        |
        v
+-------------------+
| DuckDBRetriever   |  <-- Core component for Orbit
| (orbit/retrievers)|
+-------------------+
        |
        v
+-------------------+
| Intent Config     |  <-- Routes queries to correct handler
| (orbit/config)    |
+-------------------+
        |
        v
+-------------------+
| Orbit Gateway     |  <-- External dependency (schmitech/orbit)
| (Docker deploy)   |
+-------------------+
```

**Critical path:** DuckDBRetriever must work before Orbit can serve queries.

---

## Enterprise Text-to-SQL Expectations (Industry Context)

Based on research into enterprise deployments, users expect:

### Accuracy Expectations
- **Baseline:** 70-85% query accuracy is typical for text-to-SQL systems
- **With semantic layer:** Can reach 90%+ with proper schema documentation
- **Failure mode:** Users tolerate "I don't understand" better than wrong answers

### User Experience Patterns
- **Ambiguous queries:** System should ask clarifying questions rather than guess
- **Confidence indication:** Users want to know when system is uncertain
- **SQL visibility:** Technical users want to see and verify generated SQL
- **Result limits:** Default to reasonable limits (100 rows) to prevent overwhelming results

### Common Failure Modes to Guard Against
1. **Hallucinated table/column names** - Always validate SQL against actual schema
2. **Wrong JOIN conditions** - Star schema helps but complex queries can still fail
3. **Aggregate confusion** - COUNT vs SUM vs AVG ambiguity
4. **Date/time handling** - COPS data has specific time semantics
5. **NULL handling** - IS NULL vs = NULL confusion

### JobForge-Specific Considerations
- NOC codes can be 4 or 5 digits - pattern matching must handle both
- TEER levels 0-5 - users may say "tier" instead of "TEER"
- Bilingual data - some TBS content is French
- Hierarchy navigation - "parent of 21232" type queries

---

## Orbit-Specific Features (from schmitech/orbit)

Based on research, Orbit provides:

| Feature | Description | JobForge Relevance |
|---------|-------------|-------------------|
| **Multi-provider support** | 20+ LLM providers + Ollama | Currently using Anthropic; could switch if needed |
| **Intent-aware routing** | Pattern + LLM-based classification | Using for data/metadata/compliance routing |
| **API key per adapter** | Scoped keys create "agents" | Each WiQ query type could have its own key |
| **YAML configuration** | Adapters, intents, models | Already configured in `orbit/config/` |
| **Circuit breaker** | Exponential backoff for failures | Built-in resilience |
| **Docker deployment** | Containerized with volumes | Standard deployment pattern |

**Key insight:** Orbit is designed as a gateway, not a database. It expects backends (like JobForge API) to do the actual work. The DuckDBRetriever is a custom extension that brings SQL capability inside Orbit.

---

## MVP Recommendation for v2.1

**Must ship:**
1. DuckDBRetriever working with all 24 gold tables
2. Intent routing for data queries
3. Error handling that doesn't expose internals
4. Basic deployment documentation

**Should ship if time permits:**
1. Metadata query integration (already built, just wire up)
2. Compliance query integration (already built)
3. Entity recognition validation (already configured)

**Defer to v2.2+:**
1. Rich column descriptions in schema DDL
2. Query caching
3. Multi-turn conversation
4. Confidence scoring

---

## Sources

### Orbit (schmitech/orbit)
- [GitHub - schmitech/orbit](https://github.com/schmitech/orbit) - Main repository
- [Orbit Docker README](https://github.com/schmitech/orbit/blob/main/docker/README.md) - Deployment configuration
- [schmitech-orbit-client on PyPI](https://libraries.io/pypi/schmitech-orbit-client) - Python client library

### Text-to-SQL Best Practices
- [Google Cloud: Techniques for improving text-to-SQL](https://cloud.google.com/blog/products/databases/techniques-for-improving-text-to-sql)
- [Text to SQL: The Ultimate Guide for 2025](https://medium.com/@ayushgs/text-to-sql-the-ultimate-guide-for-2025-3fa4e78cbdf9)
- [LLM & AI Models for Text-to-SQL: Modern Frameworks](https://promethium.ai/guides/llm-ai-models-text-to-sql/)
- [Exploring RAG based approaches for Text-to-SQL](https://blog.nilenso.com/blog/2025/05/15/exploring-rag-based-approach-for-text-to-sql/)

### DuckDB Documentation
- [DuckDB: Describe](https://duckdb.org/docs/stable/guides/meta/describe) - Schema introspection
- [DuckDB: Information Schema](https://duckdb.org/docs/stable/sql/meta/information_schema) - Metadata views
- [Agentic AI with DuckDB and smolagents](https://buckenhofer.com/2025/11/agentic-ai-with-duckdb-and-smolagents-natural-language-queries-for-analytics/)
- [duckdb-nsql on Ollama](https://ollama.com/library/duckdb-nsql) - Specialized DuckDB text-to-SQL model

### LLM Gateway Patterns
- [Top 5 LLM Gateways in 2025](https://www.getmaxim.ai/articles/top-5-llm-gateways-in-2025-the-definitive-guide-for-production-ai-applications/)
- [Intent-Driven Natural Language Interface](https://medium.com/data-science-collective/intent-driven-natural-language-interface-a-hybrid-llm-intent-classification-approach-e1d96ad6f35d)

### Confidence Notes
- **HIGH:** Existing JobForge implementation details (direct code inspection)
- **MEDIUM:** Orbit features and configuration patterns (documentation + WebSearch)
- **MEDIUM:** Text-to-SQL best practices (multiple authoritative sources agree)
- **LOW:** Specific Orbit DuckDBRetriever patterns (sparse documentation; inferred from similar retrievers)
