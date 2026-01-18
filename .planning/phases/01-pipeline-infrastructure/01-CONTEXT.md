# Phase 1: Pipeline Infrastructure - Context

**Gathered:** 2026-01-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Establish medallion pipeline framework so data can flow from source to gold layer with full provenance tracking. This is the foundation — no data ingestion, no semantic modeling, just the pipeline infrastructure itself.

</domain>

<decisions>
## Implementation Decisions

### Directory Structure
- **Claude's discretion** — apply DAMA DMBOK best practices
- Consider: where data lives, file organization per layer, historical versioning, naming conventions

### Layer Responsibilities
- **Claude's discretion** — apply DAMA DMBOK best practices
- Define what staged, bronze, silver, and gold layers each do
- Follow medallion architecture patterns per DAMA guidance

### Provenance Tracking
- **Claude's discretion** — apply DAMA DMBOK best practices
- Two types of metadata needed:
  1. **Row-level provenance** — columns in data (batch_id, ingested_at, source_file)
  2. **Table/column-level metadata** — separate catalog linking to:
     - Business glossary terms and definitions
     - Table descriptions and purpose
     - Lineage (upstream/downstream)
     - Business questions answered
     - Purview/Power BI property mappings
     - Source metadata (publication date, data steward)

### Error Handling
- **Claude's discretion** — apply DAMA DMBOK best practices
- Define failure modes, quarantine strategy, retry logic

### Claude's Discretion
All technical decisions for this phase are delegated to Claude, guided by:

1. **DAMA DMBOK Best Practices** at:
   `C:\Users\Administrator\Dropbox\++ Results Kit\JobForge\backend\data\reference\DAMA DMBOK best-practices`

   Key references:
   - `dama_02_data_architecture_dmbok_2_chapter_2_reference.md`
   - `dama_05_metadata_management_dmbok_2_chapter_5_reference.md`
   - `dama_07_data_integration_and_interoperability_dmbok_2_chapter_7_reference.md`
   - `dama_gc_adm_audit_overlay_policy_mapping.md` (for DADM alignment)

2. **Reference Prototype** at:
   `C:\Users\Administrator\Dropbox\++ Results Kit\JobForge`

   Contains working implementation patterns. User will point to specific parts when relevant.

</decisions>

<specifics>
## Specific Ideas

**Decision Process (project-wide):**
1. User points to relevant prototype patterns when hitting a decision point
2. Claude reviews prototype to understand what was done
3. Claude recommends implementation grounded in DAMA DMBOK
4. User approves (or iterates)

This preserves prototype knowledge while ensuring DAMA compliance without exhausting context on upfront explanations.

**Metadata Vision:**
User wants comprehensive traceability — every piece of data should link to business glossary, lineage, source metadata, and governance properties. Technical implementation (row-level vs catalog) is Claude's discretion per DAMA.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-pipeline-infrastructure*
*Context gathered: 2026-01-18*
