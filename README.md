# JobForge 2.0

A workforce intelligence platform that deploys a governed semantic model (WiQ) to Power BI with full data lineage, provenance tracking, and GC compliance.

## What It Does

JobForge ingests authoritative Canadian occupational data through a medallion pipeline (staged → bronze → silver → gold), producing **39 queryable gold tables** with a star schema ready for enterprise analytics.

**Data Sources:**
- **NOC** (National Occupational Classification) - 516 occupations with OaSIS proficiency ratings
- **COPS** (Canadian Occupational Projection System) - 10-year employment forecasts
- **Job Architecture** - 1,987 federal job titles with NOC mappings
- **TBS Occupational Groups** - 31 OG codes, 111 subgroups, qualification standards, pay rates
- **CAF Careers** - 88 military occupations with training data
- **O*NET/SOC** crosswalk for international alignment

## Core Value

**Auditable provenance from source to output** — every artifact traces back to authoritative sources. When asked "where did this come from?", JobForge answers with the complete pipeline path, including DADM directive chapter and verse.

## Current Status

| Version | Status | Phases | Key Deliverables |
|---------|--------|--------|------------------|
| v1.0 MVP | Shipped | 1-5 | Medallion pipeline, 24 gold tables, WiQ schema |
| v2.0 Self-Imputing | Shipped | 6-10 | LLM imputation, O*NET integration, live demo |
| v2.1 Orbit Integration | Shipped | 11-13 | Text-to-SQL, Docker deployment, RFC 9457 errors |
| v3.0 Data Layer Expansion | Shipped | 14-16 | TBS OG, CAF Careers, NOC concordance bridges |
| **v4.0 Governed Data Foundation** | **In Progress** | 17-23 | DAMA audit, data quality dashboard, O*NET taxonomy |

**Stats:** 39 gold tables, 36 relationships, 1,197 tests passing

## Features

### v1.0 MVP
- Medallion pipeline with full provenance tracking
- 24 gold tables in parquet format
- 22 relationships in WiQ semantic model
- `/stagegold` command for Power BI deployment
- `/lineage` CLI for data lineage queries
- Data catalogue with table metadata

### v2.0 Self-Imputing Model
- Hierarchical attribute imputation (L5→L6→L7 inheritance)
- O*NET API integration for SOC-aligned attributes
- LLM-powered description generation with provenance
- MCP-driven live demo capability

### v2.1 Orbit Integration
- Text-to-SQL via enhanced DDL with semantic hints
- Docker Compose one-command deployment
- RFC 9457 error handling with actionable guidance
- Workforce domain intelligence (demand/supply classification)

### v3.0 Data Layer Expansion
- TBS Occupational Groups: 31 OG codes, 111 subgroups, 6,765 pay rates
- CAF Careers: 88 military occupations, 11 job families, training data
- NOC-OG concordance: 2,486 fuzzy-matched mappings with confidence scoring
- CAF bridges: 880 NOC + 880 JA mappings with provenance
- DMBOK tagging: 110 columns with governance metadata

### v4.0 Governed Data Foundation (In Progress)
- DAMA DMBOK compliance audit with policy provenance
- GC DQMF 9-dimension data quality scoring
- O*NET as 5th taxonomy (completing the 5-taxonomy model)
- PAA/DRF integration from Open Government Portal
- GC HR Data Model alignment

## Tech Stack

- **Language:** Python 3.11
- **Data Processing:** Polars, DuckDB
- **Schema Validation:** Pydantic 2
- **Graph/Lineage:** NetworkX
- **CLI/UI:** Rich, Typer
- **Matching:** rapidfuzz
- **Web Scraping:** httpx, beautifulsoup4, tenacity
- **LLM Integration:** OpenAI, Anthropic
- **API:** FastAPI, uvicorn
- **Target Platform:** Power BI

## Project Structure

```
JobForge 2.0/
├── src/jobforge/
│   ├── pipeline/        # Medallion layer orchestration
│   ├── ingestion/       # Source data ingestion modules
│   ├── semantic/        # WiQ schema and relationships
│   ├── deployment/      # Power BI deployment
│   ├── lineage/         # DAG-based lineage tracking
│   ├── description/     # Description generation service
│   ├── catalog/         # Data catalogue and DMBOK tagging
│   ├── concordance/     # NOC-OG, CAF-NOC matching
│   ├── external/        # O*NET, TBS, CAF integrations
│   └── api/             # FastAPI routes
├── data/
│   ├── source/          # Raw downloaded files
│   ├── staged/          # Parquet with provenance
│   ├── bronze/          # Type-enforced
│   ├── silver/          # Cleaned & harmonized
│   ├── gold/            # Business-ready (39 tables)
│   └── catalog/         # Metadata, lineage, governance
├── tests/               # 1,197 tests
└── .planning/           # GSD project management
```

## Quick Start

```bash
# Install
pip install -e .

# Run full pipeline
jobforge ingest --all

# Deploy to Power BI
jobforge stagegold --dry-run  # Preview
jobforge stagegold            # Deploy

# Query lineage
jobforge lineage "where does dim_noc come from?"

# Refresh CAF data
jobforge caf refresh
jobforge caf status

# Start API server
jobforge api
```

## Government of Canada Context

HR job data across federal government is unstructured, non-standardized, fragmented, siloed, and unreliable. JobForge enables evidence-based workforce planning while demonstrating:

- **DADM** (Directive on Automated Decision-Making) compliance
- **DAMA DMBOK 2.0** governance alignment
- **GC DQMF** data quality framework adherence

## License

Proprietary - Government of Canada

---

*Built with [GSD](https://github.com/anthropics/claude-code) (Get Stuff Done) methodology*
