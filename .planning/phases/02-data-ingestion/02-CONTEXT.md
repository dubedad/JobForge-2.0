# Phase 2: Data Ingestion - Context

**Gathered:** 2026-01-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Ingest all five source tables through the medallion pipeline to gold layer. Sources: DIM NOC, NOC Element/Oasis attributes, NOC COPS forecasting, Job Architecture, DIM Occupations. Each table must be queryable in gold with provenance intact.

</domain>

<decisions>
## Implementation Decisions

### Source file format
- CSV files (primary format for all sources)
- Sources are government open data (Open Canada) plus local private files

### Source locations
- URLs defined in prototype's `sources.json` at `C:\Users\Administrator\Dropbox\++ Results Kit\JobForge\backend\data\metadata\sources.json`
- 6 sources documented:
  - noc-structure: https://open.canada.ca/data/en/dataset/1feee3b5-8068-4dbb-b361-180875837593
  - noc-attributes: https://open.canada.ca/data/en/dataset/4f344cd6-0912-411a-ae16-41ea160cc8b5
  - cops-forecasting: https://open.canada.ca/data/en/dataset/e80851b8-de68-43bd-a85c-c72e1b3a3890
  - onet-api: https://services.onetcenter.org/
  - onet-holland-codes: https://www.onetonline.org/find/descriptor/browse/1.B.1
  - local-private: Local files (Job Architecture, departmental tables)

### Source acquisition
- Support BOTH manual placement AND download commands
- User can drop files into a known folder; pipeline reads from there
- Also provide download commands for convenience when sources are stale or missing

### Versioning strategy
- Versioned snapshots: keep historical versions
- Gold layer reflects latest data
- Old batches remain queryable
- Only create new version when file content has actually changed (not just re-downloaded)

### Metadata structure
- Capture the same metadata as prototype (sources, schema codes, hierarchy levels, routing rules)
- Use best implementation approach (prototype patterns if they're best, improve where appropriate)
- Prototype reference: `C:\Users\Administrator\Dropbox\++ Results Kit\JobForge\backend\data\DATA_ENGINEERING_CYCLE.md`

### Claude's Discretion
- Whether to copy sources.json structure directly or adapt it
- Schema code format (prototype uses `{source}_{category}_{lang}_{level}{type}{subtype}`)
- Bronze folder structure layout
- Transform class implementation
- Validation rules for each source
- Transformation depth in silver layer

</decisions>

<specifics>
## Specific Ideas

- Prototype already has 57 files ported to bronze with 97,132 total rows
- Butterfly semantic model architecture: NOC Unit Group ID as spine, attributes radiating in one-to-many relationships
- Schema codes encode metadata in filenames (source, category, language, hierarchy level, data type, subtype)
- Hierarchy levels: L0 (guide), L5 (Unit Group), L6 (attributes of L5), L7 (example-titles, Job Architecture)
- COPS tables split into supply/demand components for workforce gap calculation

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-data-ingestion*
*Context gathered: 2026-01-18*
