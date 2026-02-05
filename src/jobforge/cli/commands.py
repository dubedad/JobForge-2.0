"""JobForge CLI commands.

This module provides Typer-based CLI commands for the JobForge platform.

Commands:
    stagegold: Deploy WiQ semantic model to Power BI
    lineage: Answer lineage questions about the WiQ data pipeline
    demo: Start demo web server for live deployment narration
    api: Start the Query API server for conversational data/metadata queries
    compliance: Generate governance compliance traceability logs
    caf: CAF data management commands (refresh, status)

Example:
    $ jobforge stagegold
    $ jobforge stagegold --dry-run
    $ jobforge lineage "Where does dim_noc come from?"
    $ jobforge api                              # Start Query API on localhost:8000
    $ jobforge api -p 8080                      # Custom port
    $ jobforge compliance dadm --summary
    $ jobforge compliance dama -o dama_compliance.json
    $ jobforge caf status                       # Show CAF table status
    $ jobforge caf refresh                      # Refresh CAF data
"""

from pathlib import Path
from typing import Optional

import typer

from jobforge.deployment import DeploymentUI, WiQDeployer

app = typer.Typer(
    name="jobforge",
    help="JobForge workforce intelligence platform CLI",
    add_completion=False,
)


@app.command()
def stagegold(
    schema_path: Optional[Path] = typer.Option(
        None,
        "--schema",
        "-s",
        help="Path to WiQ schema JSON (default: data/catalog/schemas/wiq_schema.json)",
        exists=False,
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show deployment plan without executing",
    ),
) -> None:
    """Deploy WiQ semantic model to Power BI.

    Deploys all tables and relationships from the WiQ schema to Power BI
    using the Power BI MCP Server. The deployment is narrated in the terminal
    for live demo presentations.

    The command outputs deployment specifications that Claude Code executes
    via MCP tool calls to create the actual tables and relationships in
    Power BI.

    Examples:
        # Show deployment plan
        jobforge stagegold --dry-run

        # Deploy with default schema
        jobforge stagegold

        # Deploy with custom schema
        jobforge stagegold --schema custom_schema.json
    """
    ui = DeploymentUI()
    deployer = WiQDeployer(ui=ui)

    # Validate schema path if provided
    if schema_path is not None and not schema_path.exists():
        typer.echo(f"Error: Schema file not found: {schema_path}", err=True)
        raise typer.Exit(code=1)

    # Load schema
    try:
        schema = deployer.load_schema(schema_path)
    except Exception as e:
        typer.echo(f"Error loading schema: {e}", err=True)
        raise typer.Exit(code=1)

    if dry_run:
        # Show deployment plan only
        typer.echo(deployer.generate_deployment_script(schema_path))
        return

    # Display header
    ui.show_header()

    # Generate and display deployment specs
    table_specs = deployer.generate_table_specs(schema)
    rel_specs = deployer.generate_relationship_specs(schema)

    # Output specs for Claude to execute via MCP
    typer.echo()
    typer.echo("--- DEPLOYMENT SPECS FOR MCP EXECUTION ---")
    typer.echo(f"Tables to create: {len(table_specs)}")
    typer.echo(f"Relationships to create: {len(rel_specs)}")
    typer.echo()

    # Print deployment script for Claude Code to execute
    typer.echo(deployer.generate_deployment_script(schema_path))


@app.command()
def lineage(
    question: str = typer.Argument(
        ...,
        help="Lineage question to answer (e.g., 'Where does dim_noc come from?')",
    ),
) -> None:
    """Answer lineage questions about the WiQ data pipeline.

    Query the lineage graph to understand data flow and provenance.
    Supports natural language questions about upstream/downstream
    dependencies, transformation paths, and full lineage.

    Examples:
        # Upstream lineage (where data comes from)
        jobforge lineage "Where does dim_noc come from?"
        jobforge lineage "What tables feed cops_employment?"

        # Downstream lineage (what uses this data)
        jobforge lineage "What depends on dim_noc?"
        jobforge lineage "What does noc_structure feed?"

        # Full lineage (both directions)
        jobforge lineage "Show lineage for dim_noc"

        # Transformation path
        jobforge lineage "Path from dim_noc to dim_noc"
    """
    from rich.console import Console

    from jobforge.governance import LineageGraph, LineageQueryEngine
    from jobforge.pipeline.config import PipelineConfig

    console = Console()

    try:
        config = PipelineConfig()
        graph = LineageGraph(config)
        engine = LineageQueryEngine(graph)

        answer = engine.query(question)
        console.print(answer)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}", style="bold")
        raise typer.Exit(code=1)


@app.command()
def demo(
    port: int = typer.Option(8080, "--port", "-p", help="Server port"),
    host: str = typer.Option("127.0.0.1", "--host", help="Server host"),
    schema_path: Optional[Path] = typer.Option(
        None, "--schema", "-s", help="Path to WiQ schema JSON"
    ),
) -> None:
    """Start demo web server for live deployment narration.

    The web server streams deployment NARRATION showing what is being built.
    Actual deployment is triggered separately via /stagegold in Claude Code
    (VS Code Pro with MCP access).

    PREREQUISITES:
    - Power BI Desktop must be open with a saved .pbix file (blank or target)
    - The .pbix file must be saved BEFORE running /stagegold

    RECOMMENDED DEMO SETUP:
    1. Open Power BI Desktop and save a blank .pbix file
    2. Start this server: jobforge demo
    3. Open browser to http://localhost:8080
    4. Arrange windows side-by-side: browser + Power BI Desktop
    5. In VS Code Pro, run /stagegold to trigger actual deployment

    The web UI displays narration events describing deployment progress,
    synchronized with the external Claude Code execution.

    Examples:
        # Start demo server on default port
        jobforge demo

        # Start on custom port
        jobforge demo --port 3000

        # Use custom schema
        jobforge demo --schema custom_schema.json
    """
    import uvicorn

    from jobforge.demo.app import create_app

    # Static files location (will be created in Plan 02)
    static_dir = Path(__file__).parent.parent / "demo" / "static"

    app = create_app(static_dir if static_dir.exists() else None)

    typer.echo(f"Starting JobForge demo server at http://{host}:{port}")
    typer.echo("Press Ctrl+C to stop")
    typer.echo()
    typer.echo("API Endpoints:")
    typer.echo(f"  GET http://{host}:{port}/api/deploy/stream  (SSE narration stream)")
    typer.echo(f"  GET http://{host}:{port}/api/catalogue      (Table catalogue)")
    typer.echo(f"  GET http://{host}:{port}/api/health         (Health check)")

    uvicorn.run(app, host=host, port=port)


@app.command()
def api(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload"),
) -> None:
    """Start the JobForge Query API server.

    Provides HTTP endpoints for conversational data and metadata queries:
    - POST /api/query/data - Natural language data queries (uses Claude API)
    - POST /api/query/metadata - Metadata and lineage queries
    - GET /api/compliance/{framework} - Compliance traceability logs

    Prerequisites:
    - Set ANTHROPIC_API_KEY environment variable for data queries
    - Gold layer tables must exist (run 'jobforge run' first)

    Example:
        jobforge api                    # Start on localhost:8000
        jobforge api -p 8080            # Custom port
        jobforge api --reload           # Development mode with auto-reload

    Test with curl:
        curl -X POST http://localhost:8000/api/query/metadata \\
             -H "Content-Type: application/json" \\
             -d '{"question": "how many gold tables?"}'
    """
    import uvicorn
    from rich.console import Console

    console = Console()

    console.print("[bold]Starting JobForge Query API[/bold]")
    console.print(f"  Host: {host}")
    console.print(f"  Port: {port}")
    console.print(f"  Docs: http://{host}:{port}/docs")
    console.print()
    console.print("API Endpoints:")
    console.print(f"  POST http://{host}:{port}/api/query/data      (Natural language SQL)")
    console.print(f"  POST http://{host}:{port}/api/query/metadata  (Lineage queries)")
    console.print(f"  GET  http://{host}:{port}/api/compliance/{{framework}}")
    console.print(f"  GET  http://{host}:{port}/api/tables")
    console.print(f"  GET  http://{host}:{port}/api/health")
    console.print()

    uvicorn.run(
        "jobforge.api:app" if reload else "jobforge.api:app",
        host=host,
        port=port,
        reload=reload,
    )


@app.command()
def compliance(
    framework: str = typer.Argument(
        ...,
        help="Framework: dadm, dama, or classification",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output JSON file path",
    ),
    summary_only: bool = typer.Option(
        False,
        "--summary",
        "-s",
        help="Show summary only",
    ),
) -> None:
    """Generate or view compliance traceability log.

    Generates Requirements Traceability Matrix (RTM) based compliance logs
    mapping WiQ artifacts to governance framework requirements.

    Supported frameworks:
        - dadm: Directive on Automated Decision-Making (sections 6.1-6.6)
        - dama: DAMA DMBOK Data Management Body of Knowledge (11 areas)
        - classification: NOC-based job classification compliance

    Examples:
        # View DADM compliance summary
        jobforge compliance dadm --summary

        # Generate full DAMA compliance log
        jobforge compliance dama

        # Export classification compliance to JSON
        jobforge compliance classification -o compliance.json
    """
    from rich.console import Console
    from rich.table import Table

    from jobforge.governance.compliance import (
        ClassificationComplianceLog,
        DADMComplianceLog,
        DAMAComplianceLog,
    )
    from jobforge.pipeline.config import PipelineConfig

    console = Console()

    config = PipelineConfig()

    generators = {
        "dadm": DADMComplianceLog,
        "dama": DAMAComplianceLog,
        "classification": ClassificationComplianceLog,
    }

    framework_lower = framework.lower()
    if framework_lower not in generators:
        console.print(f"[red]Unknown framework: {framework}[/red]")
        console.print(f"Available: {', '.join(generators.keys())}")
        raise typer.Exit(code=1)

    try:
        generator = generators[framework_lower](config)
        log = generator.generate()
    except Exception as e:
        console.print(f"[red]Error generating compliance log:[/red] {e}")
        raise typer.Exit(code=1)

    if summary_only:
        # Show summary table
        table = Table(title=f"{log.framework_name} Compliance Summary")
        table.add_column("Status", style="cyan")
        table.add_column("Count", justify="right", style="green")

        for status, count in log.summary.items():
            table.add_row(status, str(count))

        table.add_row("", "")
        table.add_row("Total", str(len(log.entries)), style="bold")
        table.add_row(
            "Compliance Rate",
            f"{log.compliance_rate:.1%}",
            style="bold green" if log.compliance_rate >= 0.8 else "bold yellow",
        )

        console.print(table)

    elif output:
        output.write_text(log.model_dump_json(indent=2))
        console.print(f"[green]Compliance log written to {output}[/green]")

    else:
        # Pretty print all entries with Rich
        console.print()
        console.print(f"[bold]{log.framework_name}[/bold]")
        console.print(f"Version: {log.framework_version}")
        console.print(f"Generated: {log.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        console.print()

        for entry in log.entries:
            # Color status
            status_style = {
                "compliant": "green",
                "partial": "yellow",
                "not_applicable": "dim",
                "not_implemented": "red",
            }.get(entry.status.value, "white")

            console.print(f"[bold]{entry.requirement_id}[/bold] - {entry.section}")
            console.print(f"  Status: [{status_style}]{entry.status.value}[/{status_style}]")
            console.print(f"  Requirement: {entry.requirement_text[:100]}...")

            if entry.evidence_references:
                console.print(f"  Evidence: {', '.join(entry.evidence_references[:3])}")
                if len(entry.evidence_references) > 3:
                    console.print(f"            ... and {len(entry.evidence_references) - 3} more")

            if entry.notes:
                console.print(f"  Notes: {entry.notes[:100]}...")

            console.print()

        # Summary at end
        console.print("[bold]Summary:[/bold]")
        for status, count in log.summary.items():
            if count > 0:
                console.print(f"  {status}: {count}")
        console.print(f"  Compliance Rate: {log.compliance_rate:.1%}")


@app.command()
def version() -> None:
    """Show JobForge version."""
    typer.echo("JobForge 2.0.0")


# CAF command group
caf_app = typer.Typer(
    name="caf",
    help="CAF (Canadian Armed Forces) data management commands",
)


@caf_app.command("refresh")
def caf_refresh(
    scrape: bool = typer.Option(
        False,
        "--scrape/--no-scrape",
        help="Scrape fresh data from forces.ca before building tables",
    ),
    match: bool = typer.Option(
        True,
        "--match/--no-match",
        help="Run fuzzy matching to build bridge tables (NOC and JA)",
    ),
) -> None:
    """Refresh CAF data tables.

    Rebuilds CAF gold layer tables from source data. Optionally scrapes
    fresh data from forces.ca and runs fuzzy matching to build bridge tables.

    The refresh process:
    1. (Optional) Scrape fresh career data from forces.ca
    2. Build dim_caf_occupation (88 occupations with bilingual content)
    3. Build dim_caf_job_family (11 job families)
    4. (Optional) Build bridge_caf_noc (880 NOC mappings)
    5. (Optional) Build bridge_caf_ja (880 JA mappings)

    Examples:
        # Refresh tables using existing scraped data
        jobforge caf refresh

        # Scrape fresh data and refresh all tables
        jobforge caf refresh --scrape

        # Refresh dimension tables only (skip bridge table matching)
        jobforge caf refresh --no-match
    """
    from rich.console import Console
    from rich.table import Table

    from jobforge.ingestion.caf import (
        ingest_bridge_caf_ja,
        ingest_bridge_caf_noc,
        ingest_dim_caf_job_family,
        ingest_dim_caf_occupation,
    )

    console = Console()

    results = []

    # Optionally scrape fresh data
    if scrape:
        console.print("[bold]Scraping fresh data from forces.ca...[/bold]")
        try:
            from jobforge.external.caf import CAFLinkFetcher, scrape_caf_careers

            # Scrape career listings
            console.print("  Scraping career listings...")
            scrape_caf_careers()

            # Fetch detailed career pages with bilingual content
            console.print("  Fetching career details...")
            with CAFLinkFetcher() as fetcher:
                fetcher.fetch_all_career_details()

            console.print("[green]  Scrape complete[/green]")
        except Exception as e:
            console.print(f"[red]Error scraping: {e}[/red]")
            raise typer.Exit(code=1)

    # Build dimension tables
    console.print("\n[bold]Building gold tables...[/bold]")

    try:
        console.print("  Building dim_caf_occupation...")
        result_occ = ingest_dim_caf_occupation()
        results.append(("dim_caf_occupation", result_occ["row_count"], "OK"))

        console.print("  Building dim_caf_job_family...")
        result_fam = ingest_dim_caf_job_family()
        results.append(("dim_caf_job_family", result_fam["row_count"], "OK"))
    except Exception as e:
        console.print(f"[red]Error building dimension tables: {e}[/red]")
        raise typer.Exit(code=1)

    # Optionally build bridge tables via fuzzy matching
    if match:
        try:
            console.print("  Building bridge_caf_noc...")
            result_noc = ingest_bridge_caf_noc()
            results.append(("bridge_caf_noc", result_noc["row_count"], "OK"))

            console.print("  Building bridge_caf_ja...")
            result_ja = ingest_bridge_caf_ja()
            results.append(("bridge_caf_ja", result_ja["row_count"], "OK"))
        except Exception as e:
            console.print(f"[red]Error building bridge tables: {e}[/red]")
            raise typer.Exit(code=1)

    # Display results summary
    console.print("\n[bold green]CAF refresh complete[/bold green]\n")

    table = Table(title="CAF Tables Refreshed")
    table.add_column("Table", style="cyan")
    table.add_column("Rows", justify="right", style="green")
    table.add_column("Status", style="green")

    for name, rows, status in results:
        table.add_row(name, str(rows), status)

    console.print(table)


@caf_app.command("status")
def caf_status() -> None:
    """Show CAF table status and row counts.

    Displays the current state of all CAF gold layer tables including:
    - dim_caf_occupation: CAF occupations with bilingual content
    - dim_caf_job_family: Inferred job families
    - bridge_caf_noc: CAF-to-NOC occupation mappings
    - bridge_caf_ja: CAF-to-Job Architecture mappings

    Examples:
        jobforge caf status
    """
    from pathlib import Path

    import polars as pl
    from rich.console import Console
    from rich.table import Table

    console = Console()

    gold_dir = Path("data/gold")

    caf_tables = [
        ("dim_caf_occupation", "88 CAF occupations with bilingual content"),
        ("dim_caf_job_family", "11 inferred job families"),
        ("bridge_caf_noc", "CAF-to-NOC occupation mappings"),
        ("bridge_caf_ja", "CAF-to-Job Architecture mappings"),
    ]

    table = Table(title="CAF Table Status")
    table.add_column("Table", style="cyan")
    table.add_column("Rows", justify="right", style="green")
    table.add_column("Status", style="green")
    table.add_column("Description", style="dim")

    for table_name, description in caf_tables:
        file_path = gold_dir / f"{table_name}.parquet"
        if file_path.exists():
            try:
                df = pl.read_parquet(file_path)
                rows = len(df)
                status = "OK"
            except Exception as e:
                rows = "?"
                status = f"Error: {e}"
        else:
            rows = "-"
            status = "Not found"

        table.add_row(table_name, str(rows), status, description)

    console.print(table)

    # Also show reference JSON files if they exist
    reference_dir = Path("data/reference")
    reference_files = [
        "caf_noc_mappings.json",
        "caf_ja_mappings.json",
    ]

    ref_table = Table(title="CAF Reference Files")
    ref_table.add_column("File", style="cyan")
    ref_table.add_column("Status", style="green")
    ref_table.add_column("Size", justify="right", style="dim")

    for ref_file in reference_files:
        ref_path = reference_dir / ref_file
        if ref_path.exists():
            size_kb = ref_path.stat().st_size / 1024
            ref_table.add_row(ref_file, "OK", f"{size_kb:.1f} KB")
        else:
            ref_table.add_row(ref_file, "Not found", "-")

    console.print()
    console.print(ref_table)


# Register CAF command group with main app
app.add_typer(caf_app, name="caf")


if __name__ == "__main__":
    app()
