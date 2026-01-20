# Phase 12: Schema and Domain Intelligence - Research

**Researched:** 2026-01-20
**Domain:** DDL Enhancement, Workforce Domain Semantics, Text-to-SQL Accuracy
**Confidence:** HIGH

## Summary

Phase 12 enhances the existing text-to-SQL system by enriching DDL with semantic descriptions, relationship hints, and workforce-specific domain intelligence. The current implementation generates bare-bones DDL from parquet introspection (`schema_ddl.py`), which provides only column names and types. This research reveals that significant metadata already exists in the codebase that can be extracted and injected into the DDL to improve Claude's SQL generation accuracy.

Key findings:
1. **Catalog JSON files** (`data/catalog/tables/`) already have a `ColumnMetadata.description` field, but most columns show generic "Column of type VARCHAR" descriptions
2. **Prototype documentation** (`++JobForge Reference Docs to import/`, prototype's `cops_facts.md`, `business_glossary.json`) contains rich semantic descriptions ready for extraction
3. **OaSIS guide.csv** (referenced in `resources.json`) provides column-level metadata for OASIS attribute tables
4. **COPS glossary mapping** (`cops_glossary_mapping.json`) already maps tables to glossary terms with column description templates
5. **Workforce dynamic** (demand/supply categorization) can be derived from prototype's bronze folder structure
6. **Source attribution** can be added to query responses using existing `TableMetadata.domain` and source information from lineage

**Primary recommendation:** Implement a three-stage enrichment pipeline: (1) Extract descriptions from existing docs to catalog JSON, (2) Add `workforce_dynamic` field to COPS tables, (3) Generate enhanced DDL with COMMENT statements from enriched catalog. Source attribution should be added to `DataQueryResult` model.

---

## Current Implementation

### 1. DDL Generation (`src/jobforge/api/schema_ddl.py`)

**Current state:** Generates DDL by introspecting parquet files:
```python
def generate_schema_ddl(config: PipelineConfig | None = None) -> str:
    # ...
    for parquet in sorted(gold_path.glob("*.parquet")):
        table_name = parquet.stem
        conn.execute(f"CREATE VIEW {table_name} AS SELECT * FROM '{parquet_path}'")
        cols = conn.execute(f"DESCRIBE {table_name}").fetchall()
        col_defs = [f"  {col[0]} {col[1]}" for col in cols]
        ddl_parts.append(f"CREATE TABLE {table_name} (\n" + ",\n".join(col_defs) + "\n);")
```

**Output example:**
```sql
CREATE TABLE cops_employment (
  unit_group_id VARCHAR,
  code VARCHAR,
  occupation_name_en VARCHAR,
  occupation_name_fr VARCHAR,
  2023 VARCHAR,
  2024 VARCHAR,
  -- ...
);
```

**Gap:** No semantic descriptions, no relationship hints, no domain context.

### 2. Catalog Table Metadata (`data/catalog/tables/*.json`)

**Current state:** 24 table JSON files with `ColumnMetadata` including:
- `name`, `data_type`, `nullable` (populated)
- `description` (mostly generic "Column of type VARCHAR")
- `glossary_term_id` (null)
- `source_columns` (partially populated for FK relationships)
- `example_values` (populated with sample values)

**Example from `cops_employment.json`:**
```json
{
  "name": "occupation_name_en",
  "data_type": "VARCHAR",
  "nullable": true,
  "description": "Column of type VARCHAR",  // <-- needs enrichment
  "glossary_term_id": null,
  "source_columns": [],
  "example_values": ["Legislators", "Senior government managers..."]
}
```

**Gap:** Descriptions are auto-generated, not semantic. No workforce_dynamic field at table level.

### 3. Schema JSON (`data/catalog/schemas/wiq_schema.json`)

Contains table/column schema with relationship metadata:
- `is_foreign_key`, `references_table`, `references_column` for joins
- `table_type` (fact/dimension) classification
- No column descriptions in this file

### 4. Text-to-SQL Service (`src/jobforge/api/data_query.py`)

**Current state:** Uses Claude structured outputs with DDL in prompt:
```python
SYSTEM_PROMPT = """You are a SQL expert for the WiQ (Workforce Intelligence) database.
The database contains Canadian occupational data:
- dim_noc: National Occupational Classification hierarchy
- cops_*: Canadian Occupational Projection System forecasts
...
"""

# In query():
response = self.client.messages.create(
    messages=[{
        "role": "user",
        "content": f"Schema:\n{self.schema_ddl}\n\nQuestion: {question}",
    }],
    # ...
)
```

**Gap:** No source attribution in `DataQueryResult`. No workforce domain hints in prompt.

### 5. Orbit DuckDB Retriever (`orbit/retrievers/duckdb.py`)

Uses same pattern as `DataQueryService`:
```python
SYSTEM_PROMPT = """You are a SQL expert for the WiQ (Workforce Intelligence) database.
Generate DuckDB-compatible SELECT queries only. Never modify data.
The database contains Canadian occupational data:
- dim_noc: National Occupational Classification hierarchy
...
"""
```

**Gap:** Same limitations as `DataQueryService`.

---

## Integration Points

### Where DDL Generation Happens

| Component | File | Purpose |
|-----------|------|---------|
| DDL Generator | `src/jobforge/api/schema_ddl.py` | `generate_schema_ddl()` - generates DDL from parquet introspection |
| Data Query | `src/jobforge/api/data_query.py` | `DataQueryService.schema_ddl` - caches DDL for text-to-SQL |
| Orbit Retriever | `orbit/retrievers/duckdb.py` | `DuckDBRetriever._schema_ddl` - same pattern |

**Change point:** Modify `generate_schema_ddl()` to read enriched catalog JSON and generate DDL with COMMENT statements.

### Where Catalog Enrichment Should Happen

| Task | Target | Source |
|------|--------|--------|
| Column descriptions | `data/catalog/tables/*.json` | COPS facts.md, business_glossary.json, OaSIS guide.csv |
| workforce_dynamic | `data/catalog/tables/cops_*.json` | Prototype bronze folder structure |
| Relationship hints | DDL generation | `wiq_schema.json` FK metadata |

### Where Source Attribution Goes

| Component | File | Change |
|-----------|------|--------|
| Query Result | `src/jobforge/api/data_query.py` | Add `source_tables: list[str]` and `source_attribution: str` to `DataQueryResult` |
| Response Builder | Same file | Generate attribution from `SQLQuery.tables_used` |

---

## Source Documentation Audit

### Available Source Documentation

| Source | Location | Content | Confidence |
|--------|----------|---------|------------|
| **COPS facts.md** | `JobForge/backend/data/metadata/tables/cops_facts.md` | Full column descriptions, business questions, relationships | HIGH |
| **COPS glossary mapping** | `JobForge/backend/data/metadata/cops_glossary_mapping.json` | Term-to-column mappings, category (demand/supply) | HIGH |
| **Business glossary** | `JobForge/backend/data/metadata/glossary/business_glossary.json` | Authoritative definitions from COPS/OASIS/NOC | HIGH |
| **OaSIS resources.json** | `JobForge/backend/data/metadata/oasis/resources.json` | Dataset description, proficiency scale definitions | HIGH |
| **OaSIS guide.csv** | URL in resources.json (downloadable) | Column-level metadata for OASIS tables | MEDIUM |
| **NOC Documentation** | `++JobForge Reference Docs to import/NOC Documentation English.pdf` | NOC structure definitions | MEDIUM |
| **Job Architecture guide** | `++JobForge Reference Docs to import/9. GC Job Architecture overview...pdf` | Job architecture column meanings | MEDIUM |

### Extraction Priority

1. **COPS tables** (highest priority): `cops_facts.md` has complete column descriptions
2. **OASIS tables**: Can extract from guide.csv and resources.json description
3. **dim_noc**: Extract from NOC documentation PDF
4. **job_architecture**: Extract from GC Job Architecture PDF
5. **element_* tables**: Lower priority, can use OaSIS descriptions

### Column Description Mapping (from cops_facts.md)

| Table | Column | Description |
|-------|--------|-------------|
| cops_employment | 2023-2033 | "Employment level (count) for each projection year" |
| cops_employment_growth | 2024-2033 | "Annual employment growth rate (%) for each year" |
| cops_retirements | 2024-2033 | "Projected retirement count for each year" |
| cops_retirement_rates | 2024-2033 | "Annual retirement rate (%) for each year" |
| cops_other_replacement | 2024-2033 | "Other replacement demand count for each year" |
| cops_immigration | 2024-2033 | "Immigrant workers entering occupation for each year" |
| cops_school_leavers | 2024-2033 | "School leavers entering workforce in each year" |

### Workforce Dynamic Mapping (from bronze structure)

| Table | workforce_dynamic | Rationale |
|-------|-------------------|-----------|
| cops_employment | demand | Base employment level (demand foundation) |
| cops_employment_growth | demand | Economic expansion driving demand |
| cops_retirements | demand | Replacement demand component |
| cops_retirement_rates | demand | Rate supporting replacement |
| cops_other_replacement | demand | Replacement demand component |
| cops_immigration | supply | Labour supply source |
| cops_school_leavers | supply | Labour supply source |
| cops_other_seekers | supply | Labour supply source |

**Key formula for Claude:** `Workforce Gap = SUM(job_openings) - SUM(job_seekers_total)`

---

## Technical Approach

### ORB-05: Column Descriptions in DDL

**Approach:** Generate DDL with COMMENT syntax:
```sql
CREATE TABLE cops_employment (
  unit_group_id VARCHAR COMMENT 'Foreign key to dim_noc.unit_group_id - 5-digit NOC code',
  code VARCHAR COMMENT 'NOC code as string (may include aggregates)',
  occupation_name_en VARCHAR COMMENT 'English occupation name from COPS source',
  occupation_name_fr VARCHAR COMMENT 'French occupation name from COPS source',
  "2023" VARCHAR COMMENT 'Employment level for 2023 (base year)',
  "2024" VARCHAR COMMENT 'Employment level for 2024',
  -- ...
);
-- Table purpose: Employment counts by NOC occupation, demand side projection
-- Source: COPS (Canadian Occupational Projection System)
-- Workforce dynamic: demand
```

**Implementation:**
1. Create `enrich_catalog.py` to update `data/catalog/tables/*.json` with descriptions
2. Modify `generate_schema_ddl()` to read catalog JSON and include COMMENT clauses
3. Add table-level comment with business purpose and workforce_dynamic

### ORB-06: Relationship Hints for Joins

**Approach:** Include explicit join hints in DDL comments and prompt:
```sql
-- RELATIONSHIPS:
-- cops_employment.unit_group_id REFERENCES dim_noc.unit_group_id (FK)
-- cops_employment joins dim_noc ON unit_group_id for occupation details
-- All cops_* tables share the same unit_group_id foreign key
```

**Implementation:**
1. Read `wiq_schema.json` for FK relationships
2. Generate relationship section in DDL output
3. Add join patterns to system prompt

### ORB-07: Workforce Domain Patterns

**Approach:** Enhance system prompt with domain-specific patterns:
```python
SYSTEM_PROMPT = """...

WORKFORCE INTELLIGENCE PATTERNS:
- Workforce Gap = job_openings - job_seekers_total
- demand tables: cops_employment, cops_employment_growth, cops_retirements, cops_retirement_rates, cops_other_replacement
- supply tables: cops_school_leavers, cops_immigration, cops_other_seekers
- For "shortage" queries: gap > 0 means demand exceeds supply
- For "surplus" queries: gap < 0 means supply exceeds demand
"""
```

**Implementation:**
1. Add workforce domain patterns to `DataQueryService.SYSTEM_PROMPT`
2. Add `workforce_dynamic` field to `TableMetadata` model
3. Include workforce_dynamic in DDL table comments

### ORB-08: Entity Recognition via DDL

**Approach:** Let Claude + enriched DDL handle entity recognition (per user decision):
```sql
-- ENTITY EXAMPLES in DDL comments:
-- unit_group_id: '00010', '21232', '41200' (5-digit NOC codes)
-- occupation_name_en examples: 'Legislators', 'Software engineers'
-- job_title_en examples: 'Senior Developer', 'Administrative Assistant'
```

**Implementation:**
1. Include `example_values` from catalog JSON in DDL comments
2. Ensure Claude sees NOC code patterns (5-digit, zero-padded)
3. Add entity hints to system prompt: "NOC codes are 5-digit strings like '21232'"

### ORB-09: Source Attribution

**Approach:** Add source attribution to `DataQueryResult`:
```python
class DataQueryResult(BaseModel):
    question: str
    sql: str
    explanation: str
    results: list[dict]
    row_count: int
    error: str | None = None
    source_tables: list[str] = []  # NEW
    source_attribution: str = ""   # NEW: "Source: cops_employment (COPS Open Canada)"
```

**Implementation:**
1. Extend `DataQueryResult` with source fields
2. Look up table metadata from catalog for attribution
3. Generate attribution string from `domain` and source system info
4. Format: "Source: {table_name} ({source_system})"

---

## Risks and Considerations

### Risk 1: DDL Comment Length

**Risk:** Very long DDL with all comments could exceed context window
**Mitigation:**
- Keep comments concise (one line per column)
- Truncate example_values to 3 items
- Consider summary mode for large schemas

### Risk 2: Column Name Quoting

**Risk:** Year columns (2023, 2024...) need quoting in SQL
**Mitigation:**
- DDL should show quoted column names: `"2023" VARCHAR`
- System prompt should note: "Year columns must be quoted: SELECT \"2025\""

### Risk 3: Outdated Descriptions

**Risk:** Catalog descriptions may drift from actual data
**Mitigation:**
- Include description source (e.g., "From: cops_facts.md")
- Add CLI command to refresh descriptions from source docs
- Log when descriptions are updated

### Risk 4: Hallucinated SQL on Complex Queries

**Risk:** Claude may generate incorrect SQL for workforce gap calculations
**Mitigation:**
- Include explicit formula in system prompt
- Add examples of correct gap queries
- Test with known workforce gap queries

### Risk 5: Source Attribution Accuracy

**Risk:** Attribution may not reflect actual query tables
**Mitigation:**
- Use `SQLQuery.tables_used` from Claude's structured output
- Verify tables exist in catalog before attribution
- Fall back to "Multiple sources" if uncertain

---

## Recommendations for Planning

### Plan Structure

| Plan | Focus | Requirements |
|------|-------|--------------|
| **12-01** | Catalog Enrichment | Extract descriptions, add workforce_dynamic, update catalog JSON |
| **12-02** | DDL Enhancement | Modify DDL generator to include COMMENT statements, relationship hints |
| **12-03** | Query Enhancement | Update system prompts, add source attribution to results |

### Task Dependencies

```
12-01-01: Extract COPS descriptions from cops_facts.md → catalog JSON
12-01-02: Extract OaSIS descriptions from guide.csv → catalog JSON
12-01-03: Add workforce_dynamic field to TableMetadata model
12-01-04: Add workforce_dynamic to COPS table catalog files

12-02-01: Modify generate_schema_ddl() to read catalog JSON
12-02-02: Add COMMENT statements to DDL output
12-02-03: Add relationship hints section from wiq_schema.json

12-03-01: Add workforce domain patterns to DataQueryService.SYSTEM_PROMPT
12-03-02: Add source_tables and source_attribution to DataQueryResult
12-03-03: Update DuckDBRetriever (Orbit) with same enhancements
```

### Verification Criteria

1. **SQL Column Names:** Query "employment in 2025" uses correct quoted column name
2. **Join Accuracy:** Query "employment by occupation name" correctly joins to dim_noc
3. **Workforce Gap:** Query "workforce gap for software developers" uses correct formula
4. **Entity Recognition:** Query "NOC 21232 employment" correctly identifies NOC code
5. **Source Attribution:** Response includes "Source: cops_employment (COPS Open Canada)"

---

## Code Examples

### Enhanced DDL Output (Target)

```sql
-- WiQ Schema DDL (Generated with semantic descriptions)

CREATE TABLE dim_noc (
  unit_group_id VARCHAR NOT NULL COMMENT 'Primary key - 5-digit NOC 2021 code, zero-padded (e.g., 00010, 21232)',
  noc_code VARCHAR COMMENT 'NOC code without zero-padding',
  class_title VARCHAR COMMENT 'Official NOC occupation title in English',
  class_definition VARCHAR COMMENT 'Full text description of the occupation from NOC',
  hierarchical_structure VARCHAR COMMENT 'Level in NOC hierarchy (Unit Group for L5)'
);
-- Table: National Occupational Classification (NOC 2021) reference dimension
-- Source: Statistics Canada / ESDC NOC Open Data
-- Primary key: unit_group_id

CREATE TABLE cops_employment (
  unit_group_id VARCHAR COMMENT 'FK to dim_noc.unit_group_id',
  code VARCHAR COMMENT 'NOC code (includes aggregates like TEER_0)',
  occupation_name_en VARCHAR COMMENT 'English occupation name',
  occupation_name_fr VARCHAR COMMENT 'French occupation name',
  "2023" VARCHAR COMMENT 'Employment level for 2023 (base year)',
  "2024" VARCHAR COMMENT 'Projected employment for 2024',
  "2025" VARCHAR COMMENT 'Projected employment for 2025'
  -- ... etc
);
-- Table: Employment projections by occupation
-- Source: COPS (Canadian Occupational Projection System)
-- Workforce dynamic: demand
-- Joins: cops_employment.unit_group_id -> dim_noc.unit_group_id

-- RELATIONSHIP HINTS:
-- All cops_* tables join to dim_noc via unit_group_id
-- All oasis_* tables join to dim_noc via unit_group_id
-- job_architecture.unit_group_id -> dim_noc.unit_group_id

-- WORKFORCE GAP FORMULA:
-- Gap = SUM(job_openings) - SUM(job_seekers_total)
-- demand tables: cops_employment, cops_employment_growth, cops_retirements
-- supply tables: cops_school_leavers, cops_immigration, cops_other_seekers
```

### Catalog Enrichment Script (Pattern)

```python
"""Enrich catalog table descriptions from source documentation."""
import json
from pathlib import Path

def enrich_cops_tables():
    """Add descriptions from cops_facts.md to catalog JSON."""
    catalog_path = Path("data/catalog/tables")

    # Mapping from cops_facts.md
    cops_descriptions = {
        "cops_employment": {
            "table_description": "Employment counts by NOC occupation, demand side projection",
            "workforce_dynamic": "demand",
            "columns": {
                "2023": "Employment level for 2023 (base year)",
                "2024": "Projected employment for 2024",
                # ... etc
            }
        },
        # ... other tables
    }

    for table_name, enrichment in cops_descriptions.items():
        json_path = catalog_path / f"{table_name}.json"
        if json_path.exists():
            metadata = json.loads(json_path.read_text())
            metadata["description"] = enrichment["table_description"]
            metadata["workforce_dynamic"] = enrichment["workforce_dynamic"]

            for col in metadata["columns"]:
                if col["name"] in enrichment["columns"]:
                    col["description"] = enrichment["columns"][col["name"]]

            json_path.write_text(json.dumps(metadata, indent=2))
```

### Enhanced DDL Generator (Pattern)

```python
def generate_schema_ddl_enhanced(config: PipelineConfig | None = None) -> str:
    """Generate DDL with semantic descriptions from catalog."""
    config = config or PipelineConfig()
    catalog_path = config.catalog_tables_path()

    ddl_parts = []

    for json_path in sorted(catalog_path.glob("*.json")):
        metadata = json.loads(json_path.read_text())
        table_name = metadata["table_name"]

        # Build column definitions with comments
        col_defs = []
        for col in metadata["columns"]:
            col_type = col["data_type"]
            col_name = f'"{col["name"]}"' if col["name"].isdigit() else col["name"]
            comment = col.get("description", "")
            if comment and comment != f"Column of type {col_type}":
                col_defs.append(f"  {col_name} {col_type} COMMENT '{comment}'")
            else:
                col_defs.append(f"  {col_name} {col_type}")

        ddl = f"CREATE TABLE {table_name} (\n" + ",\n".join(col_defs) + "\n);"

        # Add table-level comments
        if metadata.get("description"):
            ddl += f"\n-- Table: {metadata['description']}"
        if metadata.get("workforce_dynamic"):
            ddl += f"\n-- Workforce dynamic: {metadata['workforce_dynamic']}"

        ddl_parts.append(ddl)

    return "\n\n".join(ddl_parts)
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| DDL parsing | Custom DDL parser | DuckDB DESCRIBE + catalog JSON | Catalog already has typed metadata |
| Entity extraction | NLP entity recognizer | Claude + rich DDL | User decision; DDL context sufficient |
| Glossary lookup | Custom term matcher | glossary_term_id in catalog | Existing field, just needs population |
| Source tracking | Custom provenance system | Existing TableMetadata.domain | Already tracks source system |

---

## Sources

### Primary (HIGH confidence)
- `src/jobforge/api/schema_ddl.py` - Current DDL generator
- `src/jobforge/api/data_query.py` - Current text-to-SQL service
- `src/jobforge/pipeline/models.py` - TableMetadata, ColumnMetadata models
- `data/catalog/tables/*.json` - Current catalog structure
- `JobForge/backend/data/metadata/tables/cops_facts.md` - COPS column descriptions
- `JobForge/backend/data/metadata/cops_glossary_mapping.json` - Term-to-column mappings
- `JobForge/backend/data/metadata/glossary/business_glossary.json` - Authoritative definitions

### Secondary (MEDIUM confidence)
- `JobForge/backend/data/metadata/oasis/resources.json` - OaSIS guide.csv reference
- `++JobForge Reference Docs to import/` - NOC and Job Architecture PDFs
- Phase 10 research (10-RESEARCH.md) - Orbit integration patterns

### Tertiary (LOW confidence)
- WebSearch for DuckDB COMMENT syntax (not DuckDB native, use as SQL comments instead)

---

## Metadata

**Confidence breakdown:**
- Current implementation: HIGH - code reviewed directly
- Source documentation: HIGH - files exist and were read
- Integration approach: HIGH - follows existing patterns
- Workforce semantics: HIGH - from user decisions in CONTEXT.md

**Research date:** 2026-01-20
**Valid until:** 2026-02-20 (30 days - stable domain, internal enrichment)
