# Phase 13: Deployment and Documentation - Context

**Gathered:** 2026-01-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Production deployment configuration and integration documentation for Orbit + JobForge stack. One command starts everything, documentation serves both technical and business users.

Does NOT include: server deployment, auto-start on boot, or hosting infrastructure.

</domain>

<decisions>
## Implementation Decisions

### Deployment Approach
- One command to start everything (`docker-compose up` or equivalent)
- Browser automatically opens to chat interface on startup
- Both UIs available: JobForge demo wizard AND Orbit chat interface
- For now: personal/local use (may share with others later)

### Documentation Scope
- Audience: Both technical developers and business users
- Purposes:
  1. Get it running (step-by-step setup)
  2. Understand how it works (architecture overview)
  3. Ask workforce questions (example queries)
  4. Extend it (adding new patterns)

### Documentation Format
- Architecture diagram required (Mermaid or similar)
- Example queries covering all domains:
  - Labour supply/demand gaps
  - Occupation lookups (skills, NOC codes)
  - Trend analysis (employment projections)
  - Compliance/lineage (data provenance)
- Intent extension guide: Tutorial style (step-by-step walkthrough)

### Claude's Discretion
- Documentation location (README vs docs/ folder)
- Diagram format (Mermaid vs ASCII)
- Docker Compose file structure
- Environment variable naming conventions
- Port numbers and defaults

</decisions>

<specifics>
## Specific Ideas

- User wants browser to open automatically when system starts
- Both interfaces available but user doesn't need to choose between them
- Tutorial-style "Adding a new query pattern" guide for extensibility

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 13-deployment-documentation*
*Context gathered: 2026-01-20*
