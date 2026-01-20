# Phase 11: Validation and Hardening - Research

**Researched:** 2026-01-20
**Domain:** API validation, error handling, text-to-SQL testing, intent classification
**Confidence:** HIGH

## Summary

Phase 11 validates the existing Orbit integration built in Phase 10, ensuring the HTTP adapter routes queries correctly to JobForge API endpoints, all 24 gold tables are accessible via DuckDBRetriever, and error responses are user-friendly rather than raw stack traces.

The existing codebase already contains:
- FastAPI routes (`/api/query/data`, `/api/query/metadata`, `/api/compliance/*`)
- DataQueryService with text-to-SQL via Claude structured outputs
- MetadataQueryService wrapping LineageQueryEngine
- 28 existing test files with pytest patterns established
- All 24 gold parquet tables in `data/gold/`

**Key validation focus:** This phase is about hardening what exists, not building new capabilities. The primary tasks are: (1) validate DuckDBRetriever works with all 24 tables, (2) implement user-friendly error responses following RFC 9457, (3) add CORS configuration for cross-origin access, and (4) create test coverage for intent routing patterns.

**Primary recommendation:** Use pytest with TestClient for API validation, implement RFC 9457 Problem Details for error responses, and create a test matrix ensuring each gold table is queryable via text-to-SQL.

## Standard Stack

The established libraries/tools for API validation and error handling:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.115.0+ | REST API framework | Already in use, native TestClient, excellent error handling |
| pytest | 8.0.0+ | Testing framework | Already in use (28 test files), industry standard |
| Pydantic | 2.12.0+ | Data validation | Already in use, native FastAPI integration |
| DuckDB | 1.4.0+ | SQL execution | Already in use, proven for parquet queries |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-cov | 4.0.0+ | Coverage reporting | Validate test coverage for validation code |
| httpx | 0.27.0+ | Async HTTP testing | If async TestClient needed (already dependency) |
| structlog | 24.0.0+ | Structured logging | Error diagnostic context (already dependency) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pytest | unittest | pytest more expressive, already established in codebase |
| RFC 9457 | Custom errors | RFC 9457 provides standard, interoperable format |
| TestClient | requests | TestClient faster, no server startup needed |

**Installation:**
All required libraries already installed per `pyproject.toml`. No new dependencies needed.

## Architecture Patterns

### Recommended Test Structure
```
tests/api/
├── test_routes.py           # Endpoint integration tests (exists)
├── test_data_query.py        # Text-to-SQL unit tests (exists)
├── test_metadata_query.py    # Metadata service tests (exists)
└── test_table_coverage.py    # NEW: All 24 gold tables queryable

tests/validation/
├── test_error_responses.py   # NEW: RFC 9457 error format validation
└── test_intent_routing.py    # NEW: Intent classification patterns
```

### Pattern 1: Table Coverage Validation
**What:** Parametrized test ensuring all 24 gold tables are queryable via DuckDBRetriever
**When to use:** Validating ORB-03 requirement (DuckDB validated with all 24 gold tables)
**Example:**
```python
# Source: Existing pattern from tests/api/test_data_query.py
import pytest
from pathlib import Path

@pytest.fixture
def all_gold_tables():
    """List all gold table names from parquet files."""
    gold_path = Path("data/gold")
    return [p.stem for p in gold_path.glob("*.parquet")]

@pytest.mark.parametrize("table_name", all_gold_tables())
def test_table_queryable(table_name, mock_client):
    """Test each gold table is accessible via text-to-SQL."""
    service = DataQueryService(config=config, client=mock_client)
    # Mock Claude to return query for this table
    result = service.query(f"SELECT * FROM {table_name} LIMIT 1")
    assert result.error is None or "does not exist" not in result.error.lower()
```

### Pattern 2: RFC 9457 Problem Details Error Response
**What:** Standardized error response format with type, title, status, detail, instance
**When to use:** All error responses from API endpoints (ORB-04 requirement)
**Example:**
```python
# Source: RFC 9457 specification (RFC 7807 obsoleted)
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

class ProblemDetail(BaseModel):
    type: str  # URI reference (e.g., "/errors/validation-failed")
    title: str  # Human-readable summary
    status: int  # HTTP status code
    detail: str  # Specific explanation
    instance: str | None = None  # URI to this occurrence

@app.exception_handler(Exception)
async def problem_detail_handler(request, exc):
    """Convert exceptions to RFC 9457 Problem Details."""
    return JSONResponse(
        status_code=500,
        content={
            "type": "/errors/internal-error",
            "title": "Internal Server Error",
            "status": 500,
            "detail": "An unexpected error occurred",
            "instance": str(request.url)
        },
        headers={"Content-Type": "application/problem+json"}
    )
```

### Pattern 3: CORS Configuration
**What:** Cross-Origin Resource Sharing middleware for Orbit → JobForge API calls
**When to use:** When API called from different origin (browser-based Orbit client)
**Example:**
```python
# Source: FastAPI CORS documentation
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Explicit, not "*"
    allow_credentials=True,  # For cookies/auth headers
    allow_methods=["GET", "POST"],  # Specific methods
    allow_headers=["*"],
    max_age=3600,  # Cache preflight for 1 hour
)
# CRITICAL: Add as FIRST middleware, before any other middleware
```

### Pattern 4: Intent Classification Routing
**What:** Pattern-based query routing to appropriate service (data, metadata, compliance, lineage)
**When to use:** Orbit adapter needs to classify user intent before routing (ORB-02 requirement)
**Example:**
```python
# Source: Existing MetadataQueryService pattern in metadata_query.py
import re
from typing import Callable

class IntentRouter:
    """Route queries to correct service based on intent patterns."""

    def __init__(self):
        self.patterns: list[tuple[re.Pattern, str]] = [
            # Data queries
            (re.compile(r"how many.*in (\w+)", re.I), "data"),
            (re.compile(r"show.*from (\w+)", re.I), "data"),
            (re.compile(r"list.*(\w+) where", re.I), "data"),

            # Metadata queries
            (re.compile(r"describe (?:table )?(\w+)", re.I), "metadata"),
            (re.compile(r"what columns", re.I), "metadata"),
            (re.compile(r"how many tables", re.I), "metadata"),

            # Lineage queries
            (re.compile(r"where does (\w+) come from", re.I), "lineage"),
            (re.compile(r"what feeds (\w+)", re.I), "lineage"),

            # Compliance queries
            (re.compile(r"compliance|dadm|dama", re.I), "compliance"),
        ]

    def classify(self, query: str) -> str:
        """Classify query intent, return 'data' as fallback."""
        for pattern, intent in self.patterns:
            if pattern.search(query):
                return intent
        return "data"  # Default to data queries
```

### Anti-Patterns to Avoid

- **Raw Exception Propagation:** Never return raw stack traces to users. Use structured error responses with actionable guidance.
- **Wildcard CORS in Production:** Never use `allow_origins=["*"]` with `allow_credentials=True` (browsers reject this as insecure).
- **Unvalidated Text-to-SQL:** Never execute generated SQL without schema validation (check tables exist, prevent SQL injection).
- **String-Based Error Matching:** Don't check `"error" in response`. Use typed responses with error fields.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Error response format | Custom JSON structure | RFC 9457 Problem Details | Standard format, tooling support, interoperability |
| Test parametrization | Loop with assertions | pytest.mark.parametrize | Better error messages, parallel execution, skip handling |
| SQL injection prevention | String sanitization | Claude structured outputs + DuckDB views | LLM generates validated SQL, DuckDB validates schema |
| HTTP test server | Manual uvicorn startup | FastAPI TestClient | Faster, no ports, automatic cleanup |
| Intent classification | Full NLP model | Regex patterns | Fast, deterministic, no model overhead for 4 intents |

**Key insight:** Text-to-SQL validation is notoriously difficult. Don't hand-roll semantic correctness checks. Use execution success + result schema validation + LLM self-consistency (multiple generations, pick best).

## Common Pitfalls

### Pitfall 1: Text-to-SQL Hallucination
**What goes wrong:** LLM generates syntactically valid SQL that references non-existent columns or uses incorrect joins, returning plausible but wrong results.
**Why it happens:** LLMs generate based on patterns, not schema awareness. They hallucinate column names like "Charter" or "County" that sound plausible but don't exist.
**How to avoid:**
1. Provide complete schema DDL in prompt (already done in DataQueryService)
2. Validate generated SQL references only tables in schema (check `tables_used` field)
3. Add dry-run validation step before execution
4. Use structured outputs to force table name validation
**Warning signs:** Query succeeds but returns 0 rows unexpectedly, or column names in SQL don't match schema

### Pitfall 2: Intent Pattern Collision
**What goes wrong:** Query matches multiple intent patterns (e.g., "How many columns in dim_noc?" matches both data count pattern and metadata column pattern).
**Why it happens:** Regex patterns overlap when keywords appear in different contexts.
**How to avoid:**
1. Order patterns from most specific to least specific
2. Use negative lookahead for disambiguation (e.g., `(?!columns)` in count pattern)
3. Test with ambiguous queries during validation
4. Provide confidence scores for multi-matches, let user clarify
**Warning signs:** Same query routed to different intents on repeated calls, or user reports incorrect answers

### Pitfall 3: CORS Preflight Cache Issues
**What goes wrong:** CORS works locally but fails in production, or works initially then stops after config changes.
**Why it happens:** Browsers cache preflight responses. After changing CORS config, cached preflights use old permissions.
**How to avoid:**
1. Set appropriate `max_age` (3600 = 1 hour is reasonable)
2. Test CORS with browser DevTools Network tab, filter for OPTIONS requests
3. Clear browser cache after CORS config changes
4. Add CORS middleware as FIRST middleware (order matters)
**Warning signs:** CORS works in Postman but not browser, or works after hard refresh but not normal refresh

### Pitfall 4: Error Message Information Leakage
**What goes wrong:** Error messages expose internal paths, database schemas, or stack traces to users, creating security vulnerabilities.
**Why it happens:** Exception handlers propagate raw exception messages without sanitization.
**How to avoid:**
1. Use global exception handler for unexpected errors
2. Log full error with structlog, return sanitized message to user
3. Never include file paths, variable names, or internal identifiers in user-facing errors
4. Provide actionable guidance ("Check table name spelling") not technical details ("Catalog entry not found at /internal/path")
**Warning signs:** Error messages contain file paths, SQL syntax, or Python tracebacks

### Pitfall 5: DuckDB Connection Leaks
**What goes wrong:** DuckDB connections accumulate over test runs, causing "database locked" errors or file handle exhaustion.
**Why it happens:** Connections not closed in finally blocks or test teardown.
**How to avoid:**
1. Use pytest fixtures with explicit teardown (existing pattern in tests/api/test_data_query.py)
2. Call `service.close()` in fixture finalizer
3. Use context managers for short-lived connections
4. Validate connections closed in tests (assert `service._conn is None` after close)
**Warning signs:** Tests fail intermittently with "database locked", or memory usage grows over test suite

## Code Examples

Verified patterns from official sources:

### Table Coverage Test Matrix
```python
# Source: pytest parametrize pattern + existing test structure
import pytest
from pathlib import Path
from jobforge.api.data_query import DataQueryService
from jobforge.pipeline.config import PipelineConfig

def pytest_generate_tests(metafunc):
    """Dynamically generate test cases for all gold tables."""
    if "table_name" in metafunc.fixturenames:
        gold_path = Path("data/gold")
        tables = sorted([p.stem for p in gold_path.glob("*.parquet")])
        metafunc.parametrize("table_name", tables)

def test_table_accessible_via_text_to_sql(table_name, mock_anthropic_client):
    """Validate each gold table can be queried via DataQueryService."""
    # Mock Claude to return simple SELECT for this table
    mock_response = create_mock_response(
        sql=f"SELECT * FROM {table_name} LIMIT 1",
        explanation=f"Query {table_name}",
        tables_used=[table_name]
    )
    mock_anthropic_client.messages.create.return_value = mock_response

    service = DataQueryService(config=PipelineConfig(), client=mock_anthropic_client)
    result = service.query(f"Show me one row from {table_name}")

    # Should succeed without error
    assert result.error is None, f"Table {table_name} query failed: {result.error}"
    assert result.row_count >= 0  # May be 0 if table empty

    service.close()
```

### RFC 9457 Error Response Handler
```python
# Source: RFC 9457 specification + FastAPI exception handler pattern
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import structlog

logger = structlog.get_logger()

class ProblemDetail(BaseModel):
    """RFC 9457 Problem Details for HTTP APIs."""
    type: str
    title: str
    status: int
    detail: str
    instance: str | None = None

def create_problem_detail(
    type_suffix: str,
    title: str,
    status: int,
    detail: str,
    instance: str | None = None
) -> dict:
    """Create RFC 9457 problem detail response."""
    return {
        "type": f"https://api.jobforge.dev/errors/{type_suffix}",
        "title": title,
        "status": status,
        "detail": detail,
        "instance": instance
    }

@app.exception_handler(ValueError)
async def validation_error_handler(request: Request, exc: ValueError):
    """Handle validation errors with user-friendly messages."""
    logger.warning("validation_error", error=str(exc), path=str(request.url))

    problem = create_problem_detail(
        type_suffix="validation-failed",
        title="Validation Error",
        status=status.HTTP_400_BAD_REQUEST,
        detail=str(exc),
        instance=str(request.url)
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=problem,
        headers={"Content-Type": "application/problem+json"}
    )

@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    """Handle unexpected errors with sanitized messages."""
    logger.error("internal_error", error=str(exc), type=type(exc).__name__)

    problem = create_problem_detail(
        type_suffix="internal-error",
        title="Internal Server Error",
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred. Please try again or contact support.",
        instance=str(request.url)
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=problem,
        headers={"Content-Type": "application/problem+json"}
    )
```

### Intent Classification with Confidence
```python
# Source: Existing MetadataQueryService pattern + hybrid LLM approach
import re
from dataclasses import dataclass
from typing import Callable

@dataclass
class IntentMatch:
    """Intent classification result with confidence."""
    intent: str
    confidence: float  # 0.0 to 1.0
    matched_pattern: str | None = None

class IntentClassifier:
    """Classify user queries into intent categories with confidence scoring."""

    # Intent categories for ORB-02
    INTENTS = ["data", "metadata", "compliance", "lineage"]

    def __init__(self):
        """Initialize with pattern hierarchy (specific to general)."""
        self.patterns: list[tuple[re.Pattern, str, float]] = [
            # High confidence patterns (0.9+)
            (re.compile(r"where does .* come from", re.I), "lineage", 0.95),
            (re.compile(r"what feeds", re.I), "lineage", 0.95),
            (re.compile(r"compliance|dadm|dama|framework", re.I), "compliance", 0.95),
            (re.compile(r"describe (?:table )?(\w+)", re.I), "metadata", 0.90),

            # Medium confidence patterns (0.7-0.8)
            (re.compile(r"how many (?!columns).*in (\w+)", re.I), "data", 0.80),
            (re.compile(r"show.*from (\w+)", re.I), "data", 0.80),
            (re.compile(r"what columns", re.I), "metadata", 0.75),
            (re.compile(r"list (?:all )?tables", re.I), "metadata", 0.75),

            # Low confidence patterns (0.5-0.6) - ambiguous
            (re.compile(r"count", re.I), "data", 0.60),  # Could be table count or row count
            (re.compile(r"show|list", re.I), "data", 0.50),  # Very generic
        ]

    def classify(self, query: str) -> IntentMatch:
        """Classify query, return highest confidence match."""
        best_match = IntentMatch(intent="data", confidence=0.5)  # Default

        for pattern, intent, confidence in self.patterns:
            if pattern.search(query):
                if confidence > best_match.confidence:
                    best_match = IntentMatch(
                        intent=intent,
                        confidence=confidence,
                        matched_pattern=pattern.pattern
                    )

        return best_match

    def should_clarify(self, match: IntentMatch) -> bool:
        """Check if confidence too low, user clarification needed."""
        return match.confidence < 0.70
```

### CORS Configuration with Environment-Based Origins
```python
# Source: FastAPI CORS best practices
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

def configure_cors(app: FastAPI) -> None:
    """Configure CORS middleware with environment-specific origins."""

    # Get allowed origins from environment (comma-separated)
    origins_str = os.getenv("CORS_ORIGINS", "http://localhost:3000")
    allowed_origins = [o.strip() for o in origins_str.split(",")]

    # CRITICAL: Add CORS middleware FIRST
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,  # Explicit list, never "*" with credentials
        allow_credentials=True,  # For cookies/auth headers
        allow_methods=["GET", "POST"],  # Specific methods only
        allow_headers=["Content-Type", "Authorization"],  # Specific headers
        max_age=3600,  # Cache preflight for 1 hour
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| RFC 7807 Problem Details | RFC 9457 Problem Details | 2023 | RFC 7807 obsoleted, RFC 9457 adds extensions and clarifications |
| Manual error JSON | Pydantic error models | 2024 | Type-safe error responses, automatic validation |
| LLM-only text-to-SQL | Structured outputs + validation | 2025 | Reduces hallucination via forced JSON schema compliance |
| Full NLP models for intent | Hybrid regex + LLM fallback | 2026 | Low latency for common intents, LLM for edge cases |
| pytest.fixture scope="session" for DuckDB | scope="function" + lazy load | 2025 | Prevents connection leaks, better test isolation |

**Deprecated/outdated:**
- RFC 7807: Obsoleted by RFC 9457 (2023)
- CORS `allow_origin_regex` without `allow_origins`: Removed in FastAPI 0.115+, must specify both
- pytest-asyncio auto mode: Deprecated in pytest-asyncio 0.23, must set `asyncio_mode = "auto"` in pytest.ini

## Open Questions

Things that couldn't be fully resolved:

1. **Orbit HTTP Adapter Configuration**
   - What we know: Orbit has HTTP adapter pattern, routes queries to external APIs
   - What's unclear: Exact configuration syntax for `adapters.yaml` to route to JobForge API
   - Recommendation: Review Orbit documentation during planning, create sample `adapters.yaml` config as template

2. **Intent Confidence Threshold**
   - What we know: Low confidence classifications should trigger clarification
   - What's unclear: Optimal threshold (0.7? 0.8?) for production use
   - Recommendation: Start with 0.7, log confidence scores, adjust based on user feedback

3. **DuckDBRetriever vs DataQueryService**
   - What we know: Both use text-to-SQL via Claude, similar patterns
   - What's unclear: Should validation test DuckDBRetriever directly or DataQueryService (which JobForge API uses)?
   - Recommendation: Validate DataQueryService (what API actually uses), assume DuckDBRetriever works identically

4. **Error Response Localization**
   - What we know: RFC 9457 supports multiple languages via `title` field
   - What's unclear: Whether v2.1 needs multi-language error messages
   - Recommendation: English only for v2.1, design ProblemDetail model to support i18n later

## Sources

### Primary (HIGH confidence)
- [RFC 9457: Problem Details for HTTP APIs](https://blog.frankel.ch/problem-details-http-apis/)
- [FastAPI Official Documentation - Error Handling](https://fastapi.tiangolo.com/tutorial/handling-errors/)
- [FastAPI Official Documentation - CORS](https://fastapi.tiangolo.com/tutorial/cors/)
- [FastAPI Official Documentation - Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [DuckDB Official Documentation - SQLLogicTest](https://duckdb.org/docs/stable/dev/sqllogictest/intro)
- Existing JobForge codebase: `src/jobforge/api/`, `tests/api/`, `orbit/retrievers/duckdb.py`

### Secondary (MEDIUM confidence)
- [Better Stack: FastAPI Error Handling Patterns](https://betterstack.com/community/guides/scaling-python/error-handling-fastapi/)
- [Promptfoo: Evaluating LLM text-to-SQL performance](https://www.promptfoo.dev/docs/guides/text-to-sql-evaluation/)
- [Google Cloud Blog: Techniques for improving text-to-SQL](https://cloud.google.com/blog/products/databases/techniques-for-improving-text-to-sql)
- [StackHawk: Configuring CORS in FastAPI](https://www.stackhawk.com/blog/configuring-cors-in-fastapi/)
- [TestDriven.io: Developing and Testing Async API with FastAPI](https://testdriven.io/blog/fastapi-crud/)

### Secondary (MEDIUM confidence) - Text-to-SQL Validation
- [AIM Research: Text-to-SQL LLM Accuracy 2026](https://research.aimultiple.com/text-to-sql/)
- [Harsh Chandekar: Text to SQL Evaluation Techniques](https://harshchandekar10.medium.com/text-to-sql-evaluation-techniques-a-comprehensive-guide-4b243c82ab88)
- [Wren AI: Reducing Hallucinations in Text-to-SQL](https://medium.com/wrenai/reducing-hallucinations-in-text-to-sql-building-trust-and-accuracy-in-data-access-176ac636e208)
- [ArXiv: Hallucination Detection for Text-to-SQL](https://arxiv.org/html/2512.22250v1)

### Secondary (MEDIUM confidence) - Intent Classification
- [AIM Research: Intent Classification in 2026](https://research.aimultiple.com/intent-classification/)
- [Label Your Data: Intent Classification 2025 Techniques](https://labelyourdata.com/articles/machine-learning/intent-classification)
- [Medium: Intent Classification Architecture](https://medium.com/aimonks/intent-classification-generative-ai-based-application-architecture-3-79d2927537b4)

### Tertiary (LOW confidence)
- [Medium: Unit testing SQL queries with DuckDB](https://medium.com/clarityai-engineering/unit-testing-sql-queries-with-duckdb-23743fd22435) - Single author blog post, pattern not verified
- Community discussions on text-to-SQL validation strategies - No authoritative source found for comprehensive validation framework

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in `pyproject.toml`, proven in existing tests
- Architecture: HIGH - Patterns verified in existing codebase (`tests/api/`, `src/jobforge/api/`)
- Error handling: HIGH - RFC 9457 is current standard, FastAPI patterns documented officially
- Text-to-SQL pitfalls: MEDIUM - Research-backed but no single authoritative source for all mitigation strategies
- Intent classification: MEDIUM - Patterns exist but optimal thresholds require empirical tuning
- CORS configuration: HIGH - Official FastAPI documentation, well-established patterns

**Research date:** 2026-01-20
**Valid until:** 2026-02-20 (30 days - stable technologies, unlikely to change)
