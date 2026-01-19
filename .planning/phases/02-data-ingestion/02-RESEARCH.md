# Phase 2: Data Ingestion - Research

**Researched:** 2026-01-18
**Domain:** Data pipeline ingestion, CSV processing, source metadata management
**Confidence:** HIGH

## Summary

This research documents how to ingest the five source table types (DIM NOC, NOC Element/Oasis Attributes, COPS Forecasting, Job Architecture, DIM Occupations) through the Phase 1 medallion pipeline infrastructure to gold layer. The prototype at `C:\Users\Administrator\Dropbox\++ Results Kit\JobForge` provides comprehensive patterns for source metadata, bronze organization, schema codes, and transformation classes.

The prototype successfully ported 57 files (97,132 rows) to bronze with derived columns for `Unit Group ID` and `NOC Element Code`. JobForge 2.0 should adapt these patterns while leveraging the Phase 1 `PipelineEngine` for layer transitions rather than building new infrastructure.

**Primary recommendation:** Create a SourceRegistry class that loads prototype's `sources.json` structure, implement ingestion handlers for each source type (CSV with various schemas), and define silver-layer transforms for schema normalization and NOC code standardization.

---

## Source Schemas

### 1. DIM NOC (NOC Structure)
**Source:** `noc-structure` (Open Canada)
**Files:** 2 (English + French)
**Rows:** 822 per language

| Column | Type | Description |
|--------|------|-------------|
| Level | int | Hierarchy level 1-5 |
| Hierarchical structure | string | Level name (Broad Category, Major Group, etc.) |
| Code - NOC 2021 V1.0 | string | NOC code (1-5 digits depending on level) |
| Class title | string | Occupation title |
| Class definition | string | Description text |

**Key insight:** Contains ALL hierarchy levels (L1-L5) in one file. Unit Groups (L5) have 5-digit codes. Filtering `Level = 5` gives the 516 unit groups.

**Derived columns needed:**
- `Unit Group ID`: 5-digit zero-padded code (for L5 rows)
- Hierarchy parent columns can be derived by joining on code prefixes

---

### 2. NOC Attributes (Element + Oasis)
**Source:** `noc-attributes` (Open Canada - OASIS/SIPEC dataset)
**Files:** 32 (16 English + 16 French)
**Rows:** ~86,500 total

**Two attribute types:**

#### Oasis Attributes (with proficiency 1-5)
Skills, Abilities, Personal Attributes, Knowledges, Work Activities, Work Context, Interests

| Column | Type | Description |
|--------|------|-------------|
| OaSIS Code - Final | string | Format: XXXXX.YY (e.g., 00010.00) |
| OaSIS Label - Final | string | Occupation label |
| [Attribute columns] | int | Proficiency scores 0-5 |
| _source_file | string | Lineage tracking |
| Unit Group ID | string | Derived: first 5 chars of OaSIS Code |
| NOC Element Code | string | Derived: last 2 chars (YY portion) |

**Skills table example:** 35 columns including Reading Comprehension, Writing, Numeracy, Digital Literacy, etc.

#### Element Attributes (text descriptions)
Labels, Lead Statement, Main Duties, Employment Requirements, Example Titles, Workplaces/Employers, Additional Information, Exclusions

| Column | Type | Description |
|--------|------|-------------|
| OaSIS profile code | string | Format: XXXXX.YY |
| [Text column] | string | Description text (varies by table) |
| _source_file | string | Lineage tracking |
| Unit Group ID | string | Derived from profile code |
| NOC Element Code | string | Derived from profile code |

**Main duties example:** One row per duty statement, multiple rows per occupation.

---

### 3. COPS Forecasting
**Source:** `cops-forecasting` (Open Canada)
**Files:** 13 (bilingual)
**Rows:** ~6,929 total

**Common schema across all COPS tables:**

| Column | Type | Description |
|--------|------|-------------|
| Code | string | NOC code or aggregation code (00000, TEER_0, NOC1_1, 00010, etc.) |
| Occupation Name | string | English name |
| Nom de la profession | string | French name |
| 2023 | int | Base year value |
| 2024-2033 | int | Projection values for each year |
| _source_file | string | Lineage tracking |

**Table categories:**
- **Demand tables:** employment, employment_growth, job_openings, retirements, retirement_rates, other_replacement
- **Supply tables:** school_leavers, immigration, other_seekers, job_seekers_total
- **Summary tables:** summary, flmc, rlmc (assessments)

**Special codes:**
- `00000`: All Occupations aggregate
- `TEER_0` through `TEER_5`: TEER level aggregates
- `NOC1_0` through `NOC1_9`: Major group aggregates
- 5-digit codes: Unit group projections

---

### 4. Job Architecture (Local Private)
**Source:** `local-private`
**Files:** 1 CSV + 1 XLSX (master)
**Rows:** 1,987

| Column | Type | Description |
|--------|------|-------------|
| JT_ID | int | Job title unique identifier |
| Job_Title | string | English job title |
| Titre_de_poste | string | French job title |
| Job_Function | string | EN function name |
| Fonction_professionnelle | string | FR function name |
| Job_Family | string | EN family name |
| Famille_d'emplois | string | FR family name |
| Managerial_Level | string | EN level (Employee, Director, etc.) |
| Niveau_de_gestion | string | FR level |
| 2016_NOC_UID | string | NOC 2016 code |
| 2016_NOC_Title | string | NOC 2016 title |
| 2021_NOC_UID | string | NOC 2021 code |
| 2021_NOC_Title | string | NOC 2021 title |
| Match_Key | int | Unique match identifier |
| PSES_Subset_Mapping | string | PSES classification |
| Job_Bank_GC | string | Job Bank flag (y/n) |
| [Additional columns] | string | Notes and alternates |

**Hierarchy:** L7 (job titles) -> L6 (job families) -> job functions

---

### 5. DIM Occupations / Departmental Tables (Local Private)
**Source:** `local-private`
**Files:** 4 (employee, job_data, job_description, position)
**Rows:** 12-16 per table (sample data)

These are supplementary tables for the semantic model. Low priority for initial ingestion.

---

## Open Canada Data Patterns

### Download Mechanism

Open Canada provides CSV downloads via CKAN API. The prototype's `resources.json` documents each resource with:

```json
{
  "id": "38932102-f7a9-40c6-b4f1-fa8e81981726",
  "name": {"en": "Skills 2023 v1.0", "fr": "Competences 2023 v1.0"},
  "format": "CSV",
  "language": ["en"],
  "hash": "5055af89d4c5c4f713e8fe403bd33824",
  "url": "https://open.canada.ca/data/dataset/.../download/skills_oasis_2023_v1.0-1.csv",
  "last_modified": "2025-08-27T17:48:19",
  "local_paths": ["data/bronze/public/qualitative/English/OASIS/skills/..."]
}
```

### File Naming Convention

Open Canada files retain original names like:
- `skills_oasis_2023_v1.0-1.csv`
- `employment_emploi_2024_2033_noc2021.csv`
- `noc_2021_version_1.0_-_classification_structure.csv`

### Versioning

Files are dated by version (e.g., `2023_v1.0`) and projection period (e.g., `2024_2033`). The prototype tracks `last_modified` from CKAN metadata.

---

## Prototype Patterns to Adopt

### 1. sources.json Structure (HIGH confidence)

The prototype's `sources.json` provides authoritative source registry:

```json
{
  "source_id": "noc-structure",
  "name": {"en": "NOC Structure", "fr": "Structure de la CNP"},
  "source_type": "open_data",
  "url": "https://open.canada.ca/data/en/dataset/...",
  "schema_metadata": {
    "source": "noc",
    "data_type": "QL",
    "subtype": "RF"
  },
  "hierarchy_levels": {...},
  "business_metadata": {...}
}
```

**Recommendation:** Copy `sources.json` to JobForge 2.0 and create `SourceRegistry` class to load and query it.

### 2. Schema Code Format (HIGH confidence)

```
{source}_{category}_{lang}_{level}{type}{subtype}.csv
```

| Segment | Description | Values |
|---------|-------------|--------|
| source | Data origin | `noc`, `oasis`, `cops`, `gc` |
| category | Content type | `skills`, `structure`, `employment`, etc. |
| lang | Language | `en`, `fr`, `bi` |
| level | Hierarchy | `L0`-`L7`, `??` for unknown |
| type | Data type | `QL` (qualitative), `QN` (quantitative) |
| subtype | Qualitative subtype | `OA`, `NE`, `RF`, `00` |

**Example:** `oasis_skills_en_L5QLOA.csv`

### 3. Bronze Folder Structure (HIGH confidence)

```
bronze/
├── public/
│   ├── qualitative/
│   │   ├── english/
│   │   │   ├── dim_noc/noc_structure/
│   │   │   ├── oasis/{category}/
│   │   │   └── element/{category}/
│   │   └── french/
│   └── quantitative/
│       └── bilingual/
│           ├── cops_facts/{supply,demand}/
│           └── cops_summaries/
└── private/
    └── qualitative/
        └── bilingual/
            ├── master_dim_gc_structure/
            └── departmental_tables/
```

### 4. Transform Classes (HIGH confidence)

The prototype defines transform classes with inheritance:

| Class | Inherits | Operations |
|-------|----------|------------|
| `base` | - | normalize_encoding, trim_headers, add_source_lineage |
| `oasis_proficiency` | base | derive_unit_group_id, derive_element_code |
| `element_text` | base | derive_unit_group_id, derive_element_code |
| `cops_fact` | base | (none additional) |
| `passthrough` | base | (none additional) |

### 5. Derived Columns (HIGH confidence)

| Column | Source | Format | Description |
|--------|--------|--------|-------------|
| `Unit Group ID` | OaSIS Code | 5-digit zero-padded | Primary key for butterfly spine |
| `NOC Element Code` | OaSIS Code decimal | 2-digit | Element identifier within NOC |
| `_source_file` | Filename | String | Source lineage tracking |

---

## Pipeline Integration Points

### Phase 1 Infrastructure Available

The Phase 1 implementation provides:

1. **PipelineEngine** (`src/jobforge/pipeline/engine.py`)
   - `ingest(source_path, table_name, domain)` - Entry point for CSV files
   - `promote_to_bronze(staged_path, schema)` - Schema transformations
   - `promote_to_silver(bronze_path, transforms)` - Cleaning transforms
   - `promote_to_gold(silver_path, transforms)` - Business transforms
   - `run_full_pipeline(...)` - Convenience method for all stages

2. **Layer Classes** (`src/jobforge/pipeline/layers.py`)
   - `StagedLayer.ingest()` - Reads CSV/Excel/JSON/Parquet, adds provenance
   - `BronzeLayer.process()` - Renames, casts, no business logic
   - `SilverLayer.process()` - Cleaning transforms
   - `GoldLayer.process()` - Business transforms

3. **Provenance** (`src/jobforge/pipeline/provenance.py`)
   - `add_provenance_columns()` - Adds _source_file, _ingested_at, _batch_id, _layer
   - `generate_batch_id()` - UUID generation
   - `update_layer_column()` - Updates _layer on promotion

4. **CatalogManager** (`src/jobforge/pipeline/catalog.py`)
   - `save_table_metadata()` - Saves TableMetadata to JSON
   - `load_table_metadata()` - Retrieves by table name
   - `list_tables()` - Lists all or filtered by layer
   - `get_lineage_logs()` - Retrieves transition logs

5. **GoldQueryEngine** (`src/jobforge/pipeline/query.py`)
   - DuckDB views over gold parquet files
   - Persistent connection for SQL queries

### Integration Pattern

```python
# Phase 2 code will:
engine = PipelineEngine()

# 1. Load source registry
registry = SourceRegistry.load("sources.json")

# 2. For each source file:
source_info = registry.get_source("noc-structure")
csv_path = Path("data/source/noc_structure.csv")

# 3. Ingest through pipeline
result = engine.ingest(csv_path, table_name="dim_noc_structure", domain="noc")

# 4. Promote with schema transforms
bronze_schema = {
    "rename": {"Code - NOC 2021 V1.0": "noc_code"},
    "cast": {"Level": pl.Int32}
}
result = engine.promote_to_bronze(result["staged_path"], bronze_schema)

# 5. Apply silver transforms
def add_unit_group_id(df: pl.LazyFrame) -> pl.LazyFrame:
    return df.with_columns(
        pl.col("noc_code").str.zfill(5).alias("unit_group_id")
    )

result = engine.promote_to_silver(result["bronze_path"], [add_unit_group_id])

# 6. Promote to gold
result = engine.promote_to_gold(result["silver_path"])
```

---

## Transformation Requirements

### Bronze Layer (Schema Only)

| Source | Transformations |
|--------|-----------------|
| NOC Structure | Rename columns to snake_case, cast Level to int |
| OASIS/Element | None - keep original schema |
| COPS | Rename columns to snake_case |
| Job Architecture | Clean column names (remove special chars) |

### Silver Layer (Cleaning/Normalization)

| Source | Transformations |
|--------|-----------------|
| NOC Structure | Filter to L5 only for dim_noc; derive parent IDs |
| OASIS/Element | Derive `unit_group_id`, `noc_element_code` from OaSIS code |
| COPS | Standardize NOC code column; handle N/A values |
| Job Architecture | Derive `unit_group_id` from 2021_NOC_UID |

### Gold Layer (Business Logic)

| Source | Transformations |
|--------|-----------------|
| All | Final column selection for Power BI |
| COPS | Calculate workforce gap measures |
| Job Architecture | Link to dim_noc via unit_group_id |

---

## Key Risks and Mitigations

### 1. Source File Location Discovery

**Risk:** Files may not be in expected locations; prototype has hardcoded paths.

**Mitigation:**
- Create `SourceLocator` class that checks multiple locations
- Support both prototype paths and JobForge 2.0 data/ directory
- Provide download commands for missing files

### 2. Schema Drift

**Risk:** Open Canada may update file schemas without notice.

**Mitigation:**
- Store expected schemas in catalog/schemas/
- Validate incoming files against expected columns
- Log warnings for unexpected columns

### 3. NOC Code Variations

**Risk:** NOC codes appear in different formats (00010, 10.00, 00010.00).

**Mitigation:**
- Standardize to 5-digit zero-padded in silver layer
- Create `normalize_noc_code()` utility function
- Test with sample data from each source

### 4. Bilingual Data Handling

**Risk:** Some tables are bilingual (COPS), others split by language (OASIS).

**Mitigation:**
- Track language in schema metadata
- Process bilingual tables once, not twice
- Use language suffix in table names where appropriate

### 5. Versioning and Change Detection

**Risk:** Need to know if file content changed vs just re-downloaded.

**Mitigation:**
- Use file hash (MD5) from CKAN metadata
- Store hash in catalog metadata
- Only create new version if hash differs

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSV parsing | Custom CSV parser | Polars scan_csv | Handles encoding, delimiters, quoting |
| Schema validation | Field-by-field checks | Pydantic models | Built-in validation, serialization |
| File hashing | Custom hash function | hashlib.md5 | Standard, matches CKAN format |
| NOC hierarchy | Recursive tree builder | Self-join on code prefixes | Data already has level info |

---

## Code Examples

### Derive Unit Group ID from OaSIS Code

```python
# Source: Prototype DATA_ENGINEERING_CYCLE.md pattern
def derive_unit_group_id(df: pl.LazyFrame) -> pl.LazyFrame:
    """Extract 5-digit Unit Group ID from OaSIS code.

    OaSIS code format: XXXXX.YY (e.g., 00010.00)
    Unit Group ID: First 5 characters, zero-padded
    """
    return df.with_columns(
        pl.col("OaSIS Code - Final")
        .str.slice(0, 5)
        .str.zfill(5)
        .alias("unit_group_id")
    )

def derive_noc_element_code(df: pl.LazyFrame) -> pl.LazyFrame:
    """Extract 2-digit NOC Element Code from OaSIS code.

    OaSIS code format: XXXXX.YY
    Element code: Last 2 characters after decimal
    """
    return df.with_columns(
        pl.col("OaSIS Code - Final")
        .str.slice(-2)
        .alias("noc_element_code")
    )
```

### Normalize COPS NOC Code

```python
def normalize_cops_noc_code(df: pl.LazyFrame) -> pl.LazyFrame:
    """Standardize COPS Code column to unit_group_id format.

    COPS codes include aggregates (00000, TEER_0, NOC1_1) and
    5-digit unit group codes. Only 5-digit codes get unit_group_id.
    """
    return df.with_columns(
        pl.when(pl.col("Code").str.len_chars() == 5)
        .then(pl.col("Code").str.zfill(5))
        .otherwise(pl.lit(None))
        .alias("unit_group_id")
    )
```

### Source Registry Pattern

```python
# Source: Inspired by prototype sources.json structure
from pathlib import Path
from pydantic import BaseModel

class SourceMetadata(BaseModel):
    source_id: str
    name: dict[str, str]  # {"en": "...", "fr": "..."}
    source_type: str  # "open_data", "local", "api"
    url: str | None
    schema_metadata: dict
    business_metadata: dict

class SourceRegistry:
    def __init__(self, sources: list[SourceMetadata]):
        self._sources = {s.source_id: s for s in sources}

    @classmethod
    def load(cls, path: Path) -> "SourceRegistry":
        data = json.loads(path.read_text())
        sources = [SourceMetadata(**s) for s in data["sources"]]
        return cls(sources)

    def get_source(self, source_id: str) -> SourceMetadata:
        return self._sources[source_id]
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| NOC 2016 codes | NOC 2021 codes | 2021 | Job Architecture has both; use 2021 |
| Manual file tracking | CKAN hash-based versioning | Prototype | Enables change detection |
| Separate EN/FR processing | Schema codes track language | Prototype | Simpler processing logic |

**Deprecated/outdated:**
- NOC 2016: Still in Job Architecture for legacy reference, but 2021_NOC_UID is primary
- OASIS vs SIPEC: Same data, SIPEC is French branding; use unified "oasis" source code

---

## Open Questions

1. **Source file placement for v1**
   - What we know: Prototype has files in place; JobForge 2.0 has empty data/ structure
   - What's unclear: Should we copy from prototype or require user placement?
   - Recommendation: Document both options; prioritize manual placement for v1

2. **Language handling in gold layer**
   - What we know: Some tables have EN/FR in separate files, some are bilingual
   - What's unclear: Should gold layer unify or keep separate?
   - Recommendation: Keep separate for now; butterfly spine (dim_noc) is bilingual

3. **Aggregate row handling in COPS**
   - What we know: COPS files have 00000, TEER_*, NOC1_* aggregate rows
   - What's unclear: Should aggregates be in same table or separate fact_aggregates?
   - Recommendation: Filter to unit group level in gold; aggregates can be recalculated

---

## Sources

### Primary (HIGH confidence)
- Prototype sources.json: `C:\Users\Administrator\Dropbox\++ Results Kit\JobForge\backend\data\metadata\sources.json`
- Prototype DATA_ENGINEERING_CYCLE.md: `C:\Users\Administrator\Dropbox\++ Results Kit\JobForge\backend\data\DATA_ENGINEERING_CYCLE.md`
- Prototype bronze_tables.json: `C:\Users\Administrator\Dropbox\++ Results Kit\JobForge\backend\data\metadata\bronze\bronze_tables.json`
- Phase 1 implementation: `C:\Users\Administrator\Dropbox\++ Results Kit\JobForge 2.0\src\jobforge\pipeline\`

### Secondary (MEDIUM confidence)
- Actual CSV file headers from bronze layer (inspected during research)
- COPS facts documentation: `C:\Users\Administrator\Dropbox\++ Results Kit\JobForge\backend\data\metadata\tables\cops_facts.md`

### Tertiary (LOW confidence)
- None - all patterns verified from prototype implementation

---

## Metadata

**Confidence breakdown:**
- Source schemas: HIGH - inspected actual files
- Bronze patterns: HIGH - verified from working prototype
- Pipeline integration: HIGH - Phase 1 code reviewed
- Transformation requirements: MEDIUM - derived from patterns, not tested

**Research date:** 2026-01-18
**Valid until:** 2026-02-18 (30 days - stable domain)
