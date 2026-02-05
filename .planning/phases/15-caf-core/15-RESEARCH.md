# Phase 15: CAF Core - Research

**Researched:** 2026-02-05
**Domain:** Web scraping, bilingual data extraction, fuzzy matching, data provenance
**Confidence:** MEDIUM

## Summary

This phase requires scraping Canadian Armed Forces career data from forces.ca, a bilingual government website with 107+ occupations organized into approximately 12 job families. The research confirms that the project's existing stack (BeautifulSoup4, httpx, Pydantic 2, rapidfuzz) is well-suited for this phase. The TBS scraper pattern established in Phase 14 provides a solid foundation to follow.

Key technical challenges include handling bilingual content without duplication, implementing hybrid automated-plus-human-verified matching to NOC and Job Architecture tables, and maintaining comprehensive provenance metadata. The forces.ca website uses environment-based URL patterns (`/en/careers/env_1`, etc.) and individual career pages at `/en/career/{career-slug}/` with structured sections for overview, training, entry plans, and related careers.

The project's existing confidence scoring patterns (0.0-1.0 floats with rationale fields) and provenance tracking models align perfectly with requirements. Bridge tables should follow the Kimball dimensional modeling pattern with weight factors for confidence scores.

**Primary recommendation:** Follow the TBS scraper pattern with bilingual support, use separate columns for EN/FR content to avoid row duplication, store human-verified mappings in JSON reference files with database tables for runtime queries, and implement confidence scoring using existing project patterns (0.0-1.0 float with audit trail).

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| beautifulsoup4 | 4.12+ | HTML parsing | Industry standard for web scraping, handles malformed markup well |
| lxml | 4.9+ | HTML parser backend | Fastest parser for BeautifulSoup, production-ready |
| httpx | 0.27+ | HTTP client | Modern replacement for requests, supports async, better connection pooling |
| Pydantic | 2.12+ | Data validation | Type-safe models with validation, JSON serialization built-in |
| rapidfuzz | 3.0+ | Fuzzy string matching | Fastest fuzzy matching library for Python (Rust core), drop-in replacement for fuzzywuzzy |
| tenacity | 8.2+ | Retry logic | Declarative retry with exponential backoff, standard for resilient HTTP |
| structlog | 24.0+ | Structured logging | JSON-structured logs for provenance audit trail |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| hashlib | stdlib | Content hashing | SHA-256 checksums for data integrity verification |
| Polars | 1.37+ | Data transformation | Loading scraped JSON into gold tables |
| DuckDB | 1.4+ | SQL operations | Bridge table queries and gold layer storage |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| httpx | requests | requests is mature but synchronous-only, lacks modern connection pooling |
| beautifulsoup4 | scrapy | Scrapy is overkill for simple scraping, adds framework complexity |
| rapidfuzz | thefuzz/fuzzywuzzy | fuzzywuzzy is slower (pure Python vs Rust), less maintained |

**Installation:**
```bash
# Already in pyproject.toml - no additional dependencies required
pip install beautifulsoup4 lxml httpx pydantic rapidfuzz tenacity structlog
```

## Architecture Patterns

### Recommended Project Structure
```
src/jobforge/external/caf/
├── scraper.py           # Main CAFScraper class (follows TBS pattern)
├── parser.py            # HTML parsing functions
├── models.py            # Pydantic models with provenance
├── link_fetcher.py      # Career page detail fetcher
└── matchers.py          # Fuzzy matching to NOC/JA

data/caf/
├── careers_en.json      # Scraped career data (EN)
├── careers_fr.json      # Scraped career data (FR)
└── job_families_en.json # 12 job family metadata

data/reference/
├── caf_noc_mappings.json     # Human-verified CAF→NOC matches
└── caf_ja_mappings.json      # Human-verified CAF→JA matches
```

### Pattern 1: Bilingual Scraping Without Duplication
**What:** Scrape both EN and FR versions, store in separate columns within the same row
**When to use:** When data entities are the same across languages (same 107 occupations)
**Example:**
```python
# Source: Existing TBS pattern + research findings
class CAFOccupation(BaseModel):
    """Single CAF occupation with bilingual content."""

    occupation_id: str  # Canonical ID from URL slug
    title_en: str
    title_fr: str
    overview_en: str
    overview_fr: str
    training_en: str
    training_fr: str

    # Provenance
    source_url_en: str
    source_url_fr: str
    scraped_at: datetime
    content_hash_en: str  # SHA-256 of EN HTML
    content_hash_fr: str  # SHA-256 of FR HTML
```

### Pattern 2: Hybrid Matching with Human Verification
**What:** Automated fuzzy matching suggests candidates, human verifies and stores decisions
**When to use:** When match accuracy is critical (CAF→NOC, CAF→JA mappings)
**Example:**
```python
# Source: Project confidence scoring pattern
class CAFNOCMapping(BaseModel):
    """Mapping between CAF occupation and NOC code."""

    caf_occupation_id: str
    noc_unit_group_id: str
    confidence_score: float  # 0.0-1.0
    match_method: Literal["automated_fuzzy", "human_verified"]

    # Audit trail
    fuzzy_score: float | None  # rapidfuzz score if automated
    matched_text: str  # What text matched
    algorithm_version: str  # e.g., "rapidfuzz-3.0-token_sort_ratio"
    verified_by: str | None  # "human" or None
    verified_at: datetime | None
    rationale: str  # Why this match
```

### Pattern 3: Provenance-First Scraping
**What:** Every scraped value carries full provenance metadata
**When to use:** Always - aligns with project core value "auditable provenance"
**Example:**
```python
# Source: TBS scraper models
class ScrapedProvenance(BaseModel):
    """Provenance for scraped data."""

    source_url: str
    scraped_at: datetime
    extraction_method: str  # "css_selector", "xpath", "text_search"
    page_title: str
    scraper_version: str  # e.g., "CAFScraper-1.0.0"
    content_hash: str  # SHA-256 of raw HTML
    raw_html_path: str | None  # Optional: path to preserved HTML
```

### Pattern 4: Rate Limiting and Retry
**What:** Polite scraping with exponential backoff on failures
**When to use:** All HTTP requests to forces.ca
**Example:**
```python
# Source: httpx + tenacity best practices
from tenacity import retry, stop_after_attempt, wait_exponential
import httpx

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException))
)
def fetch_career_page(url: str, timeout: int = 30) -> str:
    """Fetch career page with retry and rate limiting."""
    # Rate limit: 1.5s between requests (polite scraping)
    time.sleep(1.5)

    response = httpx.get(url, timeout=timeout, follow_redirects=True)
    response.raise_for_status()
    return response.text
```

### Anti-Patterns to Avoid
- **Separate rows for EN/FR:** Creates artificial 2x row count, complicates joins. Use separate columns instead.
- **Scraping without content hashes:** Makes it impossible to detect source changes. Always compute SHA-256.
- **Filtering data during scrape:** Per CONTEXT.md decision, capture ALL fields. Filter in gold layer if needed.
- **Hard-coded confidence thresholds:** Per CONTEXT.md, return all matches regardless of confidence. Let users filter.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fuzzy string matching | Custom Levenshtein distance | rapidfuzz with token_sort_ratio | Handles word order, punctuation, case; 10x faster (Rust core); battle-tested |
| HTTP retry logic | Manual retry loops | tenacity decorators | Handles exponential backoff, jitter, exception types; declarative |
| Data validation | Manual dict validation | Pydantic models | Type safety, JSON serialization, clear error messages; project standard |
| Duplicate detection | Manual string comparison | Set with normalized strings | Simple, fast; hash-based deduplication |
| Content integrity | Manual file comparison | hashlib.sha256() | Cryptographic guarantee; legal defensibility per 2026 scraping guidance |
| Bridge table confidence | Custom scoring algebra | Weight factor column + rationale | Kimball pattern; supports audit trail; query-friendly |

**Key insight:** Fuzzy matching has hidden complexity (normalization, scoring methods, performance). rapidfuzz is already in the stack and provides token_sort_ratio (ignores word order), partial_ratio (substring matching), and fuzz.ratio (classic Levenshtein) out of the box. Don't reimplement these algorithms.

## Common Pitfalls

### Pitfall 1: Bilingual Content Duplication
**What goes wrong:** Treating EN and FR pages as separate entities doubles row count and breaks foreign keys.
**Why it happens:** Each URL is unique, so scraper naturally creates two records per occupation.
**How to avoid:** Use canonical occupation ID (from URL slug) as primary key, store EN/FR in separate columns.
**Warning signs:** Bridge tables show 214 CAF occupations instead of 107; JOIN queries return duplicate rows.

### Pitfall 2: Over-Filtering During Scrape
**What goes wrong:** Scraper logic decides what's "important" and drops fields, losing source fidelity.
**Why it happens:** Trying to optimize storage or simplify downstream processing.
**How to avoid:** Per CONTEXT.md decision, capture ALL available fields. Let gold layer transformations filter.
**Warning signs:** Missing fields in scraped JSON that exist on website; "we don't need that field" comments.

### Pitfall 3: Confidence Score Without Audit Trail
**What goes wrong:** Bridge tables have confidence score but no explanation of what contributed to it.
**Why it happens:** Focusing on the score as a single value rather than a derived summary.
**How to avoid:** Per CONTEXT.md, include: matching factors, intermediate scores, algorithm used, verification status.
**Warning signs:** Score column but no rationale column; unable to explain why score is 0.75 vs 0.80.

### Pitfall 4: Forgetting Content Hashes
**What goes wrong:** Re-scraping finds different data but can't prove source changed vs scraper bug.
**Why it happens:** Hashing seems like extra work with no immediate benefit.
**How to avoid:** Compute SHA-256 of raw HTML immediately after fetch, before parsing. Store in provenance.
**Warning signs:** "Data changed but we don't know if it's a real change"; debugging parser vs source.

### Pitfall 5: Mixing Automated and Human Matches Without Distinction
**What goes wrong:** Can't identify which matches need human review; automated matches get treated as verified.
**Why it happens:** Single boolean "verified" flag or no verification tracking at all.
**How to avoid:** Use match_method enum: "automated_fuzzy", "human_verified", "human_rejected". Track verified_by and verified_at.
**Warning signs:** All matches have same confidence tier; no way to filter "needs review" matches.

### Pitfall 6: URL Pattern Assumptions
**What goes wrong:** Scraper hard-codes URL patterns that break when site structure changes.
**Why it happens:** Observing a few URLs and generalizing the pattern.
**How to avoid:** Extract URLs from navigation/listing pages rather than constructing them. Fail loudly on 404s.
**Warning signs:** Magic numbers in URL construction (env_1, env_2); brittle URL string concatenation.

## Code Examples

Verified patterns from official sources:

### BeautifulSoup with lxml Parser
```python
# Source: BeautifulSoup official docs + 2026 best practices
from bs4 import BeautifulSoup
import hashlib

def parse_career_page(html: str, url: str) -> dict:
    """Parse career page using lxml backend."""
    # Compute content hash BEFORE parsing
    content_hash = hashlib.sha256(html.encode('utf-8')).hexdigest()

    # lxml parser: fastest, most tolerant
    soup = BeautifulSoup(html, 'lxml')

    # Scope search to reduce noise
    main_content = soup.find('main') or soup.find('article') or soup

    # Extract sections
    overview = main_content.find('section', {'id': 'overview'})
    training = main_content.find('section', {'id': 'training'})

    return {
        'overview': overview.get_text(strip=True) if overview else None,
        'training': training.get_text(strip=True) if training else None,
        'content_hash': content_hash,
        'source_url': url,
    }
```

### rapidfuzz Token Sort Ratio for Fuzzy Matching
```python
# Source: rapidfuzz docs + 2026 best practices
from rapidfuzz import fuzz, process

def find_noc_matches(caf_title: str, noc_titles: list[str], threshold: float = 70.0) -> list[dict]:
    """Find NOC matches using token_sort_ratio (ignores word order)."""
    # token_sort_ratio: "Infantry Officer" matches "Officer, Infantry"
    matches = process.extract(
        caf_title,
        noc_titles,
        scorer=fuzz.token_sort_ratio,
        score_cutoff=threshold,
        limit=5  # Top 5 candidates
    )

    return [
        {
            'matched_text': match[0],
            'fuzzy_score': match[1] / 100.0,  # Normalize to 0.0-1.0
            'algorithm': 'rapidfuzz-3.0-token_sort_ratio',
            'confidence_score': _fuzzy_to_confidence(match[1]),
        }
        for match in matches
    ]

def _fuzzy_to_confidence(fuzzy_score: float) -> float:
    """Convert rapidfuzz score (0-100) to confidence (0.0-1.0)."""
    # Mapping: 100→1.0, 90→0.85, 80→0.70, 70→0.55
    # Below 70 is low confidence
    if fuzzy_score >= 90:
        return 0.85 + (fuzzy_score - 90) * 0.015  # 90-100 → 0.85-1.0
    elif fuzzy_score >= 80:
        return 0.70 + (fuzzy_score - 80) * 0.015  # 80-90 → 0.70-0.85
    else:
        return fuzzy_score / 100.0 * 0.70  # <80 → <0.70
```

### httpx with tenacity Retry
```python
# Source: httpx-retries + tenacity patterns
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class CAFScraper:
    def __init__(self):
        self.client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=5)
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1.5, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException))
    )
    def fetch(self, url: str) -> str:
        """Fetch URL with retry and exponential backoff."""
        response = self.client.get(url)
        response.raise_for_status()
        return response.text
```

### Bridge Table with Confidence and Audit Trail
```python
# Source: Project imputation models + Kimball bridge pattern
class BridgeCAFNOC(BaseModel):
    """Bridge table: CAF occupation → NOC unit group."""

    # Foreign keys
    caf_occupation_id: str = Field(description="FK to dim_caf_occupation")
    noc_unit_group_id: str = Field(description="FK to dim_noc")

    # Weight factor (Kimball pattern)
    confidence_score: float = Field(ge=0.0, le=1.0, description="Match confidence")

    # Audit trail (per CONTEXT.md requirement)
    match_method: Literal["automated_fuzzy", "human_verified", "human_rejected"]
    algorithm_version: str | None = Field(description="e.g., 'rapidfuzz-3.0-token_sort_ratio'")
    fuzzy_score: float | None = Field(description="Raw rapidfuzz score if automated")
    matched_text: str = Field(description="What text was matched")
    rationale: str = Field(description="Human-readable explanation")

    # Verification
    verified_by: str | None = Field(description="'human' if human-reviewed, else None")
    verified_at: datetime | None

    # Provenance
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| requests library | httpx | 2023+ | Better async support, modern connection pooling, easier testing |
| fuzzywuzzy | rapidfuzz | 2021+ | 10x faster (Rust core), active maintenance, drop-in replacement |
| Separate preprocessing | rapidfuzz scorers | rapidfuzz 3.0+ | No default preprocessing; explicit scorer choice improves accuracy |
| MD5 hashes | SHA-256 | 2020+ | Cryptographic security, legal defensibility for audit trails |
| requests.Session() | httpx.Limits() | 2023+ | Connection pooling via explicit Limits object |

**Deprecated/outdated:**
- **fuzzywuzzy**: Replaced by rapidfuzz (faster, better maintained). Use rapidfuzz for all new code.
- **requests for new scrapers**: Use httpx for better connection pooling and potential async migration.
- **MD5 for data integrity**: Use SHA-256 per 2026 scraping guidance (legal defensibility).

## Open Questions

Things that couldn't be fully resolved:

1. **Exact number and names of 12 job families**
   - What we know: Alberta ALIS site confirms 107 careers in 12 categories; forces.ca organizes by military branch (Army/Navy/Air Force) not job families
   - What's unclear: Exact names of the 12 categories, whether they're visible on forces.ca or internal CAF classification
   - Recommendation: Scrape all career pages, extract "related careers" links, use network analysis to infer groupings. Manual verification may be required.

2. **Career URL enumeration strategy**
   - What we know: Individual careers at `/en/career/{slug}/` pattern; listing pages use environment params (`env_1`, `env_2`, `env_3`)
   - What's unclear: Whether there's a master career list page or if we need to crawl from environment pages
   - Recommendation: Start with `/en/careers` (all careers) page, extract all career links. Don't construct URLs manually.

3. **Civilian equivalent field structure**
   - What we know: Pilot page shows "related civilian occupations" (airline pilot, medical evacuation pilot, flight instructor)
   - What's unclear: Whether this is structured data or prose text; how consistently it appears across all 107 careers
   - Recommendation: Parse as unstructured text list initially. Structure during gold layer transformation if patterns emerge.

4. **Raw HTML preservation**
   - What we know: CONTEXT.md allows Claude discretion on whether to preserve raw HTML
   - What's unclear: Storage location, retention policy, whether to compress
   - Recommendation: Preserve raw HTML in `data/caf/raw/{occupation_id}_{lang}.html` for debugging and re-parsing. Not required for MVP but valuable for audit trail.

5. **Job Architecture two-level matching feasibility**
   - What we know: CONTEXT.md specifies CAF career streams → JA job families AND CAF careers → JA job roles
   - What's unclear: Whether 12 CAF job families map cleanly to JA job families, or if cardinality is many-to-many
   - Recommendation: Data analysis during implementation. If no clean mapping exists, use only career-level matching with rationale explaining why.

## Sources

### Primary (HIGH confidence)
- Existing project code: `src/jobforge/external/tbs/scraper.py` - TBS pattern to follow
- Existing project code: `src/jobforge/imputation/models.py` - Confidence scoring patterns
- Existing project code: `src/jobforge/external/models.py` - Provenance tracking patterns
- Existing project code: `data/catalog/tables/*.json` - Catalog schema patterns
- pyproject.toml dependencies - Stack versions verified

### Secondary (MEDIUM confidence)
- [forces.ca Pilot career page](https://forces.ca/en/career/pilot/) - Career page structure verified
- [Career Streams in the Canadian Armed Forces - alis](https://alis.alberta.ca/plan-your-career/career-streams-in-the-canadian-armed-forces/) - 107 careers, 12 categories confirmed
- [rapidfuzz GitHub](https://github.com/rapidfuzz/RapidFuzz) - Library capabilities verified
- [httpx-retries patterns](https://will-ockmore.github.io/httpx-retries/) - Retry implementation verified
- [DAMA DMBOK Framework Guide 2026](https://atlan.com/dama-dmbok-framework/) - Metadata management guidance
- [Data scraping evidence collection guide 2026](https://spotlight.ebu.ch/p/master-data-scraping-investigative-guide) - SHA-256 for legal defensibility
- [Many to Many Relationships Guide | DataCamp](https://www.datacamp.com/blog/many-to-many-relationship) - Bridge table weight factors
- [Kimball Group Design Tip 142: Building Bridges](https://www.kimballgroup.com/2012/02/design-tip-142-building-bridges/) - Bridge table patterns

### Tertiary (LOW confidence)
- [BeautifulSoup 2026 patterns](https://thelinuxcode.com/beautifulsoup-scraping-paragraphs-from-html-in-python-2026-edition/) - Recent guidance but not CAF-specific
- [Web scraping bilingual best practices](https://scrapfly.io/blog/posts/how-to-scrape-in-another-language-or-currency) - General guidance, not forces.ca-specific
- [Pydantic best practices 2024](https://dev.to/devasservice/best-practices-for-using-pydantic-in-python-2021) - Generic Pydantic, no bilingual validation specifics

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in project dependencies, versions verified in pyproject.toml
- Architecture: HIGH - TBS scraper pattern exists and proven, Pydantic models established, confidence scoring patterns verified in codebase
- Pitfalls: MEDIUM - Based on research findings and inference; not CAF-specific validation
- Career page structure: MEDIUM - Verified sample page (Pilot) but not all 107 careers examined
- Job family classification: LOW - Confirmed 12 categories exist but names/structure not verified from authoritative source

**Research date:** 2026-02-05
**Valid until:** 2026-03-05 (30 days - forces.ca structure is stable, libraries are mature)
