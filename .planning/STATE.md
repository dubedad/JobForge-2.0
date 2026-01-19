# Project State: JobForge 2.0

**Last Updated:** 2026-01-19

## Project Reference

**Core Value:** Auditable provenance from source to output - every artifact traces back to authoritative sources with DADM compliance scoring.

**Current Focus:** Phase 5 (Data Governance and Lineage) IN PROGRESS. LineageGraph built from 123 transition logs, enabling upstream/downstream queries.

## Current Position

**Phase:** 5 of 5 (Data Governance and Lineage)
**Plan:** 1 of 3 complete
**Status:** In Progress
**Last activity:** 2026-01-19 - Completed 05-01-PLAN.md (LineageGraph with NetworkX)

```
[██████████████████████████████░░] 91% (10/11 plans)
```

## Phases Overview

| Phase | Name | Status |
|-------|------|--------|
| 1 | Pipeline Infrastructure | Complete (3/3 plans) |
| 2 | Data Ingestion | Complete (3/3 plans) |
| 3 | WiQ Semantic Model | Complete (2/2 plans) |
| 4 | Power BI Deployment | Complete (2/2 plans) |
| 5 | Data Governance and Lineage | In Progress (1/3 plans) |

## Performance Metrics

| Metric | Value |
|--------|-------|
| Plans completed | 10 |
| Requirements delivered | 9/10 |
| Phases completed | 4/5 |
| Blockers encountered | 0 |
| Blockers resolved | 0 |

## Accumulated Context

### Key Decisions

| Decision | Rationale | Phase |
|----------|-----------|-------|
| Linear phase dependency | Each phase produces output consumed by next; no parallel tracks for v1 | Roadmap |
| Pipeline before semantic model | Cannot define relationships without data to relate | Roadmap |
| GOV + CONV in same phase | Both require stable semantic model; both about explainability | Roadmap |
| Serialization aliases for provenance | Pydantic disallows underscore-prefixed field names; use alias for serialization | 01-01 |
| Separate catalog directories | DAMA DMBOK structure: tables, lineage, glossary, schemas | 01-01 |
| scan_parquet for lazy evaluation | Use scan_parquet() not read_parquet().lazy() for optimal memory | 01-02 |
| JSON transition logs | Logs saved to catalog/lineage/{transition_id}.json using Pydantic | 01-02 |
| CatalogManager JSON storage | Table metadata saved as {table_name}.json for debugging/readability | 01-03 |
| DuckDB views not tables | Using CREATE VIEW for gold parquet keeps data in parquet, no duplication | 01-03 |
| Persistent DuckDB connection | GoldQueryEngine maintains one connection for all queries | 01-03 |
| Cast noc_code to Utf8 | Polars infers numeric-looking strings as int64, losing leading zeros | 02-01 |
| Float reconstruction for OaSIS codes | Reconstruct XXXXX.YY format from Polars f64 inference using floor/modulo | 02-02 |
| Filter 00000 aggregate | 00000 is "All occupations" aggregate, exclude from unit_group_id derivation | 02-03 |
| Flexible column rename | Filter rename dict to only existing columns for varying Job Architecture CSVs | 02-03 |
| Lineage node ID format | "{layer}.{table_name}" for unambiguous identification | 05-01 |

### Technical Discoveries

| Discovery | Details | Phase |
|-----------|---------|-------|
| Pydantic field naming | Cannot use `_source_file` as field name; must use `serialization_alias` | 01-01 |
| Polars CSV type inference | Numeric-looking strings like "00010" are inferred as int64; must cast to Utf8 | 02-01 |
| Polars float inference for decimals | "00010.00" is inferred as f64 (10.0); must reconstruct format from numeric value | 02-02 |
| NetworkX DAG from transition logs | 123 logs deduplicate to 106 nodes, 79 edges; use nx.ancestors/descendants for traversal | 05-01 |

### Pending Todos

| Todo | Area | Created |
|------|------|---------|
| DADM traceability log for Directive compliance | governance | 2026-01-19 |
| DAMA traceability log for DMBOK compliance | governance | 2026-01-19 |
| Job classification log for Classification Policy compliance | governance | 2026-01-19 |

*3 todos pending in `.planning/todos/pending/`*

### Blockers

None active.

## Session Continuity

### Last Session

**Date:** 2026-01-19
**Activity:** Completed 05-01-PLAN.md - Built LineageGraph with NetworkX
**Outcome:** LineageGraph aggregates 123 transition logs into queryable DAG with upstream/downstream traversal. All tests pass.

### Next Session Priorities

1. Continue Phase 5: Plan 05-02 (LineageQueryEngine for natural language queries)
2. Complete Phase 5: Plan 05-03 (Data Catalogue generation integration)

### Context for Claude

When resuming this project:
- Phase 1 COMPLETE (3/3 plans) - Pipeline infrastructure
- Phase 2 COMPLETE (3/3 plans) - Data ingestion
- Phase 3 COMPLETE (2/2 plans) - WiQ semantic model
- Phase 4 COMPLETE (2/2 plans) - Power BI deployment tooling
- Phase 5 IN PROGRESS (1/3 plans) - Data Governance and Lineage
- jobforge package installable with `pip install -e .`
- PipelineEngine orchestrates medallion layer transitions
- Layer classes: StagedLayer, BronzeLayer, SilverLayer, GoldLayer
- Semantic model: src/jobforge/semantic/ with models.py, schema.py, validator.py, introspect.py
- Deployment: src/jobforge/deployment/ with mcp_client.py, deployer.py, ui.py, types.py
- **Governance: src/jobforge/governance/ with graph.py, models.py, catalogue.py**
- **LineageGraph: NetworkX DAG with get_upstream(), get_downstream(), get_path()**
- CLI: /stagegold command via commands.py
- CatalogManager: saves/loads table metadata, queries lineage logs
- GoldQueryEngine: DuckDB SQL on gold parquet files
- 123 lineage JSON files in data/catalog/lineage/
- WiQ schema exported to data/catalog/schemas/wiq_schema.json
- Tests: 53+ total
- Stack: Python 3.11, Polars 1.37+, DuckDB 1.4+, Pydantic 2.12+, structlog, pytest, Rich, NetworkX 3.0+

---
*State initialized: 2026-01-18*
*Session count: 9*
