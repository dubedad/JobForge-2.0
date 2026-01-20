# Phase 8: Description Generation - Research

**Researched:** 2026-01-19
**Domain:** Text generation, hierarchical data retrieval, provenance tracking
**Confidence:** HIGH

## Summary

Phase 8 implements description generation for job architecture entities (titles, families, functions) using a source cascade: authoritative NOC lead statements first, then O*NET fallback, then LLM synthesis. The existing codebase provides substantial infrastructure that can be reused and extended.

The research found that:
1. **NOC lead statements already exist** in `element_lead_statement` table at L6 level (900 rows) with full text descriptions
2. **Resolution infrastructure is ready** - the `jobforge.imputation.resolution` module provides semantic matching through L5/L6/L7 hierarchy
3. **LLM client is operational** - `jobforge.external.llm` package handles Structured Outputs with provenance
4. **O*NET adapter is available** - `jobforge.external.onet` package handles crosswalk lookup and attribute fetching

**Primary recommendation:** Build a new `DescriptionGenerationService` that orchestrates the source cascade, reusing existing resolution and LLM infrastructure while adding description-specific prompting.

## Standard Stack

The established libraries/tools for this domain:

### Core (Already in Codebase)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| openai | >=1.52.0 | LLM API client with Structured Outputs | Already integrated in `jobforge.external.llm` |
| pydantic | 2.x | Response model schemas | Already used for `ImputationResponse` |
| polars | latest | DataFrame operations for batch processing | Project standard |

### Supporting (Already in Codebase)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| rapidfuzz | latest | Fuzzy string matching | Already in resolution module |
| structlog | latest | Structured logging | Already project-wide |

### No New Dependencies Required
This phase can be implemented entirely with existing dependencies. The description generation service builds on the same patterns as attribute imputation.

## Architecture Patterns

### Recommended Project Structure
```
src/jobforge/
├── description/                    # NEW package for description generation
│   ├── __init__.py                # Export service, models, helpers
│   ├── service.py                 # DescriptionGenerationService
│   ├── models.py                  # Description-specific Pydantic models
│   ├── prompts.py                 # System/user prompts for LLM descriptions
│   └── sources.py                 # Source cascade logic (authoritative/O*NET/LLM)
└── external/
    └── llm/                       # Existing - reuse LLMClient
```

### Pattern 1: Source Cascade
**What:** Three-tier description source with fallback chain
**When to use:** When generating any description (title, family, function)
**Example:**
```python
# Per CONTEXT.md decisions - source cascade order
class DescriptionSource(str, Enum):
    AUTHORITATIVE = "authoritative"  # NOC lead statement
    ONET = "onet"                     # O*NET occupation description
    LLM = "llm"                       # GPT-synthesized

def get_description(entity_type: str, entity_id: str) -> GeneratedDescription:
    """
    Cascade:
    1. Check for authoritative (NOC lead statement match)
    2. If no match, query O*NET (informed by NOC boundary words)
    3. If no O*NET, synthesize with LLM (prompted with NOC context)
    """
```

### Pattern 2: Resolution-Based Description Lookup
**What:** Reuse existing NOC resolution to find matching lead statements
**When to use:** For job title descriptions (L7 entities)
**Example:**
```python
# Leverage existing resolution.py module
from jobforge.imputation.resolution import resolve_job_title, build_resolution_context

def get_lead_statement_for_title(
    job_title: str,
    unit_group_id: str,
) -> tuple[str | None, DescriptionProvenance]:
    """
    Per CONTEXT.md:
    - L6 match: use L6 lead statement directly
    - L7 fallback: check L7 example titles for semantic match
    - L7 inheritance: if L7 match, inherit parent L6 lead statement
    """
    resolution = resolve_job_title(job_title, unit_group_id)
    if resolution:
        # Fetch lead statement for resolved OASIS code
        lead_statement = load_lead_statement(resolution.source_identifier)
        return lead_statement, DescriptionProvenance(
            source=DescriptionSource.AUTHORITATIVE,
            confidence=resolution.confidence_score,
            resolution_method=resolution.resolution_method,
        )
    return None, None
```

### Pattern 3: Provenance Tracking Model
**What:** Extended provenance for descriptions with full lineage
**When to use:** Every description must have provenance
**Example:**
```python
# Per CONTEXT.md: Full lineage for every description
class DescriptionProvenance(BaseModel):
    source_type: DescriptionSource  # authoritative/onet/llm
    confidence: float               # 0.0-1.0
    timestamp: datetime
    model_version: str | None       # For LLM (e.g., "gpt-4o-2024-08-06")
    input_context: str | None       # Boundary words/prompts used
    resolution_method: str | None   # How entity was resolved

class GeneratedDescription(BaseModel):
    entity_type: Literal["title", "family", "function"]
    entity_id: str
    description: str
    provenance: DescriptionProvenance
```

### Pattern 4: NOC Boundary Words Context
**What:** Use NOC vocabulary as semantic anchors for all non-authoritative descriptions
**When to use:** When calling O*NET or LLM
**Example:**
```python
# Per CONTEXT.md: NOC as "boundary words"
def build_boundary_context(unit_group_id: str) -> str:
    """Build NOC context to constrain O*NET/LLM responses."""
    context = build_resolution_context(unit_group_id)
    return f"""
NOC Unit Group: {context.unit_group_title}
Definition: {context.unit_group_definition}
Labels: {', '.join(l.label for l in context.labels)}
"""
```

### Anti-Patterns to Avoid
- **Skipping resolution:** Don't generate LLM descriptions without first checking authoritative sources
- **Missing provenance:** Never return a description without full lineage tracking
- **Ignoring unmapped titles:** Per CONTEXT.md, titles with no NOC mapping still get LLM descriptions (marked low-authority)
- **Style inconsistency:** LLM descriptions must match NOC formal voice - "Software engineers design..." not "This role involves..."

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Job title resolution | Custom matching logic | `resolve_job_title()` from resolution.py | Handles L5/L6/L7 cascade, fuzzy matching, confidence scoring |
| LLM API calls | Raw HTTP/REST calls | `LLMClient.parse()` from llm/client.py | Structured Outputs, error handling, model configuration |
| Provenance columns | Ad-hoc column naming | `ImputationProvenanceColumns` class | Consistent naming, tested patterns |
| NOC hierarchy lookup | Manual parquet queries | `build_resolution_context()` | Cached indexes, proper data structures |
| Fuzzy matching | Custom string comparison | `rapidfuzz.fuzz.WRatio()` | Already tuned threshold (70) in resolution.py |

**Key insight:** The Phase 7 infrastructure provides 80% of what's needed. Description generation is primarily about:
1. Adding description-specific prompts
2. Creating a new source cascade orchestrator
3. Extending provenance to include description-specific fields

## Common Pitfalls

### Pitfall 1: Confusing Lead Statement Sources
**What goes wrong:** Lead statements exist in both `element_lead_statement` (at OASIS profile level) and `dim_noc.class_definition` (at unit group level). Using wrong source leads to incorrect mappings.
**Why it happens:** The tables have similar content but different granularity.
**How to avoid:** Use `element_lead_statement` joined via `oasis_profile_code` for L6-level descriptions. Use `dim_noc.class_definition` only for L5 fallback.
**Warning signs:** Descriptions don't match expected label-level specificity.

### Pitfall 2: Missing NOC Context in LLM Prompts
**What goes wrong:** LLM generates generic descriptions that don't align with NOC vocabulary.
**Why it happens:** Not providing NOC "boundary words" in the prompt.
**How to avoid:** Always include unit group title, definition, and relevant labels as context when calling LLM.
**Warning signs:** Generated descriptions use terminology not found in NOC universe.

### Pitfall 3: Batch vs Single-Item Confidence
**What goes wrong:** Using batch default confidence (0.85) for individual resolutions.
**Why it happens:** Convenience vs accuracy tradeoff.
**How to avoid:** For description generation, use `resolve_job_title()` to get per-title confidence. Batch mode is for attribute inheritance, not descriptions.
**Warning signs:** All descriptions have same confidence regardless of resolution method.

### Pitfall 4: Family/Function Level Descriptions
**What goes wrong:** Treating families (L5) and functions (L4) like job titles (L7).
**Why it happens:** Different resolution paths needed.
**How to avoid:**
- Families (L6 level per context): Aggregate lead statements from member labels
- Functions (L5 level per context): Use unit group definition directly
**Warning signs:** Family descriptions are too specific; function descriptions are too generic.

### Pitfall 5: Style Mismatch in LLM Descriptions
**What goes wrong:** LLM generates casual descriptions that don't match NOC voice.
**Why it happens:** System prompt doesn't specify tone.
**How to avoid:** Per CONTEXT.md: "Formal, third-person, occupational classification voice"
**Warning signs:** Descriptions use "you", "this role", personal pronouns.

## Code Examples

Verified patterns from existing codebase:

### Loading Lead Statements (from element_lead_statement)
```python
# Source: Verified from data/catalog/tables/element_lead_statement.json
import polars as pl

def load_lead_statements(gold_path: Path) -> dict[str, str]:
    """Load lead statements indexed by oasis_profile_code."""
    df = pl.scan_parquet(gold_path / "element_lead_statement.parquet").collect()
    return {
        row["oasis_profile_code"]: row["Lead statement"]
        for row in df.iter_rows(named=True)
    }
```

### Reusing Resolution Infrastructure
```python
# Source: jobforge/imputation/resolution.py (verified)
from jobforge.imputation.resolution import (
    resolve_job_title,
    build_resolution_context,
    ResolutionContext,
    CONFIDENCE_DIRECT_MATCH,      # 1.00
    CONFIDENCE_EXAMPLE_MATCH,     # 0.95
    CONFIDENCE_UG_DOMINANT,       # 0.85
    CONFIDENCE_LABEL_IMPUTATION,  # 0.60
    CONFIDENCE_UG_IMPUTATION,     # 0.40
)
```

### LLM Description Generation Prompt
```python
# Based on existing prompts.py pattern
DESCRIPTION_SYSTEM_PROMPT = """You are generating occupational descriptions for a Canadian workforce classification system.

Guidelines:
- Use formal, third-person voice matching NOC style
- Start descriptions with the occupation name (e.g., "Software engineers design...")
- Focus on typical duties and responsibilities
- Keep descriptions between 2-4 sentences
- Use NOC-aligned terminology provided in the context

Your descriptions will supplement authoritative Canadian occupational data."""

def build_description_prompt(
    entity_name: str,
    entity_type: str,
    noc_context: str,
) -> str:
    return f"""
Entity to describe: {entity_name}
Entity type: {entity_type}

NOC Context (use as semantic boundaries):
{noc_context}

Generate a description in NOC style. Include:
- Primary function/purpose
- Typical duties or characteristics
- Where this entity fits in the occupational hierarchy
"""
```

### Description Response Model
```python
# Based on existing ImputationResponse pattern
from pydantic import BaseModel, Field

class DescriptionResponse(BaseModel):
    """LLM response for description generation."""
    description: str = Field(
        description="Generated occupational description in NOC style"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="LLM's confidence in this description (0.0-1.0)"
    )
    context_used: str = Field(
        description="Summary of NOC context that influenced the description"
    )
```

### Provenance Model Extension
```python
# Extending existing provenance pattern
from jobforge.external.models import SourcePrecedence

class DescriptionProvenance(BaseModel):
    """Full lineage for a generated description."""
    source_type: Literal["AUTHORITATIVE", "ONET", "LLM"]
    confidence: float
    timestamp: datetime
    # LLM-specific fields (None for authoritative)
    model_version: str | None = None
    input_context: str | None = None
    # Resolution-specific fields
    resolution_method: str | None = None
    matched_text: str | None = None

    @property
    def precedence(self) -> int:
        """Get source precedence for conflict resolution."""
        return {
            "AUTHORITATIVE": SourcePrecedence.AUTHORITATIVE,
            "ONET": SourcePrecedence.ONET,
            "LLM": SourcePrecedence.LLM,
        }[self.source_type]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual description writing | LLM generation with Structured Outputs | Phase 7 | Guaranteed schema compliance |
| Single description source | Source cascade with provenance | This phase | Traceability and authority hierarchy |
| Generic LLM prompts | NOC-constrained boundary words | This phase | Semantic consistency |

**Deprecated/outdated:**
- None - this is new functionality building on Phase 7 infrastructure

## Open Questions

Things that couldn't be fully resolved:

1. **Family/Function Level Definition**
   - What we know: CONTEXT.md says families at L6, functions at L5
   - What's unclear: How to aggregate descriptions for families with multiple labels
   - Recommendation: For families, concatenate lead statements or use longest/most representative. Mark as Claude's discretion per CONTEXT.md.

2. **Low-Confidence Threshold**
   - What we know: CONTEXT.md says "Threshold for 'low-confidence' to be determined during implementation"
   - What's unclear: Exact numeric cutoff
   - Recommendation: Use 0.5 (below O*NET default confidence) as initial threshold. Titles with resolution < 0.5 or LLM confidence < 0.5 flagged for review.

3. **Multiple Descriptions Storage**
   - What we know: CONTEXT.md marks "Multiple descriptions per entity vs single best" as Claude's discretion
   - What's unclear: User preference
   - Recommendation: Store all generated descriptions with provenance. Expose "best" via property that returns highest-precedence source.

## Sources

### Primary (HIGH confidence)
- `jobforge.imputation.resolution` module - NOC resolution algorithm, confidence scoring
- `jobforge.external.llm` package - LLM client, prompts, service patterns
- `jobforge.imputation.provenance` module - Provenance column patterns
- `data/catalog/tables/element_lead_statement.json` - Lead statement schema (900 rows, L6 level)
- `data/catalog/tables/job_architecture.json` - Job architecture schema (1987 rows)

### Secondary (MEDIUM confidence)
- CONTEXT.md decisions - Source cascade, NOC boundary words, tone requirements

### Tertiary (LOW confidence)
- None - all claims verified against codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in codebase, patterns verified
- Architecture: HIGH - Extends existing proven patterns from Phase 7
- Pitfalls: HIGH - Based on actual table structures and code analysis

**Research date:** 2026-01-19
**Valid until:** 2026-02-19 (30 days - stable patterns, no external dependencies changing)
