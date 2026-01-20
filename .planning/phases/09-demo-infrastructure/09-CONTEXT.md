# Phase 9: Demo Infrastructure - Context

**Gathered:** 2026-01-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Live demonstration capability: MCP integration with JobForge 2.0, `/stagegold` command triggerable via MCP, and narration UI showing Power BI building the WiQ model in real-time. Split screen demo with Power BI on one side, JobForge UI on other. This phase deploys and demonstrates what was built in Phases 6-8 — minimal transformation, primarily loading existing gold layer.

</domain>

<decisions>
## Implementation Decisions

### MCP Integration
- Power BI MCP extension only works in VS Code Pro (not terminal mode)
- Port from prototype `/JobForge/` which has working MCP config
- Development and testing must happen in VS Code Pro environment

### Narration UI Design
- **Visual style:** Clean, concise, elegant Apple-style interface in web browser
- **Information density:** Full transparency — show tables being created, relationships added, timing
- **Provenance display:** Yes, show sources inline as data flows (NOC, O*NET, LLM)
- **Status feedback:** Subtle indicators with progressive disclosure — checkmarks appear inline, hover reveals detail
- **Branding:** JobForge branding with "Workforce Intelligence" positioning
- **Color palette:** GC-aligned (Government of Canada red/white)
- **Activity log:** Current step prominent + last 3-5 steps faded below
- **Live counters:** Running totals (Tables: 12/24, Relationships: 15/22)
- **Tech stack:** Plain HTML/JS/CSS — no external CDN dependencies (GC deployment friendly)
- **Bilingual:** EN/FR toggle, full Official Languages Act compliance
- **Communication:** Server-Sent Events for real-time updates (works through GC proxies)
- **Responsive:** Fully responsive across devices (desktop, tablet, mobile)
- **Accessibility:** WCAG 2.1 AA compliant (GC standard)
- **Error handling:** Graceful display with retry/skip options
- **Dark mode:** Light/dark toggle, respects system preference

### Demo Flow (Wizard)
- **Style:** TurboTax-style wizard — guided flow with clear steps
- **Steps:**
  1. **Load** — User selects target directory/folder, hits Load
  2. **Power BI Prompts** — User responds to refresh/connection dialogs
  3. **Review** — Model loads, shows data quality visual + traceability logs (source provenance, DADM model-level mapping)
  4. **Catalogue** — Optional: prompted to create DAMA DMBOK-compliant data catalogue
- **Navigation:** Full back/forward — user can navigate freely between completed steps
- **State persistence:** Prompt to save on exit
- **Progress indicator:** Breadcrumb trail (clickable step names)
- **Help system:** Contextual tooltips (hover hints)
- **Keyboard:** Full keyboard support (Tab/Enter/Escape) — WCAG requirement
- **Shortcuts:** Standard only — no special power-user shortcuts
- **Completion:** Export option to CSV format; catalogue follows DAMA DMBOK best practices (reference user's DAMA materials)
- **DADM traceability:** Model-level compliance mapping (WiQ model traces to DADM requirements, not per-cell)

### Split Screen Setup
- **Layout:** Top: JobForge wizard / Bottom: Power BI (horizontal split)
- **Proportions:** Resizable by user with draggable divider
- **Window setup:** Single browser window with pop-out option for Power BI
- **PBI embed:** iframe embed (simpler than full Embedded API, works for demo)
- **Sync behavior:** Synced where possible — wizard step changes navigate Power BI to relevant view

### Claude's Discretion
- Exact loading skeleton design
- Precise spacing and typography within Apple aesthetic
- Default split proportions before user resizes
- iframe vs Embedded API upgrade path for future

</decisions>

<specifics>
## Specific Ideas

- "It should look like it would in a web browser. Clean, concise, elegant 'Apple' interface"
- "TurboTax wizard" style — guided steps, progress through stages, ability to review/go back
- Catalogue export must follow DAMA DMBOK best practices — reference user's DAMA materials directory
- v3.0 will build on this with JD builder wizard for managers — this demo sets the stage
- MCP configuration was hard to get working in prototype — reference that successful config

</specifics>

<deferred>
## Deferred Ideas

- Manager JD builder wizard — v3.0 milestone
- Power BI Embedded API integration (if more programmatic control needed) — future enhancement

</deferred>

---

*Phase: 09-demo-infrastructure*
*Context gathered: 2026-01-20*
