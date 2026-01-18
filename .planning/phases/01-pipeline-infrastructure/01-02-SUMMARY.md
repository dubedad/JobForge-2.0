---
phase: 01-pipeline-infrastructure
plan: 02
subsystem: pipeline
tags: [polars, medallion-architecture, data-pipeline, provenance, layer-transitions]

# Dependency graph
requires:
  - 01-01 (Pydantic models, PipelineConfig, directory structure)
provides:
  - Pipeline engine for orchestrating medallion layer transitions
  - Provenance column helpers for DataFrames
  - Layer classes with DAMA-compliant responsibilities
  - LayerTransitionLog persistence to catalog/lineage/
affects:
  - 01-03-PLAN (metadata catalog will use transition logs)
  - Phase 2 (data ingestion will use PipelineEngine)
  - All phases using data pipeline

# Tech tracking
tech-stack:
  added: []
  patterns: [layer-promotion, batch-tracking, transition-logging, lazy-evaluation]

key-files:
  created:
    - src/jobforge/pipeline/provenance.py
    - src/jobforge/pipeline/layers.py
    - src/jobforge/pipeline/engine.py
  modified:
    - src/jobforge/pipeline/__init__.py

key-decisions:
  - "Use scan_parquet for lazy evaluation, not read_parquet().lazy()"
  - "Layer classes return tuples with paths, batch_id, and row counts for logging"
  - "Transition logs saved as JSON to catalog/lineage/{transition_id}.json"
  - "Initial ingestion logged as staged->bronze transition due to model enum constraints"

patterns-established:
  - "Provenance columns added at staged layer, updated on each promotion"
  - "Each layer promotion creates LayerTransitionLog with row counts and transforms"
  - "structlog integration for audit trail logging"
  - "zstd compression for all parquet output"

# Metrics
duration: 5min
completed: 2026-01-18
---

# Phase 1 Plan 2: Pipeline Engine Summary

**Core pipeline engine with medallion layer classes, provenance helpers, and transition logging - data flows from staged through gold with full audit trail**

## Performance

- **Duration:** 5 min
- **Started:** 2026-01-18T18:43:00Z
- **Completed:** 2026-01-18T18:48:00Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Provenance helper functions for adding audit columns to Polars LazyFrames
- Four medallion layer classes with DAMA DMBOK-compliant responsibilities
- PipelineEngine orchestrator for data flow through all layers
- LayerTransitionLog persistence for each layer promotion
- Full integration test passing: source -> staged -> bronze -> silver -> gold

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Provenance Helpers** - `8fdd156` (feat)
2. **Task 2: Create Layer Classes** - `662d7d3` (feat)
3. **Task 3: Create Pipeline Engine** - `c23301e` (feat)
4. **Exports Update** - `2cb0ce5` (chore)

## Files Created/Modified

- `src/jobforge/pipeline/provenance.py` - Provenance column helpers (generate_batch_id, add_provenance_columns, update_layer_column)
- `src/jobforge/pipeline/layers.py` - Layer classes (StagedLayer, BronzeLayer, SilverLayer, GoldLayer)
- `src/jobforge/pipeline/engine.py` - PipelineEngine orchestrator with ingest/promote methods
- `src/jobforge/pipeline/__init__.py` - Updated exports for new modules

## Key Implementation Details

### Provenance Columns

Standard columns added to every DataFrame:
- `_source_file`: Original source file path
- `_ingested_at`: UTC timestamp (updated on each promotion)
- `_batch_id`: UUID linking records across layers
- `_layer`: Current medallion layer name

### Layer Responsibilities

| Layer | Allowed Operations | Forbidden |
|-------|-------------------|-----------|
| Staged | Add provenance, convert to parquet | Any data modification |
| Bronze | Column rename, type cast | Business logic |
| Silver | Cleaning, dedup, validation | Raw source changes |
| Gold | Derived fields, aggregations | None |

### PipelineEngine Methods

- `ingest(source_path, table_name, domain)` - Entry point for new data
- `promote_to_bronze(staged_path, schema)` - Schema enforcement
- `promote_to_silver(bronze_path, transforms)` - Data cleaning
- `promote_to_gold(silver_path, transforms)` - Business models
- `run_full_pipeline(...)` - Convenience method for end-to-end processing

## Decisions Made

1. **scan_parquet for lazy evaluation** - Per plan requirements, all reads use `pl.scan_parquet()` not `pl.read_parquet().lazy()` for optimal memory usage.

2. **Layer return signatures** - Each layer method returns tuple with path, batch_id, and row counts to enable transition logging without extra queries.

3. **JSON transition logs** - Logs saved to `catalog/lineage/{transition_id}.json` using Pydantic's `model_dump_json()` for schema compliance.

4. **Initial ingestion logging** - The ingest operation is logged as a staged->bronze transition (using "bronze" as target_layer) because the LayerTransitionLog model requires valid enum values for both source and target layers.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all tasks completed successfully on first attempt.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Pipeline engine fully functional for data ingestion
- Integration test confirms end-to-end flow works
- Ready for Plan 01-03 (Metadata Catalog)
- Ready for Phase 2 (Data Ingestion) to use PipelineEngine

---
*Phase: 01-pipeline-infrastructure*
*Completed: 2026-01-18*
