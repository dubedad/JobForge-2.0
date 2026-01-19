# Phase 5: Data Governance and Lineage - Research

**Researched:** 2026-01-19
**Domain:** Data Governance, Data Lineage, Data Catalogue, Conversational Queries
**Confidence:** MEDIUM

## Summary

This phase transforms WiQ from a data pipeline into a self-documenting, explainable data system. The project already has substantial infrastructure in place: 130+ lineage JSON files tracking layer transitions, Pydantic models for TableMetadata and LayerTransitionLog, and a CatalogManager with JSON storage. The challenge is to aggregate this existing infrastructure into a queryable lineage graph and generate comprehensive data catalogue documentation.

The research reveals two key insights: (1) The existing transition log format is very close to the OpenLineage standard, and alignment is straightforward without requiring external dependencies; (2) NetworkX is the standard Python library for building and querying in-memory lineage graphs, avoiding the complexity of graph databases for this scale of data.

**Primary recommendation:** Build a lightweight LineageGraph class using NetworkX that aggregates existing JSON transition logs into a queryable DAG, paired with a rule-based query interpreter for natural language lineage questions.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| networkx | 3.x | Lineage graph representation and traversal | Industry standard for Python graph analysis; used by SQLLineage, Tokern, and other lineage tools |
| pydantic | 2.x | Data models for catalogue and lineage | Already in use; provides validation, JSON serialization, schema export |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| (no new libraries) | - | Existing stack sufficient | - |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| NetworkX | Neo4j | Overkill for ~50 tables; adds infrastructure complexity |
| NetworkX | DuckDB + DuckPGQ | Powerful but adds SQL/PGQ learning curve; NetworkX simpler for Python-first queries |
| NetworkX | Simple dict traversal | Works for small graphs but NetworkX provides algorithms (BFS, shortest path) for free |

**Installation:**
```bash
pip install networkx
# networkx has no required dependencies
```

## Architecture Patterns

### Recommended Project Structure
```
src/jobforge/
  governance/
    __init__.py
    graph.py          # LineageGraph class using NetworkX
    catalogue.py      # DataCatalogue generation from schema + metadata
    query.py          # LineageQueryEngine for natural language
    models.py         # Pydantic models for catalogue artifacts
```

### Pattern 1: Aggregated Lineage Graph

**What:** Build a single NetworkX DiGraph from individual transition logs at query time
**When to use:** When user asks lineage questions; lazy-load pattern
**Example:**
```python
import networkx as nx
from pathlib import Path
import json

class LineageGraph:
    """Aggregates transition logs into queryable DAG."""

    def __init__(self, lineage_dir: Path):
        self.lineage_dir = lineage_dir
        self._graph: nx.DiGraph | None = None

    def build_graph(self) -> nx.DiGraph:
        """Build DAG from all transition log JSON files."""
        G = nx.DiGraph()

        for json_file in self.lineage_dir.glob("*.json"):
            log = json.loads(json_file.read_text())

            # Extract table name from file path
            target_table = Path(log["target_file"]).stem
            target_node = f"{log['target_layer']}.{target_table}"

            # Add target node with metadata
            G.add_node(target_node,
                layer=log["target_layer"],
                table=target_table,
                row_count=log["row_count_out"],
                transforms=log["transforms_applied"])

            # Add edges from each source
            for source_file in log["source_files"]:
                source_table = Path(source_file).stem
                source_node = f"{log['source_layer']}.{source_table}"

                G.add_node(source_node,
                    layer=log["source_layer"],
                    table=source_table)

                G.add_edge(source_node, target_node,
                    transition_id=log["transition_id"],
                    transforms=log["transforms_applied"])

        self._graph = G
        return G

    def get_upstream(self, table: str, layer: str = "gold") -> list[str]:
        """Get all upstream dependencies using BFS."""
        node = f"{layer}.{table}"
        if node not in self._graph:
            return []
        # Traverse in reverse direction (predecessors)
        return list(nx.ancestors(self._graph, node))

    def get_downstream(self, table: str, layer: str = "staged") -> list[str]:
        """Get all downstream dependents."""
        node = f"{layer}.{table}"
        if node not in self._graph:
            return []
        return list(nx.descendants(self._graph, node))

    def get_path(self, source_table: str, target_table: str) -> list[str]:
        """Get transformation path between tables."""
        # Find nodes across layers
        source_nodes = [n for n in self._graph.nodes if n.endswith(f".{source_table}")]
        target_nodes = [n for n in self._graph.nodes if n.endswith(f".{target_table}")]

        for src in source_nodes:
            for tgt in target_nodes:
                try:
                    return nx.shortest_path(self._graph, src, tgt)
                except nx.NetworkXNoPath:
                    continue
        return []
```

### Pattern 2: Rule-Based Query Interpreter

**What:** Map natural language patterns to graph operations without LLM
**When to use:** For simple, predictable lineage questions
**Example:**
```python
import re
from typing import Callable

class LineageQueryEngine:
    """Rule-based natural language to graph query."""

    def __init__(self, graph: LineageGraph):
        self.graph = graph
        self.patterns: list[tuple[re.Pattern, Callable]] = [
            # "Where does X come from?"
            (re.compile(r"where does (\w+) come from", re.I),
             self._handle_upstream),
            # "What feeds X?" / "What tables feed X?"
            (re.compile(r"what (?:tables? )?feeds? (\w+)", re.I),
             self._handle_upstream),
            # "What does X feed?" / "What depends on X?"
            (re.compile(r"what (?:does )?(\w+) feed", re.I),
             self._handle_downstream),
            (re.compile(r"what depends on (\w+)", re.I),
             self._handle_downstream),
            # "Show lineage for X" / "Lineage of X"
            (re.compile(r"(?:show )?lineage (?:for |of )?(\w+)", re.I),
             self._handle_full_lineage),
            # "How does X become Y?" / "Path from X to Y"
            (re.compile(r"how does (\w+) become (\w+)", re.I),
             self._handle_path),
            (re.compile(r"path from (\w+) to (\w+)", re.I),
             self._handle_path),
        ]

    def query(self, question: str) -> str:
        """Process natural language question, return human-readable answer."""
        for pattern, handler in self.patterns:
            match = pattern.search(question)
            if match:
                return handler(*match.groups())

        return ("I don't understand that question. Try:\n"
                "- 'Where does dim_noc come from?'\n"
                "- 'What tables feed fact_employment?'\n"
                "- 'How does noc_structure become dim_noc?'")

    def _handle_upstream(self, table: str) -> str:
        """Format upstream lineage answer."""
        upstream = self.graph.get_upstream(table)
        if not upstream:
            return f"No upstream dependencies found for '{table}'."

        # Group by layer
        by_layer = {}
        for node in upstream:
            layer, name = node.split(".", 1)
            by_layer.setdefault(layer, []).append(name)

        lines = [f"'{table}' comes from:"]
        for layer in ["staged", "bronze", "silver"]:
            if layer in by_layer:
                tables = ", ".join(sorted(by_layer[layer]))
                lines.append(f"  {layer}: {tables}")

        return "\n".join(lines)

    def _handle_downstream(self, table: str) -> str:
        """Format downstream lineage answer."""
        downstream = self.graph.get_downstream(table)
        if not downstream:
            return f"No downstream dependents found for '{table}'."

        by_layer = {}
        for node in downstream:
            layer, name = node.split(".", 1)
            by_layer.setdefault(layer, []).append(name)

        lines = [f"'{table}' feeds:"]
        for layer in ["bronze", "silver", "gold"]:
            if layer in by_layer:
                tables = ", ".join(sorted(by_layer[layer]))
                lines.append(f"  {layer}: {tables}")

        return "\n".join(lines)

    def _handle_full_lineage(self, table: str) -> str:
        """Show both upstream and downstream."""
        up = self._handle_upstream(table)
        down = self._handle_downstream(table)
        return f"{up}\n\n{down}"

    def _handle_path(self, source: str, target: str) -> str:
        """Show transformation path."""
        path = self.graph.get_path(source, target)
        if not path:
            return f"No path found from '{source}' to '{target}'."

        # Format as flow
        lines = [f"Transformation path from '{source}' to '{target}':"]
        for i, node in enumerate(path):
            layer, name = node.split(".", 1)
            prefix = "  " if i == 0 else "  -> "
            lines.append(f"{prefix}[{layer}] {name}")

        return "\n".join(lines)
```

### Pattern 3: Data Catalogue Generation

**What:** Generate catalogue JSON files from WiQ schema and parquet metadata
**When to use:** After pipeline run to update documentation
**Example:**
```python
from pathlib import Path
from datetime import datetime, timezone
import polars as pl
from pydantic import BaseModel

class CatalogueTable(BaseModel):
    """Data catalogue entry for a table."""
    table_name: str
    layer: str
    table_type: str  # "dim", "fact", "bridge"
    description: str
    business_purpose: str
    source_system: str
    row_count: int
    file_size_bytes: int
    columns: list["CatalogueColumn"]
    upstream_tables: list[str]
    last_updated: datetime

class CatalogueColumn(BaseModel):
    """Data catalogue entry for a column."""
    name: str
    data_type: str
    is_primary_key: bool
    is_foreign_key: bool
    references_table: str | None
    description: str
    example_values: list[str]

def generate_catalogue(
    schema_path: Path,
    gold_dir: Path,
    lineage_graph: "LineageGraph"
) -> list[CatalogueTable]:
    """Generate catalogue from schema and physical files."""
    import json

    schema = json.loads(schema_path.read_text())
    catalogue = []

    for table_def in schema["tables"]:
        table_name = table_def["name"]
        parquet_path = gold_dir / f"{table_name}.parquet"

        # Get physical metadata if file exists
        if parquet_path.exists():
            lf = pl.scan_parquet(parquet_path)
            row_count = lf.select(pl.len()).collect().item()
            file_size = parquet_path.stat().st_size

            # Sample values for documentation
            sample = lf.head(5).collect()
        else:
            row_count = 0
            file_size = 0
            sample = None

        # Get upstream from lineage
        upstream = lineage_graph.get_upstream(table_name, "gold")

        # Build column metadata
        columns = []
        for col_def in table_def["columns"]:
            examples = []
            if sample is not None and col_def["name"] in sample.columns:
                examples = [str(v) for v in sample[col_def["name"]].to_list()[:3]]

            columns.append(CatalogueColumn(
                name=col_def["name"],
                data_type=col_def["data_type"],
                is_primary_key=col_def.get("is_primary_key", False),
                is_foreign_key=col_def.get("is_foreign_key", False),
                references_table=col_def.get("references_table"),
                description=col_def.get("description", ""),
                example_values=examples
            ))

        catalogue.append(CatalogueTable(
            table_name=table_name,
            layer="gold",
            table_type=table_def.get("table_type", "unknown"),
            description=table_def.get("description", f"Gold layer table {table_name}"),
            business_purpose="",  # To be filled manually or via glossary
            source_system="JobForge WiQ Pipeline",
            row_count=row_count,
            file_size_bytes=file_size,
            columns=columns,
            upstream_tables=[n.split(".")[-1] for n in upstream],
            last_updated=datetime.now(timezone.utc)
        ))

    return catalogue
```

### Anti-Patterns to Avoid
- **Building full graph on every query:** Cache the built graph; only rebuild when transition logs change
- **Storing lineage in a separate database:** Keep it simple with JSON + in-memory graph; no need for Neo4j at this scale
- **Column-level lineage without clear use case:** Table-level lineage covers requirements; column-level adds complexity without immediate value
- **LLM for every query:** Rule-based patterns handle the defined query types; LLM is overkill for predictable questions

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Graph traversal algorithms | Custom BFS/DFS | NetworkX `ancestors()`, `descendants()`, `shortest_path()` | Optimized, tested, handles edge cases |
| JSON validation | Manual field checks | Pydantic models | Type safety, automatic validation, schema export |
| Graph cycle detection | Manual visited set | NetworkX `is_directed_acyclic_graph()` | Lineage should be acyclic; detect corruption |
| Topological sort | Custom implementation | NetworkX `topological_sort()` | Useful for understanding execution order |

**Key insight:** NetworkX provides all the graph algorithms needed for lineage queries. The ~130 transition logs create a graph with ~50-100 nodes maximum - well within in-memory processing capability.

## Common Pitfalls

### Pitfall 1: Treating Lineage as One-Time Generation
**What goes wrong:** Catalogue becomes stale as pipeline evolves
**Why it happens:** Lineage not integrated into pipeline execution
**How to avoid:** Generate/update catalogue as part of each pipeline run, not as a separate step
**Warning signs:** Catalogue shows old row counts, missing new tables

### Pitfall 2: Multiple Paths in Lineage Graph
**What goes wrong:** Same table appears at multiple layers with different batch IDs
**Why it happens:** Re-runs create new transition logs without invalidating old ones
**How to avoid:** Key lineage by logical path (source_layer + source_table -> target_layer + target_table), not by transition_id; aggregate multiple runs
**Warning signs:** `get_upstream()` returns duplicate tables

### Pitfall 3: Incomplete Upstream Tracking
**What goes wrong:** Lineage shows immediate parent but not full ancestry
**Why it happens:** Only tracking one level of transitions
**How to avoid:** Use `nx.ancestors()` for complete upstream, not just `predecessors()`
**Warning signs:** "Where does X come from?" only shows silver layer, not bronze/staged

### Pitfall 4: Hardcoded Layer Names
**What goes wrong:** Code breaks when layer naming changes
**Why it happens:** String literals throughout codebase
**How to avoid:** Use Layer enum from `pipeline.config` consistently
**Warning signs:** References to "staged", "bronze" strings scattered in code

### Pitfall 5: Over-Scoping Catalogue Content
**What goes wrong:** Trying to document everything leads to nothing documented well
**Why it happens:** Perfectionism about data governance
**How to avoid:** Start with GOV-01 requirements: table names, column names, types, source system, descriptions. Add more later.
**Warning signs:** Stalled progress on "business glossary integration"

## Code Examples

Verified patterns from research:

### NetworkX Graph Traversal
```python
# Source: NetworkX documentation
import networkx as nx

# Create directed graph
G = nx.DiGraph()
G.add_edge("staged.noc", "bronze.noc")
G.add_edge("bronze.noc", "silver.noc")
G.add_edge("silver.noc", "gold.dim_noc")

# All ancestors (full upstream)
upstream = nx.ancestors(G, "gold.dim_noc")
# Returns: {"staged.noc", "bronze.noc", "silver.noc"}

# All descendants (full downstream)
downstream = nx.descendants(G, "staged.noc")
# Returns: {"bronze.noc", "silver.noc", "gold.dim_noc"}

# Shortest path
path = nx.shortest_path(G, "staged.noc", "gold.dim_noc")
# Returns: ["staged.noc", "bronze.noc", "silver.noc", "gold.dim_noc"]

# Check if DAG (should be True for lineage)
is_valid = nx.is_directed_acyclic_graph(G)
```

### Pydantic Model with JSON Export
```python
# Source: Existing project pattern (models.py)
from pydantic import BaseModel, Field
from datetime import datetime

class CatalogueEntry(BaseModel):
    """Pydantic model for catalogue JSON files."""

    model_config = {"json_encoders": {datetime: lambda v: v.isoformat()}}

    table_name: str = Field(description="Logical table name")
    columns: list[dict] = Field(default_factory=list)

    def save(self, path: Path) -> None:
        path.write_text(self.model_dump_json(indent=2))

    @classmethod
    def load(cls, path: Path) -> "CatalogueEntry":
        return cls.model_validate_json(path.read_text())
```

### Aggregating Transition Logs
```python
# Source: Adapted from existing CatalogManager.get_lineage_logs()
from pathlib import Path
import json

def load_all_transitions(lineage_dir: Path) -> list[dict]:
    """Load and deduplicate transition logs."""
    transitions = []
    seen_paths = set()  # Dedupe by logical path

    for json_file in sorted(lineage_dir.glob("*.json"),
                           key=lambda p: p.stat().st_mtime,
                           reverse=True):  # Newest first
        log = json.loads(json_file.read_text())

        # Create logical path key
        target = Path(log["target_file"]).stem
        path_key = (log["source_layer"], log["target_layer"], target)

        if path_key not in seen_paths:
            transitions.append(log)
            seen_paths.add(path_key)

    return transitions
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual lineage documentation | Automated from transition logs | 2024 | No manual maintenance needed |
| Enterprise tools (Collibra, Atlan) | Open standards (OpenLineage) + simple tools | 2023-2024 | Vendor-neutral, no licensing |
| Graph databases for lineage | In-memory graph (NetworkX) for small scale | Always | Right-sizing to problem |
| LLM for all NL queries | Rule-based for predictable patterns | 2025 | Lower latency, no API costs |

**Deprecated/outdated:**
- Custom graph traversal: Use NetworkX algorithms
- Storing lineage in relational tables: JSON + NetworkX more flexible for hierarchical queries

## Open Questions

Things that couldn't be fully resolved:

1. **Business Descriptions for Columns**
   - What we know: Technical metadata can be auto-generated from schema
   - What's unclear: Where do business descriptions come from? Manual entry? Glossary file?
   - Recommendation: Start with empty descriptions; add glossary.json file for manual enrichment later

2. **Handling Multiple Pipeline Runs**
   - What we know: Each run creates new transition logs with different batch_ids
   - What's unclear: Should catalogue show latest run only, or aggregate across runs?
   - Recommendation: Dedupe by logical path, keep most recent transition; store history separately if needed

3. **Lineage for Source Files**
   - What we know: Transition logs track staged -> bronze -> silver -> gold
   - What's unclear: How to represent "source system" for CSV files?
   - Recommendation: Source system is the filename; lineage stops at staged layer

## Sources

### Primary (HIGH confidence)
- NetworkX documentation - graph algorithms, BFS traversal, ancestors/descendants
- Existing project code: `models.py`, `catalog.py`, `layers.py` - Pydantic patterns, transition log structure
- OpenLineage specification - standard lineage schema (for reference, not dependency)

### Secondary (MEDIUM confidence)
- [Data Lineage Analysis with Python and NetworkX](https://www.rittmanmead.com/blog/2024/08/data-lineage-analysis-with-python-and-networkx/) - industry patterns
- [SQLLineage](https://github.com/reata/sqllineage) - NetworkX-based lineage tool architecture
- [dbt Catalog JSON Schema](https://schemas.getdbt.com/dbt/catalog/v1.json) - catalogue structure reference
- [OpenLineage GitHub](https://github.com/OpenLineage/OpenLineage) - event schema structure

### Tertiary (LOW confidence)
- [Natural language to SQL patterns](https://dzone.com/articles/building-sqlgenie-a-natural-language-to-sql-query) - rule-based query approaches
- [Data Lineage Pitfalls](https://www.montecarlodata.com/blog-data-lineage/) - common implementation mistakes

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - NetworkX is well-established, Pydantic already in use
- Architecture: MEDIUM - Patterns adapted from industry examples, not battle-tested in this project
- Pitfalls: MEDIUM - Drawn from general best practices, project-specific issues may differ

**Research date:** 2026-01-19
**Valid until:** 30 days (stable domain, established patterns)

---

## Alignment with Existing Infrastructure

### What Already Exists
1. **LayerTransitionLog model** (`models.py`): Captures source_layer, target_layer, source_files, target_file, transforms_applied, timestamps
2. **130+ transition JSON files** (`data/catalog/lineage/`): Complete transition history
3. **CatalogManager** (`catalog.py`): Has `get_lineage_logs()` method, saves/loads TableMetadata
4. **WiQ schema** (`data/catalog/schemas/wiq_schema.json`): Table definitions with columns, types, FK relationships
5. **Catalog directory structure**: tables/, lineage/, glossary/, schemas/

### What Needs to Be Built
1. **LineageGraph class**: NetworkX DAG built from transition logs
2. **LineageQueryEngine**: Rule-based NL query interpreter
3. **Catalogue generator**: Creates table documentation from schema + physical files
4. **CLI or API**: Entry point for "Where does X come from?" queries

### Integration Points
- Read from: `config.catalog_lineage_path()` for transition logs
- Read from: `config.catalog_schemas_path()` for WiQ schema
- Write to: `config.catalog_tables_path()` for catalogue JSON files
- Use: Existing Pydantic models as base for new governance models
