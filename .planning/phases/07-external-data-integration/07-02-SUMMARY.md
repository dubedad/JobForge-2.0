---
phase: "07"
plan: "02"
subsystem: external-data
tags: ["llm", "openai", "imputation", "provenance", "gpt-4o"]
dependency-graph:
  requires: ["07-01"]
  provides: ["LLM imputation service", "structured outputs", "attribute provenance"]
  affects: ["08-*"]
tech-stack:
  added: ["openai>=1.52.0"]
  patterns: ["Structured Outputs", "Pydantic response models", "Service pattern"]
key-files:
  created:
    - src/jobforge/external/llm/__init__.py
    - src/jobforge/external/llm/client.py
    - src/jobforge/external/llm/prompts.py
    - src/jobforge/external/llm/service.py
    - tests/test_llm_imputation.py
  modified:
    - src/jobforge/external/models.py
    - src/jobforge/external/__init__.py
    - pyproject.toml
decisions:
  - id: "07-02-D1"
    decision: "Accept ALL LLM responses regardless of confidence"
    rationale: "Per CONTEXT.md - store confidence+rationale for downstream filtering rather than rejecting at imputation time"
  - id: "07-02-D2"
    decision: "Use gpt-4o-2024-08-06 model"
    rationale: "Supports Structured Outputs for guaranteed schema compliance"
metrics:
  duration: "~12 min"
  completed: "2026-01-20"
---

# Phase 7 Plan 2: LLM Imputation Summary

**One-liner:** OpenAI Structured Outputs integration with GPT-4o for imputing missing attributes, storing confidence+rationale for downstream filtering per CONTEXT.md.

## What Was Built

### LLM Package Structure
Created `jobforge.external.llm` package providing:
- **LLMClient**: OpenAI wrapper with `parse()` method for Structured Outputs
- **AttributeImputationService**: Orchestrates imputation with job context
- **Prompt templates**: System prompt and user prompt builder

### Pydantic Models
- **ImputedAttributeValue**: Single imputed attribute with confidence and rationale
- **ImputationResponse**: Structured Outputs response format for batch imputation
- **LLMImputedAttribute**: Extended model with source_type='LLM', model_used, imputed_at

### Key Capabilities
1. **Structured Outputs**: Type-safe LLM responses via `client.parse(response_format=ImputationResponse)`
2. **Context-aware prompts**: Include job title, family, function, unit group, and known attributes
3. **Full provenance**: Every imputed value carries source_type='LLM', model_used, timestamp
4. **No confidence filtering**: Accepts all answers per CONTEXT.md for downstream filtering

## Technical Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| 07-02-D1 | Accept ALL LLM responses regardless of confidence | Per CONTEXT.md - store for downstream filtering |
| 07-02-D2 | Use gpt-4o-2024-08-06 model | Structured Outputs support for guaranteed schema compliance |
| 07-02-D3 | LLM_SOURCE_PRECEDENCE = 1 | Lowest precedence in hierarchy (LLM < O*NET < Authoritative) |

## Commits

| Hash | Type | Description |
|------|------|-------------|
| c1a5295 | feat | Add LLM client and response models |
| 79dcfb4 | test | Add LLM imputation tests (26 tests) |

## Test Coverage

**26 tests added** (all passing):
- 5 prompt building tests (minimal, full context, known attrs, empty)
- 2 system prompt tests (existence, content)
- 5 client tests (model, availability, custom model, parse requires key)
- 8 service tests (empty input, single/multiple attrs, provenance, low confidence, rationale, timestamp)
- 1 convenience function test
- 4 response model tests (parsing, confidence bounds, timestamp, serialization)
- 1 source precedence test

## Deviations from Plan

None - plan executed exactly as written.

## Files Created/Modified

### Created
```
src/jobforge/external/llm/__init__.py    # Package exports
src/jobforge/external/llm/client.py      # LLMClient with Structured Outputs
src/jobforge/external/llm/prompts.py     # IMPUTATION_SYSTEM_PROMPT, build_imputation_prompt
src/jobforge/external/llm/service.py     # AttributeImputationService, impute_missing_attributes
tests/test_llm_imputation.py             # 26 tests for LLM imputation
```

### Modified
```
src/jobforge/external/models.py          # Added ImputedAttributeValue, ImputationResponse, LLMImputedAttribute
src/jobforge/external/__init__.py        # Export new LLM models
pyproject.toml                           # Added openai>=1.52.0
```

## API Usage Example

```python
from jobforge.external.llm import AttributeImputationService

service = AttributeImputationService()
results = service.impute_attributes(
    job_title="Data Analyst",
    missing_attributes=["leadership", "communication"],
    job_family="Analytics",
    job_function="Business Intelligence",
    unit_group="21211",
    known_attributes={"skill1": "Python", "skill2": "SQL"},
)

for attr in results:
    print(f"{attr.attribute_name}: {attr.value}")
    print(f"  Confidence: {attr.confidence}")
    print(f"  Rationale: {attr.rationale}")
    print(f"  Source: {attr.source_type}, Model: {attr.model_used}")
```

## Verification Results

| Check | Result |
|-------|--------|
| Package structure imports | PASS |
| Response models import | PASS |
| Prompt building includes all context | PASS |
| pytest tests/test_llm_imputation.py | 26 passed |
| pytest (full suite) | 225 passed, 3 skipped |

## Success Criteria Checklist

- [x] LLMClient uses OpenAI Structured Outputs with gpt-4o-2024-08-06
- [x] AttributeImputationService accepts ALL responses regardless of confidence
- [x] Every imputed value has confidence + rationale stored
- [x] source_type='LLM' set on all imputed attributes
- [x] model_used and imputed_at timestamp tracked
- [x] Tests pass without requiring real API key (mocked)

## Next Phase Readiness

**Ready for Phase 8 (Gold Layer V2):**
- LLM imputation completes the external data cascade: Hierarchical -> O*NET -> LLM
- All sources have consistent provenance tracking
- SourcePrecedence enum enables conflict resolution

**API Key Setup Required:**
To use LLM imputation, set environment variable:
```bash
export OPENAI_API_KEY="your-key-here"
# Get key from: https://platform.openai.com/api-keys
```

---
*Plan completed: 2026-01-20*
*Duration: ~12 minutes*
*Tests: 26 new (225 total passing)*
