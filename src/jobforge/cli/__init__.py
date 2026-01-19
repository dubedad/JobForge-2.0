"""JobForge CLI module.

Provides command-line interface for JobForge operations.

Example:
    >>> from jobforge.cli import app
    >>> # Run with Typer
    >>> app()
"""

from jobforge.cli.commands import app

__all__ = ["app"]
