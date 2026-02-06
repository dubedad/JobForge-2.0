# Phase 18: Data Quality Dashboard - Context

**Gathered:** 2026-02-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can assess and monitor data quality across all gold tables using the GC DQMF 9-dimension framework. Includes quality scoring, API access, Streamlit dashboard with visualizations, and trend tracking over time. Business metadata capture is a separate phase (19).

</domain>

<decisions>
## Implementation Decisions

### Dashboard Layout & Visualization
- Side-by-side radar chart comparison (2-3 tables on same radar)
- Summary grid landing page with traffic-light status for all tables
- Traffic lights show color + percentage score (e.g., 78%)
- Both search (by table name) and filtering (by domain, score thresholds)
- Desktop-first optimization (internal analyst tool)
- ISO date format (2026-02-05)
- Export: both PDF reports and CSV data dump

### Dimension Scoring Approach
- Fixed GC-aligned weights (not equal, not user-configurable)
- 9 GC DQMF dimensions scored per table

### Trend Tracking Behavior
- Degradation detection: both threshold crossing AND trend-based decline
- Sparklines in summary grid + dedicated trend page for deep analysis

### API & CLI Surface
- CLI outputs: Table (rich), JSON (--json), CSV (--csv)
- On-demand commands: full refresh + targeted single-table check

### Claude's Discretion
- Drill-down depth (column-level vs dimension-only)
- Specific traffic-light thresholds (research GC practice)
- Timeliness calculation method (days since refresh vs SLA-based)
- Handling of non-automatable dimensions (manual assessment, proxy metrics, or exclude)
- History retention period (balance storage vs audit utility)
- Snapshot granularity (daily, on-refresh, or weekly)
- API endpoint pattern (align with existing JobForge conventions)
- CLI command structure (subcommand vs flag patterns)

</decisions>

<specifics>
## Specific Ideas

- Radar charts support comparing multiple tables to spot patterns across datasets
- Traffic-light with score provides both quick visual scan and precision when needed
- Both absolute thresholds and trend detection catch different types of quality issues

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 18-data-quality-dashboard*
*Context gathered: 2026-02-05*
