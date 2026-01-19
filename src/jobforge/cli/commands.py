"""JobForge CLI commands.

This module provides Typer-based CLI commands for the JobForge platform.

Commands:
    stagegold: Deploy WiQ semantic model to Power BI

Example:
    $ jobforge stagegold
    $ jobforge stagegold --dry-run
    $ jobforge stagegold --schema custom_schema.json
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
def version() -> None:
    """Show JobForge version."""
    typer.echo("JobForge 2.0.0")


if __name__ == "__main__":
    app()
