# Phase 11: Validation and Hardening - Context

**Gathered:** 2026-01-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Validate existing Orbit components from Phase 10, ensure HTTP adapter routes queries correctly to JobForge API, and harden error handling for all 24 gold tables. This phase makes the existing integration reliable — no new capabilities.

Requirements: ORB-01, ORB-02, ORB-03, ORB-04

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

User delegated all implementation decisions for Phase 11. Claude has flexibility on:

**Error response format:**
- JSON structure for error responses
- User-friendly message content
- What diagnostic info to include (query, intent, timing)
- Error categorization (validation, execution, timeout, etc.)

**Intent classification:**
- Strictness of pattern matching
- Handling of ambiguous queries
- Fallback behavior when intent unclear
- Confidence thresholds

**Validation approach:**
- Test query coverage for 24 gold tables
- Which query patterns to validate
- Assertion strategy for responses

**API response structure:**
- Metadata to include (timing, source, confidence)
- Response envelope format
- Pagination/truncation behavior for large results

</decisions>

<specifics>
## Specific Ideas

**User context on Orbit:**
- User wants to understand how Orbit enables "conversation with the semantic model and knowledge graph"
- Clarified that Orbit is the conversational gateway that routes queries to JobForge capabilities
- Query flow: User → Orbit (intent classification) → JobForge API → DuckDB/NetworkX → Response

**Existing capabilities to validate:**
- Text-to-SQL (data queries)
- MetadataQueryService (table/column info)
- LineageQueryEngine (provenance via NetworkX DAG)
- Compliance queries (DADM/DAMA logs)

</specifics>

<deferred>
## Deferred Ideas

- Multi-turn conversation memory — explicitly out of scope for v2.1 (anti-feature)

</deferred>

---

*Phase: 11-validation-and-hardening*
*Context gathered: 2026-01-20*
