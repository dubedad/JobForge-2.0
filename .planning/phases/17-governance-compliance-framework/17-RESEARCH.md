# Phase 17: Governance Compliance Framework - Research

**Researched:** 2026-02-05
**Domain:** Data governance, compliance auditing, policy traceability, PDF report generation
**Confidence:** HIGH

## Summary

This phase builds a governance compliance framework enabling DAMA DMBOK audits with quantitative metrics, policy-to-data traceability, and audit-ready reporting. The research confirms the existing JobForge stack already contains all necessary libraries (matplotlib for radar charts, weasyprint for PDF generation, duckdb for views, typer for CLI). The standard approach extends the existing compliance module with policy mappings, scoring calculations, and multiple output formats.

Key findings:
1. **Radar charts**: matplotlib's polar projection with RadarAxes provides production-ready spider charts that save directly to PNG/PDF
2. **PDF reports**: WeasyPrint 68.0 (already installed) converts HTML/CSS to PDF, enabling template-based reports with embedded charts
3. **REPL mode**: click-repl library integrates with Typer (via Click) for interactive shell mode with command completion
4. **DuckDB views**: Simple CREATE VIEW syntax exposes policy_mappings and compliance_scores as queryable views
5. **DMBOK maturity**: 5 levels (Initial, Managed, Defined, Quantitatively Managed, Optimized) map directly to user-requested 4-level model

**Primary recommendation:** Use existing stack (matplotlib + weasyprint + typer + duckdb) with click-repl for REPL mode. No new dependencies required beyond click-repl.

## Standard Stack

The established libraries/tools for this domain:

### Core (Already Installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| matplotlib | 3.8.0 | Radar/spider chart generation | Battle-tested, polar projection support, direct PDF export |
| weasyprint | 68.0 | HTML-to-PDF report generation | CSS3 support, Python 3.11+, already in project |
| duckdb | 1.4.3 | Governance data views and queries | Already primary query engine, CREATE VIEW support |
| typer | 0.21.1 | CLI framework | Already used for jobforge CLI |
| pydantic | 2.12.0+ | Policy mapping and scoring models | Already used for all domain models |

### Supporting (New)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| click-repl | 0.3.0 | Interactive REPL shell mode | For `jobforge governance repl` command |
| jinja2 | 3.1.0+ | HTML template rendering for PDF reports | Already a WeasyPrint dependency |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| matplotlib | plotly | Plotly better for interactive charts, but matplotlib simpler for static PDF |
| weasyprint | reportlab | ReportLab more control, but WeasyPrint already installed and uses familiar HTML/CSS |
| click-repl | prompt_toolkit directly | prompt_toolkit more powerful, but click-repl integrates with Typer/Click out of box |

**Installation:**
```bash
pip install click-repl>=0.3.0
```

## Architecture Patterns

### Recommended Project Structure
```
src/jobforge/
├── governance/
│   ├── compliance/           # Existing: DADM, DAMA, Classification logs
│   │   ├── __init__.py
│   │   ├── models.py         # TraceabilityEntry, ComplianceLog
│   │   ├── dadm.py           # DADM compliance generator
│   │   ├── dama.py           # DAMA compliance generator
│   │   ├── classification.py # Classification compliance generator
│   │   ├── audit.py          # NEW: DAMA audit with quantitative metrics
│   │   ├── scoring.py        # NEW: Compliance scoring (pass/fail, %, maturity)
│   │   └── policy_refs.py    # NEW: Policy reference management
│   ├── policy/               # NEW: Policy mapping layer
│   │   ├── __init__.py
│   │   ├── models.py         # PolicyMapping, PolicyClause, PolicySource models
│   │   ├── registry.py       # Policy source registry (TBS DSD, DAMA, ATIP, etc.)
│   │   └── mappings.py       # Table/column/relationship to policy mappings
│   ├── reports/              # NEW: Report generation
│   │   ├── __init__.py
│   │   ├── radar.py          # DAMA dimension radar chart generation
│   │   ├── templates/        # Jinja2 HTML templates for PDF
│   │   │   ├── audit_detailed.html
│   │   │   └── audit_summary.html
│   │   └── export.py         # JSON, Markdown, PDF export
│   └── query.py              # Existing: LineageQueryEngine (extend for policy)
├── cli/
│   └── commands.py           # Extend with governance commands and REPL
└── api/
    └── routes.py             # Extend with governance endpoints
```

### Pattern 1: Policy Mapping with Version Tracking
**What:** Store policy references with version dates and clause text alongside mappings
**When to use:** All policy-to-data mappings
**Example:**
```python
# Source: CONTEXT.md decisions
from pydantic import BaseModel, Field
from datetime import date
from enum import Enum

class PolicySource(str, Enum):
    TBS_DSD = "TBS Directive on Service and Digital"
    DAMA_DMBOK = "DAMA DMBOK"
    ATIP = "Access to Information and Privacy Act"
    PRIVACY_ACT = "Privacy Act"
    GC_HR_ERD = "GC HR ERD and Data Dictionary"
    DADM = "Directive on Automated Decision-Making"
    AIA = "Algorithmic Impact Assessment"

class PolicyClause(BaseModel):
    """A specific clause from a policy document."""
    policy_source: PolicySource
    version_date: date  # e.g., 2024-04-01 for "TBS DSD 2024-04"
    clause_id: str  # e.g., "6.1.1", "DAMA-7.3"
    clause_text: str  # Full text of the clause
    url: str | None = None  # Deep link to official source

class PolicyMapping(BaseModel):
    """Mapping between data element and policy clause."""
    element_type: str  # "table", "column", "relationship"
    element_path: str  # e.g., "dim_noc", "dim_noc.unit_group_id", "dim_noc->cops_employment"
    primary_policy: PolicyClause
    secondary_policies: list[PolicyClause] = Field(default_factory=list)
    compliance_status: str  # "compliant", "partial", "not_compliant", "na"
    compliance_justification: str
    na_reason: str | None = None  # Required if status is "na"
    last_verified: date
```

### Pattern 2: Three-Tier Compliance Scoring
**What:** Calculate compliance at element, phase, and milestone levels with multiple views
**When to use:** All compliance score generation
**Example:**
```python
# Source: CONTEXT.md decisions
from enum import Enum

class MaturityLevel(str, Enum):
    INITIAL = "Initial"  # L1: Ad-hoc, no governance
    MANAGED = "Managed"  # L2: Basic processes in place
    DEFINED = "Defined"  # L3: Documented standards
    OPTIMIZED = "Optimized"  # L4/L5: Quantified and improving

class ComplianceScore(BaseModel):
    """Multi-view compliance score for an element or aggregate."""
    scope: str  # "element", "phase", "milestone", "project"
    scope_id: str  # e.g., "dim_noc", "phase-17", "v4.0"

    # Binary pass/fail
    pass_fail: bool
    failed_requirements: list[str] = Field(default_factory=list)

    # Percentage score (0-100)
    percentage: float

    # Maturity level
    maturity: MaturityLevel

    # DAMA dimension breakdown (for radar chart)
    dimension_scores: dict[str, float]  # e.g., {"Data Governance": 85.0, ...}

    # Weights used (GC-aligned defaults)
    weights_applied: dict[str, float]

# GC-aligned default weights per DAMA dimension (TBS priorities)
GC_DAMA_WEIGHTS = {
    "Data Governance": 1.5,  # TBS emphasizes governance
    "Data Architecture": 1.0,
    "Data Modeling and Design": 1.0,
    "Data Storage and Operations": 1.0,
    "Data Security": 1.2,  # Privacy Act emphasis
    "Data Integration and Interoperability": 1.3,  # GC interoperability priority
    "Metadata Management": 1.4,  # FAIR principles emphasis
    "Data Quality": 1.3,  # GC DQMF priority
    "Reference and Master Data": 1.2,
    "Data Warehousing and Business Intelligence": 0.8,  # Lower GC priority
    "Document and Content Management": 0.7,  # Less relevant to WiQ
}
```

### Pattern 3: Radar Chart Generation for PDF
**What:** Generate DAMA dimension radar charts using matplotlib polar projection
**When to use:** PDF report generation with visual compliance profiles
**Example:**
```python
# Source: matplotlib official documentation
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO

def generate_dama_radar_chart(
    dimension_scores: dict[str, float],
    title: str = "DAMA DMBOK Compliance Profile"
) -> bytes:
    """Generate radar chart as PNG bytes for embedding in PDF."""
    # DAMA 11 dimensions
    dimensions = [
        "Data Governance", "Data Architecture", "Data Modeling",
        "Storage & Ops", "Data Security", "Integration",
        "Metadata Mgmt", "Data Quality", "Reference Data",
        "DW & BI", "Document Mgmt"
    ]

    # Get scores in order (default to 0 if missing)
    values = [dimension_scores.get(d, 0) / 100 for d in dimensions]

    # Number of dimensions
    num_vars = len(dimensions)

    # Compute angle for each dimension
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()

    # Complete the loop
    values += values[:1]
    angles += angles[:1]

    # Create figure
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

    # Draw the radar chart
    ax.plot(angles, values, 'o-', linewidth=2, color='#2E7D32')
    ax.fill(angles, values, alpha=0.25, color='#2E7D32')

    # Set the labels
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(dimensions, size=9)

    # Set the y-axis limits
    ax.set_ylim(0, 1)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(['20%', '40%', '60%', '80%', '100%'], size=8)

    ax.set_title(title, size=14, y=1.08)

    # Save to bytes
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf.read()
```

### Pattern 4: Bidirectional Policy Query
**What:** Query policy-to-data and data-to-policy relationships via DuckDB views
**When to use:** Governance CLI and API query endpoints
**Example:**
```python
# Source: DuckDB documentation
import duckdb

def create_governance_views(conn: duckdb.DuckDBPyConnection) -> None:
    """Create DuckDB views for governance queries."""

    # View: policy_mappings - all policy-to-data mappings
    conn.execute("""
        CREATE OR REPLACE VIEW policy_mappings AS
        SELECT
            element_type,
            element_path,
            primary_policy_source,
            primary_policy_clause_id,
            primary_policy_version,
            compliance_status,
            last_verified
        FROM read_json_auto('data/catalog/policy_mappings.json')
    """)

    # View: compliance_scores - rollup scores by scope
    conn.execute("""
        CREATE OR REPLACE VIEW compliance_scores AS
        SELECT
            scope,
            scope_id,
            pass_fail,
            percentage,
            maturity_level,
            calculated_at
        FROM read_json_auto('data/catalog/compliance_scores.json')
    """)

    # Example queries:
    # "What policies govern dim_noc?"
    # SELECT * FROM policy_mappings WHERE element_path LIKE 'dim_noc%'

    # "What tables satisfy TBS DSD 6.1?"
    # SELECT element_path FROM policy_mappings
    # WHERE primary_policy_clause_id = '6.1' AND compliance_status = 'compliant'
```

### Pattern 5: Interactive REPL Mode
**What:** Add REPL mode to governance CLI using click-repl
**When to use:** Interactive governance exploration
**Example:**
```python
# Source: click-repl documentation
import click
from click_repl import register_repl
import typer

# Create a Click group that wraps the Typer app
governance_app = typer.Typer(name="governance")

@governance_app.command()
def audit(
    framework: str = typer.Argument("dama", help="Framework: dama, dadm, all"),
    output: str = typer.Option(None, "--output", "-o", help="Output file"),
    format: str = typer.Option("table", help="Format: table, json, markdown, pdf"),
):
    """Run governance compliance audit."""
    pass

@governance_app.command()
def policies(
    element: str = typer.Argument(..., help="Element path to query"),
):
    """Show policies governing an element."""
    pass

@governance_app.command()
def elements(
    policy: str = typer.Argument(..., help="Policy clause to query"),
):
    """Show elements satisfying a policy clause."""
    pass

# Convert to Click and register REPL
# Note: Typer apps are Click groups under the hood
click_app = typer.main.get_command(governance_app)
register_repl(click_app)

# Usage:
# $ jobforge governance repl
# governance> audit dama --format table
# governance> policies dim_noc
# governance> elements "TBS-DSD-6.1"
```

### Anti-Patterns to Avoid
- **Storing policy text separately from mappings:** Keep clause text WITH the mapping for full auditability
- **Binary-only compliance scoring:** Always provide percentage AND maturity views
- **Generating charts at query time:** Pre-generate and cache radar charts for PDF performance
- **Hardcoding policy versions:** Always include version_date for temporal traceability
- **Ignoring N/A justifications:** Require explicit na_reason when marking elements as not applicable

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Radar chart rendering | Custom SVG generation | matplotlib RadarAxes | Proven polar projection, handles closing, PDF export |
| HTML-to-PDF conversion | String concatenation | WeasyPrint + Jinja2 | CSS3 support, page breaks, headers/footers |
| Interactive CLI shell | While loop with input() | click-repl | Command completion, history, shell escapes |
| Policy version comparison | String parsing | date objects | Python date comparison handles edge cases |
| JSON view in DuckDB | Python dict iteration | CREATE VIEW + read_json_auto | DuckDB handles lazy loading, caching |

**Key insight:** The PDF generation and radar chart domains have deep edge cases (page breaks, label positioning, polar coordinates) that libraries handle well. Custom solutions will miss edge cases and require ongoing maintenance.

## Common Pitfalls

### Pitfall 1: Maturity Level Mismatch
**What goes wrong:** DAMA DMBOK uses 5 levels, user requested 4 levels (Initial/Managed/Defined/Optimized)
**Why it happens:** DAMA L4 (Quantitatively Managed) and L5 (Optimized) distinction is subtle
**How to avoid:** Collapse L4 and L5 into "Optimized" with optional sub-distinction in metadata
**Warning signs:** Inconsistent maturity labeling across phases

### Pitfall 2: Policy Version Staleness
**What goes wrong:** Mappings reference outdated policy versions, audit shows false compliance
**Why it happens:** Policies update but mappings don't track version dates
**How to avoid:** Include version_date on every PolicyClause, add freshness warnings in reports
**Warning signs:** Reports showing compliance to policies with different dates than current

### Pitfall 3: Radar Chart Overlapping Labels
**What goes wrong:** DAMA 11-dimension labels overlap on small charts
**Why it happens:** 11 dimensions is dense for radar visualization
**How to avoid:** Use abbreviated dimension names (e.g., "Metadata Mgmt" not "Metadata Management"), increase figure size
**Warning signs:** Labels truncated or overlapping in PDF output

### Pitfall 4: PDF Report Performance
**What goes wrong:** Large reports with many charts take 30+ seconds to generate
**Why it happens:** Chart regeneration on every export
**How to avoid:** Pre-generate and cache chart images, only regenerate when scores change
**Warning signs:** Slow response on /api/governance/report endpoint

### Pitfall 5: N/A vs Not Mapped Confusion
**What goes wrong:** Elements marked N/A incorrectly, or unmapped elements shown as compliant
**Why it happens:** Missing explicit distinction between "intentionally exempt" and "not yet assessed"
**How to avoid:** Require na_reason field for N/A status, default unmapped elements to "not_assessed"
**Warning signs:** Audit showing 100% compliance when mappings are incomplete

## Code Examples

Verified patterns from official sources:

### WeasyPrint HTML-to-PDF with Embedded Chart
```python
# Source: WeasyPrint documentation + Jinja2
from weasyprint import HTML
from jinja2 import Environment, FileSystemLoader
import base64

def generate_pdf_report(
    scores: ComplianceScore,
    chart_bytes: bytes,
    output_path: str,
    detailed: bool = True
) -> None:
    """Generate PDF compliance report with embedded radar chart."""
    # Set up Jinja2
    env = Environment(loader=FileSystemLoader('templates'))
    template_name = 'audit_detailed.html' if detailed else 'audit_summary.html'
    template = env.get_template(template_name)

    # Embed chart as base64 data URI
    chart_b64 = base64.b64encode(chart_bytes).decode('utf-8')
    chart_uri = f"data:image/png;base64,{chart_b64}"

    # Render HTML
    html_content = template.render(
        scores=scores,
        chart_uri=chart_uri,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

    # Convert to PDF
    HTML(string=html_content).write_pdf(output_path)
```

### DuckDB View Creation with JSON Source
```python
# Source: DuckDB documentation
def setup_governance_database(conn: duckdb.DuckDBPyConnection) -> None:
    """Set up governance views in DuckDB connection."""
    # Create policy mappings view
    conn.execute("""
        CREATE OR REPLACE VIEW policy_mappings AS
        SELECT
            j.element_type,
            j.element_path,
            j.primary_policy.policy_source AS policy_source,
            j.primary_policy.clause_id AS clause_id,
            j.primary_policy.clause_text AS clause_text,
            j.primary_policy.version_date AS version_date,
            j.compliance_status,
            j.last_verified
        FROM read_json_auto(
            'data/catalog/policy_mappings.json',
            format='array'
        ) AS j
    """)

    # Query: What policies govern table X?
    def policies_for_element(element: str) -> list[dict]:
        result = conn.execute("""
            SELECT policy_source, clause_id, clause_text, compliance_status
            FROM policy_mappings
            WHERE element_path = ? OR element_path LIKE ?
        """, [element, f"{element}.%"]).fetchall()
        return [dict(zip(['source', 'clause', 'text', 'status'], r)) for r in result]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual compliance checklists | Automated RTM generation | DAMA DMBOK2 (2017) | Auditable, repeatable assessments |
| Binary compliance (pass/fail) | Multi-view scoring (%, maturity) | GC DQMF (2020) | More nuanced compliance picture |
| Paper audit trails | JSON policy mappings with provenance | TBS DSD (2024) | Machine-readable, queryable governance |
| Static PDF reports | HTML-to-PDF with embedded visualizations | WeasyPrint 68.0 (2026) | Dynamic reports with charts |

**Deprecated/outdated:**
- ReportLab direct PDF generation: WeasyPrint + HTML/CSS is more maintainable for complex layouts
- Plotly for static charts: matplotlib simpler for non-interactive PDF embedding
- Manual maturity assessments: Automated scoring based on artifact presence preferred

## Open Questions

Things that couldn't be fully resolved:

1. **GC-aligned DAMA weights**
   - What we know: TBS prioritizes governance, privacy, interoperability, quality
   - What's unclear: Exact weight multipliers for each DAMA dimension
   - Recommendation: Start with proposed weights (1.5 governance, 1.4 metadata, etc.), allow user override via config

2. **Policy text storage size**
   - What we know: Some policy clauses are lengthy (500+ words)
   - What's unclear: Impact on catalog JSON file sizes
   - Recommendation: Store full text but consider separate policy_clauses.json if catalogs grow too large

3. **Interactive REPL history persistence**
   - What we know: click-repl supports FileHistory for persistent command history
   - What's unclear: Best location for history file (.jobforge/history vs project-local)
   - Recommendation: Use ~/.jobforge/governance_history for cross-project persistence

## Sources

### Primary (HIGH confidence)
- [matplotlib RadarAxes](https://matplotlib.org/stable/gallery/specialty_plots/radar_chart.html) - Official radar chart example
- [DuckDB CREATE VIEW](https://duckdb.org/docs/stable/sql/statements/create_view) - View creation syntax
- [WeasyPrint documentation](https://doc.courtbouillon.org/weasyprint/stable/) - HTML-to-PDF conversion
- [click-repl GitHub](https://github.com/click-contrib/click-repl) - REPL integration for Click/Typer

### Secondary (MEDIUM confidence)
- [DAMA DMBOK Framework Guide](https://atlan.com/dama-dmbok-framework/) - 11 knowledge areas and maturity model
- [TBS Directive on Service and Digital](https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=32601) - GC data governance requirements
- [GC Data Strategy 2023-2026](https://www.canada.ca/en/government/system/digital-government/leveraging-information-data/annual-report-2023-2026-data-strategy.html) - FAIR principles, CDO guidance

### Tertiary (LOW confidence)
- DAMA DMBOK scoring weights: No authoritative source found; proposed weights based on TBS priorities

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already installed or well-documented
- Architecture: HIGH - Extends existing governance module with clear patterns
- Pitfalls: MEDIUM - Based on general data governance experience, not WiQ-specific history
- GC weights: LOW - No authoritative source for TBS DAMA dimension priorities

**Research date:** 2026-02-05
**Valid until:** 2026-03-05 (30 days - stable domain, libraries mature)
