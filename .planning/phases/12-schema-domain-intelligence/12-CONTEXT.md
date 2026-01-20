# Phase 12: Schema and Domain Intelligence - Context

**Gathered:** 2026-01-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Improve text-to-SQL accuracy through enhanced DDL with semantic descriptions, relationship hints for joins, workforce-specific entity recognition (via folder structure semantics), and source attribution in query responses.

Does NOT include: extensive manual enrichment interview (deferred until after Orbit testing).

</domain>

<decisions>
## Implementation Decisions

### Metadata Enrichment Strategy
- **Hybrid approach**: Extract from existing docs first, manual enhancement later
- Extract column descriptions from RESEARCH.md files (Phase 2 has full data dictionaries)
- Extract from guide.csv (OaSIS metadata)
- Import from `C:\Users\Administrator\Dropbox\++ Results Kit\++JobForge Reference Docs` (NOC and Job Architecture docs)
- COPS glossary for forecasting terminology
- YAML-driven interview for key columns — **deferred until after Orbit testing**

### DDL Generation
- Both: Update catalog JSON files AND generate DDL with COMMENT statements
- DDL comments derived from enriched catalog (single source of truth)
- Include example values in comments for Claude context

### Workforce Domain Semantics (from folder structure)
- Add `workforce_dynamic` field to COPS table metadata
- Map from original JobForge bronze structure:
  - `cops_facts/demand/` → workforce_dynamic: "demand"
  - `cops_facts/supply/` → workforce_dynamic: "supply"
- DEMAND tables: employment, employment_growth, retirements, retirement_rates, other_replacement, job_openings
- SUPPLY tables: school_leavers, immigration, other_seekers, job_seekers_total
- This enables Claude to understand: Workforce Gap = SUM(demand) - SUM(supply)

### Entity Recognition
- Let Claude + enhanced DDL handle entity recognition
- No pre-processing layer for entity extraction
- Rich DDL with workforce_dynamic, column descriptions, and relationships gives Claude enough context

### Source Attribution
- Always include source attribution in query responses
- Format: "Source: {table_name} ({source_system})"
- Example: "Source: cops_employment (COPS Open Canada)"

### Claude's Discretion
- Exact DDL comment format
- How to structure multi-table relationship hints
- Handling of columns with no source documentation

</decisions>

<specifics>
## Specific Ideas

- Reference original JobForge bronze structure for DEMAND/SUPPLY categorization:
  ```
  bronze/public/quantitative/bilingual/cops_facts/
  ├── demand/           # employment, growth, retirements, replacement
  │   └── demand_totals/  # job_openings
  └── supply/           # school_leavers, immigration, other_seekers
      └── supply_totals/  # job_seekers_total
  ```
- Power BI measures from reference: `Workforce Gap = SUM(demand) - SUM(supply)`
- QA measures: Supply Components Sum, Supply Variance, Demand Replacement Sum

</specifics>

<deferred>
## Deferred Ideas

- Extensive YAML-driven interview for column/table enrichment — after Orbit testing
- Interview granularity: table-level, column-level, and question-driven all desired
- Business glossary population — future phase (PBI-02 in requirements)

</deferred>

---

*Phase: 12-schema-domain-intelligence*
*Context gathered: 2026-01-20*
