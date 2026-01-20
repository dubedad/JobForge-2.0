"""RFC 9457 Problem Details error handling for JobForge API.

Provides standardized error responses following RFC 9457 (Problem Details for HTTP APIs).
All API errors return structured JSON with type, title, status, detail, and optional instance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from fastapi import Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = structlog.get_logger()


class ProblemDetail(BaseModel):
    """RFC 9457 Problem Details for HTTP APIs.

    Provides a standardized format for error responses that includes:
    - type: URI reference identifying the problem type
    - title: Human-readable summary
    - status: HTTP status code
    - detail: Specific explanation with actionable guidance
    - instance: Optional URI to this specific occurrence
    """

    type: str
    title: str
    status: int
    detail: str
    instance: str | None = None


class QueryError(Exception):
    """Error during data query execution.

    Raised when a text-to-SQL query fails, providing user-friendly error details.
    """

    def __init__(self, message: str, guidance: str | None = None):
        """Initialize query error.

        Args:
            message: Error description.
            guidance: Actionable guidance for the user.
        """
        self.message = message
        self.guidance = guidance or "Check your query syntax and try again."
        super().__init__(message)


class TableNotFoundError(Exception):
    """Error when requested table does not exist.

    Raised when a query references a table that doesn't exist in the gold layer.
    """

    def __init__(self, table_name: str, available_tables: list[str] | None = None):
        """Initialize table not found error.

        Args:
            table_name: Name of the requested table.
            available_tables: List of valid table names.
        """
        self.table_name = table_name
        self.available_tables = available_tables or []
        super().__init__(f"Table '{table_name}' not found")


def create_problem_detail(
    type_suffix: str,
    title: str,
    status_code: int,
    detail: str,
    instance: str | None = None,
) -> dict:
    """Create RFC 9457 problem detail response dictionary.

    Args:
        type_suffix: Error type identifier (e.g., "validation-failed").
        title: Human-readable error summary.
        status_code: HTTP status code.
        detail: Specific explanation with actionable guidance.
        instance: Optional URI to this specific occurrence.

    Returns:
        Dictionary formatted as RFC 9457 Problem Details.
    """
    return {
        "type": f"/errors/{type_suffix}",
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": instance,
    }


async def validation_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Handle ValueError with user-friendly validation error message.

    Args:
        request: FastAPI request object.
        exc: ValueError exception.

    Returns:
        JSONResponse with RFC 9457 Problem Details.
    """
    logger.warning(
        "validation_error",
        error=str(exc),
        path=str(request.url),
        method=request.method,
    )

    problem = create_problem_detail(
        type_suffix="validation-failed",
        title="Validation Error",
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Invalid input: {exc}. Check your query syntax and ensure all required fields are provided.",
        instance=str(request.url),
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=problem,
        headers={"Content-Type": "application/problem+json"},
    )


async def query_error_handler(request: Request, exc: QueryError) -> JSONResponse:
    """Handle QueryError with query-specific guidance.

    Args:
        request: FastAPI request object.
        exc: QueryError exception.

    Returns:
        JSONResponse with RFC 9457 Problem Details.
    """
    logger.warning(
        "query_error",
        error=exc.message,
        guidance=exc.guidance,
        path=str(request.url),
        method=request.method,
    )

    problem = create_problem_detail(
        type_suffix="query-failed",
        title="Query Error",
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"{exc.message}. {exc.guidance}",
        instance=str(request.url),
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=problem,
        headers={"Content-Type": "application/problem+json"},
    )


async def not_found_handler(request: Request, exc: TableNotFoundError) -> JSONResponse:
    """Handle TableNotFoundError with available tables list.

    Args:
        request: FastAPI request object.
        exc: TableNotFoundError exception.

    Returns:
        JSONResponse with RFC 9457 Problem Details.
    """
    logger.warning(
        "table_not_found",
        table=exc.table_name,
        available=exc.available_tables[:10] if exc.available_tables else [],
        path=str(request.url),
        method=request.method,
    )

    # Build helpful message with available tables
    if exc.available_tables:
        tables_preview = ", ".join(exc.available_tables[:5])
        if len(exc.available_tables) > 5:
            tables_preview += f", ... ({len(exc.available_tables)} total)"
        guidance = f"Available tables: {tables_preview}"
    else:
        guidance = "No tables are currently available."

    problem = create_problem_detail(
        type_suffix="not-found",
        title="Resource Not Found",
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Table '{exc.table_name}' not found. {guidance}",
        instance=str(request.url),
    )

    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=problem,
        headers={"Content-Type": "application/problem+json"},
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions with sanitized message.

    Logs full error details but returns only safe user-facing message.

    Args:
        request: FastAPI request object.
        exc: Any exception.

    Returns:
        JSONResponse with RFC 9457 Problem Details.
    """
    logger.error(
        "internal_error",
        error=str(exc),
        error_type=type(exc).__name__,
        path=str(request.url),
        method=request.method,
    )

    problem = create_problem_detail(
        type_suffix="internal-error",
        title="Internal Server Error",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred. Please try again or contact support if the problem persists.",
        instance=str(request.url),
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=problem,
        headers={"Content-Type": "application/problem+json"},
    )


def register_error_handlers(app: FastAPI) -> None:
    """Register all RFC 9457 error handlers with the FastAPI application.

    Args:
        app: FastAPI application instance.
    """
    app.add_exception_handler(ValueError, validation_error_handler)
    app.add_exception_handler(QueryError, query_error_handler)
    app.add_exception_handler(TableNotFoundError, not_found_handler)
    app.add_exception_handler(Exception, generic_error_handler)

    logger.info("error_handlers_registered", handlers=4)
