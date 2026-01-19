"""Rich-based terminal UI for WiQ deployment demos.

This module provides a beautiful terminal UI for live deployment demonstrations.
The UI narrates each deployment step while the actual data model comes alive
in Power BI on the other side of the screen.

Demo Experience Requirements:
- Continuous flow with visual highlights (no pauses)
- Each step highlighted as it happens
- Split-screen friendly (terminal + Power BI)
- Beautiful formatting: colors, panels, tables
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


def get_table_source(table_name: str) -> str:
    """Get authoritative source for a table.

    Maps table naming conventions to their authoritative data sources
    for demo narration and attribution.

    Args:
        table_name: Name of the table to get source for.

    Returns:
        Source attribution string.

    Example:
        >>> get_table_source("dim_noc")
        'StatCan NOC 2021'
        >>> get_table_source("oasis_skills")
        'O*NET/OASIS'
    """
    if table_name.startswith("dim_"):
        return "StatCan NOC 2021"
    elif table_name.startswith("element_"):
        return "StatCan NOC 2021"
    elif table_name.startswith("oasis_"):
        return "O*NET/OASIS"
    elif table_name.startswith("cops_"):
        return "ESDC COPS"
    elif table_name == "job_architecture":
        return "Job Architecture"
    return "Unknown"


def get_table_type_display(table_type: str) -> str:
    """Get display-friendly table type.

    Args:
        table_type: Table type string (dimension, fact, attribute).

    Returns:
        Human-readable display string.
    """
    return table_type.lower()


class DeploymentUI:
    """Rich-based terminal UI for WiQ deployment demos.

    Provides methods for displaying deployment progress with beautiful
    Rich formatting suitable for live demo presentations.

    Example:
        >>> ui = DeploymentUI()
        >>> ui.show_header()
        >>> ui.show_deploying_table("dim_noc", "dimension", "StatCan NOC 2021")
        >>> ui.show_table_complete("dim_noc", 8)
        >>> ui.show_summary(["dim_noc"], 0, 1.5)
    """

    def __init__(self) -> None:
        """Initialize the deployment UI with a Rich console."""
        self.console = Console()
        self.tables_deployed: list[str] = []
        self.relationships_created: int = 0

    def show_header(self) -> None:
        """Display deployment header panel.

        Shows a prominent header panel to start the deployment demo.
        """
        header_content = Table.grid(padding=(0, 2))
        header_content.add_column(justify="center")
        header_content.add_row("[bold cyan]Workforce Intelligence Platform[/]")
        header_content.add_row("[dim]Deploying semantic model to Power BI...[/]")

        self.console.print()
        self.console.print(Panel(
            header_content,
            title="[bold white]WiQ Semantic Model Deployment[/]",
            border_style="cyan",
            padding=(1, 2),
        ))
        self.console.print()

    def show_deploying_table(self, table_name: str, table_type: str, source: str) -> None:
        """Display table deployment in progress.

        Args:
            table_name: Name of the table being deployed.
            table_type: Type of table (dimension, fact, attribute).
            source: Authoritative source for the data.
        """
        type_display = get_table_type_display(table_type)
        self.console.print(
            f"  [cyan]Deploying:[/] {table_name} "
            f"[dim]({type_display})[/] from [yellow]{source}[/]"
        )

    def show_table_complete(self, table_name: str, column_count: int) -> None:
        """Display table deployment completion.

        Args:
            table_name: Name of the table that was deployed.
            column_count: Number of columns in the table.
        """
        self.tables_deployed.append(table_name)
        self.console.print(
            f"  [green]Created:[/] {table_name} with [bold]{column_count}[/] columns"
        )

    def show_deploying_relationship(self, from_table: str, to_table: str) -> None:
        """Display relationship deployment in progress.

        Args:
            from_table: Source table name.
            to_table: Target table name.
        """
        self.console.print(
            f"  [cyan]Linking:[/] {from_table} -> {to_table}"
        )

    def show_relationship_complete(
        self, from_table: str, to_table: str, cardinality: str
    ) -> None:
        """Display relationship completion.

        Args:
            from_table: Source table name.
            to_table: Target table name.
            cardinality: Cardinality of the relationship (e.g., "1:*").
        """
        self.relationships_created += 1
        self.console.print(
            f"  [green]Linked:[/] {from_table} -> {to_table} [dim]({cardinality})[/]"
        )

    def show_summary(
        self, tables: list[str], relationships: int, duration: float
    ) -> None:
        """Display final summary panel.

        Shows a comprehensive summary panel with deployment results,
        data sources represented, and timing information.

        Args:
            tables: List of table names that were deployed.
            relationships: Number of relationships created.
            duration: Total deployment duration in seconds.
        """
        # Identify sources represented
        sources = self._get_sources_represented(tables)

        # Build summary grid
        summary = Table.grid(padding=(0, 2))
        summary.add_column(style="bold cyan", justify="right")
        summary.add_column(style="green")

        summary.add_row("Tables Deployed:", str(len(tables)))
        summary.add_row("Relationships Created:", str(relationships))
        summary.add_row("Sources Represented:", ", ".join(sources))
        summary.add_row("Duration:", f"{duration:.1f}s")

        self.console.print()
        self.console.print(Panel(
            summary,
            title="[bold green]WiQ Model Ready in Power BI[/]",
            border_style="green",
            padding=(1, 2),
        ))

    def show_section_header(self, title: str) -> None:
        """Display a section header for grouping related operations.

        Args:
            title: Section title to display.
        """
        self.console.print()
        self.console.print(f"[bold white]{title}[/]")
        self.console.print("[dim]" + "-" * 40 + "[/]")

    def show_error(self, message: str) -> None:
        """Display an error message.

        Args:
            message: Error message to display.
        """
        self.console.print(f"[bold red]Error:[/] {message}")

    def show_warning(self, message: str) -> None:
        """Display a warning message.

        Args:
            message: Warning message to display.
        """
        self.console.print(f"[yellow]Warning:[/] {message}")

    def _get_sources_represented(self, tables: list[str]) -> list[str]:
        """Get list of unique data sources represented in deployed tables.

        Args:
            tables: List of table names.

        Returns:
            Sorted list of unique source names.
        """
        sources: set[str] = set()
        for table_name in tables:
            source = get_table_source(table_name)
            if source != "Unknown":
                sources.add(source)
        return sorted(sources)
