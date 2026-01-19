# Phase 3: WiQ Semantic Model - Research

**Researched:** 2026-01-18
**Domain:** Power BI Star Schema / Pydantic Data Modeling
**Confidence:** HIGH

## Summary

This research investigates how to create a machine-readable semantic model definition for Power BI consumption using Pydantic models. The WiQ schema must define dimensional relationships between gold layer parquet tables (DIM NOC as the hub dimension, connecting to attribute/fact tables via unit_group_id).

The standard approach is to define Pydantic models representing tables, columns, and relationships, then serialize to JSON for consumption by deployment scripts. Power BI requires specific relationship properties (cardinality, cross-filter direction, active status) that must be captured in the schema definition.

**Primary recommendation:** Create Pydantic models for `Table`, `Column`, and `Relationship` that serialize to JSON compatible with downstream deployment. Use DuckDB's `DESCRIBE` to introspect actual parquet schemas and validate against defined relationships.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pydantic | 2.12+ | Schema definition and validation | Already in codebase, generates JSON schema |
| DuckDB | 1.4+ | Parquet schema introspection | Already in codebase via GoldQueryEngine |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| structlog | existing | Logging schema operations | Consistent with codebase logging |
| pytest | existing | Schema validation tests | Verify relationships are valid |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pydantic models | TMDL files | TMDL is Power BI native but adds tooling complexity; Pydantic keeps consistency |
| Custom JSON | TMSL format | TMSL is deployment-ready but verbose; custom JSON is simpler for this phase |

**Installation:**
```bash
# No new dependencies - uses existing Pydantic 2.12+ and DuckDB 1.4+
```

## Architecture Patterns

### Recommended Project Structure
```
src/jobforge/
├── semantic/                    # NEW: Semantic model definitions
│   ├── __init__.py
│   ├── models.py               # Pydantic models for Table, Column, Relationship
│   ├── schema.py               # WiQ schema definition (the actual model)
│   └── validator.py            # Validation against gold parquet files
```

### Pattern 1: Relationship Definition Model
**What:** Pydantic models that capture Power BI relationship requirements
**When to use:** Defining any table-to-table relationship in the semantic model

```python
# Source: Microsoft Learn - Power BI Relationships
from pydantic import BaseModel
from typing import Literal
from enum import Enum

class Cardinality(str, Enum):
    ONE_TO_MANY = "1:*"
    MANY_TO_ONE = "*:1"
    ONE_TO_ONE = "1:1"
    MANY_TO_MANY = "*:*"

class CrossFilterDirection(str, Enum):
    SINGLE = "Single"
    BOTH = "Both"

class Relationship(BaseModel):
    """Power BI compatible relationship definition."""
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    cardinality: Cardinality
    cross_filter_direction: CrossFilterDirection = CrossFilterDirection.SINGLE
    is_active: bool = True

    model_config = {"use_enum_values": True}
```

### Pattern 2: Table Classification Model
**What:** Distinguish dimension tables from fact/attribute tables
**When to use:** Organizing tables by their role in the star schema

```python
# Source: Microsoft Learn - Star Schema Guidance
from pydantic import BaseModel
from typing import Literal

class TableType(str, Enum):
    DIMENSION = "dimension"
    FACT = "fact"
    ATTRIBUTE = "attribute"  # Links to dimension, contains descriptive data

class Column(BaseModel):
    """Column metadata for schema definition."""
    name: str
    data_type: str  # From DuckDB DESCRIBE
    is_primary_key: bool = False
    is_foreign_key: bool = False
    references_table: str | None = None

class Table(BaseModel):
    """Table definition in semantic model."""
    name: str
    table_type: TableType
    columns: list[Column]
    primary_key: str | None = None
```

### Pattern 3: Complete Schema Model
**What:** Root model containing all tables and relationships
**When to use:** Defining the complete WiQ semantic model

```python
class WiQSchema(BaseModel):
    """Complete semantic model definition."""
    name: str = "WiQ"
    tables: list[Table]
    relationships: list[Relationship]

    def to_json(self) -> str:
        """Export for deployment scripts."""
        return self.model_dump_json(indent=2)

    def get_dimension_tables(self) -> list[Table]:
        return [t for t in self.tables if t.table_type == TableType.DIMENSION]

    def get_relationships_for_table(self, table_name: str) -> list[Relationship]:
        return [r for r in self.relationships if r.from_table == table_name or r.to_table == table_name]
```

### Anti-Patterns to Avoid
- **Hardcoding column names:** Always introspect from actual parquet files using DuckDB DESCRIBE
- **Circular relationships:** Power BI cannot resolve ambiguous filter paths; validate no cycles exist
- **Bidirectional filters everywhere:** Use SINGLE direction unless there's a specific need for BOTH
- **Missing cardinality:** Every relationship must explicitly state cardinality for Power BI

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parquet schema introspection | Custom parquet reader | DuckDB `DESCRIBE` / `parquet_schema()` | Edge cases in type mapping |
| JSON serialization | Manual dict building | Pydantic `model_dump_json()` | Handles nested models, enums correctly |
| Schema validation | Manual column checking | Pydantic validators | Declarative, testable |
| Enum handling in JSON | String manipulation | Pydantic `use_enum_values=True` | Consistent serialization |

**Key insight:** DuckDB already provides parquet introspection; Pydantic already handles JSON schema generation. The work is defining the models correctly, not building infrastructure.

## Common Pitfalls

### Pitfall 1: Assuming Column Types Match Across Tables
**What goes wrong:** FK column in attribute table has different type than PK in dimension
**Why it happens:** Parquet files may have been generated with inconsistent type handling
**How to avoid:** Validate FK/PK column types match during schema construction
**Warning signs:** Relationship validation fails on type mismatch

### Pitfall 2: Missing Primary Keys in Dimensions
**What goes wrong:** Dimension table lacks unique identifier, causing many-to-many relationships
**Why it happens:** Source data didn't enforce uniqueness
**How to avoid:** Verify PK uniqueness via DuckDB query: `SELECT COUNT(*) = COUNT(DISTINCT pk_col)`
**Warning signs:** Cardinality detection shows unexpected many-to-many

### Pitfall 3: Circular Relationship Paths
**What goes wrong:** Power BI cannot determine filter propagation direction
**Why it happens:** Multiple paths exist between same tables
**How to avoid:** Build relationship graph and check for cycles before finalizing
**Warning signs:** Graph traversal from any dimension reaches same table via multiple paths

### Pitfall 4: Inconsistent Table Naming
**What goes wrong:** Schema references "dim_noc" but file is "DIM_NOC.parquet"
**Why it happens:** Case sensitivity differences between Python and file system
**How to avoid:** Normalize all table names to lowercase, strip extensions
**Warning signs:** Table lookup fails during validation

### Pitfall 5: Forgetting Attribute Tables Are Not Facts
**What goes wrong:** Attribute tables (oasis_*, element_*) treated as facts with measures
**Why it happens:** They have numeric columns that look like measures
**How to avoid:** Classify by purpose: attributes describe dimensions, facts record events
**Warning signs:** Aggregations on attribute tables produce wrong results

## Code Examples

Verified patterns from official sources:

### Introspecting Parquet Schema with DuckDB
```python
# Source: DuckDB Documentation - Parquet Metadata
import duckdb

def get_table_columns(parquet_path: str) -> list[dict]:
    """Get column names and types from parquet file."""
    conn = duckdb.connect()
    result = conn.execute(f"DESCRIBE SELECT * FROM '{parquet_path}'").fetchall()
    return [
        {"name": row[0], "data_type": row[1]}
        for row in result
    ]
```

### Validating Relationship Cardinality
```python
# Source: Power BI Guidance - Star Schema
def validate_one_to_many(
    conn: duckdb.DuckDBPyConnection,
    from_table: str,
    from_col: str,
    to_table: str,
    to_col: str
) -> bool:
    """Verify from_table.from_col has unique values (the 'one' side)."""
    query = f"""
    SELECT COUNT(*) = COUNT(DISTINCT {from_col})
    FROM '{from_table}'
    """
    return conn.execute(query).fetchone()[0]
```

### Exporting Schema to JSON
```python
# Source: Pydantic Documentation - JSON Schema
from pydantic import BaseModel

class WiQSchema(BaseModel):
    tables: list[Table]
    relationships: list[Relationship]

schema = WiQSchema(tables=[...], relationships=[...])

# For deployment scripts
json_output = schema.model_dump_json(indent=2)

# For programmatic access
dict_output = schema.model_dump()
```

### Detecting Circular Relationships
```python
# Graph cycle detection for relationship validation
from collections import defaultdict

def has_circular_relationships(relationships: list[Relationship]) -> bool:
    """Check if relationship graph has cycles."""
    graph = defaultdict(list)
    for rel in relationships:
        graph[rel.from_table].append(rel.to_table)

    visited = set()
    rec_stack = set()

    def dfs(node):
        visited.add(node)
        rec_stack.add(node)
        for neighbor in graph[node]:
            if neighbor not in visited:
                if dfs(neighbor):
                    return True
            elif neighbor in rec_stack:
                return True
        rec_stack.remove(node)
        return False

    for node in graph:
        if node not in visited:
            if dfs(node):
                return True
    return False
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| TMSL single JSON file | TMDL folder structure | Power BI Feb 2024 | Better source control, human-readable |
| Manual relationship definition | Automated from metadata | 2024-2025 | Reduces errors, enables validation |
| Snowflake schemas | Star schema preferred | Consistent | Simpler queries, better performance |

**Deprecated/outdated:**
- TMSL for source control: Use TMDL for human-readable, git-friendly format
- Bidirectional filters by default: Power BI now recommends single direction unless needed

## WiQ-Specific Schema Design

Based on the context provided, here is the recommended schema structure:

### Table Classification
| Table | Type | Primary Key | Foreign Keys |
|-------|------|-------------|--------------|
| dim_noc | DIMENSION | unit_group_id | - |
| dim_occupations | DIMENSION | occupation_id (assumed) | - |
| job_architecture | ATTRIBUTE | job_id (assumed) | occupation_id |
| oasis_* | ATTRIBUTE | row_id (assumed) | unit_group_id |
| element_* | ATTRIBUTE | row_id (assumed) | unit_group_id |
| cops_* | FACT | composite | unit_group_id |

### Relationship Definitions
| From Table | From Column | To Table | To Column | Cardinality |
|------------|-------------|----------|-----------|-------------|
| dim_noc | unit_group_id | oasis_* | unit_group_id | 1:* |
| dim_noc | unit_group_id | element_* | unit_group_id | 1:* |
| dim_noc | unit_group_id | cops_* | unit_group_id | 1:* |
| dim_occupations | occupation_id | job_architecture | occupation_id | 1:* |

**Note:** Actual column names must be validated against parquet files via DuckDB introspection.

## Phase 4 Consumption

The downstream consumer (`/stagegold` deployment) needs:

1. **JSON format** - Machine-readable schema definition
2. **Relationship list** - Iterable relationships with all Power BI properties
3. **Table metadata** - Names, types, columns for each table
4. **Validation status** - Whether schema has been validated against actual files

Recommended output format:
```json
{
  "name": "WiQ",
  "tables": [
    {
      "name": "dim_noc",
      "table_type": "dimension",
      "primary_key": "unit_group_id",
      "columns": [...]
    }
  ],
  "relationships": [
    {
      "from_table": "dim_noc",
      "from_column": "unit_group_id",
      "to_table": "oasis_skills",
      "to_column": "unit_group_id",
      "cardinality": "1:*",
      "cross_filter_direction": "Single",
      "is_active": true
    }
  ],
  "validated": true,
  "validation_date": "2026-01-18"
}
```

## Open Questions

Things that couldn't be fully resolved:

1. **Actual column names in gold parquet files**
   - What we know: unit_group_id is the FK pattern
   - What's unclear: Exact PK names in dim_occupations, job_architecture
   - Recommendation: First task should introspect all gold files

2. **COPS table granularity**
   - What we know: COPS has year projections (forecast data)
   - What's unclear: Is there one row per NOC per year, or multiple
   - Recommendation: Validate grain matches expected cardinality

3. **CatalogManager integration**
   - What we know: CatalogManager stores table metadata as JSON
   - What's unclear: Whether semantic model should extend or replace catalog entries
   - Recommendation: Add semantic metadata as new field in catalog JSON

## Sources

### Primary (HIGH confidence)
- [Microsoft Learn - Power BI Relationships](https://learn.microsoft.com/en-us/power-bi/transform-model/desktop-relationships-understand) - Cardinality types, cross-filter direction, relationship properties
- [Microsoft Learn - Star Schema Guide](https://learn.microsoft.com/en-us/power-bi/guidance/star-schema) - Dimension/fact classification, design principles
- [DuckDB Parquet Metadata](https://duckdb.org/docs/stable/data/parquet/metadata) - Schema introspection functions
- [Pydantic JSON Schema](https://docs.pydantic.dev/latest/concepts/json_schema/) - model_json_schema, nested models, enum handling

### Secondary (MEDIUM confidence)
- [TMDL vs TMSL Comparison](https://medium.com/@islafurkan/understanding-the-power-bi-semantic-model-folder-structure-tmdl-vs-tmsl-and-source-control-a41880bbf2a7) - Modern Power BI model formats
- [Dimensional Modeling Guide](https://www.owox.com/blog/articles/dimensional-data-modeling) - Star schema best practices 2025

### Tertiary (LOW confidence)
- WebSearch results for Pydantic data catalog patterns - Limited directly applicable examples

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Uses existing codebase libraries (Pydantic, DuckDB)
- Architecture: HIGH - Follows established Power BI patterns from Microsoft docs
- Pitfalls: MEDIUM - Common issues documented, but project-specific risks unknown

**Research date:** 2026-01-18
**Valid until:** 2026-02-18 (30 days - stable domain)
