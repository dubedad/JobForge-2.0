---
phase: 05
plan: 01
subsystem: governance
tags: [lineage, networkx, graph, dag, traversal]

dependency-graph:
  requires: [04-02]
  provides: [lineage-graph, upstream-queries, downstream-queries]
  affects: [05-02, 05-03]

tech-stack:
  added: [networkx>=3.0]
  patterns: [dag-traversal, lazy-loading, deduplication-by-logical-path]

key-files:
  created:
    - src/jobforge/governance/graph.py
    - src/jobforge/governance/models.py
    - tests/test_lineage_graph.py
  modified:
    - pyproject.toml
    - src/jobforge/governance/__init__.py

decisions:
  - id: lineage-node-id-format
    choice: "{layer}.{table_name}"
    rationale: Unambiguous identification of table at specific layer

metrics:
  duration: ~15 minutes
  completed: 2026-01-19
---

# Phase 5 Plan 1: Lineage Graph Summary

**One-liner:** NetworkX DAG built from 123 transition logs enabling upstream/downstream lineage queries via nx.ancestors() and nx.descendants().

## What Was Built

### LineageGraph Class (`src/jobforge/governance/graph.py`)

Aggregates layer transition logs into a queryable NetworkX directed acyclic graph:

- **build_graph()**: Loads all JSON transition logs from `data/catalog/lineage/`, deduplicates by logical path (keeping most recent), builds DAG with nodes for each table at each layer
- **get_upstream(table, layer)**: Returns full ancestry using `nx.ancestors()`
- **get_downstream(table, layer)**: Returns full dependents using `nx.descendants()`
- **get_path(source_table, target_table)**: Returns transformation path using `nx.shortest_path()`
- **get_node_metadata(node_id)**: Returns LineageNode with row_count, transforms
- **is_valid_dag()**: Validates no cycles exist in lineage

### Pydantic Models (`src/jobforge/governance/models.py`)

- **LineageNode**: Represents a table at a specific layer with metadata
- **LineageEdge**: Represents a transition between layers with timestamp

### Test Coverage (`tests/test_lineage_graph.py`)

13 tests covering:
- Graph building from real transition logs
- Upstream/downstream traversal correctness
- Path finding between tables
- Edge case handling (unknown tables)
- DAG validation

## Key Technical Details

### Node ID Format
```
{layer}.{table_name}
# Examples:
gold.dim_noc
staged.noc_structure
bronze.cops_employment
```

### Deduplication Strategy
Multiple pipeline runs create multiple transition logs for the same logical path. The graph keeps only the most recent transition per (source_layer, target_layer, target_table) tuple.

### Graph Statistics
- **Nodes:** 106 (tables across all layers)
- **Edges:** 79 (transitions between layers)
- **Source logs:** 123 JSON files

### Example Query
```python
from jobforge.governance import LineageGraph
from jobforge.pipeline.config import PipelineConfig

g = LineageGraph(PipelineConfig())
upstream = g.get_upstream("cops_employment", "gold")
# Returns: ['bronze.cops_employment', 'silver.cops_employment', 'staged.cops_employment']
```

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

| Check | Result |
|-------|--------|
| Module structure | __init__.py, models.py, graph.py present |
| Import works | `from jobforge.governance import LineageGraph` |
| Graph builds | 123 logs -> 106 nodes, 79 edges |
| Traversal works | get_upstream returns staged/bronze/silver ancestors |
| Tests pass | 12 passed, 1 skipped |

## Next Phase Readiness

Plan 05-01 provides the foundation for:
- **05-02**: LineageQueryEngine (natural language queries using this graph)
- **05-03**: Data Catalogue generation (catalogue.py already exists, needs integration)

### Blockers/Concerns
None.
