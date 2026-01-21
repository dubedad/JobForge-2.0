# Extending Intent Patterns

Step-by-step tutorial for adding new query patterns to the JobForge + Orbit integration.

## Understanding Intent Classification

When a user asks a question, JobForge needs to determine where to route it. This process is called **intent classification**.

### How It Works

1. **Pattern Matching (Primary):** Check if the question matches known patterns in configuration files
2. **LLM Fallback (Secondary):** If patterns are inconclusive, use Claude for classification
3. **Route to Endpoint:** Send question to appropriate API endpoint based on intent

### Intent Categories

JobForge supports three intent categories:

| Intent Category | Routes To | Purpose | Requires API Key |
|----------------|-----------|---------|------------------|
| `data_query` | POST /api/query/data | SQL queries against gold tables | Yes (ANTHROPIC_API_KEY) |
| `metadata_query` | POST /api/query/metadata | Lineage and provenance questions | No |
| `compliance_query` | GET /api/compliance/{framework} | Governance compliance reports | No |

### Configuration Files

Intent routing is controlled by two YAML files:

**1. orbit/config/adapters/jobforge.yaml**
- Endpoint routing (which URL for each intent)
- HTTP configuration (timeout, headers)
- Pattern lists for fast matching
- Example questions for testing

**2. orbit/config/intents/wiq_intents.yaml**
- Domain vocabulary (NOC, TEER, COPS terms)
- Entity patterns (regex for NOC codes, TEER levels)
- Sample questions by domain category
- Fallback behavior when classification is ambiguous

## Step-by-Step: Adding a New Query Pattern

Let's walk through a real example of extending JobForge to handle a new type of question.

### Scenario

You want to add support for certification questions like:
- "What certifications are needed for nurses?"
- "List licenses required for 21232"
- "Show credential requirements for software developers"

### Step 1: Identify the Endpoint

First, determine which endpoint should handle this question.

**Ask yourself:** What does this question need?
- Does it query **data** from tables? → `data_query`
- Does it ask about **lineage or structure**? → `metadata_query`
- Does it ask about **governance compliance**? → `compliance_query`

**For certification questions:**
- This queries attribute data from tables (likely `element_employment_requirements`)
- Answer: Route to `data_query` → POST /api/query/data

### Step 2: Add Pattern to jobforge.yaml

Edit `orbit/config/adapters/jobforge.yaml` to include new pattern keywords.

**Before:**
```yaml
intents:
  - name: data_query
    description: "Questions about WiQ data (counts, aggregations, lookups)"
    endpoint: data
    patterns:
      - "how many"
      - "count of"
      - "list all"
      - "what is the"
      - "show me"
      - "find"
      - "total"
      - "average"
      - "sum"
      - "group by"
```

**After (add certification patterns):**
```yaml
intents:
  - name: data_query
    description: "Questions about WiQ data (counts, aggregations, lookups)"
    endpoint: data
    patterns:
      - "how many"
      - "count of"
      - "list all"
      - "what is the"
      - "show me"
      - "find"
      - "total"
      - "average"
      - "sum"
      - "group by"
      - "certifications"          # NEW
      - "what certifications"     # NEW
      - "licenses"                # NEW
      - "credentials"             # NEW
      - "requirements"            # NEW (careful: might overlap with metadata)
```

**Pattern Guidelines:**
- Use lowercase (matching is case-insensitive)
- Be specific enough to avoid false matches
- Order matters: more specific patterns should come first
- Consider partial phrases ("what certifications" catches "what certifications are needed")

### Step 3: Add Domain Vocabulary to wiq_intents.yaml

Edit `orbit/config/intents/wiq_intents.yaml` to help the LLM understand certification vocabulary.

**Before:**
```yaml
intent_categories:
  attribute_queries:
    description: "Questions about occupational attributes (skills, abilities, knowledge)"
    keywords:
      - skill
      - ability
      - knowledge
      - work activity
      - work context
      - OASIS
      - competency
      - requirement
    sample_questions:
      - "What skills are needed for 21232?"
      - "List abilities for software developers"
      - "What work activities are common in TEER 1?"
      - "Show knowledge requirements for data analysts"
      - "What work context attributes apply to nurses?"
```

**After (add certification vocabulary):**
```yaml
intent_categories:
  attribute_queries:
    description: "Questions about occupational attributes (skills, abilities, knowledge)"
    keywords:
      - skill
      - ability
      - knowledge
      - work activity
      - work context
      - OASIS
      - competency
      - requirement
      - certification         # NEW
      - credential            # NEW
      - license               # NEW
      - registration          # NEW
      - professional designation  # NEW
    sample_questions:
      - "What skills are needed for 21232?"
      - "List abilities for software developers"
      - "What work activities are common in TEER 1?"
      - "Show knowledge requirements for data analysts"
      - "What work context attributes apply to nurses?"
      - "What certifications are needed for nurses?"              # NEW
      - "List licenses required for software developers"          # NEW
      - "Show credential requirements for data analysts"          # NEW
```

**Why add this:**
- When pattern matching fails, LLM uses these keywords for classification
- Sample questions train the LLM on expected phrasing
- Keywords help with semantic similarity matching

### Step 4: Test the New Pattern

Restart the Docker stack to load new configuration:

```bash
docker compose down
docker compose up -d
```

Wait for services to be healthy:

```bash
docker compose ps
```

Test the new pattern:

```bash
curl -X POST http://localhost:8000/api/query/data \
  -H "Content-Type: application/json" \
  -d '{"question": "What certifications are needed for nurses?"}'
```

**Expected behavior:**
1. Pattern matching sees "certifications" keyword
2. Routes to `data_query` intent
3. Calls POST /api/query/data
4. Claude generates SQL querying `element_employment_requirements`
5. Returns results with certification information

**Debugging:**
- Check Docker logs: `docker compose logs -f api`
- Verify pattern matched (look for "Matched intent: data_query")
- If routed to wrong endpoint, pattern may be too generic

### Step 5: Refine Pattern Specificity

If your pattern is causing false positives (wrong routing), make it more specific.

**Problem:** "requirements" matches both data queries and metadata queries.

**Solution:** Use multi-word patterns or add confidence scoring.

**Refined pattern:**
```yaml
patterns:
  - "certification requirements"    # More specific
  - "license requirements"          # More specific
  - "credential requirements"       # More specific
  - "employment requirements"       # Specific to NOC element data
```

**Avoid:**
```yaml
patterns:
  - "requirements"    # TOO GENERIC - matches everything
```

## Adding a New Entity Type

Entities are structured patterns that help classify questions more accurately.

### When to Add Entities

Add an entity when you have:
- A well-defined pattern (e.g., NOC codes are 4-5 digits)
- Multiple questions referring to the same concept
- Need for validation (e.g., TEER levels are only 0-5)

### Example: Adding Certification Type Entity

**Edit orbit/config/intents/wiq_intents.yaml:**

```yaml
entities:
  noc_code:
    description: "National Occupational Classification code (4-5 digits)"
    patterns:
      - "\\b\\d{4,5}\\b"
    examples:
      - "21232"
      - "2123"
      - "21"

  teer_level:
    description: "Training, Education, Experience, Responsibilities level (0-5)"
    patterns:
      - "TEER\\s*[0-5]"
      - "tier\\s*[0-5]"
    examples:
      - "TEER 1"
      - "TEER 0"
      - "tier 2"

  # NEW: Certification type entity
  certification_type:
    description: "Professional certifications and licenses"
    patterns:
      - "\\b[A-Z]{2,6}\\b"           # Matches: RN, P.Eng, CPA, CFA
      - "professional\\s+\\w+"       # Matches: professional engineer
      - "certified\\s+\\w+"          # Matches: certified accountant
    examples:
      - "RN"
      - "P.Eng"
      - "CPA"
      - "professional engineer"
      - "certified public accountant"
```

**How entities are used:**
- Pattern matching extracts entities from questions
- Entities are passed to endpoint for query context
- Helps Claude understand what user is asking about

**Regex tips:**
- `\\b` = word boundary (prevents matching inside words)
- `\\s*` = zero or more spaces
- `[0-5]` = character class (matches any digit 0-5)
- `\\w+` = one or more word characters
- Test regex at https://regex101.com

## Testing Intent Classification

### Manual Testing

```bash
# Test data query pattern
curl -X POST http://localhost:8000/api/query/data \
  -H "Content-Type: application/json" \
  -d '{"question": "How many software developers?"}'

# Test metadata query pattern
curl -X POST http://localhost:8000/api/query/metadata \
  -H "Content-Type: application/json" \
  -d '{"question": "Where does dim_noc come from?"}'

# Test compliance query pattern
curl http://localhost:8000/api/compliance/dadm
```

### Verifying Pattern Matching

Check API logs to see which pattern matched:

```bash
docker compose logs -f api | grep "intent"
```

Look for log lines like:
```
INFO intent_classifier: Matched intent=data_query confidence=0.95 pattern="certifications"
```

### Common Mistakes

**1. Overlapping Patterns**

**Problem:**
```yaml
# metadata_query patterns
patterns:
  - "table"
  - "what tables"

# data_query patterns
patterns:
  - "how many tables"    # CONFLICT: "tables" matches metadata first
```

**Solution:** Put more specific patterns first or use confidence scoring.

**2. Too Generic Patterns**

**Problem:**
```yaml
patterns:
  - "what"    # Matches almost every question
  - "show"    # Too broad
```

**Solution:** Use multi-word phrases:
```yaml
patterns:
  - "what is the"
  - "show me the"
```

**3. Case-Sensitive Matching**

**Problem:** Pattern `"NOC"` won't match `"noc"` or `"Noc"`.

**Solution:** Pattern matching is case-insensitive by default. Use lowercase in config.

### LLM Fallback Testing

To test LLM fallback behavior, ask a question with no matching patterns:

```bash
curl -X POST http://localhost:8000/api/query/data \
  -H "Content-Type: application/json" \
  -d '{"question": "I need to know about programmer jobs in the future"}'
```

**Expected flow:**
1. No pattern matches
2. Falls back to LLM classification
3. LLM sees "programmer" (occupation), "future" (forecast) → `data_query`
4. Routes to POST /api/query/data

**Check logs:**
```
INFO intent_classifier: No pattern match, using LLM fallback
INFO intent_classifier: LLM classified as data_query confidence=0.88
```

## Configuration File Reference

### jobforge.yaml Structure

```yaml
name: jobforge-wiq
description: "Workforce Intelligence Query interface"
enabled: true
type: http

http:
  base_url: "http://localhost:8000"
  timeout: 30
  endpoints:
    data:                           # Endpoint ID (referenced by intents)
      path: "/api/query/data"       # API path
      method: POST                  # HTTP method
      headers:
        Content-Type: "application/json"
      body:
        question: "{{query}}"       # Template: {{query}} replaced with user question

intents:
  - name: data_query                # Intent name
    description: "..."              # Human-readable description
    endpoint: data                  # Maps to endpoint ID above
    patterns:                       # Keyword patterns for matching
      - "how many"
      - "count of"
    examples:                       # Sample questions for testing
      - "How many software developers?"

llm:
  provider: anthropic               # LLM provider for fallback
  model: claude-sonnet-4-20250514   # Model version
  temperature: 0                    # Deterministic output
  max_tokens: 256                   # Short classification responses
```

**File location:** `orbit/config/adapters/jobforge.yaml`

### wiq_intents.yaml Structure

```yaml
domain: workforce_intelligence
description: "Canadian Occupational Classification and Workforce Projections"
version: "1.0"

entities:                           # Structured patterns
  noc_code:
    description: "..."              # What this entity represents
    patterns:                       # Regex patterns to match
      - "\\b\\d{4,5}\\b"
    examples:                       # Example matches
      - "21232"

intent_categories:                  # Domain vocabulary
  occupation_queries:
    description: "..."              # Category description
    keywords:                       # Terms that indicate this category
      - NOC
      - occupation
    sample_questions:               # Training examples for LLM
      - "What occupations are in broad category 2?"

fallback:
  strategy: "metadata_first"        # When ambiguous, prefer metadata query
  description: "..."                # Why this strategy
  clarification_prompt: |           # Optional: ask user to clarify
    I'm not sure if you're asking about the data itself or about the data's structure/lineage.
```

**File location:** `orbit/config/intents/wiq_intents.yaml`

## Advanced: Confidence Scoring

For complex scenarios where patterns overlap, implement confidence scoring.

### Pattern Specificity Rules

More specific patterns get higher confidence:

```yaml
intents:
  - name: metadata_query
    patterns:
      - name: "table_count"
        pattern: "how many tables"
        confidence: 0.95          # Very specific
      - name: "table_mention"
        pattern: "table"
        confidence: 0.60          # Generic

  - name: data_query
    patterns:
      - name: "count_query"
        pattern: "how many"
        confidence: 0.70          # Moderately specific
```

**Classification logic:**
1. Check all patterns
2. Select highest confidence match
3. If confidence < threshold (e.g., 0.80), use LLM fallback

**Note:** This is advanced configuration. Start with simple pattern lists first.

## Best Practices

### Pattern Design

1. **Start broad, then refine:** Add generic patterns first, then make specific based on testing
2. **Use multi-word phrases:** "what certifications" is better than "certifications"
3. **Test edge cases:** Try variations (plural/singular, different phrasings)
4. **Monitor false positives:** Check logs for misrouted questions

### Domain Vocabulary

1. **Keep keywords updated:** Add new terms as they emerge in user questions
2. **Provide diverse examples:** Cover different phrasings of the same question
3. **Align with data:** Keywords should reflect actual table/column names
4. **Document decisions:** Comment why you added specific patterns

### Testing Strategy

1. **Test locally first:** Use Docker Compose stack for rapid iteration
2. **Check both match and fallback:** Ensure LLM fallback works when patterns fail
3. **Monitor production usage:** Log questions that triggered fallback
4. **Iterate based on data:** Add patterns for commonly asked questions

### Version Control

1. **Commit config changes:** Track intent configuration in git
2. **Document changes:** Note why you added patterns (in commit message or comments)
3. **Test before deploying:** Verify patterns don't break existing queries
4. **Use feature branches:** Test major changes in isolation

## Examples: Real-World Extensions

### Example 1: Adding Geographic Queries

**User request:** "I want to ask about occupations by province"

**Step 1 - Identify endpoint:** Geographic data is in tables → `data_query`

**Step 2 - Add patterns to jobforge.yaml:**
```yaml
patterns:
  - "by province"
  - "by region"
  - "in Ontario"
  - "in Quebec"
  - "provincial"
  - "regional"
```

**Step 3 - Add vocabulary to wiq_intents.yaml:**
```yaml
intent_categories:
  geographic_queries:
    description: "Questions about regional or provincial workforce data"
    keywords:
      - province
      - region
      - provincial
      - regional
      - Ontario
      - Quebec
      - British Columbia
      - Alberta
    sample_questions:
      - "How many software developers in Ontario?"
      - "Employment growth by province for TEER 1"
```

### Example 2: Adding Comparison Queries

**User request:** "I want to compare occupations"

**Step 1 - Identify endpoint:** Comparisons query data → `data_query`

**Step 2 - Add patterns to jobforge.yaml:**
```yaml
patterns:
  - "compare"
  - "versus"
  - "vs"
  - "difference between"
  - "higher than"
  - "lower than"
```

**Step 3 - Add vocabulary to wiq_intents.yaml:**
```yaml
intent_categories:
  comparison_queries:
    description: "Questions comparing occupations or time periods"
    keywords:
      - compare
      - comparison
      - versus
      - difference
      - higher
      - lower
      - greater
      - less
    sample_questions:
      - "Compare software developers vs data analysts"
      - "What's the difference between TEER 1 and TEER 2?"
      - "Is employment growth higher in 2025 or 2030?"
```

### Example 3: Adding Time-Series Queries

**User request:** "I want to see trends over time"

**Step 1 - Identify endpoint:** Time-series data → `data_query`

**Step 2 - Add patterns to jobforge.yaml:**
```yaml
patterns:
  - "trend"
  - "over time"
  - "from {year} to {year}"
  - "between {year} and {year}"
  - "historical"
  - "forecast"
```

**Step 3 - Add year entity to wiq_intents.yaml:**
```yaml
entities:
  year_range:
    description: "Year or year range in COPS data (2023-2033)"
    patterns:
      - "\\b20[23]\\d\\b"           # Matches 2023-2039
      - "from\\s+\\d{4}\\s+to\\s+\\d{4}"
    examples:
      - "2025"
      - "from 2023 to 2033"
```

## Summary

**To add a new query pattern:**

1. Identify which endpoint should handle it (data/metadata/compliance)
2. Add keyword patterns to `orbit/config/adapters/jobforge.yaml`
3. Add domain vocabulary to `orbit/config/intents/wiq_intents.yaml`
4. Restart Docker stack: `docker compose down && docker compose up -d`
5. Test with curl commands
6. Monitor logs for classification accuracy
7. Refine patterns based on false positives/negatives

**Key files:**
- `orbit/config/adapters/jobforge.yaml` - HTTP routing and pattern matching
- `orbit/config/intents/wiq_intents.yaml` - Domain vocabulary and LLM fallback

**Testing checklist:**
- [ ] Pattern matches expected questions
- [ ] No false positives (wrong endpoint routing)
- [ ] LLM fallback works when patterns don't match
- [ ] Logs show correct intent classification
- [ ] Results are accurate and complete

Happy extending!
