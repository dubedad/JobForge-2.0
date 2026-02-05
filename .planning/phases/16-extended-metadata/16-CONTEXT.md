# Phase 16: Extended Metadata - Context

**Gathered:** 2026-02-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Enrich OG and CAF data with qualification standards, job evaluation, training requirements, and governance metadata. Includes represented pay rates, collective agreements, and DMBOK practice provenance. Users can query detailed role requirements, pay structures, and training paths with full audit trails.

</domain>

<decisions>
## Implementation Decisions

### Content Depth

**Qualification Standards:**
- Full text + structured fields (education, experience, certification, language)
- Separate fields for essential vs asset qualifications
- Structured bilingual requirements (reading, writing, oral levels)
- Structured security clearance levels (Reliability, Secret, Top Secret)
- Professional designations normalized to dim_professional_designation with FK
- Experience: numeric min_years + original text for context
- Education: standardized credential level + original text
- Equivalency statements: has_equivalency boolean + equivalency_statement text
- Cross-reference TBS competencies to OASIS skills/abilities where possible
- Structured conditions of employment flags (requires_travel, shift_work, physical_demands)
- Structured operational requirements flags (overtime, on-call, deployments)

**Job Evaluation Standards:**
- Both classification standard definitions AND evaluation factors
- Numeric points where available + descriptive text for all levels
- Full history if TBS provides historical versions
- Per-record source URLs linking back to TBS authority

**General:**
- Per-record source URLs to authoritative TBS pages
- Track effective dates and version history for standards

### Representation Scope

**Pay Rates:**
- Both excluded employees (Phase 14-04) AND represented (unionized) rates
- All available historical rates scraped (not just current)
- Regional pay differentials if TBS publishes them
- EX salary ranges included from TBS executive compensation
- pay_progression_type field: 'step', 'performance', or 'hybrid'

**Collective Agreements:**
- dim_collective_agreement table with FK from pay rates
- Full metadata: name, expiry date, bargaining agent, employer signatory

**Allowances:**
- fact_og_allowances separate table (bilingual bonus, supervisory, isolated post, etc.)

### CAF Training Coverage

**Scope:**
- All 107 CAF occupations included (even if training info sparse)
- BMQ and occupation-specific training as separate records

**Training Details:**
- Duration: standardized weeks + original text
- Locations: normalized dim_caf_training_location with FK
- Certifications/qualifications awarded: linked to training programs
- Prerequisites: structured prerequisite_courses array + minimum_rank field
- Civilian equivalency: mapped to standardized credential levels
- Recurring requirements: recertification_required boolean + recertification_frequency

### Governance Granularity

**DMBOK Tagging:**
- Table-level: primary DMBOK knowledge area
- Field-level: DMBOK data element types

**Data Quality:**
- Computed quality metrics per table (% complete, freshness date)

**Stewardship:**
- data_steward and data_owner fields in catalog metadata

**Lineage:**
- Full lineage from source URL through bronze/silver/gold transformations
- Continue using data/catalog/lineage/ structure

**Metadata:**
- refresh_frequency field (daily, weekly, monthly, as_published)
- retention_period per table (e.g., '7 years', 'indefinite')
- GC security classification (Unclassified, Protected A/B/C)
- intended_consumers field (JD Builder, WiQ, Public API)

### Claude's Discretion
- Exact regex patterns for parsing qualification text
- Table normalization decisions (when to create lookup vs embed)
- Handling of inconsistent source data formats
- Matching algorithm details for competency cross-references

</decisions>

<specifics>
## Specific Ideas

- "Both numeric AND text for experience/education" — enables filtering by years while preserving original wording
- "Essential vs asset qualifications as separate fields" — critical for JD Builder to distinguish mandatory from preferred
- "Per-record source URLs" — auditability is core project value; users must be able to verify any data point
- "Full history" — supports trend analysis and audit trails
- "Cross-reference to OASIS" — enables skills-based matching across NOC and OG domains

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 16-extended-metadata*
*Context gathered: 2026-02-05*
