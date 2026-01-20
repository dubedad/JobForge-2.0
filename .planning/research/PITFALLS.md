# Pitfalls Research: Orbit Integration

**Domain:** Orbit/DuckDBRetriever integration with existing JobForge 2.0 data platform
**Researched:** 2026-01-20
**Confidence:** MEDIUM (Orbit documentation limited; DuckDB and text-to-SQL pitfalls well-documented)
**Context:** Adding Orbit as deployment target to existing system with 24 gold Parquet tables and working text-to-SQL capability

---

## Configuration Pitfalls

Mistakes in intent configuration and adapter setup that cause routing failures or incorrect behavior.

### Pitfall C1: Intent Pattern Collision

**What goes wrong:** User questions match multiple intent patterns, causing inconsistent routing. For example, "How many tables contain NOC data?" matches both data patterns ("how many") and metadata patterns ("tables contain").

**Why it happens:** Intent patterns are additive and don't account for phrase context. Pattern matching is greedy without priority weighting.

**Warning signs:**
- Same question routes differently on repeated attempts
- Users report inconsistent answers to similar questions
- Orbit logs show intent classification flip-flopping
- Questions with mixed vocabulary return unexpected results

**Consequences:**
- Data queries routed to metadata endpoint return error/no results
- Metadata queries routed to data endpoint generate invalid SQL
- User trust erodes from inconsistent behavior

**Prevention:**
- Design intent patterns with mutual exclusivity in mind
- Add priority ordering to intents (metadata patterns checked before data patterns for ambiguous queries)
- Include negative patterns: data_query should exclude "where does", "lineage", "come from"
- Test with ambiguous queries during development:
  - "How many sources feed dim_noc?" (metadata, not data)
  - "List tables with employment data" (metadata, not data)
  - "What is the source of cops_employment?" (metadata)

**Phase to address:** Intent configuration phase (Plan 10-03)

**Source:** [Orbit GitHub - Intent Routing](https://github.com/schmitech/orbit)

---

### Pitfall C2: Hardcoded localhost in Production

**What goes wrong:** Adapter configuration uses `http://localhost:8000` which works in development but fails when Orbit and JobForge run in separate containers or hosts.

**Why it happens:** Development convenience becomes production debt. Docker networking differs from local development.

**Warning signs:**
- Orbit works locally but fails in Docker Compose
- "Connection refused" errors in Orbit logs
- curl from Orbit container to JobForge fails

**Consequences:**
- Deployment fails completely
- Debugging requires understanding container networking
- Production rollout delayed

**Prevention:**
- Use environment variable: `base_url: "${JOBFORGE_API_URL:-http://localhost:8000}"`
- Docker Compose: use service names (`http://jobforge-api:8000`)
- Document network configuration in deployment guide
- Test full Docker Compose stack before declaring integration complete

**Phase to address:** Deployment configuration phase

**Source:** [Orbit Docker README](https://github.com/schmitech/orbit/blob/main/docker/README.md)

---

### Pitfall C3: Missing API Key Configuration

**What goes wrong:** Orbit starts without ANTHROPIC_API_KEY, appears healthy, but fails on first real query. Silent initialization means users discover failure only when querying.

**Why it happens:** Orbit validates structure but not credentials at startup. API key errors surface at query time, not deployment time.

**Warning signs:**
- Orbit health check passes but queries fail
- First query returns authentication error
- Logs show "Anthropic API authentication error" only after user interaction

**Consequences:**
- Users experience failure on first interaction
- Support tickets about "broken" system
- Difficult to diagnose without checking query-time logs

**Prevention:**
- Validate ANTHROPIC_API_KEY at retriever initialization, not first query
- Add startup health check that makes minimal API call
- Document required environment variables prominently
- Fail fast: refuse to start if required credentials missing

**Phase to address:** Retriever implementation (DuckDBRetriever.initialize)

**Source:** [Anthropic API docs - Authentication](https://docs.claude.com/en/docs/build-with-claude/authentication)

---

### Pitfall C4: Schema DDL Drift

**What goes wrong:** DuckDBRetriever generates schema DDL at initialization but gold tables are updated without restarting Orbit. LLM generates SQL for stale schema.

**Why it happens:** Schema DDL is cached for performance. No mechanism to detect table changes.

**Warning signs:**
- Queries fail with "column not found" after schema updates
- New tables not available in queries
- Restarting Orbit "fixes" query issues

**Consequences:**
- Users can't query new or modified tables
- SQL generation references stale columns
- Requires service restart after any schema change

**Prevention:**
- Document that Orbit restart required after schema changes
- Consider schema DDL TTL (regenerate every N minutes)
- Add schema version check endpoint
- Log schema DDL generation with timestamp for debugging

**Phase to address:** Operational documentation and retriever lifecycle

---

## Performance Pitfalls

Issues that cause slow queries, memory problems, or resource exhaustion.

### Pitfall P1: DuckDB Connection Memory Leak in Async Environment

**What goes wrong:** Memory usage grows unbounded in async FastAPI context. DuckDB in-memory connections don't release memory properly when concurrent requests interleave allocations across memory spans.

**Why it happens:** musl malloc (common in Alpine Docker images) keeps entire memory spans resident until all allocations freed. Async request interleaving prevents span cleanup.

**Warning signs:**
- RSS memory creeps upward over time
- Memory not released after request completion
- Eventually OOM kills in Kubernetes
- Memory profiler shows allocation outside Python runtime

**Consequences:**
- Production crashes from OOM
- Requires pod restarts to reclaim memory
- Memory limits cause early eviction

**Prevention:**
- Use jemalloc allocator in production Docker images (designed for concurrent workloads)
- Monitor memory trends, not just snapshots
- Set memory limits with buffer for leak growth
- Consider connection pooling with explicit cleanup
- Alternative: subprocess pattern for DuckDB CLI execution (subprocess cleanup forces OS memory release)

**Phase to address:** Production deployment configuration

**Sources:**
- [BetterUp - Async FastAPI Memory Leak with jemalloc fix](https://build.betterup.com/chasing-a-memory-leak-in-our-async-fastapi-service-how-jemalloc-fixed-our-rss-creep/)
- [DuckDB Issue #18031 - Parallel insertion memory leak](https://github.com/duckdb/duckdb/issues/18031)

---

### Pitfall P2: Full Schema in Every LLM Prompt

**What goes wrong:** Schema DDL for all 24 gold tables included in every text-to-SQL request. This increases token usage, slows response time, and can exceed context window for large schemas.

**Why it happens:** Simpler to include full schema than implement dynamic schema selection. "More context is better" assumption.

**Warning signs:**
- High token usage per query (check Anthropic dashboard)
- Response time scales with schema size, not query complexity
- Cost unexpectedly high for simple queries

**Consequences:**
- Higher API costs (input tokens)
- Slower response times
- LLM attention diffused across irrelevant tables
- Schema grows, performance degrades

**Prevention:**
- Implement schema pruning: only include tables likely relevant to query
- Use two-stage approach: first LLM call identifies relevant tables, second generates SQL
- Group tables by domain (occupation, forecast, attributes) and include relevant groups
- Monitor token usage per query type

**Phase to address:** Query optimization iteration (post-MVP)

**Source:** [K2View - LLM text-to-SQL challenges](https://www.k2view.com/blog/llm-text-to-sql/)

---

### Pitfall P3: No Query Result Caching

**What goes wrong:** Same question asked repeatedly generates new LLM call and SQL execution each time. Common questions (e.g., "how many unit groups?") waste resources.

**Why it happens:** Caching adds complexity. Each query "feels" unique even when semantically identical.

**Warning signs:**
- API costs scale linearly with query volume
- Same questions appear repeatedly in logs
- Response time consistent regardless of query history

**Consequences:**
- Unnecessary API costs
- Slower than necessary for common queries
- Resource waste on repeated computations

**Prevention:**
- Implement query result cache with TTL (1 hour for static data)
- Cache key: normalized question text (lowercased, trimmed)
- Consider semantic similarity for cache hits (fuzzy matching)
- Cache both SQL and results (SQL cache enables human review)

**Phase to address:** Performance optimization phase

---

### Pitfall P4: Timeout Too Short for Complex Queries

**What goes wrong:** Complex queries exceed 30-second HTTP timeout. LLM generates valid SQL but Orbit times out before results return.

**Why it happens:** Default timeout reasonable for simple queries. Complex analytical queries (aggregations across multiple tables) take longer.

**Warning signs:**
- Timeout errors for queries involving multiple joins
- Partial results or connection reset errors
- Users report intermittent failures for complex questions

**Consequences:**
- Complex queries always fail
- Users learn to avoid certain question types
- Capability underutilized

**Prevention:**
- Set realistic timeout based on query complexity (60-120s for analytical queries)
- Implement async query pattern: submit, poll for results
- Add query complexity estimation before execution
- Document expected response times for different query types

**Phase to address:** Adapter configuration (jobforge.yaml timeout setting)

---

## Deployment Pitfalls

Common failures when deploying Orbit with JobForge integration.

### Pitfall D1: Port Conflicts

**What goes wrong:** Orbit default ports (3000, 5173) conflict with existing services. Deployment fails silently or takes over wrong port.

**Why it happens:** Common development ports. Existing services may use same defaults.

**Warning signs:**
- "Port already in use" errors
- Orbit starts but connects to wrong service
- React UI unreachable

**Consequences:**
- Deployment fails or breaks existing services
- Debugging requires checking all port mappings
- Production incident from port collision

**Prevention:**
- Survey existing port usage before deployment
- Use non-standard ports for Orbit (e.g., 3100, 5273)
- Document all port assignments in deployment guide
- Docker Compose: explicit port mappings, not defaults

**Phase to address:** Deployment planning phase

**Source:** [Orbit GitHub README](https://github.com/schmitech/orbit)

---

### Pitfall D2: Python/Node Version Mismatch

**What goes wrong:** Orbit requires Python 3.12+ and Node 18+. Older versions cause cryptic failures during installation or runtime.

**Why it happens:** Version requirements buried in docs. System Python/Node often older.

**Warning signs:**
- Syntax errors during pip install
- npm install fails with version warnings
- Runtime errors about missing features

**Consequences:**
- Installation fails
- Partial installation causes confusing errors
- Requires environment rebuild

**Prevention:**
- Verify versions before starting installation
- Use version managers (pyenv, nvm) for isolated environments
- Docker: base on known-compatible images
- CI pipeline validates versions match requirements

**Phase to address:** Pre-deployment checklist

**Source:** [Orbit Prerequisites](https://github.com/schmitech/orbit)

---

### Pitfall D3: DuckDBRetriever Not Registered in Orbit

**What goes wrong:** DuckDBRetriever copied to Orbit but not registered in retriever factory. Adapter references non-existent retriever class.

**Why it happens:** Orbit uses factory pattern for retrievers. Adding a file isn't enough; must register class.

**Warning signs:**
- "Unknown retriever type: duckdb" errors
- Adapter configuration looks correct but doesn't work
- Other retrievers work, DuckDB doesn't

**Consequences:**
- Integration fails at runtime
- Confusing error messages about retriever not found
- Manual registration step easy to miss

**Prevention:**
- Document full registration steps:
  1. Copy duckdb.py to orbit/server/retrievers/
  2. Add import to orbit/server/retrievers/__init__.py
  3. Register in retriever factory (if applicable)
- Verify registration with unit test before deployment
- Create installation script that handles all steps

**Phase to address:** Integration documentation (docs/orbit-integration.md)

---

### Pitfall D4: CORS Not Configured for Cross-Origin Requests

**What goes wrong:** Orbit React UI running on port 3000 cannot make requests to JobForge API on port 8000 due to CORS policy.

**Why it happens:** Browsers enforce CORS. Default FastAPI doesn't allow cross-origin requests.

**Warning signs:**
- "CORS policy" errors in browser console
- API calls work from curl but fail from browser
- Orbit UI shows "network error" for all queries

**Consequences:**
- Frontend completely non-functional
- Users cannot access any queries through UI
- Works in testing (same origin) but fails in deployment

**Prevention:**
- Configure CORS middleware in FastAPI:
  ```python
  from fastapi.middleware.cors import CORSMiddleware
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["http://localhost:3000", "http://orbit:3000"],
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```
- Test cross-origin requests before deployment
- Document CORS configuration for different deployment scenarios

**Phase to address:** API configuration (routes.py)

---

## Integration Pitfalls

Issues when adding Orbit to existing JobForge system.

### Pitfall I1: Text-to-SQL Column Hallucination

**What goes wrong:** LLM generates SQL referencing columns that don't exist, especially when column names are similar to common concepts (e.g., generating "job_title" when actual column is "class_title").

**Why it happens:** LLM guesses based on semantic similarity. Schema provided but model doesn't always use it precisely.

**Warning signs:**
- DuckDB errors: "column X does not exist"
- Generated SQL looks plausible but fails execution
- Errors correlate with queries about concepts vs specific columns

**Consequences:**
- Query failures for valid questions
- Users receive unhelpful error messages
- Trust in system degrades

**Prevention:**
- Include column descriptions in schema DDL, not just names:
  ```sql
  CREATE TABLE dim_noc (
    noc_code VARCHAR,  -- 5-digit NOC code like "21232"
    class_title VARCHAR,  -- Official occupation title
    ...
  );
  ```
- Implement SQL validation before execution
- Return "I couldn't generate a valid query" instead of raw SQL errors
- Log failed queries for schema improvement

**Phase to address:** Schema DDL generation enhancement

**Sources:**
- [Text-to-SQL LLM Comparison 2026](https://research.aimultiple.com/text-to-sql/)
- [Six Failures of Text-to-SQL](https://medium.com/google-cloud/the-six-failures-of-text-to-sql-and-how-to-fix-them-with-agents-ef5fd2b74b68)

---

### Pitfall I2: Join Logic Errors

**What goes wrong:** LLM generates incorrect JOIN operations between tables, especially for complex questions involving multiple tables. May omit necessary JOINs or use wrong join keys.

**Why it happens:** Multi-table queries require understanding relationships. LLM may not infer correct join keys from schema alone.

**Warning signs:**
- Results include all rows (missing WHERE/JOIN)
- Cartesian products from missing join conditions
- Queries return empty when data should exist

**Consequences:**
- Wrong answers that look correct (partial results)
- Performance issues from Cartesian products
- Users receive misleading information

**Prevention:**
- Include relationship hints in system prompt:
  ```
  Relationships:
  - dim_noc.noc_code joins to cops_employment.noc_code
  - dim_occupations.group_code joins to job_architecture.group_code
  ```
- Implement result validation: check for unexpected row counts
- Consider agent pattern: LLM plans query, validates, then executes
- Log and review queries that return 0 rows or >10K rows

**Phase to address:** System prompt enhancement

**Source:** [K2View - Join failures in text-to-SQL](https://www.k2view.com/blog/llm-text-to-sql/)

---

### Pitfall I3: Conflicting Query Interfaces

**What goes wrong:** JobForge has existing text-to-SQL (DataQueryService) and now adds Orbit DuckDBRetriever. Two paths to same data with potentially different behaviors.

**Why it happens:** Incremental development. New capability added without deprecating or aligning with existing.

**Warning signs:**
- Same question returns different results via API vs Orbit
- Different system prompts in each implementation
- Bug fixes applied to one but not the other

**Consequences:**
- Inconsistent user experience
- Maintenance burden doubles
- Confusion about which interface is "correct"

**Prevention:**
- Single source of truth: DuckDBRetriever should delegate to DataQueryService
- Or: DataQueryService wraps DuckDBRetriever
- Avoid duplicating system prompts and SQL generation logic
- Document authoritative path clearly

**Phase to address:** Architecture decision during integration

---

### Pitfall I4: Structured Output Model Compatibility

**What goes wrong:** Structured outputs require specific Claude models (Sonnet 4.5, Opus 4.1). Using unsupported model (Haiku, older Sonnet) causes silent failures or unstructured responses.

**Why it happens:** Model selection based on cost/speed without checking feature compatibility. Beta feature has limited model support.

**Warning signs:**
- Response is freeform text instead of JSON
- Parse errors when validating SQLQuery model
- "structured-outputs" beta header has no effect

**Consequences:**
- SQL generation fails unpredictably
- Fallback to freeform parsing unreliable
- Query success rate drops

**Prevention:**
- Hardcode compatible model in DuckDBRetriever
- Validate model supports structured outputs before using
- Document model requirements in adapter config
- Add graceful fallback if structured output fails

**Phase to address:** Retriever implementation

**Source:** [Anthropic Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)

---

### Pitfall I5: Error Message Exposure

**What goes wrong:** Raw DuckDB errors, API errors, or stack traces exposed to end users through Orbit responses.

**Why it happens:** Error handling focuses on not crashing, not on user-friendly messages.

**Warning signs:**
- Users see SQL syntax errors
- Stack traces in Orbit responses
- Technical error codes without explanation

**Consequences:**
- Poor user experience
- Potential security risk (schema exposure)
- Support burden from confused users

**Prevention:**
- Wrap all retriever errors in user-friendly messages
- Log technical details, return generic message
- Categorize errors:
  - "I couldn't understand that question" (parse failure)
  - "I couldn't find data matching your query" (empty results)
  - "Something went wrong, please try again" (system error)
- Never expose raw SQL or column names in errors

**Phase to address:** Error handling in DuckDBRetriever.retrieve()

---

## Prevention Strategies Summary

| Pitfall | Category | Prevention Strategy | Phase |
|---------|----------|---------------------|-------|
| C1: Intent collision | Config | Mutual exclusivity patterns, priority ordering | 10-03 |
| C2: Hardcoded localhost | Config | Environment variables, Docker service names | Deployment |
| C3: Missing API key | Config | Fail-fast validation at initialization | 10-03 |
| C4: Schema drift | Config | Restart documentation, schema TTL | Operations |
| P1: Memory leak | Performance | jemalloc allocator, memory monitoring | Deployment |
| P2: Full schema prompts | Performance | Schema pruning, two-stage approach | Post-MVP |
| P3: No caching | Performance | Query result cache with TTL | Optimization |
| P4: Short timeout | Performance | Increase timeout, async pattern | 10-03 |
| D1: Port conflicts | Deployment | Port survey, explicit mappings | Pre-deployment |
| D2: Version mismatch | Deployment | Version validation, Docker images | Pre-deployment |
| D3: Retriever not registered | Deployment | Full registration documentation | 10-03 |
| D4: CORS not configured | Deployment | CORS middleware, cross-origin testing | 10-02 |
| I1: Column hallucination | Integration | Column descriptions in DDL | 10-03 |
| I2: Join errors | Integration | Relationship hints in prompt | 10-03 |
| I3: Conflicting interfaces | Integration | Single source of truth architecture | 10-03 |
| I4: Model compatibility | Integration | Hardcode compatible model | 10-03 |
| I5: Error exposure | Integration | User-friendly error wrapping | 10-03 |

---

## Phase-Specific Checklist

### Pre-Deployment (Before Starting Integration)
- [ ] Verify Python 3.12+ and Node 18+ available
- [ ] Survey existing port usage (3000, 5173, 8000)
- [ ] Confirm ANTHROPIC_API_KEY available and valid
- [ ] Review existing DataQueryService for reuse opportunity

### Plan 10-02 (JobForge HTTP API)
- [ ] Configure CORS middleware for Orbit origins
- [ ] Validate API health check includes credential verification
- [ ] Test cross-origin requests from browser

### Plan 10-03 (Orbit Integration)
- [ ] Design intent patterns with mutual exclusivity
- [ ] Add negative patterns to prevent collision
- [ ] Include relationship hints in system prompt
- [ ] Add column descriptions to schema DDL
- [ ] Wrap errors in user-friendly messages
- [ ] Document retriever registration steps
- [ ] Test with ambiguous queries
- [ ] Verify structured outputs model compatibility

### Deployment
- [ ] Use environment variables for URLs (not hardcoded localhost)
- [ ] Configure jemalloc or monitor memory trends
- [ ] Set appropriate timeouts (60s+ for complex queries)
- [ ] Test full Docker Compose stack end-to-end

### Operations
- [ ] Document schema change requires Orbit restart
- [ ] Monitor API costs and token usage
- [ ] Track query failure rates by error type
- [ ] Establish memory baseline and alert on drift

---

## Sources

### Primary (HIGH confidence)
- [Orbit GitHub Repository](https://github.com/schmitech/orbit) - Official documentation and requirements
- [Orbit Docker README](https://github.com/schmitech/orbit/blob/main/docker/README.md) - Deployment configuration
- [Anthropic Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) - Model compatibility and usage
- [DuckDB Performance Guide](https://duckdb.org/docs/stable/guides/performance/overview) - Query optimization

### Secondary (MEDIUM confidence)
- [BetterUp - FastAPI Memory Leak](https://build.betterup.com/chasing-a-memory-leak-in-our-async-fastapi-service-how-jemalloc-fixed-our-rss-creep/) - jemalloc fix for async memory issues
- [K2View - LLM Text-to-SQL Challenges](https://www.k2view.com/blog/llm-text-to-sql/) - Join and hallucination issues
- [Six Failures of Text-to-SQL](https://medium.com/google-cloud/the-six-failures-of-text-to-sql-and-how-to-fix-them-with-agents-ef5fd2b74b68) - Agent patterns for error recovery
- [DuckDB Issue #18031](https://github.com/duckdb/duckdb/issues/18031) - Parallel insertion memory leak

### Tertiary (LOW confidence - needs validation)
- [Text-to-SQL Comparison 2026](https://research.aimultiple.com/text-to-sql/) - General accuracy benchmarks
- [DuckDB Concurrency Discussion #13719](https://github.com/duckdb/duckdb/discussions/13719) - In-memory DuckDB with FastAPI

---

## Metadata

**Research focus:** Integration pitfalls specific to adding Orbit/DuckDBRetriever to existing JobForge 2.0 system
**Excluded:** Generic pitfalls already documented in existing PITFALLS.md (medallion, DADM, Power BI)
**Confidence assessment:**
- Configuration pitfalls: HIGH (well-documented patterns)
- Performance pitfalls: MEDIUM (DuckDB memory issues confirmed, Orbit-specific less documented)
- Deployment pitfalls: HIGH (common patterns)
- Integration pitfalls: MEDIUM (text-to-SQL well-documented, Orbit-specific patterns inferred)

**Valid until:** 60 days (Orbit actively developed, patterns may change)
