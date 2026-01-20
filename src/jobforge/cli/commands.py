"""JobForge CLI commands.

This module provides Typer-based CLI commands for the JobForge platform.

Commands:
    stagegold: Deploy WiQ semantic model to Power BI
    lineage: Answer lineage questions about the WiQ data pipeline

Example:
    $ jobforge stagegold
    $ jobforge stagegold --dry-run
    $ jobforge stagegold --schema custom_schema.json
    $ jobforge lineage "Where does dim_noc come from?"
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
def version() -> None:
    """Show JobForge version."""
    typer.echo("JobForge 2.0.0")


if __name__ == "__main__":
    app()
