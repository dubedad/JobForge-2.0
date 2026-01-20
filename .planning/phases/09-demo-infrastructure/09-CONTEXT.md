# Phase 9: Demo Infrastructure - Context

**Gathered:** 2026-01-20
**Status:** Partial - continue in VS Code Pro

<domain>
## Phase Boundary

Live demonstration capability: MCP integration with JobForge 2.0, `/stagegold` command triggerable via MCP, and narration UI showing Power BI building the WiQ model in real-time. Split screen demo with Power BI on one side, JobForge UI on other.

</domain>

<decisions>
## Implementation Decisions

### MCP Integration
- **Constraint:** Power BI MCP extension only works in VS Code Pro, not terminal mode
- **Approach:** Port from prototype (JobForge) which has working MCP config after multiple attempts
- **Reference:** Check `/JobForge/` sibling directory for successful MCP configuration
- **Execution environment:** VS Code Pro required for MCP development and testing

### Claude's Discretion
- Pending full discussion in VS Code Pro environment

</decisions>

<specifics>
## Specific Ideas

- MCP configuration in prototype was hard to get working - reference that successful config
- Development must happen in VS Code Pro due to Power BI MCP extension constraint

</specifics>

<pending_discussion>
## Areas Still to Discuss

The following areas were identified but not yet discussed:
- Narration UI design (visual style, real-time updates, information density)
- Demo flow orchestration (automatic steps, manual triggers, timing)
- Split screen setup (layout, synchronization, what shows where)

Continue discussion in VS Code Pro with `/gsd:discuss-phase 9`.

</pending_discussion>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 09-demo-infrastructure*
*Context gathered: 2026-01-20 (partial)*
