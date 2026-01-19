---
phase: 05-data-governance-lineage
plan: 03
subsystem: governance
tags: [lineage, query-engine, NLP, CLI, provenance]

dependency-graph:
  requires:
    - "05-01: LineageGraph for DAG traversal"
    - "05-02: CatalogueGenerator for table metadata"
  provides:
    - "LineageQueryEngine class"
    - "/lineage CLI command"
    - "Natural language lineage queries"
  affects:
    - "Future: governance dashboards can use query engine"
    - "Future: chatbot integration for lineage questions"

tech-stack:
  added: []
  patterns:
    - "Rule-based NLP with regex pattern matching"
    - "Lazy graph building for performance"
    - "Rich console output for CLI"

key-files:
  created:
    - src/jobforge/governance/query.py
    - tests/test_lineage_query.py
  modified:
    - src/jobforge/governance/__init__.py
    - src/jobforge/cli/commands.py

decisions:
  - id: "RULE_BASED_NLP"
    choice: "Regex pattern matching instead of LLM/ML"
    reason: "Deterministic, fast, no dependencies, sufficient for structured queries"
  - id: "LAZY_GRAPH_BUILD"
    choice: "Build graph on first query via _ensure_graph_built()"
    reason: "Avoid unnecessary I/O if engine created but never used"
  - id: "LAYER_DESCRIPTIONS"
    choice: "Human-readable layer names in output"
    reason: "Better UX than raw layer codes (staged vs 'Staged (raw)')"

metrics:
  duration: "~8 minutes"
  completed: "2026-01-19"
---

# Phase 05 Plan 03: Lineage Query Engine Summary

**One-liner:** LineageQueryEngine parses natural language questions like "Where does DIM NOC come from?" using regex patterns and returns formatted answers with provenance metadata (transforms, layers, pipeline path).

## What Was Built

### LineageQueryEngine Class
Created `src/jobforge/governance/query.py` with:
- **Pattern matching:** 7 regex patterns for query recognition
- **Query handlers:** `_handle_upstream()`, `_handle_downstream()`, `_handle_path()`, `_handle_full_lineage()`
- **Table normalization:** Case-insensitive, space-to-underscore conversion
- **Provenance formatting:** Layer descriptions, transform names, pipeline path visualization
- **Error handling:** Helpful messages for unknown tables and unrecognized queries

### Supported Query Patterns

| Pattern | Example | Handler |
|---------|---------|---------|
| "Where does X come from?" | "Where does dim_noc come from?" | upstream |
| "What feeds X?" | "What tables feed cops_employment?" | upstream |
| "What depends on X?" | "What depends on dim_noc?" | downstream |
| "What does X feed?" | "What does noc_structure feed?" | downstream |
| "Show lineage for X" | "Show lineage for dim_noc" | full |
| "Lineage of X" | "Lineage of cops_employment" | full |
| "Path from X to Y" | "Path from dim_noc to dim_noc" | path |
| "How does X become Y?" | "How does noc_structure become dim_noc?" | path |

### CLI Command
Added `/lineage` command to `src/jobforge/cli/commands.py`:
```bash
jobforge lineage "Where does dim_noc come from?"
jobforge lineage "What tables feed cops_employment?"
jobforge lineage "Show lineage for dim_noc"
```

### Test Coverage
34 tests in `tests/test_lineage_query.py`:
- Pattern matching (10 tests)
- Upstream queries (3 tests)
- Downstream queries (2 tests)
- Path queries (3 tests)
- Full lineage (2 tests)
- Provenance metadata (3 tests)
- Edge cases (5 tests)
- Engine initialization (2 tests)
- Table name normalization (4 tests)

## Key Implementation Details

### Pattern Matching
```python
patterns = [
    (re.compile(r"where\s+does\s+([a-zA-Z0-9_\s]+?)\s+come\s+from", re.I),
     self._handle_upstream),
    # ... 6 more patterns
]
```

### Answer Formatting
Answers include:
- **Layer grouping:** Tables organized by medallion layer
- **Layer descriptions:** Human-readable names (e.g., "Gold (consumption)")
- **Transform info:** Functions applied at each step
- **Pipeline path:** Compact arrow notation (e.g., `dim_noc[S] -> dim_noc[B] -> dim_noc[G]`)

### Example Output
```
Upstream lineage for 'dim_noc' (Gold (consumption)):

Staged (raw):
  - dim_noc [Staged (raw)]

Bronze (validated):
  - dim_noc [Bronze (validated)] (transforms: rename_columns, cast_types)

Silver (transformed):
  - dim_noc [Silver (transformed)] (transforms: filter_unit_groups, derive_unit_group_id)

Pipeline path:
  dim_noc[G]
```

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

| Check | Result |
|-------|--------|
| Module imports | OK |
| CLI command works | OK |
| Upstream query (dim_noc) | Shows staged/bronze/silver path |
| Upstream query (cops_employment) | Shows staged/bronze/silver path |
| Provenance in answers | Transforms, layers visible |
| All tests pass | 34/34 |
| Test file lines | 334 (min: 60) |

## Success Criteria Verification

| Criterion | Status |
|-----------|--------|
| LineageQueryEngine parses 5+ query patterns | 7 patterns |
| Answers include provenance metadata | transforms, layers, path |
| /lineage CLI command works | Verified |
| "Where does DIM NOC come from?" returns pipeline path | Verified |
| "What tables feed cops_employment?" returns upstream | Verified |
| All tests pass | 34/34 |

## Phase 05 Completion

With 05-03 complete, Phase 05 (Data Governance and Lineage) is **COMPLETE**:
- **05-01:** LineageGraph (NetworkX DAG from transition logs)
- **05-02:** CatalogueGenerator (24 table JSON catalogues)
- **05-03:** LineageQueryEngine (/lineage CLI for natural language queries)

All CONV-01 requirements satisfied:
- Users can ask "Where does DIM NOC come from?" and get pipeline path
- Users can ask "What tables feed FACT NOC COPS?" and get upstream dependencies
- Lineage answers include provenance metadata (transforms, layers)
