---
phase: 09-demo-infrastructure
plan: 01
subsystem: demo
tags: [mcp, sse, starlette, uvicorn, power-bi, narration]

# Dependency graph
requires:
  - phase: 05-deployment
    provides: WiQDeployer, MCPClient, get_table_source
provides:
  - MCP permissions for Power BI operations
  - /stagegold command for Claude Code deployment
  - SSE backend streaming deployment narration events
  - CLI command to start demo server
affects: [09-02, power-bi-integration, live-demo]

# Tech tracking
tech-stack:
  added: [uvicorn>=0.30.0, starlette>=0.38.0, sse-starlette>=2.0.0]
  patterns: [SSE streaming, narration-only orchestrator, async generators]

key-files:
  created:
    - .claude/settings.local.json
    - .claude/commands/stage-gold.md
    - src/jobforge/demo/__init__.py
    - src/jobforge/demo/events.py
    - src/jobforge/demo/orchestrator.py
    - src/jobforge/demo/app.py
    - tests/demo/__init__.py
    - tests/demo/test_events.py
    - tests/demo/test_orchestrator.py
  modified:
    - pyproject.toml
    - src/jobforge/cli/commands.py

key-decisions:
  - "09-01-D1: Narration-only orchestrator - does NOT call MCP tools"
  - "09-01-D2: SSE streaming with small delays for visual effect"

patterns-established:
  - "Narration-only orchestrator: reads schema metadata, yields events, does not execute deployment"
  - "SSE event format: {event: type, data: json_string} via sse-starlette"
  - "Architecture split: Python backend narrates, Claude Code executes"

# Metrics
duration: 25min
completed: 2026-01-20
---

# Phase 9 Plan 1: MCP and SSE Backend Summary

**MCP configuration ported from prototype with 14 Power BI permissions, SSE backend streaming deployment narration events via Starlette, and CLI demo command with clear prerequisites**

## Performance

- **Duration:** 25 min
- **Started:** 2026-01-20T18:09:26Z
- **Completed:** 2026-01-20T18:34:00Z
- **Tasks:** 3
- **Files modified:** 11

## Accomplishments

- All 14 Power BI MCP Server permissions ported to settings.local.json
- /stagegold command created with JobForge 2.0 parquet paths and prerequisites
- DemoOrchestrator yields START, TABLE, RELATIONSHIP, COMPLETE events
- SSE endpoint at /api/deploy/stream streams narration events
- Demo CLI command with clear help text explaining architecture
- 32 new tests for demo module (330 total tests passing)

## Task Commits

Each task was committed atomically:

1. **Task 1: Port MCP Configuration, Stage-Gold Command, and Add Dependencies** - `255bb5b` (feat)
2. **Task 2: Create SSE Event Models and Demo Orchestrator** - `0053370` (feat)
3. **Task 3: Create Starlette App and CLI Command** - `88def52` (feat)

## Files Created/Modified

- `.claude/settings.local.json` - 14 MCP permissions for Power BI operations
- `.claude/commands/stage-gold.md` - Claude Code command for deployment
- `pyproject.toml` - Added uvicorn, starlette, sse-starlette dependencies
- `src/jobforge/demo/__init__.py` - Package exports
- `src/jobforge/demo/events.py` - EventType enum, DemoEvent dataclass
- `src/jobforge/demo/orchestrator.py` - DemoOrchestrator with stream_deployment()
- `src/jobforge/demo/app.py` - Starlette app with SSE endpoint
- `src/jobforge/cli/commands.py` - Added demo command
- `tests/demo/test_events.py` - 18 tests for event models
- `tests/demo/test_orchestrator.py` - 14 tests for orchestrator

## Decisions Made

1. **09-01-D1: Narration-only orchestrator**
   - DemoOrchestrator reads schema and yields metadata events
   - Does NOT import or call MCPClient
   - Actual deployment executed by Claude Code externally
   - Clear architecture separation verified by test

2. **09-01-D2: SSE streaming with visual delays**
   - 0.1s delay after START event
   - 0.05s delay between TABLE events
   - 0.03s delay between RELATIONSHIP events
   - Provides smooth visual progression in UI

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Test initially imported non-existent `DataType` from semantic.models
- Fixed by using string data types directly (e.g., "VARCHAR" instead of DataType.VARCHAR)

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- SSE backend ready for Plan 02 (web UI implementation)
- MCP permissions in place for live demo
- /stagegold command ready for Claude Code to execute
- CLI command documents recommended demo setup flow

**Ready for:**
- Plan 02: Web UI with wizard steps, bilingual support, GC design
- Live demo: Power BI Desktop + JobForge UI side-by-side

---
*Phase: 09-demo-infrastructure*
*Plan: 01*
*Completed: 2026-01-20*
