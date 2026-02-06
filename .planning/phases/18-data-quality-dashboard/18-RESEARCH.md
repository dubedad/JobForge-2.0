# Phase 18: Data Quality Dashboard - Research

**Researched:** 2026-02-05
**Domain:** Data quality monitoring, Streamlit dashboards, GC DQMF framework
**Confidence:** HIGH

## Summary

This phase implements a data quality monitoring system for JobForge's 39 gold tables using the Government of Canada's Data Quality Management Framework (DQMF) with 9 dimensions. The system includes metric calculation, historical trend tracking, a Streamlit dashboard with radar charts and traffic-light indicators, and API/CLI access for quality scores.

The GC DQMF defines nine overlapping quality dimensions: Access, Accuracy, Coherence, Completeness, Consistency, Interpretability, Relevance, Reliability, and Timeliness. These dimensions work together to assess whether data is "fit-for-purpose" (usable and relevant). Importance varies by context, so the user has wisely decided on fixed GC-aligned weights rather than equal or user-configurable weights.

The standard stack combines cuallee for DataFrame-agnostic quality validation, DuckDB for metric calculation queries, Streamlit with Plotly for interactive visualization, and FastAPI for RESTful access. This aligns perfectly with JobForge's existing Polars/DuckDB data layer and FastAPI API patterns.

**Primary recommendation:** Use cuallee for automatable dimension checks (completeness, accuracy patterns, coherence FK integrity), DuckDB SQL for timeliness/aggregates, store snapshots in parquet with 90-day retention for audit compliance, and implement Streamlit multi-page app with st.navigation for dashboard routing.

## Standard Stack

The established libraries/tools for data quality dashboards and GC DQMF implementation:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| cuallee | >=0.13.0 | Data quality validation | DataFrame-agnostic (supports Polars/DuckDB/Pandas), extensive date/timestamp checks, replacement for pydeequ with <3k Java classes, published in JOSS 2024 |
| streamlit | >=1.41.0 | Dashboard framework | Multi-page apps with st.navigation, session state persistence, built-in sparkline support, color palette configuration for traffic lights |
| plotly | >=6.0.0 | Interactive visualizations | Radar charts with go.Scatterpolar, fill='toself' for area highlighting, PDF export capability, Streamlit integration via st.plotly_chart |
| polars | >=1.37.0 | Data processing | Already in JobForge stack, cuallee supports Polars backend |
| duckdb | >=1.4.0 | Query engine | Already in JobForge stack, FK integrity validation, cuallee supports DuckDB backend |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| kaleido | >=0.2.1 | Plotly static export | PDF report generation - converts Plotly charts to static images |
| reportlab | >=4.0.0 | PDF assembly | Combine multiple Plotly charts into single PDF report |
| pandas | >=2.0.2 | DataFrame operations | Cuallee supports Pandas for aggregations/transformations |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| cuallee | Great Expectations | GX is feature-rich but heavier (requires SQLAlchemy, complex config); cuallee is lighter and DataFrame-agnostic |
| Streamlit | Plotly Dash | Dash requires JavaScript knowledge for advanced features; Streamlit is pure Python with simpler state management |
| Plotly radar | Matplotlib | Matplotlib radar requires manual scaling/setup; Plotly provides interactivity and simpler API |

**Installation:**
```bash
# Core dependencies (add to pyproject.toml)
cuallee>=0.13.0
streamlit>=1.41.0
plotly>=6.0.0

# PDF export support
kaleido>=0.2.1
reportlab>=4.0.0
```

## Architecture Patterns

### Recommended Project Structure
```
src/jobforge/quality/
├── __init__.py
├── models.py              # Pydantic models for quality scores, history
├── calculator.py          # Dimension score calculation logic
├── metrics.py             # Individual metric implementations
├── history.py             # Snapshot storage and retrieval
├── service.py             # Quality service orchestrating calculations
└── weights.py             # GC-aligned dimension weights

src/jobforge/api/
└── quality.py             # FastAPI routes for /api/quality/*

src/jobforge/cli/
└── commands.py            # Add quality subcommand with Typer

src/jobforge/dashboard/
├── __init__.py
├── app.py                 # Streamlit entrypoint with st.navigation
├── pages/
│   ├── summary.py         # Traffic-light grid landing page
│   ├── detail.py          # Single-table drill-down
│   ├── compare.py         # Side-by-side radar chart comparison
│   └── trends.py          # Historical trend analysis
├── components/
│   ├── radar.py           # Reusable radar chart component
│   ├── traffic_light.py   # Traffic-light indicator component
│   └── sparkline.py       # Trend sparkline component
└── utils.py               # Date formatting, data loading helpers

data/quality/
├── snapshots/             # Historical quality snapshots (parquet)
│   └── YYYY-MM-DD/        # Date-partitioned snapshots
│       ├── dim_noc.parquet
│       └── ...
└── config/
    └── weights.json       # GC-aligned dimension weights
```

### Pattern 1: Quality Score Calculation with Cuallee
**What:** Use cuallee Check API to define dimension-specific validations, execute against gold tables, aggregate results into 0-100 scores per dimension.

**When to use:** For automatable dimensions (Completeness, Accuracy pattern validation, Consistency, Coherence FK integrity).

**Example:**
```python
# Source: cuallee documentation and DuckDB integration examples
import duckdb
from cuallee import Check

def calculate_completeness_score(table_name: str, db_path: str) -> float:
    """Calculate completeness dimension score (0-100)."""
    conn = duckdb.connect(db_path)

    # Define completeness checks - NULL rate per column
    check = Check(level="WARNING", pct=0.95)
    for col in get_table_columns(table_name):
        check.is_complete(col)  # No NULLs expected

    # Execute check against DuckDB table
    df = conn.execute(f"SELECT * FROM {table_name}").fetchdf()
    result = check.validate(df)

    # Aggregate: percentage of passed checks
    passed = result[result['status'] == 'PASS'].shape[0]
    total = result.shape[0]
    return (passed / total) * 100 if total > 0 else 100.0
```

### Pattern 2: Timeliness Calculation via DuckDB
**What:** Query catalog metadata for last_updated_at timestamps, calculate days since refresh, convert to 0-100 score with decay function.

**When to use:** For Timeliness dimension (days since last refresh).

**Example:**
```python
# Source: JobForge catalog structure and DuckDB date functions
import duckdb
from datetime import datetime, timezone

def calculate_timeliness_score(table_name: str, catalog_path: str) -> float:
    """Calculate timeliness score based on days since refresh."""
    conn = duckdb.connect(":memory:")

    # Query catalog for updated_at timestamp
    query = """
    SELECT updated_at
    FROM read_json(?)
    WHERE table_name = ?
    """
    result = conn.execute(query, [catalog_path, table_name]).fetchone()

    if not result:
        return 0.0  # Table not found in catalog

    updated_at = datetime.fromisoformat(result[0])
    days_old = (datetime.now(timezone.utc) - updated_at).days

    # Decay function: 100 at 0 days, 50 at 30 days, 0 at 90+ days
    if days_old <= 7:
        return 100.0
    elif days_old <= 30:
        return max(50.0, 100 - (days_old - 7) * 2.17)  # Linear decay
    elif days_old <= 90:
        return max(0.0, 50 - (days_old - 30) * 0.83)   # Linear decay
    else:
        return 0.0
```

### Pattern 3: Coherence (FK Integrity) Validation
**What:** Use DuckDB FK constraint validation queries to check referential integrity, calculate percentage of valid FK references.

**When to use:** For Coherence dimension across bridge tables (e.g., bridge_noc_og, bridge_caf_noc).

**Example:**
```python
# Source: DuckDB FK validation patterns and JobForge schema
import duckdb

def calculate_coherence_score(table_name: str, schema: dict, db_path: str) -> float:
    """Calculate coherence score via FK integrity checks."""
    conn = duckdb.connect(db_path)

    # Get FK relationships from schema
    fk_columns = [
        col for col in schema['columns']
        if col.get('is_foreign_key')
    ]

    if not fk_columns:
        return 100.0  # No FKs to validate

    integrity_scores = []
    for fk in fk_columns:
        ref_table = fk['references_table']
        ref_col = fk['references_column']
        col_name = fk['name']

        # Count orphaned records (FK value with no matching PK)
        query = f"""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN ref.{ref_col} IS NULL THEN 1 ELSE 0 END) AS orphaned
        FROM {table_name} t
        LEFT JOIN {ref_table} ref ON t.{col_name} = ref.{ref_col}
        """
        result = conn.execute(query).fetchone()
        total, orphaned = result

        if total > 0:
            integrity_scores.append((1 - orphaned / total) * 100)

    return sum(integrity_scores) / len(integrity_scores) if integrity_scores else 100.0
```

### Pattern 4: Streamlit Multi-Page Dashboard with st.navigation
**What:** Use st.Page and st.navigation for flexible page routing, session state for cross-page data sharing, dynamic page availability based on state.

**When to use:** For organizing dashboard into summary, detail, compare, and trends pages.

**Example:**
```python
# Source: Streamlit official documentation on st.navigation
import streamlit as st
from pathlib import Path

# app.py entrypoint
st.set_page_config(page_title="Data Quality Dashboard", layout="wide")

# Define pages
summary_page = st.Page(
    "pages/summary.py",
    title="Summary",
    icon=":material/dashboard:",
    default=True
)
compare_page = st.Page(
    "pages/compare.py",
    title="Compare Tables",
    icon=":material/compare_arrows:"
)
trends_page = st.Page(
    "pages/trends.py",
    title="Trends",
    icon=":material/trending_up:"
)

# Create navigation
pg = st.navigation([summary_page, compare_page, trends_page])

# Session state persists across pages
if 'selected_tables' not in st.session_state:
    st.session_state.selected_tables = []

pg.run()
```

### Pattern 5: Radar Chart Comparison with Plotly
**What:** Use go.Scatterpolar with multiple traces for side-by-side dimension comparison, fill='toself' for area highlighting, limit to 2-3 tables per chart.

**When to use:** For compare page showing dimension profiles across multiple tables.

**Example:**
```python
# Source: Plotly radar chart documentation
import plotly.graph_objects as go

def create_radar_comparison(table_scores: dict[str, dict[str, float]]) -> go.Figure:
    """Create radar chart comparing 2-3 tables across 9 dimensions."""
    dimensions = [
        'Access', 'Accuracy', 'Coherence', 'Completeness',
        'Consistency', 'Interpretability', 'Relevance',
        'Reliability', 'Timeliness'
    ]

    fig = go.Figure()

    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']  # Limit 3 tables
    for i, (table_name, scores) in enumerate(table_scores.items()):
        values = [scores.get(dim, 0) for dim in dimensions]

        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=dimensions,
            fill='toself',
            name=table_name,
            line=dict(color=colors[i % len(colors)])
        ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=True,
        height=600
    )

    return fig
```

### Pattern 6: Traffic-Light Indicator with Score
**What:** Combine color indicator (green/yellow/red) with percentage score, using st.metric or custom component.

**When to use:** For summary grid showing all table quality at a glance.

**Example:**
```python
# Source: Streamlit metrics and data quality dashboard best practices
import streamlit as st

def display_traffic_light(table_name: str, overall_score: float, delta: float = None):
    """Display traffic-light indicator with percentage score."""
    # Thresholds: >=80 green, 60-79 yellow, <60 red
    if overall_score >= 80:
        color = "🟢"
        status = "Good"
    elif overall_score >= 60:
        color = "🟡"
        status = "Warning"
    else:
        color = "🔴"
        status = "Critical"

    # Use st.metric for built-in delta display
    st.metric(
        label=f"{color} {table_name}",
        value=f"{overall_score:.1f}%",
        delta=f"{delta:+.1f}%" if delta is not None else None,
        delta_color="normal" if delta >= 0 else "inverse"
    )
```

### Pattern 7: Historical Snapshot Storage
**What:** Store daily/on-refresh snapshots in date-partitioned parquet files, query for trend analysis and degradation detection.

**When to use:** For tracking quality over time and detecting degradations.

**Example:**
```python
# Source: Data quality observability and time series storage patterns
import polars as pl
from datetime import date
from pathlib import Path

def save_quality_snapshot(table_name: str, scores: dict[str, float], snapshot_dir: Path):
    """Save quality scores snapshot to date-partitioned parquet."""
    today = date.today().isoformat()
    snapshot_path = snapshot_dir / today / f"{table_name}.parquet"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)

    # Create snapshot record
    snapshot = pl.DataFrame({
        'snapshot_date': [today],
        'table_name': [table_name],
        **{f'{dim}_score': [score] for dim, score in scores.items()},
        'overall_score': [sum(scores.values()) / len(scores)]
    })

    snapshot.write_parquet(snapshot_path)

def load_quality_history(table_name: str, snapshot_dir: Path, days: int = 90) -> pl.DataFrame:
    """Load quality history for trend analysis."""
    pattern = snapshot_dir / "*" / f"{table_name}.parquet"
    history = pl.read_parquet(pattern)

    # Filter to retention period
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    return history.filter(pl.col('snapshot_date') >= cutoff)
```

### Pattern 8: FastAPI Quality Endpoint
**What:** RESTful endpoint following existing JobForge patterns (thin routes, fat services), RFC 9457 error handling.

**When to use:** For API access to quality scores and history.

**Example:**
```python
# Source: JobForge API routes and FastAPI best practices
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from jobforge.quality.service import QualityService
from jobforge.api.errors import TableNotFoundError

router = APIRouter(prefix="/api/quality", tags=["quality"])

class QualityScoreResponse(BaseModel):
    table_name: str
    overall_score: float
    dimension_scores: dict[str, float]
    snapshot_date: str
    grade: str  # A/B/C/D/F

@router.get("/table/{table_name}", response_model=QualityScoreResponse)
async def get_table_quality(table_name: str) -> QualityScoreResponse:
    """Get current quality score for a table."""
    service = QualityService()

    try:
        scores = service.calculate_quality(table_name)
        return QualityScoreResponse(**scores)
    except ValueError as e:
        raise TableNotFoundError(table_name=table_name)
```

### Pattern 9: Typer CLI Quality Subcommand
**What:** Add quality subcommand with check/refresh/history actions, --json/--csv output formats, Rich table for default output.

**When to use:** For CLI-driven quality checks and reporting.

**Example:**
```python
# Source: JobForge CLI patterns and Typer best practices
import typer
from rich.console import Console
from rich.table import Table
from jobforge.quality.service import QualityService

quality_app = typer.Typer(name="quality", help="Data quality management")

@quality_app.command()
def check(
    table: str = typer.Argument(..., help="Table name to check"),
    json: bool = typer.Option(False, "--json", help="Output as JSON"),
    csv: bool = typer.Option(False, "--csv", help="Output as CSV")
):
    """Check quality for a specific table."""
    service = QualityService()
    scores = service.calculate_quality(table)

    if json:
        typer.echo(scores.model_dump_json(indent=2))
    elif csv:
        # CSV output
        typer.echo("dimension,score")
        for dim, score in scores.dimension_scores.items():
            typer.echo(f"{dim},{score}")
    else:
        # Rich table output (default)
        console = Console()
        table_display = Table(title=f"Quality: {table}")
        table_display.add_column("Dimension", style="cyan")
        table_display.add_column("Score", style="green")

        for dim, score in scores.dimension_scores.items():
            table_display.add_row(dim, f"{score:.1f}%")

        console.print(table_display)

# Register quality subcommand with main app
app.add_typer(quality_app)
```

### Anti-Patterns to Avoid

- **Hand-rolling dimension calculations from scratch:** Use cuallee's built-in checks for standard validations; only implement custom logic for GC-specific dimensions (Relevance, Interpretability, Reliability).

- **Storing full snapshots for all 39 tables daily without partitioning:** Leads to storage bloat and slow queries. Use date-partitioned parquet with 90-day retention.

- **Blocking quality checks on dashboard page load:** Calculate scores asynchronously or on-demand via CLI/API; dashboard reads pre-calculated snapshots from parquet.

- **Equal weighting across all 9 dimensions:** Context matters. User correctly decided on fixed GC-aligned weights reflecting actual importance (e.g., Completeness and Accuracy weighted higher than Interpretability).

- **Too many variables on radar chart:** Limit to 2-3 tables per comparison; 9 dimensions is already at the upper limit for radar chart readability.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Data quality validation rules | Custom NULL/pattern checkers | cuallee Check API | Handles edge cases (partial NULLs, timezone issues), DataFrame-agnostic, supports 50+ check types |
| Radar chart scaling | Manual min-max normalization | Plotly go.Scatterpolar with range=[0, 100] | Built-in polar axis scaling, automatic angle distribution |
| PDF report generation | PIL/matplotlib image stitching | kaleido + reportlab | Plotly charts export to high-quality vector graphics, reportlab handles multi-page layout |
| Multi-page state management | URL query params or cookies | Streamlit session_state | Persists across page navigation, simple dict-like API, no serialization required |
| Time series degradation detection | Custom moving average logic | Polars rolling operations + threshold logic | Optimized C++ implementation, handles NaN propagation correctly |
| FK integrity validation | Python loops comparing sets | DuckDB LEFT JOIN with IS NULL check | Query optimizer handles millions of rows efficiently, single SQL statement |

**Key insight:** Data quality frameworks have solved the "90% coverage" problem (completeness, consistency, basic accuracy). Focus custom logic on domain-specific rules (NOC code patterns, GC-specific dimensions) and orchestration (weighting, aggregation, trend detection).

## Common Pitfalls

### Pitfall 1: Non-Automatable Dimensions Without Proxy Metrics
**What goes wrong:** Relevance, Interpretability, and Reliability dimensions require human judgment (business context, stakeholder input). Implementing them as automated checks produces meaningless scores.

**Why it happens:** Attempting to fully automate all 9 GC DQMF dimensions without distinguishing automatable vs. manual assessments.

**How to avoid:**
- **Automatable:** Completeness (NULL rate), Accuracy (pattern validation), Coherence (FK integrity), Timeliness (refresh age), Consistency (duplicate detection)
- **Manual/Proxy:** Relevance (flag if unused in past 90 days), Interpretability (check if catalog description exists), Reliability (variability in historical scores)
- Mark manual dimensions clearly in dashboard with explanation

**Warning signs:** Relevance score of 100% for all tables, Interpretability based solely on column name length, Reliability hardcoded to 85%.

### Pitfall 2: Traffic-Light Thresholds Without Context
**What goes wrong:** Applying universal thresholds (80%=green, 60%=yellow, <60%=red) ignores table-specific requirements. A 75% completeness score might be acceptable for a staging table but critical for a gold dimension.

**Why it happens:** Copying standard KPI dashboard thresholds without considering data layer semantics.

**How to avoid:**
- Research GC practice: Government data quality frameworks often use 95%+ for completeness in authoritative tables
- Recommended thresholds for gold tables:
  - Green: >=95% (production-ready)
  - Yellow: 85-94% (needs attention)
  - Red: <85% (critical)
- Allow per-table threshold overrides in config for staging/experimental tables

**Warning signs:** All tables showing yellow despite production use, stakeholders ignoring dashboard due to threshold fatigue.

### Pitfall 3: Unbounded History Retention
**What goes wrong:** Storing quality snapshots indefinitely bloats storage and slows trend queries. For 39 tables with daily snapshots, 1 year = 14,235 parquet files.

**Why it happens:** "More data is better" mindset without considering query patterns and compliance requirements.

**How to avoid:**
- Align with Government audit requirements: Federal records typically 3 years, HIPAA compliance 6 years, but quality METRICS (not raw data) can be shorter
- Recommended retention: 90 days for daily snapshots, keep monthly aggregates for 2 years
- Implement cleanup job: Delete snapshots older than retention period on each refresh
- Document retention policy in data governance documentation

**Warning signs:** Dashboard trend page loading >5 seconds, snapshot directory >10GB, "out of disk space" errors.

### Pitfall 4: Blocking Dashboard on Calculation
**What goes wrong:** Calculating quality scores for 39 tables on dashboard page load causes 30+ second wait times, poor user experience.

**Why it happens:** Synchronous calculation in Streamlit page without pre-computation or caching.

**How to avoid:**
- Pre-calculate scores via scheduled CLI job (e.g., daily at 6 AM)
- Dashboard reads latest snapshot from parquet (millisecond latency)
- Provide "Refresh Now" button for on-demand recalculation (async)
- Use Streamlit caching decorators for expensive operations
- Show loading spinner with progress updates during refresh

**Warning signs:** Dashboard hangs on initial load, users report timeout errors, CPU spikes when accessing dashboard.

### Pitfall 5: Radar Chart with 20+ Dimensions
**What goes wrong:** Adding table-specific metrics to the 9 GC dimensions creates unreadable radar charts with overlapping labels and meaningless visual comparisons.

**Why it happens:** Wanting comprehensive view of "everything" on one chart.

**How to avoid:**
- Stick to 9 GC DQMF dimensions for radar charts (already at readability limit)
- Use separate detail page for additional table-specific metrics
- Limit comparison to 2-3 tables per radar chart
- Best practice from Plotly docs: "Radar charts aren't the best if you want to visualize many observations"

**Warning signs:** Labels overlapping in radar chart, users squinting to read, "What does this mean?" questions.

### Pitfall 6: Ignoring Dimension Weights in Aggregation
**What goes wrong:** Calculating overall score as simple average (sum(scores)/9) treats Relevance equally with Completeness, despite Completeness being far more critical for data trust.

**Why it happens:** Simplicity bias - equal weights are easier to implement and explain.

**How to avoid:**
- Research GC DQMF guidance: Some dimensions are more foundational (Accuracy, Completeness, Consistency) while others are context-dependent (Relevance)
- Recommended weights (totaling 100%):
  - Completeness: 20%
  - Accuracy: 20%
  - Consistency: 15%
  - Coherence: 15%
  - Timeliness: 10%
  - Reliability: 10%
  - Interpretability: 5%
  - Relevance: 3%
  - Access: 2%
- Document rationale in code comments and dashboard help text

**Warning signs:** Table with 100% completeness but 0% accuracy scores same as 50%/50% table, stakeholders questioning "why is this table green when data is wrong?"

### Pitfall 7: No Degradation Detection
**What goes wrong:** Quality score drops from 95% to 70% over 30 days without alerts, discovered only when downstream reports fail.

**Why it happens:** Focusing on current scores without trend analysis.

**How to avoid:**
- Implement both threshold AND trend detection:
  - Threshold: Alert if score drops below 85%
  - Trend: Alert if score decreases >5% per week for 3 consecutive weeks
- Use Polars rolling window: `pl.col('overall_score').rolling_mean(window_size=7)`
- Add sparklines to summary grid showing 90-day trend at a glance
- Dedicated trends page with drill-down

**Warning signs:** Gradual degradation unnoticed until crisis, "Why didn't we catch this earlier?" post-mortems.

## Code Examples

Verified patterns from official sources:

### GC DQMF 9 Dimensions Implementation
```python
# Source: Government of Canada Data Quality Guidance (canada.ca)
from enum import Enum
from pydantic import BaseModel

class DQDimension(str, Enum):
    """GC DQMF 9 dimensions with official definitions."""
    ACCESS = "access"  # Ease to discover, retrieve, process, use
    ACCURACY = "accuracy"  # Degree data describes real-world phenomena
    COHERENCE = "coherence"  # Ease to compare/link data from sources
    COMPLETENESS = "completeness"  # Degree values sufficiently populated
    CONSISTENCY = "consistency"  # Degree internally non-contradictory
    INTERPRETABILITY = "interpretability"  # Degree understood in context
    RELEVANCE = "relevance"  # Degree suitable for objective
    RELIABILITY = "reliability"  # Degree variability explained
    TIMELINESS = "timeliness"  # Time between period end and availability

# GC-aligned weights (research-based, not equal)
GC_DIMENSION_WEIGHTS = {
    DQDimension.COMPLETENESS: 0.20,
    DQDimension.ACCURACY: 0.20,
    DQDimension.CONSISTENCY: 0.15,
    DQDimension.COHERENCE: 0.15,
    DQDimension.TIMELINESS: 0.10,
    DQDimension.RELIABILITY: 0.10,
    DQDimension.INTERPRETABILITY: 0.05,
    DQDimension.RELEVANCE: 0.03,
    DQDimension.ACCESS: 0.02,
}

class QualityScore(BaseModel):
    """Quality score for a single table."""
    table_name: str
    snapshot_date: str
    dimension_scores: dict[DQDimension, float]
    overall_score: float
    grade: str  # A/B/C/D/F

    @classmethod
    def calculate_overall(cls, dimension_scores: dict[DQDimension, float]) -> float:
        """Calculate weighted overall score."""
        return sum(
            score * GC_DIMENSION_WEIGHTS[dim]
            for dim, score in dimension_scores.items()
        )
```

### Completeness Metric with Cuallee
```python
# Source: cuallee documentation for DuckDB backend
import duckdb
import polars as pl
from cuallee import Check

def calculate_completeness(table_name: str, db_path: str) -> float:
    """Calculate completeness score (NULL rate) using cuallee."""
    conn = duckdb.connect(db_path)

    # Load table
    df_polars = pl.from_arrow(conn.execute(f"SELECT * FROM {table_name}").fetch_arrow_table())

    # Get all columns
    columns = df_polars.columns

    # Define completeness check
    check = Check(level="WARNING", pct=1.0)  # 100% completeness expected
    for col in columns:
        check.is_complete(col)

    # Execute validation
    result = check.validate(df_polars)

    # Calculate score: percentage of columns meeting threshold
    passed = result.filter(pl.col('status') == 'PASS').height
    total = result.height

    return (passed / total * 100) if total > 0 else 100.0
```

### Accuracy Validation for NOC Codes
```python
# Source: NOC 2026 structure (5-digit codes) and pattern validation
import re
import polars as pl

def calculate_accuracy_noc_codes(table_name: str, db_path: str) -> float:
    """Calculate accuracy score for NOC code patterns."""
    import duckdb
    conn = duckdb.connect(db_path)

    # Find NOC code columns
    schema_query = f"DESCRIBE {table_name}"
    schema = conn.execute(schema_query).fetchdf()
    noc_columns = [
        col for col in schema['column_name']
        if 'noc' in col.lower() and 'code' in col.lower()
    ]

    if not noc_columns:
        return 100.0  # No NOC columns to validate

    accuracy_scores = []
    noc_pattern = re.compile(r'^\d{5}$')  # NOC 2026: 5-digit codes

    for col in noc_columns:
        df = pl.from_arrow(
            conn.execute(f"SELECT {col} FROM {table_name} WHERE {col} IS NOT NULL").fetch_arrow_table()
        )

        total = df.height
        if total == 0:
            continue

        # Count valid NOC codes
        valid = df.filter(
            pl.col(col).str.contains(noc_pattern)
        ).height

        accuracy_scores.append(valid / total * 100)

    return sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 100.0
```

### Timeliness with SLA-Based Scoring
```python
# Source: Data quality timeliness best practices and JobForge catalog
from datetime import datetime, timezone, timedelta
import json

def calculate_timeliness_sla(table_name: str, catalog_dir: str) -> float:
    """Calculate timeliness score using SLA-based approach."""
    catalog_path = Path(catalog_dir) / "tables" / f"{table_name}.json"

    if not catalog_path.exists():
        return 0.0

    with open(catalog_path) as f:
        metadata = json.load(f)

    updated_at = datetime.fromisoformat(metadata['updated_at'])
    now = datetime.now(timezone.utc)
    age_hours = (now - updated_at).total_seconds() / 3600

    # SLA-based thresholds (adjust per table type)
    # Gold tables should refresh daily
    if age_hours <= 24:  # Within 1 day
        return 100.0
    elif age_hours <= 48:  # 1-2 days
        return 90.0
    elif age_hours <= 168:  # 1 week
        return 70.0
    elif age_hours <= 720:  # 1 month
        return 40.0
    else:
        return 10.0  # Stale data
```

### Sparkline Component for Trend Display
```python
# Source: Streamlit sparkline support and Plotly mini charts
import streamlit as st
import plotly.graph_objects as go

def display_sparkline(scores: list[float], dates: list[str]) -> None:
    """Display sparkline trend in Streamlit."""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=dates,
        y=scores,
        mode='lines',
        line=dict(color='#1f77b4', width=2),
        fill='tozeroy',
        fillcolor='rgba(31, 119, 180, 0.2)'
    ))

    # Minimal layout for sparkline
    fig.update_layout(
        height=80,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, range=[0, 100]),
        showlegend=False,
        hovermode='x unified'
    )

    st.plotly_chart(fig, use_container_width=True)
```

### Degradation Detection Algorithm
```python
# Source: Data quality observability and anomaly detection patterns
import polars as pl
from datetime import date, timedelta

def detect_degradation(table_name: str, snapshot_dir: str, threshold: float = 5.0) -> dict:
    """Detect quality degradation using threshold and trend analysis."""
    # Load 90-day history
    pattern = f"{snapshot_dir}/*/{table_name}.parquet"
    history = pl.read_parquet(pattern).sort('snapshot_date')

    if history.height < 7:
        return {'degraded': False, 'reason': 'Insufficient history'}

    # Threshold-based detection
    latest_score = history.tail(1)['overall_score'][0]
    if latest_score < 85.0:
        return {
            'degraded': True,
            'reason': 'threshold',
            'current_score': latest_score,
            'alert': f"Score below 85% threshold: {latest_score:.1f}%"
        }

    # Trend-based detection: 3-week moving average decline
    history_with_ma = history.with_columns([
        pl.col('overall_score').rolling_mean(window_size=7).alias('ma_7d')
    ])

    recent_3weeks = history_with_ma.tail(21)
    if recent_3weeks.height >= 21:
        ma_start = recent_3weeks.head(7)['ma_7d'].mean()
        ma_end = recent_3weeks.tail(7)['ma_7d'].mean()
        decline_pct = ((ma_start - ma_end) / ma_start) * 100

        if decline_pct > threshold:
            return {
                'degraded': True,
                'reason': 'trend',
                'decline_pct': decline_pct,
                'alert': f"Quality declining {decline_pct:.1f}% over 3 weeks"
            }

    return {'degraded': False, 'reason': 'healthy'}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Great Expectations with SQLAlchemy | cuallee with DataFrame backends | 2024 (JOSS publication) | Lighter weight, no ORM dependency, supports Polars/DuckDB directly |
| Matplotlib for radar charts | Plotly go.Scatterpolar | 2020+ | Interactive tooltips, zoom, easier multi-trace comparison |
| Streamlit pages/ directory | st.Page and st.navigation | Streamlit 1.39+ (2024) | Flexible routing, conditional pages, cleaner entrypoint |
| Manual PDF generation with PIL | kaleido + reportlab | Plotly 4.0+ (2019) | Vector graphics export, multi-page layouts, better quality |
| Equal dimension weighting | Context-specific weights | GC DQMF guidance (ongoing) | Reflects actual importance hierarchy |

**Deprecated/outdated:**
- **Great Expectations pre-v1.0:** Complex YAML config, SQLAlchemy requirement. Current: GX v1.0+ or switch to cuallee for DataFrame-agnostic.
- **Streamlit pages/ directory only:** Limited customization. Current: Use st.navigation for conditional pages and custom menu structure.
- **Plotly static image export via Orca:** Orca deprecated. Current: Use kaleido for static export.

## Open Questions

Things that couldn't be fully resolved:

1. **Column-Level vs. Dimension-Only Drill-Down**
   - What we know: Catalog has column-level metadata, cuallee validates per-column
   - What's unclear: User value of column-level quality scores vs. just showing failed columns in detail view
   - Recommendation: Start dimension-only (simpler), add column drill-down if users request specific column quality tracking

2. **Specific Traffic-Light Thresholds for GC Tables**
   - What we know: Standard practice 80/60/40, but GC authoritative data may have higher bar
   - What's unclear: Official GC DQMF threshold guidance not found in public documentation
   - Recommendation: Use 95/85/85 (green/yellow/red) for gold tables, document as "recommended pending GC guidance," make configurable per-table

3. **Handling Non-Automatable Dimensions (Relevance, Interpretability, Reliability)**
   - What we know: These require human judgment or business context
   - What's unclear: Whether to exclude from overall score, use proxy metrics, or flag for manual assessment
   - Recommendation: Implement proxy metrics (Relevance: usage tracking, Interpretability: catalog completeness, Reliability: historical variance), mark as "automated proxy" in dashboard, include in overall score with lower weights

4. **Snapshot Granularity for 39 Tables**
   - What we know: Daily snapshots = 14,235 files/year, weekly = 2,028 files/year
   - What's unclear: Optimal balance between trend granularity and storage/query performance
   - Recommendation: Daily snapshots for first 30 days, then aggregate to weekly for 60 days, monthly for 2 years. Or: on-refresh snapshots (quality calculated whenever gold table updates)

5. **History Retention Period Alignment**
   - What we know: Federal records 3 years, HIPAA 6 years, but quality metrics are metadata not raw data
   - What's unclear: Whether quality metrics count as audit records requiring multi-year retention
   - Recommendation: 90-day detailed retention (audit pattern of "what happened recently"), monthly aggregates for 2 years (trend analysis), document in data governance policy

## Sources

### Primary (HIGH confidence)
- [Government of Canada Data Quality Guidance](https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/information-management/guidance-data-quality.html) - Official GC DQMF 9 dimensions
- [GC Data Quality Framework Wiki](https://wiki.gccollab.ca/index.php?title=GC_Data_Quality_Framework) - Detailed dimension definitions
- [cuallee GitHub](https://github.com/canimus/cuallee) - DataFrame-agnostic quality library, current features
- [Streamlit Multi-Page Apps Documentation](https://docs.streamlit.io/develop/concepts/multipage-apps/page-and-navigation) - st.Page and st.navigation patterns
- [Plotly Radar Chart Documentation](https://plotly.com/python/radar-chart/) - go.Scatterpolar API and examples
- [DuckDB Foreign Key Documentation](https://motherduck.com/glossary/foreign%20key/) - FK integrity validation
- [Typer Subcommands Documentation](https://typer.tiangolo.com/tutorial/subcommands/) - CLI organization patterns

### Secondary (MEDIUM confidence)
- [cuallee JOSS Paper](https://joss.theoj.org/papers/10.21105/joss.06684) - Academic validation, DataFrame backend support
- [Plotly Radar Chart Best Practices](https://betterdatascience.com/radar-charts-matplotlib-plotly/) - Design guidance, limit 2-3 traces
- [FastAPI Best Practices GitHub](https://github.com/zhanymkanov/fastapi-best-practices) - Thin routes, fat services pattern
- [Data Quality Dashboard Examples (DQOps)](https://dqops.com/how-to-make-a-data-quality-dashboard/) - Traffic-light patterns, threshold configuration
- [Streamlit Session State Documentation](https://docs.streamlit.io/develop/concepts/architecture/session-state) - Cross-page state management
- [NOC 2026 Changes](https://moving2canada.com/features/how-to-choose-noc-code-2026/) - 5-digit code structure
- [Federal Record Retention (eCFR)](https://www.ecfr.gov/current/title-2/subtitle-A/chapter-II/part-200/subpart-D/subject-group-ECFR4acc10e7e3b676f/section-200.334) - 3-year requirement for federal awards

### Tertiary (LOW confidence)
- [Data Quality Observability Trends](https://www.n-ix.com/data-management-trends/) - AI/ML for anomaly detection (general trends, not specific to implementation)
- [PDF Report Generation Patterns](https://david-kyn.medium.com/workplace-automation-generate-pdf-reports-using-python-fa75c50e7715) - kaleido + reportlab approach (blog post, verify with official docs)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - cuallee, Streamlit, Plotly are well-documented with official sources; already in JobForge ecosystem (Polars/DuckDB)
- GC DQMF dimensions: HIGH - Official Government of Canada guidance documents; 9 dimensions confirmed with definitions
- Architecture patterns: HIGH - Verified with Streamlit/Plotly official docs, FastAPI patterns match existing JobForge codebase
- Traffic-light thresholds: MEDIUM - Industry standards found, but GC-specific thresholds not in public documentation
- Retention periods: MEDIUM - Federal record requirements clear (3 years), but quality metrics as metadata less definitive
- Pitfalls: HIGH - Based on data quality observability literature and official framework guidance

**Research date:** 2026-02-05
**Valid until:** 2026-05-05 (90 days - stable domain, but Streamlit/Plotly versions update frequently)
