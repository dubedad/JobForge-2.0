# Technology Stack for v4.0 Governed Data Foundation

**Project:** JobForge v4.0
**Researched:** 2026-02-05
**Overall Confidence:** HIGH

---

## Executive Summary

v4.0 requires **minimal stack additions**. The existing Polars/DuckDB/Pydantic/httpx stack handles most new requirements. Key additions:

1. **cuallee** (>=0.13.0) for GC DQMF data quality validation - native Polars/DuckDB support
2. **ckanapi** (>=4.9) for Open Government Portal access to PAA/DRF datasets
3. **Streamlit** (>=1.41.0) for data quality dashboard UI

The existing O*NET client already implements v2 API patterns. DAMA audit integration extends existing compliance modules with no new dependencies.

**Total new install footprint:** ~45MB (vs ~50MB for Great Expectations alone)

---

## Recommended Stack Additions

### Data Quality Framework (GC DQMF)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **cuallee** | >=0.13.0 | Data quality checks | DataFrame-agnostic; native Polars + DuckDB support; 50+ built-in checks; maps directly to GC 9 dimensions; JOSS peer-reviewed |
| pointblank | >=0.13.0 | Interactive reports (optional) | Stakeholder-friendly HTML reports; DuckDB via Ibis; complements cuallee for presentation |

**Rationale:** cuallee is the best fit for JobForge's existing stack:
- Native Polars and DuckDB support (no conversion overhead)
- Built as pydeequ replacement with cleaner Python API
- 50+ validation checks covering completeness, accuracy, consistency
- Published in [Journal of Open Source Software](https://joss.theoj.org/papers/10.21105/joss.06684) (peer-reviewed)
- Lightweight: ~15MB vs Great Expectations ~50MB

**GC DQMF Dimension Mapping:**

| GC Dimension | cuallee Check | Notes |
|--------------|---------------|-------|
| Completeness | `is_complete()` | Null/missing value ratio |
| Accuracy | `is_in_range()`, `satisfies()` | Custom validation rules |
| Consistency | `is_unique()`, `has_pattern()` | Cross-field validation |
| Timeliness | Custom timestamp checks | Age of data calculation |
| Relevance | Business rule validation | Domain-specific |
| Reliability | `has_mean()`, `has_std()` | Statistical bounds |
| Coherence | `has_correlation()` | Cross-dataset alignment |
| Access | N/A | Out of cuallee scope (metadata) |
| Interpretability | N/A | Out of cuallee scope (documentation) |

**Integration pattern:**
```python
from cuallee import Check, CheckLevel
import polars as pl

def validate_gold_completeness(df: pl.DataFrame, table_name: str) -> dict:
    """Validate completeness against GC DQMF standards."""
    check = Check(CheckLevel.WARNING, f"{table_name}_completeness")

    # Required columns must be complete
    check.is_complete("noc_code")
    check.is_complete("title_en")

    # Pattern validation
    check.has_pattern("noc_code", r"^\d{5}$")

    result = check.validate(df)
    return {
        "dimension": "completeness",
        "table": table_name,
        "score": result.pass_rate,
        "checks_passed": result.n - result.failures,
        "checks_total": result.n,
    }
```

### Open Government Portal Access (PAA/DRF Data)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **ckanapi** | >=4.9 | CKAN API client | Official CKAN client; GET-only for open.canada.ca; maintained by CKAN core team |

**Rationale:** Canada's Open Government Portal uses CKAN. ckanapi is the official Python client:
- Maintained by CKAN core team (GitHub: ckan/ckanapi)
- Supports dataset search, resource download, metadata retrieval
- Works with open.canada.ca endpoints
- No authentication needed for public datasets

**Note:** PAA (Program Activity Architecture) was replaced by DRF (Departmental Results Framework) in 2017. DRF datasets are available on Open Government Portal.

**Integration pattern:**
```python
from ckanapi import RemoteCKAN

def fetch_drf_dataset(dataset_id: str) -> dict:
    """Fetch DRF dataset from Open Government Portal."""
    portal = RemoteCKAN("https://open.canada.ca/data")

    # Get dataset metadata
    dataset = portal.action.package_show(id=dataset_id)

    # Download resources (CSV/JSON)
    for resource in dataset["resources"]:
        if resource["format"].upper() == "CSV":
            # Download and process
            pass

    return dataset
```

**Known DRF datasets:**
- `320e0439-187a-4db5-b120-4079ed05ff99` - Departmental Results Framework and Program Inventory
- `9fbed581-4dd3-42c9-8244-59ee0b50bde8` - National Defence DRF

### Dashboard Layer

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **streamlit** | >=1.41.0 | Data quality dashboard UI | Production-ready Python dashboards; native DuckDB support; no frontend build |
| **plotly** | >=6.0.0 | Interactive visualizations | Interactive charts; integrates with Streamlit; hover/zoom/filter |

**Rationale:** Streamlit is the pragmatic choice for v4.0:
- Pure Python (matches existing stack, no Node.js)
- Production-grade in 2026 (enterprise features: OIDC, scaling)
- Native DuckDB integration for querying gold tables
- Deploys alongside existing FastAPI on separate port (8501)

**Integration pattern:**
```python
import streamlit as st
import duckdb
import plotly.express as px

# Connect to gold layer
conn = duckdb.connect("data/gold/jobforge.duckdb", read_only=True)

# Query quality metrics
quality_df = conn.execute("""
    SELECT table_name, dimension, score, measured_at
    FROM data_quality_scores
    WHERE measured_at >= CURRENT_DATE - INTERVAL 7 DAYS
    ORDER BY measured_at DESC
""").pl()

# Display dashboard
st.title("JobForge Data Quality Dashboard")
st.dataframe(quality_df)

fig = px.bar(quality_df, x="table_name", y="score", color="dimension")
st.plotly_chart(fig)
```

---

## Existing Stack (Reuse, No Changes)

These components already in pyproject.toml handle v4.0 requirements:

### O*NET API Integration

| Existing | Version | v4.0 Use |
|----------|---------|----------|
| httpx | >=0.27.0 | O*NET Web Services API v2 calls |
| tenacity | >=8.2.0 | Retry with exponential backoff |

**Status:** Existing `ONetClient` in `src/jobforge/external/onet/client.py` already implements:
- Basic auth header (X-API-Key via Authorization)
- Rate limit handling (429 retry with exponential backoff)
- Skills, abilities, knowledge endpoints
- Parallel attribute fetching via asyncio.gather

**v4.0 extension needed:** Add work activities, work context endpoints using same pattern:
```python
async def get_work_activities(self, soc_code: str) -> list[dict[str, Any]]:
    """Fetch work activities for a SOC code."""
    data = await self._request(f"/online/occupations/{soc_code}/summary/work_activities")
    return data.get("element", []) if data else []

async def get_work_context(self, soc_code: str) -> list[dict[str, Any]]:
    """Fetch work context for a SOC code."""
    data = await self._request(f"/online/occupations/{soc_code}/summary/work_context")
    return data.get("element", []) if data else []
```

### DAMA DMBOK Audit

| Existing | Version | v4.0 Use |
|----------|---------|----------|
| pydantic | >=2.12.0 | Compliance log models |
| structlog | >=24.0.0 | Structured audit logging |

**Status:** Existing `DAMAComplianceLog` in `src/jobforge/governance/compliance/dama.py` implements 11 knowledge areas. v4.0 extends this with:
- More granular evidence collection (practice-level, not just area-level)
- Automated evidence generation from pipeline runs
- DAMA-8 (Data Quality) integration with cuallee results

**No new dependencies needed.** DAMA DMBOK is a framework, not a technology.

### Web Scraping (PAA/DRF Alternative)

| Existing | Version | v4.0 Use |
|----------|---------|----------|
| beautifulsoup4 | >=4.12.0 | HTML parsing fallback |
| requests | >=2.31.0 | HTTP for sync scraping |
| httpx | >=0.27.0 | HTTP for async scraping |

**Status:** TBS/CAF scraper patterns in `src/jobforge/external/tbs/scraper.py` established. Can reuse for:
- GC InfoBase if CKAN fails
- GC HR Data Model pages (if published)

### Policy Provenance

| Existing | Version | v4.0 Use |
|----------|---------|----------|
| pdfplumber | >=0.11.0 | PDF text extraction |
| networkx | >=3.0 | Provenance DAG extension |

**Status:** pdfplumber already used for PDF extraction. Policy document paragraph-level indexing extends existing provenance graph.

### Data Pipeline

| Existing | Version | v4.0 Use |
|----------|---------|----------|
| polars | >=1.37.0 | DataFrame operations |
| duckdb | >=1.4.0 | SQL queries on gold tables |
| pyarrow | >=15.0.0 | Parquet I/O |

**Status:** Core pipeline unchanged. Data quality checks via cuallee integrate at layer transitions.

---

## Installation Commands

### New Dependencies

```bash
# Data quality validation
pip install "cuallee>=0.13.0"

# Open Government Portal access
pip install "ckanapi>=4.9"

# Dashboard layer
pip install "streamlit>=1.41.0" "plotly>=6.0.0"

# Optional: pointblank for stakeholder reports
pip install "pointblank[duckdb]>=0.13.0"
```

### Updated pyproject.toml

```toml
dependencies = [
    # ... existing dependencies unchanged ...

    # v4.0 additions
    "cuallee>=0.13.0",
    "ckanapi>=4.9",
    "streamlit>=1.41.0",
    "plotly>=6.0.0",
]

[project.optional-dependencies]
dev = [
    # ... existing dev dependencies ...
]

dashboard = [
    "streamlit>=1.41.0",
    "plotly>=6.0.0",
    "pointblank[duckdb]>=0.13.0",
]
```

---

## What NOT to Use

### Great Expectations

**Reason:** Does not support Polars natively. [GitHub discussion #10144](https://github.com/great-expectations/great_expectations/discussions/10144) shows community requesting Polars support via Narwhals adapter, but not officially supported as of 2026. cuallee provides same functionality with native Polars support and 1/3 the install size.

### Pandera (for DQ metrics)

**Reason:** While Pandera 0.29.0 supports Polars validation, it focuses on **schema validation** (type checking, column presence) rather than **data quality metrics** (completeness percentages, distribution analysis). cuallee provides quality-metric-focused checks aligned with GC DQMF dimensions.

**Note:** Keep existing Pydantic for schema validation. Add cuallee for quality metrics. Different purposes.

### Evidence BI

**Reason:** Introduces Node.js runtime dependency. JobForge is Python-only. Streamlit achieves same dashboard result without new runtime.

### Soda Core

**Reason:** YAML-first DSL conflicts with JobForge's code-first Pydantic patterns. Requires separate connector packages (soda-core-duckdb). Better suited for SQL-native teams, not Python-first pipelines.

### Apache Atlas / OpenMetadata

**Reason:** Enterprise metadata catalogs are overkill for single-project scope. JobForge already has JSON-based catalog in `data/catalog/`.

### Django AuditLog / Python-Audit-Log

**Reason:** Django-specific or web-framework-focused. JobForge already has structlog-based audit logging. Extend existing patterns rather than introducing new paradigm.

### LlamaIndex / LangChain

**Reason:** Overkill for policy document paragraph indexing. stdlib regex + pdfplumber sufficient for DADM/DMBOK structure parsing.

---

## Version Compatibility Notes

### Python Version

- Keep Python 3.11+ requirement
- All new dependencies support 3.11 and 3.12

### DuckDB Compatibility

- cuallee uses DuckDB SQL interface (not relational API)
- pointblank uses Ibis for DuckDB connection
- Both work with DuckDB >=1.4.0 (current in pyproject.toml)

### Polars Compatibility

- cuallee >=0.13.0 has native Polars support
- Works with Polars >=1.0.0 (current: 1.37.0)
- No LazyFrame conversion overhead

### Streamlit + FastAPI Coexistence

- Streamlit runs on separate port (default 8501)
- FastAPI continues on existing port (default 8000)
- Docker Compose orchestrates both services
- Consider Traefik/nginx reverse proxy for unified entry point in production

---

## Integration Points Summary

| v4.0 Feature | New Library | Integrates With |
|--------------|-------------|-----------------|
| GC DQMF metrics | cuallee | Polars DataFrames, DuckDB tables |
| Quality dashboard | Streamlit + Plotly | DuckDB gold tables |
| PAA/DRF data | ckanapi | Existing medallion pipeline |
| O*NET 5th taxonomy | (existing httpx) | Existing ONetClient |
| DAMA audit | (existing pydantic) | Existing compliance module |
| Policy provenance | (existing pdfplumber) | Existing lineage graph |
| GC HR Data Model | (existing beautifulsoup4) | Existing scraper patterns |

---

## Sources

### HIGH Confidence (Official Documentation)

- [O*NET Web Services API](https://services.onetcenter.org/) - Existing client implements v2
- [O*NET Web Services Reference Manual](https://services.onetcenter.org/reference/) - API v2.0 specification
- [GC Guidance on Data Quality](https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/information-management/guidance-data-quality.html) - 9 dimensions definition
- [Open Government API](https://open.canada.ca/en/access-our-application-programming-interface-api) - CKAN API for open.canada.ca
- [ckanapi PyPI](https://pypi.org/project/ckanapi/) - Version 4.9 confirmed
- [cuallee PyPI](https://pypi.org/project/cuallee/) - Version and Polars/DuckDB support

### MEDIUM Confidence (Verified with Multiple Sources)

- [cuallee JOSS Paper](https://joss.theoj.org/papers/10.21105/joss.06684) - Peer-reviewed documentation
- [pointblank Documentation](https://posit-dev.github.io/pointblank/) - DuckDB integration via Ibis
- [Streamlit Documentation](https://streamlit.io/) - Production-ready status
- [2023-2026 Data Strategy](https://www.canada.ca/en/treasury-board-secretariat/corporate/reports/2023-2026-data-strategy.html) - GC data strategy context
- [DAMA DMBOK Framework Guide](https://atlan.com/dama-dmbok-framework/) - DAMA principles

### LOW Confidence (Needs Validation During Implementation)

- [DRF Datasets on Open Government Portal](https://open.canada.ca/data/en/dataset/320e0439-187a-4db5-b120-4079ed05ff99) - Verify specific datasets exist and coverage
- GC HR Data Model alignment - Limited public documentation found; may need TBS consultation
- PAA historical data - PAA replaced by DRF in 2017; historical data availability varies

---

## Open Questions for Phase Planning

1. **GC HR Data Model:** Limited public documentation. Need to verify if data model specification is published or requires direct TBS engagement.

2. **PAA/DRF Completeness:** Open Government Portal has DRF data, but coverage across departments varies. May need department-specific scraping for complete coverage.

3. **O*NET Rate Limits:** Current client handles 429 responses. v4.0 expanded usage (5th taxonomy for all NOCs) may need higher rate limit tier from O*NET developer program.

4. **Dashboard Authentication:** Streamlit has OIDC support for enterprise. Determine if v4.0 dashboard needs authentication or is internal-only.

5. **cuallee vs pandera:** Could use both - pandera for schema validation (types, required columns), cuallee for quality metrics (completeness scores, distribution checks). Evaluate if dual approach adds value or complexity.

---

*Generated by research agent for v4.0 Governed Data Foundation roadmap planning*
