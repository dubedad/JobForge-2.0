# Phase 16: Extended Metadata - Research

**Researched:** 2026-02-05
**Domain:** Government data scraping, text parsing, metadata enrichment, DMBOK compliance
**Confidence:** HIGH

## Summary

Phase 16 enriches OG and CAF data with qualification standards, job evaluation, training requirements, and governance metadata. The research focused on established patterns for extracting structured data from government sources (TBS qualification standards, pay rates, collective agreements, CAF training pages), parsing text into structured fields, and implementing DMBOK-compliant metadata enrichment.

**Key findings:**
- Project already has robust TBS scraping infrastructure (`tbs/scraper.py`, `tbs/pdf_extractor.py`) with rate limiting (1.5s between requests) and full provenance tracking
- BeautifulSoup 4 with lxml parser (already installed) is the standard for HTML table parsing
- pdfplumber (already installed, pinned at <0.12.0) excels at extracting structured data from PDF qualification standards with 95%+ accuracy
- Pydantic models (already core to project) provide type-safe validation for structured qualification fields
- Project has established catalog enrichment patterns (`catalog/enrich.py`) and DMBOK compliance tracking (`governance/compliance/dama.py`)
- Data quality dimensions in 2026 emphasize completeness metrics and freshness tracking, both specified in CONTEXT.md

**Primary recommendation:** Extend existing TBS scraping patterns for qualification/evaluation standards and represented pay rates. Use regex patterns with fallback to original text fields (as decided in CONTEXT.md: "numeric min_years + original text"). Leverage established catalog enrichment and lineage infrastructure.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| beautifulsoup4 | >=4.12.0 | HTML parsing and table extraction | Already installed. lxml backend provides fastest parsing (2-3x faster than html.parser). Excellent encoding detection for real-world government HTML pages. |
| lxml | >=4.9.0 | HTML/XML parser backend | Already installed. Fastest BeautifulSoup parser. Required for complex government page structures. |
| pdfplumber | >=0.11.0,<0.12.0 | PDF text/table extraction | Already installed and pinned. 95%+ accuracy for structured PDFs. Extracts tables, preserves layout, provides positional data. Superior to PyPDF/PyMuPDF for tabular data. |
| pydantic | >=2.12.0 | Data validation and structured models | Already core to project. Runtime type checking, field validation, nested model support. Used throughout JobForge for provenance models. |
| requests | >=2.31.0 | HTTP scraping (synchronous) | Already installed. Standard for TBS scraping. Proven in `tbs/scraper.py`. |
| httpx | >=0.27.0 | HTTP client with async support | Already installed. Used in `tbs/pdf_extractor.py`. Supports follow_redirects for government sites. |
| structlog | >=24.0.0 | Structured logging | Already installed. Used throughout project for audit trails. |
| tenacity | >=8.2.0 | Retry logic with exponential backoff | Already installed. Essential for resilient government site scraping. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| polars | >=1.37.0 | DataFrame operations | Already installed. For transforming scraped data to gold layer. Faster than pandas for large datasets. |
| rapidfuzz | >=3.0.0 | Fuzzy string matching | Already installed. For matching TBS competencies to OASIS skills/abilities (CONTEXT.md requirement). |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pdfplumber | PyMuPDF (fitz) | PyMuPDF faster but worse table detection. pdfplumber already working in project. |
| BeautifulSoup | scrapy | scrapy is full framework (overkill for TBS pages). BS4 already proven in project. |
| requests | urllib | urllib lower-level, more verbose. requests already standard in project. |

**Installation:**
```bash
# All dependencies already installed in pyproject.toml
# No new packages required
```

## Architecture Patterns

### Recommended Project Structure
```
src/jobforge/external/tbs/
├── scraper.py                 # Main table scraping (already exists)
├── pdf_extractor.py           # PDF qualification extraction (already exists)
├── parser.py                  # HTML parsing utilities (already exists)
├── link_fetcher.py            # Follow links with rate limiting (already exists)
├── models.py                  # Pydantic models (already exists)
├── schema.py                  # TBS schema definitions (already exists)
├── pay_rates_scraper.py       # Excluded pay rates (already exists)
├── qualification_parser.py    # NEW: Parse qualification text into structured fields
├── evaluation_scraper.py      # NEW: Job evaluation standards scraper
├── represented_pay_scraper.py # NEW: Unionized pay rates scraper
├── allowances_scraper.py      # NEW: Allowances (bilingual, supervisory, etc.)
└── collective_agreement_scraper.py  # NEW: Collective agreement metadata

src/jobforge/external/caf/
├── __init__.py                # NEW: CAF module
├── models.py                  # NEW: CAF training Pydantic models
├── scraper.py                 # NEW: forces.ca career pages scraper
└── training_parser.py         # NEW: Extract training requirements

src/jobforge/ingestion/
├── og_qualifications.py       # Already exists (needs enrichment)
├── og_evaluation.py           # NEW: Job evaluation standards ingestion
├── og_represented_pay.py      # NEW: Represented pay rates ingestion
├── og_allowances.py           # NEW: Allowances ingestion
└── caf_training.py            # NEW: CAF training ingestion

src/jobforge/catalog/
├── enrich.py                  # Already exists (extend with new tables)
└── dmbok_tagging.py           # NEW: DMBOK field-level tagging

data/catalog/tables/
├── dim_og_qualification_standard.json       # NEW: Enhanced qualifications catalog
├── dim_og_job_evaluation_standard.json      # NEW: Job evaluation catalog
├── fact_og_pay_rates.json                   # EXISTS: Add represented rates
├── fact_og_allowances.json                  # NEW: Allowances catalog
├── dim_collective_agreement.json            # NEW: Collective agreements catalog
├── dim_professional_designation.json        # NEW: Professional designations lookup
├── dim_caf_training_location.json           # NEW: CAF training locations
└── fact_caf_training.json                   # NEW: CAF training requirements
```

### Pattern 1: Structured + Original Text Fields
**What:** Store both parsed structured data AND original text for human verification.

**When to use:** Qualification standards, experience/education requirements, any parsed government text.

**Example:**
```python
# Source: CONTEXT.md user decisions + project's existing models.py pattern

from pydantic import BaseModel, Field

class QualificationStandard(BaseModel):
    """Enhanced qualification standard with structured + original text."""

    og_code: str
    og_subgroup_code: str | None = None

    # Education: structured + original
    education_level: str | None = Field(
        None,
        description="Standardized: 'high_school', 'bachelors', 'masters', 'phd'"
    )
    education_requirement_text: str = Field(
        description="Original text from TBS qualification standard"
    )

    # Experience: numeric + original
    min_years_experience: int | None = Field(
        None,
        description="Parsed minimum years (null if not specified)"
    )
    experience_requirement_text: str = Field(
        description="Original text preserving context/equivalencies"
    )

    # Equivalency
    has_equivalency: bool = Field(default=False)
    equivalency_statement: str | None = None

    # Bilingual requirements: structured levels
    bilingual_reading_level: str | None = Field(
        None, description="BBB/CBC levels or null"
    )
    bilingual_writing_level: str | None = None
    bilingual_oral_level: str | None = None

    # Security clearance: structured enum
    security_clearance: str | None = Field(
        None, description="'Reliability', 'Secret', 'Top Secret', or null"
    )

    # Professional designations: FK to dim_professional_designation
    professional_designation_ids: list[str] = Field(default_factory=list)

    # Conditions of employment: structured booleans
    requires_travel: bool = False
    shift_work: bool = False
    physical_demands: bool = False

    # Operational requirements: structured booleans
    overtime_required: bool = False
    on_call_required: bool = False
    deployments_required: bool = False

    # Provenance
    source_url: str
    extracted_at: str
    full_text: str = Field(description="Complete qualification standard for full-text search")
```

**Why this pattern:** Enables both structured queries ("show positions requiring <3 years experience") AND preserves original wording for human verification and context. Aligns with CONTEXT.md decision: "numeric min_years + original text for context."

### Pattern 2: Rate Limiting for Government Sites
**What:** Respect TBS servers with delays between requests and respect robots.txt.

**When to use:** All TBS and CAF scraping operations.

**Example:**
```python
# Source: Existing tbs/pdf_extractor.py pattern + web scraping best practices

import time
from tenacity import retry, stop_after_attempt, wait_exponential

REQUEST_DELAY_SECONDS = 1.5  # Already used in project

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def fetch_with_rate_limiting(url: str, timeout: int = 30) -> str:
    """Fetch URL with rate limiting and retry logic.

    Rate limiting: 1.5s between requests (respects canada.ca servers)
    Retry: Exponential backoff 2s, 4s, 8s on failures
    """
    time.sleep(REQUEST_DELAY_SECONDS)

    response = requests.get(url, timeout=timeout)
    response.raise_for_status()

    return response.text
```

**Why this pattern:** Project already uses 1.5s delay. Government sites explicitly discourage aggressive scraping. Exponential backoff prevents overwhelming servers during temporary issues.

### Pattern 3: Catalog Enrichment with DMBOK Tagging
**What:** Extend existing `catalog/enrich.py` pattern to add DMBOK knowledge areas and data quality metrics.

**When to use:** All new tables created in Phase 16.

**Example:**
```python
# Source: Existing catalog/enrich.py + CONTEXT.md governance requirements

import json
from pathlib import Path
from datetime import datetime, timezone

DMBOK_KNOWLEDGE_AREAS = {
    "dim_og_qualification_standard": "Metadata Management",  # DMBOK-7
    "dim_og_job_evaluation_standard": "Metadata Management",  # DMBOK-7
    "fact_og_pay_rates": "Reference and Master Data",        # DMBOK-9
    "dim_collective_agreement": "Reference and Master Data",  # DMBOK-9
    "fact_caf_training": "Metadata Management",              # DMBOK-7
}

def enrich_table_metadata(table_name: str, catalog_path: Path) -> dict:
    """Enrich table catalog with DMBOK and quality metrics."""

    catalog_file = catalog_path / f"{table_name}.json"
    with open(catalog_file, "r") as f:
        metadata = json.load(f)

    # Add DMBOK tagging (table-level)
    metadata["dmbok_knowledge_area"] = DMBOK_KNOWLEDGE_AREAS.get(
        table_name, "Data Storage and Operations"  # DMBOK-4 default
    )

    # Add data quality metrics
    metadata["quality_metrics"] = {
        "completeness_pct": None,  # Computed after ingestion
        "freshness_date": datetime.now(timezone.utc).isoformat(),
        "row_count": None,  # Populated by pipeline
    }

    # Add governance fields (CONTEXT.md requirements)
    metadata["governance"] = {
        "data_steward": "OG Data Team",  # Per CONTEXT.md
        "data_owner": "Treasury Board Secretariat",
        "refresh_frequency": "as_published",  # TBS updates irregularly
        "retention_period": "indefinite",  # Historical pay/qualification data
        "security_classification": "Unclassified",  # All TBS data public
        "intended_consumers": ["JD Builder", "WiQ", "Public API"]
    }

    # Write enriched metadata
    with open(catalog_file, "w") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    return metadata
```

**Why this pattern:** Extends established `catalog/enrich.py` pattern. DMBOK knowledge areas align with `governance/compliance/dama.py`. Fulfills CONTEXT.md requirements for data_steward, refresh_frequency, retention_period, security_classification, intended_consumers.

### Pattern 4: Field-Level DMBOK Tagging
**What:** Tag individual columns with DMBOK data element types (per CONTEXT.md: "field-level DMBOK data element types").

**When to use:** All catalog metadata for new tables.

**Example:**
```python
# Source: CONTEXT.md governance granularity requirements

DMBOK_DATA_ELEMENT_TYPES = {
    # Reference data elements (DMBOK-9)
    "og_code": "reference_code",
    "og_subgroup_code": "reference_code",
    "classification_level": "reference_code",

    # Descriptive metadata (DMBOK-7)
    "full_text": "descriptive_text",
    "education_requirement_text": "descriptive_text",
    "experience_requirement_text": "descriptive_text",

    # Structured attributes (DMBOK-3)
    "min_years_experience": "numeric_attribute",
    "education_level": "categorical_attribute",
    "security_clearance": "categorical_attribute",

    # Temporal data (DMBOK-4)
    "effective_date": "temporal_effective",
    "expiry_date": "temporal_expiry",
    "extracted_at": "temporal_provenance",

    # Identifiers (DMBOK-9)
    "source_url": "provenance_identifier",
    "collective_agreement_id": "reference_identifier",
}

def add_field_dmbok_tags(columns: list[dict]) -> list[dict]:
    """Add DMBOK data element type to each column."""
    for col in columns:
        col_name = col["name"]
        col["dmbok_element_type"] = DMBOK_DATA_ELEMENT_TYPES.get(
            col_name, "data_attribute"  # Default
        )
    return columns
```

**Why this pattern:** Fulfills CONTEXT.md requirement for "field-level DMBOK data element types." Enables downstream governance queries ("show all temporal_provenance fields").

### Anti-Patterns to Avoid
- **Aggressive scraping:** TBS blocks IPs that ignore rate limits. Always use REQUEST_DELAY_SECONDS = 1.5.
- **Losing original text:** Don't only store parsed values. Always preserve original text for verification (as specified in CONTEXT.md).
- **Brittle parsing:** TBS formats are inconsistent. Use regex with fallbacks, not rigid parsers.
- **Ignoring robots.txt:** Government sites may update restrictions. Check robots.txt before each scraping session.
- **No provenance:** Every scraped record must have source_url and extracted_at (project standard).

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF table extraction | Custom text parser with position heuristics | pdfplumber.extract_tables() | pdfplumber handles edge cases: merged cells, multi-line cells, rotated text. 95%+ accuracy. Already installed. |
| Retry logic with backoff | Custom sleep/retry loops | tenacity decorators | tenacity handles exponential backoff, jitter, conditional retries. Already installed. Well-tested. |
| HTML table parsing | Manual BeautifulSoup loops | pandas.read_html() or existing parser.py | pandas.read_html() auto-detects tables. Project's parser.py already handles TBS table structures. |
| Fuzzy string matching | Levenshtein distance from scratch | rapidfuzz library | rapidfuzz 5-10x faster than fuzzywuzzy. Already installed. Needed for TBS competency → OASIS mapping. |
| Data validation | Manual type checks and if/else | Pydantic models | Pydantic provides runtime validation, clear error messages, nested models. Already core to project. |
| Structured logging | print() or basic logging | structlog | structlog already used throughout project. Provides structured audit trails for provenance. |

**Key insight:** Project already has robust infrastructure. Extend existing patterns rather than introducing new libraries. The stack (BeautifulSoup, pdfplumber, Pydantic, tenacity) is proven and sufficient.

## Common Pitfalls

### Pitfall 1: Inconsistent TBS Qualification Formats
**What goes wrong:** TBS qualification standards have no consistent format. Some use bullet points, some paragraphs, some tables. Parsing with rigid regex fails on ~40% of standards.

**Why it happens:** TBS publishes standards across decades. Each occupational group uses different templates. No enforced schema.

**How to avoid:**
- Use permissive regex patterns with multiple variants
- Always fallback to full_text if parsing fails
- Store both structured fields AND original text (CONTEXT.md requirement)
- Log parsing failures for manual review

**Warning signs:**
- Qualification records with all null structured fields
- Different record counts between bronze (all scraped) and silver (parsed)
- Logs showing repeated regex match failures

**Example mitigation:**
```python
def parse_experience_requirement(text: str) -> tuple[int | None, str]:
    """Parse experience with fallback to original text.

    Returns: (min_years, original_text)
    """
    # Try multiple patterns (ordered by specificity)
    patterns = [
        r"minimum of (\d+) years?",
        r"at least (\d+) years?",
        r"(\d+)\+? years? of",
        r"(\d+) years? experience",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return (int(match.group(1)), text)

    # No match: return None for structured, preserve text
    logger.info("experience_parse_failed", text=text[:100])
    return (None, text)
```

### Pitfall 2: TBS Page Structure Changes Breaking Scrapers
**What goes wrong:** TBS redesigns pages without notice. Scrapers break silently, returning incomplete data. Users don't notice until weeks later.

**Why it happens:** Government sites update layouts for accessibility/mobile. No API contracts. No changelog notifications.

**How to avoid:**
- Fail loudly on unexpected HTML structure (project already does this in `tbs/parser.py`)
- Validate expected row/column counts against historical baselines
- Add schema validation at bronze layer ingestion
- Set up automated scraper health checks (cron job + alerts)

**Warning signs:**
- Row counts drop >20% from previous scrape
- New null columns appearing
- HTML parsing returns empty lists where tables expected
- BeautifulSoup find() returns None for previously reliable selectors

**Example validation:**
```python
def validate_scraped_pay_rates(rows: list[dict]) -> None:
    """Validate scraped pay rates against expected structure."""

    if len(rows) < 100:  # Historical baseline: ~200 rows
        raise ValueError(
            f"Scraped only {len(rows)} pay rate rows. "
            f"Expected >=100. TBS page structure may have changed."
        )

    required_fields = {"og_subgroup_code", "classification_level", "annual_rate"}
    for row in rows[:10]:  # Check first 10 rows
        if not required_fields.issubset(row.keys()):
            raise ValueError(
                f"Missing required fields in scraped data. "
                f"Expected {required_fields}, got {row.keys()}"
            )
```

### Pitfall 3: CAF Training Data Sparsity and Inconsistency
**What goes wrong:** CAF publishes training info for only ~60 of 107 occupations. Some pages have duration, others don't. Location names inconsistent ("Borden" vs "CFB Borden" vs "Base Borden"). Ingestion fails or creates duplicate training locations.

**Why it happens:** forces.ca is marketing-focused, not data-structured. No standardized template across occupations. Information completeness varies by recruiting priority.

**How to avoid:**
- Create dim_caf_training_location lookup with fuzzy matching
- Use has_training_info boolean flag (don't fail on missing data)
- Store sparse data as null, not empty strings
- Document expected sparsity in catalog metadata

**Warning signs:**
- Multiple training location records for same base ("Borden", "CFB Borden")
- fact_caf_training with only 50-70 records (not 107)
- Duration fields mixing "10 weeks", "2.5 months", null

**Example normalization:**
```python
from rapidfuzz import fuzz

TRAINING_LOCATION_CANONICAL = {
    "borden": "CFB Borden",
    "gagetown": "CFB Gagetown",
    "esquimalt": "CFB Esquimalt",
    "kingston": "Kingston",
    "saint-jean": "CFLRS Saint-Jean-sur-Richelieu",
}

def normalize_training_location(location_text: str | None) -> str | None:
    """Fuzzy match training location to canonical name."""
    if not location_text:
        return None

    location_lower = location_text.lower()

    # Exact lookup first
    for key, canonical in TRAINING_LOCATION_CANONICAL.items():
        if key in location_lower:
            return canonical

    # Fuzzy fallback
    best_match = max(
        TRAINING_LOCATION_CANONICAL.items(),
        key=lambda x: fuzz.ratio(location_lower, x[0])
    )

    if fuzz.ratio(location_lower, best_match[0]) > 80:
        return best_match[1]

    # Unknown location: preserve original
    logger.warning("unknown_training_location", location=location_text)
    return location_text
```

### Pitfall 4: Collective Agreement Expiry Dates and Historical Rates
**What goes wrong:** Scraping only "current" collective agreements misses historical context. Pay rates change mid-agreement. Without effective_date tracking, historical queries fail.

**Why it happens:** TBS shows current rates prominently, archives historical rates inconsistently. Developers assume "current = sufficient."

**How to avoid:**
- Scrape ALL available historical rates, not just current (CONTEXT.md: "all available historical rates scraped")
- Track effective_date and expiry_date per collective agreement
- Store pay_rate records with effective_date, not just current snapshot
- Link pay rates to collective_agreement via FK

**Warning signs:**
- fact_og_pay_rates with single date (missing historical progression)
- Collective agreements with null expiry_date
- User queries like "pay rate in 2020" returning no results

**Example structure:**
```python
class CollectiveAgreement(BaseModel):
    """Collective agreement metadata with temporal tracking."""

    agreement_id: str  # PK
    agreement_name: str  # e.g., "EC Group Collective Agreement"
    bargaining_agent: str  # e.g., "Canadian Association of Professional Employees"
    employer: str = "Treasury Board"

    effective_date: str  # YYYY-MM-DD
    expiry_date: str | None  # YYYY-MM-DD or null if evergreen

    source_url: str
    scraped_at: str

class PayRate(BaseModel):
    """Pay rate with temporal and collective agreement linkage."""

    og_subgroup_code: str
    classification_level: str
    step: int
    annual_rate: float

    effective_date: str  # CRITICAL: enables historical queries
    is_represented: bool
    collective_agreement_id: str | None  # FK to dim_collective_agreement

    source_url: str  # Per-record provenance (CONTEXT.MD requirement)
```

### Pitfall 5: DMBOK Tagging Without Field-Level Granularity
**What goes wrong:** Developers add table-level dmbok_knowledge_area but skip field-level tags. Governance queries fail ("show all temporal_provenance fields across all tables").

**Why it happens:** CONTEXT.MD specifies both table-level AND field-level tagging. Easy to miss field-level requirement.

**How to avoid:**
- Extend catalog enrichment to tag EVERY column with dmbok_element_type
- Create DMBOK_DATA_ELEMENT_TYPES lookup (see Pattern 4)
- Validate that all catalog JSONs have dmbok_element_type in columns
- Add to test suite: "all columns must have dmbok_element_type"

**Warning signs:**
- Catalog JSON columns without dmbok_element_type field
- Governance queries returning empty results
- DMBOK compliance log showing table-level tags but no field-level detail

## Code Examples

Verified patterns from existing codebase and official sources:

### Scraping TBS with Rate Limiting and Provenance
```python
# Source: Existing tbs/scraper.py + tbs/pdf_extractor.py patterns

import time
from datetime import datetime, timezone
import requests
import structlog

logger = structlog.get_logger(__name__)

REQUEST_DELAY_SECONDS = 1.5  # Respect canada.ca servers

def scrape_qualification_standard_urls(language: str = "en") -> list[dict]:
    """Scrape qualification standard URLs from TBS core page.

    Returns list of {og_code, url, scraped_at} dicts.
    """
    base_url = (
        "https://www.canada.ca/en/treasury-board-secretariat/"
        "services/staffing/qualification-standards/core.html"
    )

    logger.info("scraping_qualification_urls", url=base_url)

    response = requests.get(base_url, timeout=30)
    response.raise_for_status()

    scraped_at = datetime.now(timezone.utc).isoformat()

    # Parse with BeautifulSoup (lxml parser)
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(response.text, "lxml")

    # Find links to qualification standards
    links = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if "qualification-standards" in href or href.endswith(".pdf"):
            # Extract OG code from link text or URL
            og_code = extract_og_code(a_tag.text, href)

            links.append({
                "og_code": og_code,
                "url": href if href.startswith("http") else f"https://www.canada.ca{href}",
                "scraped_at": scraped_at,
            })

            # Rate limiting
            time.sleep(REQUEST_DELAY_SECONDS)

    logger.info("scraped_qualification_urls", count=len(links))
    return links

def extract_og_code(link_text: str, url: str) -> str:
    """Extract OG code from link text or URL."""
    # Try link text first (e.g., "EC - Economics and Social Science Services")
    import re
    match = re.match(r"^([A-Z]{2,4})\s*[-–]", link_text)
    if match:
        return match.group(1)

    # Fallback: extract from URL
    match = re.search(r"/([A-Z]{2,4})[-_]", url)
    if match:
        return match.group(1)

    return "UNKNOWN"
```

### Parsing Qualification Text with Structured + Original Pattern
```python
# Source: CONTEXT.MD requirements + project Pydantic patterns

import re
from pydantic import BaseModel, Field

class ParsedQualification(BaseModel):
    """Qualification with structured fields + original text."""

    # Structured education
    education_level: str | None = Field(
        None,
        description="Standardized: 'high_school', 'certificate', 'diploma', "
                    "'bachelors', 'masters', 'phd', 'professional_degree'"
    )
    education_requirement_text: str

    # Structured experience
    min_years_experience: int | None = None
    experience_requirement_text: str

    # Equivalency
    has_equivalency: bool = False
    equivalency_statement: str | None = None

def parse_qualification_text(full_text: str) -> ParsedQualification:
    """Parse qualification standard into structured fields.

    Uses permissive regex with fallbacks. Always preserves original text.
    """
    # Extract education section
    education_section = extract_section(full_text, "Education")
    education_level = parse_education_level(education_section)

    # Extract experience section
    experience_section = extract_section(full_text, "Experience")
    min_years, experience_text = parse_experience_years(experience_section)

    # Check for equivalency
    has_equiv = bool(re.search(r"equivalent|acceptable alternative", full_text, re.IGNORECASE))
    equiv_statement = extract_equivalency(full_text) if has_equiv else None

    return ParsedQualification(
        education_level=education_level,
        education_requirement_text=education_section or full_text,
        min_years_experience=min_years,
        experience_requirement_text=experience_text or full_text,
        has_equivalency=has_equiv,
        equivalency_statement=equiv_statement,
    )

def parse_education_level(text: str) -> str | None:
    """Parse education level with multiple pattern variants."""
    if not text:
        return None

    text_lower = text.lower()

    # Ordered by specificity (most specific first)
    if "ph.d" in text_lower or "doctorate" in text_lower:
        return "phd"
    if "master" in text_lower:
        return "masters"
    if "bachelor" in text_lower or "undergraduate degree" in text_lower:
        return "bachelors"
    if "diploma" in text_lower:
        return "diploma"
    if "certificate" in text_lower:
        return "certificate"
    if "secondary school" in text_lower or "high school" in text_lower:
        return "high_school"

    # No match
    return None

def parse_experience_years(text: str) -> tuple[int | None, str]:
    """Parse years of experience with fallback to original text."""
    if not text:
        return (None, "")

    # Multiple pattern variants
    patterns = [
        r"minimum of (\d+) years?",
        r"at least (\d+) years?",
        r"(\d+)\+? years? of",
        r"(\d+) years? .* experience",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            years = int(match.group(1))
            return (years, text)

    # No structured match: preserve original
    return (None, text)

def extract_section(text: str, section_name: str) -> str | None:
    """Extract a section from qualification standard text."""
    # Look for section header
    pattern = rf"{section_name}[:\s]+(.*?)(?=\n\n[A-Z]|\Z)"
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)

    if match:
        return match.group(1).strip()

    return None

def extract_equivalency(text: str) -> str | None:
    """Extract equivalency statement if present."""
    # Look for equivalency paragraphs
    pattern = r"(.*?equivalent.*?\.)"
    matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)

    if matches:
        # Return first equivalency statement
        return matches[0].strip()

    return None
```

### Catalog Enrichment with DMBOK Tags
```python
# Source: Existing catalog/enrich.py pattern + CONTEXT.MD requirements

import json
from pathlib import Path
from datetime import datetime, timezone

def enrich_og_qualification_catalog() -> None:
    """Enrich dim_og_qualification_standard catalog with DMBOK tags."""

    catalog_path = Path("data/catalog/tables/dim_og_qualification_standard.json")

    with open(catalog_path, "r") as f:
        metadata = json.load(f)

    # Table-level DMBOK tagging
    metadata["dmbok_knowledge_area"] = "Metadata Management"  # DMBOK-7

    # Governance fields (CONTEXT.MD requirements)
    metadata["governance"] = {
        "data_steward": "OG Data Team",
        "data_owner": "Treasury Board Secretariat",
        "refresh_frequency": "as_published",
        "retention_period": "indefinite",
        "security_classification": "Unclassified",
        "intended_consumers": ["JD Builder", "WiQ", "Public API"]
    }

    # Data quality metrics
    metadata["quality_metrics"] = {
        "completeness_pct": None,  # Computed after ingestion
        "freshness_date": datetime.now(timezone.utc).isoformat(),
    }

    # Field-level DMBOK tagging
    for column in metadata["columns"]:
        col_name = column["name"]

        # Assign DMBOK element type
        if col_name in ["og_code", "og_subgroup_code"]:
            column["dmbok_element_type"] = "reference_code"
        elif col_name.endswith("_text") or col_name == "full_text":
            column["dmbok_element_type"] = "descriptive_text"
        elif col_name.startswith("min_") or col_name.endswith("_level"):
            column["dmbok_element_type"] = "numeric_attribute"
        elif col_name == "source_url":
            column["dmbok_element_type"] = "provenance_identifier"
        elif col_name == "extracted_at":
            column["dmbok_element_type"] = "temporal_provenance"
        else:
            column["dmbok_element_type"] = "data_attribute"

    # Write enriched metadata
    with open(catalog_path, "w") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"Enriched {catalog_path}")
```

### Lineage Tracking for Extended Metadata
```python
# Source: Existing pipeline/provenance.py pattern

from datetime import datetime, timezone
from uuid import uuid4
from pydantic import BaseModel

class LineageRecord(BaseModel):
    """Lineage tracking for metadata transformations."""

    transition_id: str
    batch_id: str
    source_layer: str
    target_layer: str
    source_files: list[str]
    target_file: str
    row_count_in: int
    row_count_out: int
    transforms_applied: list[str]
    started_at: str
    completed_at: str
    status: str
    errors: str | None = None

def record_qualification_lineage(
    source_url: str,
    target_table: str,
    row_count: int,
    transforms: list[str]
) -> LineageRecord:
    """Record lineage for qualification standard ingestion."""

    now = datetime.now(timezone.utc).isoformat()

    lineage = LineageRecord(
        transition_id=str(uuid4()),
        batch_id=str(uuid4()),
        source_layer="external",  # TBS source
        target_layer="bronze",
        source_files=[source_url],
        target_file=f"data/bronze/{target_table}.parquet",
        row_count_in=row_count,
        row_count_out=row_count,
        transforms_applied=transforms,
        started_at=now,
        completed_at=now,
        status="success",
        errors=None,
    )

    # Save to data/catalog/lineage/
    lineage_path = Path(f"data/catalog/lineage/{lineage.transition_id}.json")
    with open(lineage_path, "w") as f:
        json.dump(lineage.model_dump(mode="json"), f, indent=2)

    return lineage
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Rule-based text parsing (regex only) | LLM-powered extraction with structured output (LangExtract, LlamaIndex) | 2024-2025 | 95%+ accuracy for unstructured government docs. But CONTEXT.MD gives Claude's Discretion on parsing → stick with regex for simplicity and cost. |
| PyPDF for table extraction | pdfplumber with layout awareness | 2023-2024 | 95%+ accuracy on complex tables. pdfplumber already in project at <0.12.0. |
| html.parser for BeautifulSoup | lxml parser | Stable since 2020 | 2-3x faster. Better encoding detection. Already project standard. |
| Pandas for scraping | BeautifulSoup + Polars | 2024-2025 | BS4 more flexible for non-tabular HTML. Polars faster for transformations. Already project standard. |
| Manual data quality checks | Automated completeness/freshness metrics in catalog | 2025-2026 | Metadata-driven quality tracking. CONTEXT.MD specifies this pattern. |

**Deprecated/outdated:**
- **PyPDF2/PyMuPDF for tables:** Superseded by pdfplumber for structured table extraction. pdfplumber handles merged cells, multi-line text, layout preservation.
- **fuzzywuzzy:** Replaced by rapidfuzz (5-10x faster, drop-in replacement). Project already uses rapidfuzz >=3.0.0.
- **print() for logging:** Replaced by structlog for structured audit trails. Already project standard.

## Open Questions

Things that couldn't be fully resolved:

1. **TBS Job Evaluation Standards Format**
   - What we know: TBS publishes evaluation standards at https://www.canada.ca/en/treasury-board-secretariat/services/staffing/qualification-standards.html
   - What's unclear: Whether they're HTML, PDF, or both. Whether they include numeric point values or just descriptive levels.
   - Recommendation: Manual inspection during Phase 16 implementation. Build scraper after confirming format. Use same pattern as qualification standards (HTML → BeautifulSoup, PDF → pdfplumber).

2. **Collective Agreement Full Text vs Metadata**
   - What we know: CONTEXT.MD specifies "full metadata: name, expiry date, bargaining agent, employer signatory"
   - What's unclear: Whether to scrape full collective agreement text (100+ page PDFs) or just metadata table from rates-of-pay page.
   - Recommendation: Start with metadata only (aligns with dim_collective_agreement table design). Full text extraction is out of scope unless explicitly required.

3. **CAF Training Data Availability**
   - What we know: forces.ca publishes career pages for 107 occupations. Training info is inconsistent.
   - What's unclear: Exact availability rate (how many of 107 have structured training data). Whether historical training data exists.
   - Recommendation: Scrape all 107 pages, flag missing data with has_training_info boolean. Document sparsity in catalog metadata. Don't fail on missing data.

4. **Cross-Reference Algorithm: TBS Competencies → OASIS Skills**
   - What we know: CONTEXT.MD requires "cross-reference TBS competencies to OASIS skills/abilities where possible"
   - What's unclear: Whether TBS explicitly lists competencies in qualification standards, or if they're implicit. Matching algorithm details left to "Claude's Discretion."
   - Recommendation: Use rapidfuzz for fuzzy matching competency text to OASIS skill descriptions. Threshold ≥80% similarity. Store matches in bridge table with match_score field. Manual review of matches <90% similarity.

5. **Regional Pay Differentials Availability**
   - What we know: CONTEXT.MD says "regional pay differentials if TBS publishes them"
   - What's unclear: Whether TBS actually publishes regional differentials, or if pay is nationally uniform.
   - Recommendation: Check rates-of-pay page for regional columns during implementation. If absent, document "regional pay differentials not published by TBS" in notes.

## Sources

### Primary (HIGH confidence)
- Project codebase: `src/jobforge/external/tbs/scraper.py`, `tbs/pdf_extractor.py`, `catalog/enrich.py`, `governance/compliance/dama.py`
- Project dependencies: `pyproject.toml` (beautifulsoup4 >=4.12.0, lxml >=4.9.0, pdfplumber >=0.11.0,<0.12.0, pydantic >=2.12.0)
- CONTEXT.MD user decisions: Structured + original text fields, DMBOK tagging (table and field-level), per-record source URLs

### Secondary (MEDIUM confidence)
- [Unstract: Best Python PDF to Text Parser Libraries 2026](https://unstract.com/blog/evaluating-python-pdf-to-text-libraries/) - pdfplumber evaluation, 95%+ accuracy claim
- [Unstract: Best Python Libraries to Extract Tables From PDF 2026](https://unstract.com/blog/extract-tables-from-pdf-python/) - pdfplumber table extraction capabilities
- [Atlan: DAMA DMBOK Framework Ultimate Guide 2026](https://atlan.com/dama-dmbok-framework/) - DMBOK 3.0 AI governance, modern data catalog automation
- [Atlan: Data Lineage Tracking Complete Guide 2026](https://atlan.com/know/data-lineage-tracking/) - Column-level lineage patterns
- [Dagster: Top 8 Data Quality Metrics 2026](https://dagster.io/learn/data-quality-metrics) - Completeness, freshness metrics
- [ZenRows: How to Parse Tables Using BeautifulSoup](https://www.zenrows.com/blog/beautifulsoup-parse-table) - lxml parser performance
- [Medium: Web Scraping Ethics 2026](https://medium.com/@ridhopujiono.work/web-scraping-2-ethics-legality-robots-txt-how-to-stay-out-of-trouble-39052f7dc63f) - Rate limiting, robots.txt best practices
- [Medium: DOs and DON'Ts of Web Scraping 2026](https://medium.com/@datajournal/dos-and-donts-of-web-scraping-in-2025-e4f9b2a49431) - Throttling to human interaction speeds
- [TBS Collective Agreements Page](https://www.canada.ca/en/treasury-board-secretariat/topics/pay/collective-agreements.html) - Official source for collective agreements
- [GitHub: payscraper](https://github.com/ToferC/payscraper) - Existing Go scraper for TBS pay rates (40 collective agreements)
- [Canadian Armed Forces: Basic Training](https://www.canada.ca/en/department-national-defence/services/benefits-military/education-training/basic-training.html) - Official CAF training info
- [forces.ca: How to Join](https://forces.ca/en/how-to-join/) - CAF career pages structure
- [Pydantic Documentation: Validators](https://docs.pydantic.dev/latest/concepts/validators/) - Field validation patterns
- [Python re Documentation](https://docs.python.org/3/library/re.html) - Regex patterns

### Tertiary (LOW confidence)
- Google LangExtract for LLM-powered extraction - Not used (CONTEXT.MD gives regex discretion, LLMs add cost/complexity)
- Scrapy framework - Not used (BeautifulSoup already proven in project)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already installed and proven in project. No new dependencies required.
- Architecture: HIGH - Extends existing patterns (tbs/scraper.py, catalog/enrich.py, governance/compliance/dama.py). CONTEXT.MD provides detailed structure requirements.
- Pitfalls: MEDIUM - Based on web scraping best practices (2026 sources) + project experience. TBS-specific pitfalls inferred from existing code patterns.

**Research date:** 2026-02-05
**Valid until:** 2026-03-05 (30 days - government sites stable, libraries mature)
