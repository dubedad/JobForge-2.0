# Phase 1: Pipeline Infrastructure - Research

**Researched:** 2026-01-18
**Domain:** Medallion architecture, data provenance, metadata catalog
**Confidence:** HIGH (verified via DAMA DMBOK reference files, prototype analysis, official documentation)

## Summary

This research covers the foundational pipeline infrastructure for JobForge 2.0, implementing a medallion architecture (staged -> bronze -> silver -> gold) with comprehensive provenance tracking per DAMA DMBOK principles.

The key findings are:
1. **Medallion architecture** is the dominant pattern for data lakehouse implementations, with clear responsibilities at each layer
2. **Row-level provenance** should be implemented via standard columns (`_source_file`, `_ingested_at`, `_batch_id`) embedded in every parquet file
3. **Table/column-level metadata** requires a separate catalog structure (JSON files) that links to business glossary, lineage, and governance metadata
4. **DuckDB + Polars** combination provides optimal performance for parquet-based pipelines with lazy evaluation and SQL analytics
5. **DAMA DMBOK** mandates explicit lineage at transformation boundaries, metadata as first-class output, and separation of conceptual/logical/physical layers

**Primary recommendation:** Build a 4-layer medallion pipeline using Polars for transformations and DuckDB for analytics, with metadata captured both inline (row-level provenance columns) and externally (JSON catalog files per DAMA requirements).

---

## Standard Stack

The established libraries/tools for this domain:

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **Polars** | 1.37.1 | DataFrame operations, ETL transformations | 3-10x faster than Pandas, native Parquet read/write, lazy evaluation for memory efficiency, Rust-based parallelization |
| **DuckDB** | 1.4.3 | SQL analytics on Parquet files | In-process OLAP, projection/filter pushdown to Parquet, zero-copy Arrow integration with Polars |
| **PyArrow** | (bundled) | Parquet I/O, metadata handling | Both Polars and DuckDB use Arrow natively; required for custom parquet metadata |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **Pydantic** | 2.12.5 | Schema validation, metadata models | Define and validate pipeline metadata schemas |
| **structlog** | latest | Structured logging | JSON logs for pipeline execution, DAMA audit compliance |
| **uuid** | (stdlib) | Batch ID generation | Generate unique batch identifiers for provenance |
| **datetime** | (stdlib) | Timestamp generation | Record ingestion timestamps |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Polars | Pandas | Pandas is 3-10x slower, single-threaded, higher memory; use only for ML library compatibility |
| DuckDB | SQLite | SQLite lacks columnar storage, Parquet pushdown, parallel execution |
| JSON metadata | SQLite catalog | SQLite adds complexity; JSON is human-readable, versionable in git, sufficient for this scale |
| Delta Lake | Plain Parquet | Delta adds ACID transactions but requires Spark; Polars atomic writes provide sufficient guarantees |

**Installation:**
```bash
pip install polars==1.37.1 duckdb==1.4.3 pyarrow pydantic>=2.12.0 structlog
```

---

## Architecture Patterns

### Recommended Directory Structure

```
data/
├── staged/                     # Layer 0: Raw ingestion
│   ├── {source_id}/           # One folder per source
│   │   └── {YYYY-MM-DD}/      # Date-partitioned batches
│   │       └── {original_filename}.parquet
│   └── _manifests/            # Batch manifests
│
├── bronze/                     # Layer 1: Type-enforced
│   ├── {domain}/              # Grouped by data domain
│   │   └── {table_name}.parquet
│   └── _metadata/             # Bronze-specific metadata
│
├── silver/                     # Layer 2: Cleaned & harmonized
│   ├── {domain}/
│   │   └── {table_name}.parquet
│   └── _metadata/
│
├── gold/                       # Layer 3: Business-ready model
│   ├── {table_name}.parquet   # Dimensional model tables
│   └── _metadata/
│
├── quarantine/                 # Error isolation
│   ├── {layer}/               # Per-layer quarantine
│   │   └── {date}/
│   └── _error_logs/
│
└── catalog/                    # External metadata catalog
    ├── tables/                # Table-level metadata
    │   └── {table_name}.json
    ├── lineage/               # Lineage graphs
    │   └── {pipeline_run}.json
    ├── glossary/              # Business terms
    │   └── glossary.json
    └── schemas/               # Validation schemas
        └── *.schema.json
```

### Pattern 1: Row-Level Provenance Columns

**What:** Standard columns added to every parquet file tracking data origin
**When to use:** Always - every parquet file at every layer must have provenance columns

**Columns (DAMA-compliant):**

| Column | Type | Purpose | Example |
|--------|------|---------|---------|
| `_source_file` | str | Original filename/path | `noc_2021_v1.3.csv` |
| `_ingested_at` | datetime | UTC timestamp of ingestion | `2026-01-18T14:30:00Z` |
| `_batch_id` | str (UUID) | Unique batch identifier | `550e8400-e29b-41d4-a716-446655440000` |
| `_layer` | str | Current medallion layer | `bronze`, `silver`, `gold` |

**Example (Polars):**
```python
import polars as pl
from datetime import datetime, timezone
import uuid

def add_provenance_columns(
    df: pl.LazyFrame,
    source_file: str,
    batch_id: str,
    layer: str
) -> pl.LazyFrame:
    """Add standard provenance columns per DAMA DMBOK."""
    return df.with_columns([
        pl.lit(source_file).alias("_source_file"),
        pl.lit(datetime.now(timezone.utc)).alias("_ingested_at"),
        pl.lit(batch_id).alias("_batch_id"),
        pl.lit(layer).alias("_layer"),
    ])
```

### Pattern 2: Layer Transition Logging

**What:** JSON log entries capturing each layer transition for queryable audit trail
**When to use:** Every time data moves from one layer to the next

**Log Schema:**
```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Literal

class LayerTransitionLog(BaseModel):
    """DAMA-compliant layer transition record."""
    transition_id: str           # UUID
    batch_id: str                # Links to row-level _batch_id
    source_layer: Literal["staged", "bronze", "silver"]
    target_layer: Literal["bronze", "silver", "gold"]
    source_files: list[str]      # Input file paths
    target_file: str             # Output file path
    row_count_in: int
    row_count_out: int
    transforms_applied: list[str]
    started_at: datetime
    completed_at: datetime
    status: Literal["success", "partial", "failed"]
    errors: Optional[list[str]] = None
```

**Storage:**
```
data/catalog/lineage/
├── 2026-01-18_batch_550e8400.json  # One file per batch
└── index.json                      # Queryable index
```

### Pattern 3: Table-Level Metadata Catalog

**What:** External JSON files containing rich metadata for each table, linking to business glossary, lineage, and governance
**When to use:** Create/update when tables are created or schema changes

**Catalog Entry Schema (per DAMA DMBOK Chapter 5):**
```python
class ColumnMetadata(BaseModel):
    """Column-level technical and business metadata."""
    name: str
    data_type: str
    nullable: bool
    description: str                      # Business description
    glossary_term_id: Optional[str]       # Link to business glossary
    source_columns: list[str]             # Lineage - where this came from
    pii_classification: Optional[str]     # Security classification
    example_values: list[str]

class TableMetadata(BaseModel):
    """Table-level metadata per DAMA DMBOK."""
    table_name: str
    layer: str
    domain: str
    file_path: str

    # Technical metadata
    row_count: int
    column_count: int
    file_size_bytes: int
    schema_version: str
    created_at: datetime
    updated_at: datetime

    # Business metadata
    description: str
    business_purpose: str
    data_owner: str
    data_steward: Optional[str]

    # Lineage metadata
    upstream_tables: list[str]
    downstream_tables: list[str]
    transform_script: Optional[str]

    # Governance metadata
    retention_days: Optional[int]
    classification: str                   # public, internal, confidential

    # Column metadata
    columns: list[ColumnMetadata]
```

### Pattern 4: Medallion Layer Responsibilities

**What:** Clear separation of concerns per layer (DAMA Chapter 2 - Architecture)
**When to use:** Design principle for all transformations

| Layer | DAMA Responsibility | Allowed Operations | Forbidden |
|-------|--------------------|--------------------|-----------|
| **Staged** | Preserve source fidelity | Add provenance columns only; convert to parquet | Modify source data |
| **Bronze** | Type standardization | Enforce schema, standardize dates, add source_system | Business logic |
| **Silver** | Clean & harmonize | Deduplicate, validate, apply crosswalks | Aggregations |
| **Gold** | Business model | Build dimensions, compute derived fields, FK relationships | Raw source access |

**Layer Contract Example:**
```python
class LayerContract:
    """Enforce layer responsibilities per DAMA architecture."""

    STAGED_ALLOWED_COLUMNS = ["_source_file", "_ingested_at", "_batch_id", "_layer"]

    @staticmethod
    def validate_staged(df: pl.LazyFrame, original_columns: list[str]) -> bool:
        """Staged layer must only add provenance columns."""
        new_columns = set(df.columns) - set(original_columns)
        return new_columns.issubset(set(LayerContract.STAGED_ALLOWED_COLUMNS))
```

### Anti-Patterns to Avoid

- **Skipping layers:** Never write directly from staged to silver; bronze enforces schemas and catches issues early
- **Business logic in bronze:** Bronze is for type enforcement only; business rules belong in silver/gold
- **Inline metadata only:** Row-level provenance is necessary but insufficient; external catalog required for DAMA compliance
- **Overwriting without versioning:** Always preserve ability to replay from staged layer

---

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parquet read/write | Custom Arrow code | `pl.scan_parquet()`, `df.write_parquet()` | Polars handles compression, partitioning, schema evolution |
| SQL on parquet | Custom query engine | `duckdb.sql("SELECT * FROM 'file.parquet'")` | Pushdown optimizations, parallelization built-in |
| Schema validation | Manual type checks | Pydantic models + pandera | Declarative, generates JSON schema, better error messages |
| UUID generation | Custom ID scheme | `uuid.uuid4()` | Standard, collision-free, widely understood |
| Timestamp handling | Manual formatting | `datetime.now(timezone.utc)` | Timezone-aware, ISO format by default |
| JSON serialization | Custom encoders | Pydantic `.model_dump_json()` | Handles datetime, nested models, validation |

**Key insight:** The prototype already demonstrates effective patterns for metadata JSON files, manifest tracking, and transform logging. Reuse these patterns rather than inventing new approaches.

---

## Common Pitfalls

### Pitfall 1: Eager vs Lazy Execution Confusion

**What goes wrong:** Using `pl.read_parquet().lazy()` instead of `pl.scan_parquet()`, forcing full file materialization
**Why it happens:** Habit from Pandas where everything is eager
**How to avoid:** Always use `scan_*` functions when working with LazyFrames
**Warning signs:** Memory errors on large files, slow performance

```python
# BAD - Forces full read then converts to lazy
df = pl.read_parquet("large_file.parquet").lazy()

# GOOD - Lazy from the start, enables pushdown
df = pl.scan_parquet("large_file.parquet")
```

### Pitfall 2: Missing Provenance on Joins

**What goes wrong:** Joining tables loses provenance columns or creates ambiguous provenance
**Why it happens:** Standard joins don't know which source's provenance to keep
**How to avoid:** Explicitly handle provenance in joins; suffix or prefix by source
**Warning signs:** `_source_file` column contains wrong file, or is null after join

```python
# Preserve provenance from both sources
joined = left.join(
    right,
    on="key",
    suffix="_right"
).with_columns([
    pl.concat_str([
        pl.col("_source_file"),
        pl.lit("+"),
        pl.col("_source_file_right")
    ]).alias("_source_file")
])
```

### Pitfall 3: Schema Evolution Breaking Downstream

**What goes wrong:** Adding column to bronze breaks silver transforms that assume fixed schema
**Why it happens:** Hard-coded column lists instead of schema-aware processing
**How to avoid:** Use schema introspection; document schema contracts; version schemas
**Warning signs:** Pipeline failures after source changes

```python
# BAD - Hard-coded columns
df = df.select(["col1", "col2", "col3"])

# GOOD - Schema-aware, preserves new columns
required_cols = ["col1", "col2", "col3"]
df = df.select([pl.col(c) for c in required_cols] + [pl.col("*").exclude(required_cols)])
```

### Pitfall 4: Quarantine Without Error Context

**What goes wrong:** Moving bad records to quarantine without capturing why they failed
**Why it happens:** Focusing on "get it out of the way" rather than root cause analysis
**How to avoid:** Always log error reason, rule ID, and original values with quarantined records
**Warning signs:** Growing quarantine with no understanding of issues

```python
class QuarantineRecord(BaseModel):
    """Quarantined record with full error context."""
    original_row: dict
    error_type: str
    error_message: str
    validation_rule_id: str
    source_file: str
    quarantined_at: datetime
    layer: str
```

### Pitfall 5: DuckDB Connection Management

**What goes wrong:** Creating new DuckDB connections per query, losing in-memory state
**Why it happens:** Treating DuckDB like a traditional database instead of in-process engine
**How to avoid:** Use persistent connection or in-memory database for session; register DataFrames as views
**Warning signs:** Repeated "table not found" errors, slow queries

```python
import duckdb

# Create one connection for the session
conn = duckdb.connect(":memory:")  # or "pipeline.duckdb" for persistence

# Register Polars DataFrame as DuckDB view
conn.register("my_table", df.collect().to_arrow())

# Query across multiple tables efficiently
result = conn.execute("""
    SELECT * FROM my_table
    WHERE layer = 'gold'
""").pl()
```

---

## Code Examples

Verified patterns from official documentation and prototype analysis:

### Reading Multiple Parquet Files with Glob

```python
# Source: Polars documentation - scan_parquet with glob
import polars as pl

# Read all parquet files from bronze layer
df = pl.scan_parquet("data/bronze/**/*.parquet")

# Read with filename as column (for lineage)
df = pl.scan_parquet(
    "data/bronze/**/*.parquet",
    include_file_paths="source_path"
)
```

### Writing Parquet with Compression

```python
# Source: Polars documentation - write_parquet
import polars as pl

df = pl.LazyFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})

# Write with snappy compression (default, good balance)
df.collect().write_parquet("output.parquet", compression="snappy")

# Write with zstd for better compression ratio
df.collect().write_parquet("output.parquet", compression="zstd")
```

### DuckDB Direct Parquet Query

```python
# Source: DuckDB documentation - parquet overview
import duckdb

# Query parquet files directly with SQL
result = duckdb.sql("""
    SELECT
        _source_file,
        COUNT(*) as row_count,
        MAX(_ingested_at) as latest_ingestion
    FROM 'data/gold/*.parquet'
    GROUP BY _source_file
    ORDER BY latest_ingestion DESC
""").pl()

# Filter pushdown to parquet (automatic)
result = duckdb.sql("""
    SELECT * FROM 'data/silver/dim_noc.parquet'
    WHERE noc_code LIKE '21%'
""").pl()
```

### Layer Transition with Logging

```python
# Combines Polars transformation with DAMA-compliant logging
import polars as pl
from datetime import datetime, timezone
import uuid
import json

def bronze_to_silver(
    bronze_path: str,
    silver_path: str,
    transforms: list[callable],
    catalog_path: str
) -> dict:
    """Transform bronze to silver with full provenance tracking."""

    batch_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc)

    # Read bronze with lazy evaluation
    df = pl.scan_parquet(bronze_path)
    row_count_in = df.select(pl.len()).collect().item()

    # Apply transforms
    transforms_applied = []
    for transform in transforms:
        df = transform(df)
        transforms_applied.append(transform.__name__)

    # Update provenance
    df = df.with_columns([
        pl.lit("silver").alias("_layer"),
        pl.lit(batch_id).alias("_batch_id"),
        pl.lit(datetime.now(timezone.utc)).alias("_ingested_at"),
    ])

    # Write to silver
    df.collect().write_parquet(silver_path, compression="zstd")

    row_count_out = pl.scan_parquet(silver_path).select(pl.len()).collect().item()
    completed_at = datetime.now(timezone.utc)

    # Create transition log
    log = {
        "transition_id": str(uuid.uuid4()),
        "batch_id": batch_id,
        "source_layer": "bronze",
        "target_layer": "silver",
        "source_files": [bronze_path],
        "target_file": silver_path,
        "row_count_in": row_count_in,
        "row_count_out": row_count_out,
        "transforms_applied": transforms_applied,
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "status": "success"
    }

    # Save transition log
    log_path = f"{catalog_path}/lineage/{batch_id}.json"
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2)

    return log
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pandas for ETL | Polars for ETL | 2023-2024 | 3-10x performance improvement, lower memory |
| CSV intermediate files | Parquet at every layer | 2022+ | Columnar efficiency, schema enforcement |
| Database for pipeline state | JSON/Parquet metadata files | 2024+ | Simpler deployment, git-versioned |
| Manual lineage docs | Automated lineage capture | 2023+ | DAMA compliance, audit-ready |

**Deprecated/outdated:**
- **Delta Lake for small-scale pipelines:** Adds Spark dependency; plain Parquet with Polars atomic writes sufficient for <100GB
- **Custom metadata schemas:** Use established patterns from prototype (sources.json, transforms.json, *.meta.json)
- **Eager-only Polars:** Lazy evaluation is now mature; always prefer `scan_*` over `read_*`

---

## DAMA DMBOK Alignment

This phase implements controls from multiple DAMA chapters:

### Chapter 2: Data Architecture

| Principle | Implementation |
|-----------|----------------|
| Separate meaning from implementation | Catalog stores business metadata separately from physical files |
| Canonical structure | Gold layer provides single source of truth for dimensions |
| Architecture decisions documented | Layer contracts and schemas stored in version control |

### Chapter 5: Metadata Management

| Requirement | Implementation |
|-------------|----------------|
| Metadata as first-class output | Every transformation produces metadata alongside data |
| Link business, technical, operational | Table catalog links to glossary (business), schema (technical), logs (operational) |
| Capture lineage at transformation boundaries | LayerTransitionLog records every layer movement |
| Machine-readable metadata | JSON schemas with Pydantic validation |

### Chapter 7: Data Integration

| Requirement | Implementation |
|-------------|----------------|
| Transformations explicit and traceable | transforms_applied array in every log |
| Interface versioning | Schema versioning in catalog metadata |
| Lineage across boundaries | _batch_id links records across all layers |

### Chapter 4: Data Quality

| Requirement | Implementation |
|-------------|----------------|
| Detect vs correct separation | Quarantine isolates bad data without modifying |
| Preserve original values | Staged layer is immutable; corrections in silver/gold |
| Quality metrics alongside data | row_count_in/out, errors array in logs |

---

## Open Questions

Things that couldn't be fully resolved:

1. **Partitioning strategy for large tables**
   - What we know: Polars supports Hive-style partitioning via PyArrow
   - What's unclear: Whether to partition by date, source, or domain for this specific workload
   - Recommendation: Start without partitioning; add when files exceed 1GB

2. **Incremental vs full refresh**
   - What we know: Prototype uses full refresh; incremental is more complex
   - What's unclear: Whether sources provide change indicators
   - Recommendation: Start with full refresh; design for incremental when source capabilities are confirmed

3. **Metadata catalog persistence format**
   - What we know: JSON is simple and git-friendly; SQLite provides query capabilities
   - What's unclear: Scale at which JSON becomes unwieldy
   - Recommendation: Use JSON for MVP; the catalog/ structure supports migration to SQLite later

---

## Sources

### Primary (HIGH confidence)

- DAMA DMBOK Chapter 2 - Data Architecture: `dama_02_data_architecture_dmbok_2_chapter_2_reference.md`
- DAMA DMBOK Chapter 5 - Metadata Management: `dama_05_metadata_management_dmbok_2_chapter_5_reference.md`
- DAMA DMBOK Chapter 7 - Data Integration: `dama_07_data_integration_and_interoperability_dmbok_2_chapter_7_reference.md`
- DAMA GC/ADM Audit Overlay: `dama_gc_adm_audit_overlay_policy_mapping.md`
- JobForge prototype data structure analysis (existing working implementation)
- [Polars Documentation - write_parquet](https://docs.pola.rs/py-polars/html/reference/api/polars.DataFrame.write_parquet.html)
- [DuckDB Documentation - Parquet Overview](https://duckdb.org/docs/stable/data/parquet/overview)
- Project STACK.md and ARCHITECTURE.md research documents

### Secondary (MEDIUM confidence)

- [Databricks - Medallion Architecture](https://www.databricks.com/glossary/medallion-architecture)
- [Microsoft Learn - Medallion Lakehouse Architecture](https://learn.microsoft.com/en-us/azure/databricks/lakehouse/medallion)
- [Data Lineage Best Practices 2025](https://seemoredata.io/blog/data-lineage-in-2025-examples-techniques-best-practices/)

### Tertiary (LOW confidence)

- WebSearch results on partitioning strategies (varied recommendations, context-dependent)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - verified via PyPI, official docs, project research
- Architecture: HIGH - DAMA DMBOK reference files provide explicit guidance
- Pitfalls: HIGH - based on prototype analysis and official documentation warnings

**Research date:** 2026-01-18
**Valid until:** 2026-02-18 (30 days - stable domain)
