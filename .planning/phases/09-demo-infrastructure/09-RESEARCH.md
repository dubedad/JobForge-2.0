# Phase 9: Demo Infrastructure - Research

**Researched:** 2026-01-20
**Domain:** MCP Integration, Web UI, SSE Communication, GC Design Standards
**Confidence:** HIGH

## Summary

This phase integrates MCP configuration from the working prototype, builds a browser-based narration UI following Government of Canada design standards, and creates a wizard-style demo flow with real-time Server-Sent Events communication.

The prototype (`/JobForge/`) has working MCP configuration in `.claude/settings.local.json` with permissions for all Power BI MCP Server operations. The existing JobForge 2.0 codebase already has CLI (`jobforge stagegold`), deployment orchestration (`WiQDeployer`), and MCP specification generation (`MCPClient`). The phase builds a web-based UI layer that communicates via SSE to show deployment progress in real-time.

Key constraints from CONTEXT.md:
- Plain HTML/JS/CSS only (no CDN dependencies for GC deployment)
- GC color palette (FIP red #eb2d37, white #fff, dark grey #333)
- WCAG 2.1 AA compliance
- Bilingual EN/FR support
- TurboTax-style wizard with 4 steps (Load, Power BI Prompts, Review, Catalogue)

**Primary recommendation:** Build a minimal Python backend with SSE endpoint that wraps existing `WiQDeployer`, serving static HTML/CSS/JS that implements the wizard UI with native `EventSource` API for real-time updates.

## Standard Stack

The established libraries/tools for this domain:

### Core (Already in Project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Typer | >=0.12.0 | CLI framework | Already used for `jobforge` CLI |
| Rich | >=14.1.0 | Terminal UI | Already used in `DeploymentUI` |
| httpx | >=0.27.0 | HTTP client | Already in deps, async-capable |
| Pydantic | >=2.12.0 | Data models | Already used throughout |

### New (Required for Demo UI)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| uvicorn | >=0.30.0 | ASGI server | Standard FastAPI/Starlette server |
| starlette | >=0.38.0 | ASGI framework | Lightweight, SSE support built-in |
| sse-starlette | >=2.0.0 | SSE response helper | Proper SSE formatting for Starlette |

### Frontend (No Dependencies)
| Technology | Purpose | Why |
|------------|---------|-----|
| Vanilla HTML5 | Structure | GC deployment, no build step |
| Vanilla CSS3 | Styling | GC deployment, no dependencies |
| Vanilla JavaScript | Interactivity | Native EventSource API for SSE |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Starlette | FastAPI | FastAPI adds overhead; Starlette is lighter for SSE-only backend |
| sse-starlette | Manual SSE | sse-starlette handles reconnection, proper formatting |
| Vanilla JS | React/Vue | External CDN dependencies prohibited by GC deployment |

**Installation:**
```bash
pip install uvicorn starlette sse-starlette
```

Or add to pyproject.toml:
```toml
dependencies = [
    # ... existing deps ...
    "uvicorn>=0.30.0",
    "starlette>=0.38.0",
    "sse-starlette>=2.0.0",
]
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── jobforge/
│   ├── demo/                    # NEW: Demo infrastructure
│   │   ├── __init__.py
│   │   ├── app.py               # Starlette app with SSE endpoint
│   │   ├── events.py            # SSE event models and formatting
│   │   ├── orchestrator.py      # Wraps WiQDeployer for SSE streaming
│   │   └── static/              # Static web assets
│   │       ├── index.html       # Main wizard UI
│   │       ├── css/
│   │       │   ├── main.css     # Main styles
│   │       │   ├── gc-theme.css # GC color palette
│   │       │   └── a11y.css     # Accessibility utilities
│   │       ├── js/
│   │       │   ├── main.js      # Main app logic
│   │       │   ├── wizard.js    # Wizard step management
│   │       │   ├── sse.js       # EventSource wrapper
│   │       │   └── i18n.js      # Bilingual support
│   │       └── locales/
│   │           ├── en.json      # English strings
│   │           └── fr.json      # French strings
│   ├── deployment/              # Existing
│   │   ├── deployer.py          # WiQDeployer (reuse)
│   │   ├── mcp_client.py        # MCPClient (reuse)
│   │   └── ui.py                # DeploymentUI (reuse/extend)
│   └── cli/
│       └── commands.py          # Add demo command
```

### Pattern 1: SSE Backend with Starlette
**What:** Lightweight ASGI app serving SSE events during deployment
**When to use:** Real-time progress updates without WebSocket complexity
**Example:**
```python
# Source: Official Starlette + sse-starlette documentation
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
import asyncio

async def deployment_stream(request):
    """SSE endpoint for deployment progress."""
    async def event_generator():
        # Yield events during deployment
        yield {"event": "step", "data": json.dumps({"step": "load", "status": "started"})}
        yield {"event": "table", "data": json.dumps({"name": "dim_noc", "status": "created"})}
        yield {"event": "complete", "data": json.dumps({"tables": 24, "relationships": 22})}

    return EventSourceResponse(event_generator())

app = Starlette(routes=[
    Route("/api/deploy/stream", deployment_stream),
    Mount("/", StaticFiles(directory="static", html=True)),
])
```

### Pattern 2: Vanilla JavaScript EventSource
**What:** Native browser API for receiving SSE
**When to use:** Client-side SSE consumption without libraries
**Example:**
```javascript
// Source: MDN Web Docs EventSource API
class DeploymentStream {
    constructor(url) {
        this.source = new EventSource(url);

        // Named event handlers
        this.source.addEventListener("step", (e) => {
            const data = JSON.parse(e.data);
            this.onStep(data);
        });

        this.source.addEventListener("table", (e) => {
            const data = JSON.parse(e.data);
            this.onTable(data);
        });

        this.source.addEventListener("complete", (e) => {
            const data = JSON.parse(e.data);
            this.onComplete(data);
            this.source.close();
        });

        // Error handling with auto-reconnect
        this.source.onerror = (err) => {
            console.error("SSE error:", err);
            // EventSource auto-reconnects unless closed
        };
    }

    close() {
        this.source.close();
    }
}
```

### Pattern 3: Accessible Wizard Step Indicator
**What:** WCAG-compliant wizard progress using semantic HTML
**When to use:** Multi-step form/wizard interfaces
**Example:**
```html
<!-- Source: CSS-Tricks Multi-Step Forms Guide -->
<nav aria-label="Progress" class="wizard-nav">
    <ol class="wizard-steps">
        <li class="step completed" aria-current="false">
            <a href="#step-load">
                <span class="step-number" aria-hidden="true">1</span>
                <span class="step-label">Load</span>
                <span class="visually-hidden">Step 1 of 4 - Completed</span>
            </a>
        </li>
        <li class="step current" aria-current="step">
            <span class="step-number" aria-hidden="true">2</span>
            <span class="step-label">Power BI</span>
            <span class="visually-hidden">Step 2 of 4 - Current</span>
        </li>
        <!-- ... -->
    </ol>
</nav>
```

### Pattern 4: GC-Compliant Color Palette
**What:** CSS custom properties for FIP colors
**When to use:** All UI elements
**Example:**
```css
/* Source: Canada.ca Design System + FIP Color Standard */
:root {
    /* FIP Core Colors */
    --gc-red: #eb2d37;           /* FIP Red - Pantone 032 */
    --gc-white: #ffffff;
    --gc-black: #000000;
    --gc-pewter: #969696;        /* Pewter grey - Pantone 429 */

    /* Canada.ca Design System Colors */
    --gc-text: #333333;          /* Dark grey for text */
    --gc-accent: #26374a;        /* Main accent */
    --gc-link: #284162;          /* Default link */
    --gc-link-hover: #0535d2;    /* Hover/focus link */
    --gc-link-visited: #7834bc;  /* Visited link */
    --gc-error: #d3080c;         /* Error/required indicator */

    /* Light/Dark mode */
    --bg-primary: var(--gc-white);
    --text-primary: var(--gc-text);
}

@media (prefers-color-scheme: dark) {
    :root {
        --bg-primary: #1a1a1a;
        --text-primary: #f0f0f0;
    }
}
```

### Anti-Patterns to Avoid
- **External CDN dependencies:** Prohibited for GC deployment - use inline or local assets only
- **WebSockets for one-way data:** SSE is simpler, works through proxies, auto-reconnects
- **Custom accessibility solutions:** Use native HTML semantics (`<button>`, `<nav>`, ARIA only when needed)
- **Inline styles for theming:** Use CSS custom properties for maintainability
- **Language detection by URL:** Use toggle button + localStorage for bilingual

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE formatting | Custom event formatter | sse-starlette | Handles reconnection, proper Content-Type, buffering |
| Wizard state machine | Custom state management | Simple class with validation | Wizard is 4 linear steps, no complex branching |
| i18n | Complex i18n library | JSON files + simple lookup | Only 2 languages, static content |
| Focus management | Manual focus code | Native focus + CSS `:focus-visible` | WCAG compliance built-in |
| Form validation | Custom validators | HTML5 constraint validation | Native, accessible, no JS required for basics |
| Dark mode detection | JS-based detection | CSS `prefers-color-scheme` | Native, no JS, respects system preference |

**Key insight:** The demo UI is presentation-focused, not data-heavy. Vanilla solutions work well for this scope; frameworks add unnecessary complexity for GC deployment requirements.

## Common Pitfalls

### Pitfall 1: SSE Connection Limits per Domain
**What goes wrong:** Opening multiple browser tabs exhausts the 6-connection limit (HTTP/1.1)
**Why it happens:** SSE maintains persistent connections; browsers limit per-domain connections
**How to avoid:**
- Use HTTP/2 (default in modern servers) for higher limits (100+ streams)
- Close SSE connections when not actively streaming
- Implement explicit "close" events when deployment completes
**Warning signs:** New tabs hang on "connecting" state

### Pitfall 2: GC Proxy SSE Buffering
**What goes wrong:** SSE events arrive in batches instead of real-time
**Why it happens:** Corporate proxies may buffer responses before forwarding
**How to avoid:**
- Set `Cache-Control: no-cache` header
- Set `X-Accel-Buffering: no` for nginx proxies
- Consider periodic heartbeat events to prevent timeout
**Warning signs:** Events arrive in groups after long delays

### Pitfall 3: Focus Trap in Modal/Wizard
**What goes wrong:** Keyboard users get trapped or can't navigate between steps
**Why it happens:** Poor focus management when showing/hiding wizard steps
**How to avoid:**
- Move focus to first interactive element when step changes
- Use `aria-live` regions for dynamic announcements
- Keep wizard navigation always accessible (not hidden)
**Warning signs:** Tab key doesn't reach expected elements

### Pitfall 4: iframe Security/CORS Issues
**What goes wrong:** Power BI embed fails with CORS or X-Frame-Options errors
**Why it happens:** Power BI service has strict embedding policies
**How to avoid:**
- Use Power BI's "Publish to web" or "Embed" URL patterns
- For internal demos, may need local Power BI Desktop view (not embedded)
- Test embed URL patterns before implementation
**Warning signs:** iframe shows blank or error message

### Pitfall 5: Bilingual Content Misalignment
**What goes wrong:** French/English UI has different lengths causing layout breaks
**Why it happens:** French text is typically 15-20% longer than English
**How to avoid:**
- Use flexible layouts (flexbox/grid) that adapt to content length
- Test with French content first (longer strings)
- Avoid fixed-width containers for text
**Warning signs:** French text overflows or truncates

## Code Examples

Verified patterns from official sources:

### SSE Server Response Format
```python
# Source: sse-starlette documentation + Starlette docs
from sse_starlette.sse import EventSourceResponse
from starlette.applications import Starlette
from starlette.routing import Route
import asyncio
import json

async def stream_deployment(request):
    """Stream deployment events via SSE."""
    async def generate():
        # Start event
        yield {
            "event": "start",
            "data": json.dumps({"total_tables": 24, "total_relationships": 22})
        }

        # Table creation events
        for table in tables:
            yield {
                "event": "table",
                "data": json.dumps({
                    "name": table.name,
                    "source": get_table_source(table.name),
                    "columns": len(table.columns)
                })
            }
            await asyncio.sleep(0.1)  # Small delay for visual effect

        # Complete event
        yield {
            "event": "complete",
            "data": json.dumps({"success": True, "duration_ms": duration})
        }

    return EventSourceResponse(
        generate(),
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )

app = Starlette(routes=[
    Route("/api/stream", stream_deployment),
])
```

### Accessible Wizard HTML Structure
```html
<!-- Source: WCAG 2.1 AA Guidelines + CSS-Tricks -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JobForge Demo - Workforce Intelligence</title>
</head>
<body>
    <!-- Skip link for keyboard users -->
    <a href="#main-content" class="skip-link">Skip to main content</a>

    <!-- Header with language toggle -->
    <header role="banner">
        <div class="header-brand">
            <img src="logo.svg" alt="JobForge">
            <span>Workforce Intelligence</span>
        </div>
        <button id="lang-toggle" aria-label="Switch to French">FR</button>
    </header>

    <!-- Wizard progress -->
    <nav aria-label="Wizard progress" class="wizard-progress">
        <ol role="list">
            <li role="listitem" class="step" data-step="1">
                <span class="step-indicator" aria-hidden="true">1</span>
                <span class="step-text" data-i18n="step.load">Load</span>
            </li>
            <!-- ... more steps -->
        </ol>
    </nav>

    <!-- Main content area -->
    <main id="main-content" role="main">
        <fieldset class="wizard-step" id="step-load" data-step="1">
            <legend class="visually-hidden">Step 1 of 4: Load Data</legend>
            <!-- Step content -->
        </fieldset>
    </main>

    <!-- Live region for announcements -->
    <div aria-live="polite" aria-atomic="true" class="visually-hidden" id="announcements"></div>
</body>
</html>
```

### JavaScript Wizard Controller
```javascript
// Source: CSS-Tricks Multi-Step Forms + MDN EventSource
class WizardController {
    constructor() {
        this.currentStep = 1;
        this.totalSteps = 4;
        this.steps = document.querySelectorAll('.wizard-step');
        this.progressItems = document.querySelectorAll('.wizard-progress .step');
        this.announcer = document.getElementById('announcements');
    }

    goToStep(stepNumber) {
        if (stepNumber < 1 || stepNumber > this.totalSteps) return;

        // Hide all steps
        this.steps.forEach(step => {
            step.hidden = true;
            step.setAttribute('aria-hidden', 'true');
        });

        // Show target step
        const targetStep = document.getElementById(`step-${stepNumber}`);
        targetStep.hidden = false;
        targetStep.setAttribute('aria-hidden', 'false');

        // Update progress indicators
        this.progressItems.forEach((item, index) => {
            const isCompleted = index + 1 < stepNumber;
            const isCurrent = index + 1 === stepNumber;

            item.classList.toggle('completed', isCompleted);
            item.classList.toggle('current', isCurrent);
            item.setAttribute('aria-current', isCurrent ? 'step' : 'false');
        });

        // Focus management - focus first interactive element
        const firstFocusable = targetStep.querySelector(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        if (firstFocusable) {
            firstFocusable.focus();
        }

        // Announce step change
        this.announce(`Step ${stepNumber} of ${this.totalSteps}`);

        this.currentStep = stepNumber;
    }

    announce(message) {
        this.announcer.textContent = message;
    }

    next() {
        this.goToStep(this.currentStep + 1);
    }

    previous() {
        this.goToStep(this.currentStep - 1);
    }
}
```

### Simple i18n Implementation
```javascript
// Source: Project-specific for bilingual support
class I18n {
    constructor() {
        this.locale = localStorage.getItem('locale') || 'en';
        this.strings = {};
    }

    async load(locale) {
        const response = await fetch(`/locales/${locale}.json`);
        this.strings = await response.json();
        this.locale = locale;
        localStorage.setItem('locale', locale);
        this.apply();
        document.documentElement.lang = locale;
    }

    t(key) {
        return key.split('.').reduce((obj, k) => obj?.[k], this.strings) || key;
    }

    apply() {
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.dataset.i18n;
            el.textContent = this.t(key);
        });
        document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
            const key = el.dataset.i18nPlaceholder;
            el.placeholder = this.t(key);
        });
    }

    toggle() {
        const newLocale = this.locale === 'en' ? 'fr' : 'en';
        this.load(newLocale);
    }
}
```

## MCP Configuration

### Prototype MCP Settings (Working Config)
```json
// Source: c:\Users\Administrator\Dropbox\++ Results Kit\JobForge\.claude\settings.local.json
{
  "permissions": {
    "allow": [
      "mcp__powerbi-modeling__table_operations",
      "mcp__powerbi-modeling__relationship_operations",
      "mcp__powerbi-modeling__named_expression_operations",
      "mcp__powerbi-modeling__column_operations",
      "mcp__powerbi-modeling__partition_operations",
      "mcp__powerbi-modeling__model_operations",
      "mcp__powerbi-modeling__dax_query_operations",
      "mcp__powerbi-modeling__batch_table_operations",
      "mcp__powerbi-modeling__measure_operations",
      "mcp__powerbi-modeling__batch_column_operations",
      "mcp__powerbi-modeling__connection_operations",
      "mcp__powerbi-modeling__batch_measure_operations",
      "mcp__powerbi-modeling__database_operations",
      "mcp__powerbi-modeling__transaction_operations"
    ]
  }
}
```

### Key MCP Operations for Demo
| Operation | Tool | Purpose |
|-----------|------|---------|
| Connect to PBI Desktop | connection_operations | ListLocalInstances, Connect |
| Create tables | table_operations, batch_table_operations | Create tables with M expressions |
| Create relationships | relationship_operations | Link tables with cardinality |
| Create measures | measure_operations, batch_measure_operations | Add DAX measures |
| Execute queries | dax_query_operations | Validate model with EVALUATE |

## Power BI Embedding

### Embedding Options for Demo
| Method | URL Pattern | Pros | Cons |
|--------|-------------|------|------|
| Publish to Web | `https://app.powerbi.com/reportEmbed?...` | Simple, no auth | Public, no filtering |
| Secure Embed | `https://app.powerbi.com/reportEmbed?...&autoAuth=true` | Auth-aware | Requires PBI login |
| Local Desktop | No embed - side-by-side | Full control | No iframe integration |

### iframe Embed Code
```html
<!-- Source: Microsoft Learn - Power BI Embed -->
<iframe
    title="WiQ Semantic Model"
    width="100%"
    height="400"
    src="https://app.powerbi.com/reportEmbed?reportId={REPORT_ID}&autoAuth=true"
    frameborder="0"
    allowFullScreen="true">
</iframe>
```

### Recommended Approach
Given the demo context (VS Code Pro environment, local Power BI Desktop), the most practical approach is:
1. Split screen layout with JobForge UI in browser
2. Power BI Desktop as separate window (not iframe)
3. Pop-out option in UI that opens Power BI URL in new window

This avoids iframe security complexities while achieving the split-screen demo goal.

## WCAG 2.1 AA Requirements

### Key Requirements for Wizard UI
| Criterion | Requirement | Implementation |
|-----------|-------------|----------------|
| 1.3.1 | Info and relationships programmatically determined | Use semantic HTML, ARIA landmarks |
| 1.4.3 | Contrast ratio 4.5:1 for text | GC palette meets this (#333 on #fff) |
| 1.4.11 | Non-text contrast 3:1 | Buttons, form fields, focus indicators |
| 2.1.1 | Keyboard accessible | All interactive elements focusable |
| 2.1.2 | No keyboard trap | Tab navigation flows naturally |
| 2.4.3 | Focus order logical | DOM order matches visual order |
| 2.4.6 | Headings and labels descriptive | Clear, unique labels |
| 2.4.7 | Focus visible | CSS `:focus-visible` with outline |
| 3.2.2 | On input predictable | No unexpected context changes |
| 3.3.1 | Error identification | Error messages with field association |
| 3.3.2 | Labels or instructions | All inputs have visible labels |

### Focus Indicator CSS
```css
/* Source: WCAG 2.1 2.4.7 Focus Visible */
:focus-visible {
    outline: 3px solid var(--gc-link-hover);
    outline-offset: 2px;
}

/* Remove default outline, add custom */
:focus:not(:focus-visible) {
    outline: none;
}

/* High contrast mode support */
@media (forced-colors: active) {
    :focus-visible {
        outline: 3px solid CanvasText;
    }
}
```

## DAMA DMBOK Data Catalogue

### Required Catalogue Fields (DAMA DMBOK Chapter 5)
Based on existing `TableMetadata` model in JobForge 2.0:

| Field | Source | Purpose |
|-------|--------|---------|
| table_name | Schema | Logical identifier |
| layer | Pipeline | Medallion layer (gold) |
| domain | Classification | Data domain |
| description | Schema | Business description |
| business_purpose | Derived | Use case |
| data_owner | Config | Accountability |
| data_steward | Config | Responsibility |
| row_count | Physical | Volume metrics |
| column_count | Schema | Structure metrics |
| file_size_bytes | Physical | Storage metrics |
| columns | Schema | Column metadata array |
| upstream_tables | Lineage | Data provenance |
| downstream_tables | Lineage | Impact analysis |
| classification | Governance | Security level |

### Catalogue CSV Export Format
```csv
table_name,layer,domain,description,business_purpose,data_owner,row_count,column_count
dim_noc,gold,reference,"NOC 2021 Dimension Table","Provides reference data",JobForge WiQ,516,11
oasis_skills,gold,oasis,"OASIS Skills ratings","Skills proficiency data",JobForge WiQ,4128,10
```

### Existing Implementation
JobForge 2.0 already has `CatalogueGenerator` in `src/jobforge/governance/catalogue.py` that:
- Loads WiQ schema from JSON
- Reads physical parquet metadata
- Generates `TableMetadata` objects
- Saves to `data/catalog/tables/{table_name}.json`

The demo needs to expose this via the UI as the "Catalogue" wizard step.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| WebSockets for all real-time | SSE for server-push, WS for bidirectional | 2023+ | Simpler architecture for one-way updates |
| jQuery for DOM manipulation | Vanilla JS with modern APIs | 2020+ | No dependencies, better performance |
| Custom accessibility solutions | Native HTML + ARIA | 2019+ | Better AT support, less code |
| Fixed breakpoints | CSS Container Queries | 2023+ | Component-based responsive design |

**Deprecated/outdated:**
- jQuery: Vanilla JS has all needed features
- XHTML ARIA roles: HTML5 semantic elements preferred
- SSE polyfills: All modern browsers support EventSource natively

## Open Questions

Things that couldn't be fully resolved:

1. **Power BI Desktop iframe embedding**
   - What we know: PBI Service has embed URLs with authentication
   - What's unclear: Whether local PBI Desktop can be embedded at all
   - Recommendation: Use side-by-side layout, not iframe, for local Desktop

2. **GC Proxy SSE compatibility**
   - What we know: SSE works through most proxies
   - What's unclear: Specific GC infrastructure buffering behavior
   - Recommendation: Implement heartbeat events, test in target environment

3. **DADM model-level traceability mapping**
   - What we know: CONTEXT.md specifies "model-level mapping to DADM"
   - What's unclear: Specific DADM requirements to map against
   - Recommendation: Reference user's DADM materials during implementation

## Sources

### Primary (HIGH confidence)
- [MDN EventSource API](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events) - SSE client implementation
- [Canada.ca Design System - Colours](https://design.canada.ca/styles/colours.html) - GC color palette (#333 text, #284162 links)
- [FIP Colour Design Standard](https://www.canada.ca/en/treasury-board-secretariat/services/government-communications/design-standard/colour-design-standard-fip.html) - FIP red #eb2d37
- [WCAG 2.1](https://www.w3.org/TR/WCAG21/) - Accessibility guidelines
- Prototype MCP config: `c:\Users\Administrator\Dropbox\++ Results Kit\JobForge\.claude\settings.local.json`
- Prototype stage-gold command: `c:\Users\Administrator\Dropbox\++ Results Kit\JobForge\.claude\commands\stage-gold.md`

### Secondary (MEDIUM confidence)
- [CSS-Tricks Multi-Step Forms](https://css-tricks.com/how-to-create-multi-step-forms-with-vanilla-javascript-and-css/) - Wizard pattern guidance
- [sse-starlette PyPI](https://pypi.org/project/sse-starlette/) - SSE server implementation
- [Microsoft Learn - Power BI Embed](https://learn.microsoft.com/en-us/power-bi/collaborate-share/service-embed-secure) - Embed URL patterns
- [Accessible.org WCAG Checklist](https://accessible.org/wcag/) - WCAG 2.1 AA checklist

### Tertiary (LOW confidence)
- [DAMA DMBOK Framework](https://atlan.com/dama-dmbok-framework/) - General framework overview (need specific DAMA materials)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Using existing project patterns + well-documented libraries
- Architecture: HIGH - Based on working prototype code and standard patterns
- MCP Integration: HIGH - Direct from working prototype config
- GC Design Standards: HIGH - Official Government of Canada sources
- WCAG Compliance: HIGH - W3C official specification
- Power BI Embedding: MEDIUM - Options documented but local Desktop embedding unclear
- DAMA Catalogue: MEDIUM - Existing code, but DADM mapping needs user materials

**Research date:** 2026-01-20
**Valid until:** 2026-02-20 (30 days - stable domain)
