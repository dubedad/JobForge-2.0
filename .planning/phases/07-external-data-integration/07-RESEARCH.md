# Phase 7: External Data Integration - Research

**Researched:** 2026-01-19
**Domain:** External data integration (O*NET API, LLM imputation, TBS scraping)
**Confidence:** MEDIUM-HIGH

## Summary

Phase 7 integrates three external data sources into WiQ: O*NET API for SOC-aligned attributes, LLM (OpenAI) for remaining attribute gaps, and TBS web scraping for occupational group metadata. Each source has distinct technical requirements and provenance patterns.

The NOC-SOC crosswalk is the critical dependency for O*NET integration. The Brookfield Institute provides a MIT-licensed NOC 2021 to O*NET 26 crosswalk (noc2021_onet26.csv) with 1,468 mappings. This establishes 1:N relationships where one NOC code may map to multiple SOC codes.

O*NET Web Services 2.0 provides a RESTful API requiring registration for HTTP Basic Auth credentials. The bulk database download (CC-BY-4.0) is available in multiple formats if API rate limits are a concern. OpenAI's Structured Outputs feature ensures reliable JSON schema adherence for LLM responses using Pydantic models directly. TBS pages are standard HTML tables scrapable with BeautifulSoup/requests.

**Primary recommendation:** Use the bulk NOC-O*NET crosswalk CSV for mapping, O*NET Web Services API for attribute fetch, OpenAI Structured Outputs with Pydantic models for LLM imputation, and BeautifulSoup for TBS scraping with provenance timestamps.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | 0.27+ | HTTP client for O*NET API | Async support, HTTP/2, connection pooling |
| openai | 1.52+ | LLM imputation | Official SDK with Pydantic structured outputs |
| beautifulsoup4 | 4.12+ | TBS HTML parsing | De-facto standard for HTML scraping |
| requests | 2.31+ | HTTP fetches (sync) | Simple, reliable for scraping |
| polars | 1.37+ | Data processing (already in stack) | Fast DataFrame operations |
| pydantic | 2.12+ | Schema validation (already in stack) | Structured outputs, API models |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tenacity | 8.2+ | Retry logic | API failures, rate limits |
| lxml | 4.9+ | Fast HTML parser | Performance-critical parsing |
| pandas | 2.0+ (optional) | CSV crosswalk loading | Alternative to Polars for CSVs |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| httpx | aiohttp | aiohttp is more performant but less ergonomic, no sync fallback |
| httpx | requests | requests lacks async, but simpler for scraping-only use |
| openai SDK | direct HTTP | SDK provides Pydantic integration, retry logic |
| beautifulsoup4 | selectolax | selectolax faster but less mature |

**Installation:**
```bash
pip install httpx openai beautifulsoup4 tenacity lxml
```

## Architecture Patterns

### Recommended Project Structure
```
src/jobforge/
  external/
    __init__.py
    models.py          # Pydantic models for external sources
    onet/
      __init__.py
      client.py        # O*NET Web Services client
      crosswalk.py     # NOC-SOC crosswalk loading
      adapter.py       # Convert O*NET -> WiQ schema
    llm/
      __init__.py
      client.py        # OpenAI client wrapper
      service.py       # Imputation orchestration
      prompts.py       # Prompt templates
    tbs/
      __init__.py
      scraper.py       # TBS page scraping
      parser.py        # HTML to structured data
      models.py        # Occupational group schema
```

### Pattern 1: Adapter Pattern for O*NET Integration
**What:** Wrap O*NET API calls behind a typed adapter that converts O*NET schema to WiQ schema
**When to use:** All O*NET data fetches
**Example:**
```python
# Source: O*NET API documentation + project patterns
@dataclass
class ONetAttribute:
    """O*NET attribute aligned to WiQ provenance."""
    element_id: str
    name: str
    description: str
    importance_score: float  # 0-100 scale
    source_soc: str
    source_noc: str  # Mapped via crosswalk

class ONetAdapter:
    """Adapter converting O*NET API responses to WiQ schema."""

    def __init__(self, client: ONetClient, crosswalk: NOCSOCCrosswalk):
        self.client = client
        self.crosswalk = crosswalk

    async def get_attributes_for_noc(
        self, noc_code: str
    ) -> list[ONetAttribute]:
        """Fetch O*NET attributes for a NOC code via crosswalk."""
        soc_codes = self.crosswalk.noc_to_soc(noc_code)
        attributes = []
        for soc in soc_codes:
            raw = await self.client.get_skills(soc)
            attributes.extend(self._adapt(raw, soc, noc_code))
        return attributes
```

### Pattern 2: Structured Output for LLM Imputation
**What:** Define Pydantic models that OpenAI SDK uses for guaranteed schema adherence
**When to use:** All LLM imputation calls
**Example:**
```python
# Source: OpenAI Cookbook structured_outputs_intro
from pydantic import BaseModel, Field
from openai import OpenAI

class ImputedAttributeValue(BaseModel):
    """Single imputed attribute with confidence and rationale."""
    value: str = Field(description="The imputed attribute value")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence 0-1")
    rationale: str = Field(description="Explanation for the imputation")

class ImputationResponse(BaseModel):
    """LLM response for attribute imputation."""
    attributes: list[ImputedAttributeValue]
    context_used: str = Field(description="What context influenced the answer")

client = OpenAI()

completion = client.beta.chat.completions.parse(
    model="gpt-4o-2024-08-06",
    messages=[
        {"role": "system", "content": IMPUTATION_SYSTEM_PROMPT},
        {"role": "user", "content": build_imputation_prompt(job_context)},
    ],
    response_format=ImputationResponse,
)
result = completion.choices[0].message.parsed  # Typed ImputationResponse
```

### Pattern 3: Provenance-First Scraping
**What:** Every scraped value carries full provenance (URL, timestamp, extraction method)
**When to use:** All TBS scraping
**Example:**
```python
# Source: Project provenance patterns (Phase 6)
from datetime import datetime, timezone
from dataclasses import dataclass

@dataclass
class ScrapedValue:
    """Value with scraping provenance."""
    value: str
    source_url: str
    scraped_at: datetime
    extraction_method: str  # "table_cell", "link_text", etc.
    page_title: str

def scrape_with_provenance(soup: BeautifulSoup, url: str) -> list[ScrapedValue]:
    """Extract table data with full provenance."""
    now = datetime.now(timezone.utc)
    title = soup.find("title").text if soup.find("title") else "Unknown"

    values = []
    for cell in soup.find_all("td"):
        values.append(ScrapedValue(
            value=cell.text.strip(),
            source_url=url,
            scraped_at=now,
            extraction_method="table_cell",
            page_title=title,
        ))
    return values
```

### Pattern 4: Source Precedence Override
**What:** Fixed hierarchy where higher-precedence sources auto-override lower ones
**When to use:** When storing imputed values to avoid conflicts
**Example:**
```python
# Source: 07-CONTEXT.md decisions
class SourcePrecedence(IntEnum):
    """Source precedence - higher values override lower."""
    LLM = 1
    ONET = 2
    AUTHORITATIVE = 3

def should_override(existing_source: SourcePrecedence, new_source: SourcePrecedence) -> bool:
    """Determine if new value should override existing."""
    return new_source >= existing_source
```

### Anti-Patterns to Avoid
- **Calling O*NET API per job title:** Use bulk crosswalk lookup + cache at unit group level
- **Hardcoding SOC codes:** Always go through NOC-SOC crosswalk
- **Trusting LLM confidence blindly:** Store LLM confidence as-is but flag for review
- **Scraping without timestamps:** Every scraped value needs provenance
- **Ignoring robots.txt:** Check Canada.ca policies before scraping

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| NOC-SOC mapping | Custom mapping logic | Brookfield NOC-O*NET Crosswalk | 1,468 pre-validated mappings, MIT license |
| HTTP retry logic | Manual try/except | tenacity library | Exponential backoff, jitter, max attempts |
| JSON schema validation | Manual parsing | OpenAI Structured Outputs | 100% schema adherence guaranteed |
| HTML table parsing | Regex extraction | BeautifulSoup + pandas.read_html | Handles edge cases, malformed HTML |
| API authentication | Custom auth headers | httpx.BasicAuth | Proper encoding, session management |

**Key insight:** The NOC-SOC crosswalk is the foundation - without it, O*NET integration fails. The Brookfield Institute crosswalk has been validated against official ISCO mappings and covers all 516 NOC unit groups.

## Common Pitfalls

### Pitfall 1: NOC-SOC Cardinality Mismatch
**What goes wrong:** Assuming 1:1 mapping when NOC-SOC is actually 1:N or N:1
**Why it happens:** Different occupational scopes between Canadian and US systems
**How to avoid:** Always handle multiple SOC codes per NOC; aggregate attributes across mappings
**Warning signs:** Missing O*NET data for valid NOC codes, duplicate attributes

### Pitfall 2: O*NET API Rate Limiting
**What goes wrong:** Getting 429 errors during bulk operations
**Why it happens:** O*NET has undocumented rate limits
**How to avoid:** Use bulk database download for initial load; cache API responses; implement exponential backoff
**Warning signs:** Intermittent failures, HTTP 429 responses

### Pitfall 3: LLM Confidence Hallucination
**What goes wrong:** LLM returns high confidence for fabricated information
**Why it happens:** LLMs don't have calibrated uncertainty
**How to avoid:** Store confidence as-is per CONTEXT.md decision; use rationale for manual review; don't filter by confidence
**Warning signs:** Suspiciously uniform confidence scores, implausible attributes

### Pitfall 4: TBS Page Structure Changes
**What goes wrong:** Scraper silently returns empty/wrong data after site update
**Why it happens:** Government sites get redesigned
**How to avoid:** Fail loudly per CONTEXT.md - detect expected elements, raise exception if missing; store page structure version
**Warning signs:** Empty results, schema validation failures

### Pitfall 5: Missing Bilingual Content
**What goes wrong:** Only scraping English, missing French metadata
**Why it happens:** Forgetting Canada.ca has /en/ and /fr/ versions
**How to avoid:** Per CONTEXT.md - scrape both languages into separate files
**Warning signs:** Missing lang column, incomplete coverage

### Pitfall 6: Stale Crosswalk Data
**What goes wrong:** Using outdated NOC 2016 crosswalk with NOC 2021 codes
**Why it happens:** Multiple crosswalk versions exist
**How to avoid:** Use noc2021_onet26.csv (NOC 2021 + O*NET 26); verify NOC version in source data
**Warning signs:** Failed lookups, key mismatches

## Code Examples

Verified patterns from official sources:

### O*NET Web Services Authentication
```python
# Source: O*NET Web Services documentation + GitHub samples
import httpx

ONET_BASE_URL = "https://services.onetcenter.org/ws/online"

class ONetClient:
    """O*NET Web Services client with Basic Auth."""

    def __init__(self, username: str, password: str):
        self.auth = httpx.BasicAuth(username, password)
        self.headers = {"Accept": "application/json"}

    async def get_occupation_skills(self, soc_code: str) -> dict:
        """Fetch skills for a SOC code."""
        async with httpx.AsyncClient(auth=self.auth) as client:
            url = f"{ONET_BASE_URL}/occupations/{soc_code}/summary/skills"
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
```

### OpenAI Structured Output with Pydantic
```python
# Source: OpenAI Platform docs + Cookbook
from pydantic import BaseModel, Field
from openai import OpenAI

class AttributeImputation(BaseModel):
    """Schema for LLM attribute imputation."""
    attribute_name: str
    imputed_value: str
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str

class ImputationBatch(BaseModel):
    """Batch response for multiple imputations."""
    imputations: list[AttributeImputation]

def impute_attributes(
    client: OpenAI,
    job_title: str,
    job_family: str,
    known_attributes: dict[str, str],
    missing_attributes: list[str],
) -> ImputationBatch:
    """Impute missing attributes using LLM."""
    context = f"""
Job Title: {job_title}
Job Family: {job_family}
Known Attributes: {known_attributes}
Missing Attributes: {missing_attributes}
"""
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": context},
        ],
        response_format=ImputationBatch,
    )
    return completion.choices[0].message.parsed
```

### TBS Table Scraping with Provenance
```python
# Source: BeautifulSoup docs + project patterns
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from dataclasses import dataclass, field

@dataclass
class OccupationalGroupRow:
    """Single row from TBS occupational groups table."""
    group_code: str
    group_name: str
    definition_url: str | None
    evaluation_standard_url: str | None
    scraped_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_url: str = ""

def scrape_occupational_groups(url: str, lang: str = "en") -> list[OccupationalGroupRow]:
    """Scrape TBS occupational groups table."""
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "lxml")
    table = soup.find("table")

    if not table:
        raise ValueError(f"No table found at {url} - page structure may have changed")

    rows = []
    for tr in table.find_all("tr")[1:]:  # Skip header
        cells = tr.find_all("td")
        if len(cells) < 2:
            continue

        code_cell = cells[0]
        name_cell = cells[1]

        # Extract links if present
        def_link = cells[5].find("a") if len(cells) > 5 else None
        eval_link = cells[6].find("a") if len(cells) > 6 else None

        rows.append(OccupationalGroupRow(
            group_code=code_cell.text.strip(),
            group_name=name_cell.text.strip(),
            definition_url=def_link["href"] if def_link else None,
            evaluation_standard_url=eval_link["href"] if eval_link else None,
            source_url=url,
        ))

    return rows
```

### NOC-SOC Crosswalk Loading
```python
# Source: Brookfield NOC_ONet_Crosswalk repository
import polars as pl
from pathlib import Path

class NOCSOCCrosswalk:
    """NOC 2021 to O*NET 26 crosswalk."""

    def __init__(self, crosswalk_path: Path):
        self.df = pl.read_csv(crosswalk_path)
        # Build lookup indexes
        self._noc_to_soc = (
            self.df.group_by("noc")
            .agg(pl.col("onet").alias("soc_codes"))
            .to_dicts()
        )
        self._noc_lookup = {r["noc"]: r["soc_codes"] for r in self._noc_to_soc}

    def noc_to_soc(self, noc_code: str) -> list[str]:
        """Get O*NET SOC codes for a NOC code."""
        return self._noc_lookup.get(noc_code, [])

    def has_mapping(self, noc_code: str) -> bool:
        """Check if NOC code has O*NET mapping."""
        return noc_code in self._noc_lookup
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| JSON Mode (guarantees valid JSON only) | Structured Outputs (guarantees schema adherence) | Aug 2024 | 100% reliability vs ~40% for schema following |
| requests (sync only) | httpx (sync + async) | 2020+ | Better performance for API calls |
| Manual NOC-SOC mapping | Brookfield crosswalk | 2024 | 1,468 validated mappings available |
| O*NET API v1.9 | O*NET API v2.0 | 2023 | New endpoints, improved data |
| O*NET 25.x | O*NET 29.3 | Dec 2024 | Latest occupation data |

**Deprecated/outdated:**
- `response_format={"type": "json_object"}`: Use `json_schema` with `strict: true` instead
- O*NET API v1.9: Migrate to v2.0 for latest features
- NOC 2016 crosswalks: Use NOC 2021 version for current data

## Open Questions

Things that couldn't be fully resolved:

1. **O*NET API Rate Limits**
   - What we know: Registration required, rate limits exist
   - What's unclear: Exact thresholds (requests/minute)
   - Recommendation: Implement exponential backoff; consider bulk download for initial load

2. **TBS Page Update Frequency**
   - What we know: Monthly scrape per CONTEXT.md; page updated 2023-11-07
   - What's unclear: How often TBS updates content
   - Recommendation: Implement page hash comparison to detect changes

3. **O*NET Confidence Mapping to WiQ**
   - What we know: O*NET uses 0-100 importance scale
   - What's unclear: How to map to WiQ 0-1 confidence scale
   - Recommendation: Use mapping_strength (1.0 for exact NOC-SOC match, lower for fuzzy)

## Sources

### Primary (HIGH confidence)
- [O*NET Web Services Reference Manual](https://services.onetcenter.org/reference/) - API endpoints, authentication
- [O*NET Resource Center Database](https://www.onetcenter.org/database.html) - Bulk download, CC-BY-4.0 license
- [Brookfield NOC-O*NET Crosswalk](https://github.com/BrookfieldIIE/NOC_ONet_Crosswalk) - noc2021_onet26.csv
- [OpenAI Structured Outputs Guide](https://platform.openai.com/docs/guides/structured-outputs) - Pydantic integration
- [OpenAI Cookbook Structured Outputs](https://cookbook.openai.com/examples/structured_outputs_intro) - Code examples
- [TBS Occupational Groups Page](https://www.canada.ca/en/treasury-board-secretariat/services/collective-agreements/occupational-groups.html) - Source page

### Secondary (MEDIUM confidence)
- [HTTPX Documentation](https://www.python-httpx.org/) - Async client patterns
- [BeautifulSoup Documentation](https://beautiful-soup-4.readthedocs.io/) - HTML parsing
- [Statistics Canada NOC-SOC Correspondence](https://www.statcan.gc.ca/en/statistical-programs/document/reference-note/noc2016v1_3-soc2018US) - Official crosswalk methodology
- [The Dais NOC-O*NET Crosswalk Blog](https://brookfieldinstitute.ca/crosswalk-blog-post) - Crosswalk methodology

### Tertiary (LOW confidence)
- O*NET rate limits: Not documented; inferred from community reports
- TBS page structure stability: Based on current observation only

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Documented libraries with clear APIs
- Architecture: HIGH - Based on existing project patterns and official docs
- O*NET integration: MEDIUM - API documented but rate limits unclear
- LLM imputation: HIGH - OpenAI Structured Outputs well-documented
- TBS scraping: MEDIUM - Page structure may change without notice
- NOC-SOC crosswalk: HIGH - MIT-licensed, validated methodology

**Research date:** 2026-01-19
**Valid until:** 2026-02-19 (30 days for stable libraries, TBS page may change)
