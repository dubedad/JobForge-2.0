# JobForge 2.0

A workforce intelligence platform that deploys a governed semantic model (WiQ) to Power BI with full data lineage and provenance tracking.

## What It Does

JobForge ingests authoritative Canadian occupational data through a medallion pipeline (staged → bronze → silver → gold), producing 24 queryable gold tables with a star schema ready for enterprise analytics.

**Data Sources:**
- NOC (National Occupational Classification) - 516 occupations
- COPS (Canadian Occupational Projection System) - 10-year forecasts
- OaSIS proficiency ratings
- Job Architecture (1,987 job titles)
- O*NET/SOC crosswalk for international alignment

## Core Value

**Auditable provenance from source to output** — every artifact traces back to authoritative sources. When asked "where did this come from?", JobForge can answer with the complete pipeline path, including DADM directive chapter and verse.

## Features

### v1.0 (Shipped)
- Medallion pipeline with full provenance tracking
- 24 gold tables in parquet format
- 22 relationships in WiQ semantic model
- `/stagegold` command for Power BI deployment
- `/lineage` CLI for data lineage queries
- Data catalogue with 24 table metadata files
- 100 tests passing

### v2.0 (In Progress - 60%)
- Hierarchical attribute imputation (L5→L6→L7 inheritance)
- O*NET API integration for SOC-aligned attributes
- LLM-powered description generation with provenance
- TBS Occupational Groups scraping
- MCP-driven live demo capability
- 298 tests passing

## Tech Stack

- **Language:** Python 3.11
- **Data Processing:** Polars, DuckDB
- **Schema Validation:** Pydantic 2
- **Graph/Lineage:** NetworkX
- **CLI/UI:** Rich
- **External APIs:** O*NET, OpenAI (gpt-4o)
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
│   └── external/        # O*NET, TBS, LLM integrations
├── data/
│   ├── source/          # Raw downloaded files
│   ├── staged/          # Parquet with provenance
│   ├── bronze/          # Type-enforced
│   ├── silver/          # Cleaned & harmonized
│   ├── gold/            # Business-ready (24 tables)
│   └── catalog/         # Metadata & lineage logs
├── tests/               # 298 tests
└── .planning/           # GSD project management
```

## Quick Start

```bash
# Install
pip install -e .

# Run pipeline
jobforge ingest --all

# Deploy to Power BI
jobforge stagegold --dry-run  # Preview
jobforge stagegold            # Deploy

# Query lineage
jobforge lineage "where does dim_noc come from?"
```

## Government of Canada Context

HR job data across federal government is unstructured, non-standardized, fragmented, siloed, and unreliable. JobForge enables evidence-based workforce planning while demonstrating DADM (Directive on Automated Decision-Making) compliance.

## License

Proprietary - Government of Canada

---

*Built with [GSD](https://github.com/gsd-framework/gsd) (Get Stuff Done) methodology*
