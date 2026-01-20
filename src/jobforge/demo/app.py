"""Starlette app with SSE endpoint for demo narration.

This module provides a Starlette web application that serves SSE events
for the demo UI. The SSE endpoint streams narration events describing
what is being deployed, while the actual deployment is executed externally.

Example:
    >>> from jobforge.demo.app import create_app
    >>> app = create_app()
    >>> # Run with: uvicorn.run(app, host="127.0.0.1", port=8080)
"""

from pathlib import Path
from typing import AsyncGenerator, Optional

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from sse_starlette.sse import EventSourceResponse

from jobforge.demo.orchestrator import DemoOrchestrator


async def deployment_stream(request: Request) -> EventSourceResponse:
    """SSE endpoint for deployment narration stream.

    Streams DemoEvent objects as SSE events. The events describe deployment
    progress (NARRATION) - actual deployment is triggered externally via
    Claude Code with MCP.

    Query Parameters:
        schema_path: Optional path to WiQ schema JSON file.

    Returns:
        EventSourceResponse streaming deployment narration events.

    Example:
        GET /api/deploy/stream
        GET /api/deploy/stream?schema_path=/path/to/schema.json
    """
    schema_path_str = request.query_params.get("schema_path")
    schema_path = Path(schema_path_str) if schema_path_str else None

    orchestrator = DemoOrchestrator(schema_path=schema_path)

    async def event_generator() -> AsyncGenerator[dict, None]:
        """Generate SSE events from orchestrator."""
        async for event in orchestrator.stream_deployment():
            yield event.to_sse_dict()

    return EventSourceResponse(
        event_generator(),
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


async def catalogue_data(request: Request) -> JSONResponse:
    """API endpoint for catalogue metadata.

    Returns table catalogue data for the Catalogue wizard step.

    Query Parameters:
        schema_path: Optional path to WiQ schema JSON file.

    Returns:
        JSONResponse with list of table metadata.

    Example:
        GET /api/catalogue
    """
    schema_path_str = request.query_params.get("schema_path")
    schema_path = Path(schema_path_str) if schema_path_str else None

    orchestrator = DemoOrchestrator(schema_path=schema_path)
    data = orchestrator.get_catalogue_data()

    return JSONResponse({"tables": data})


async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint.

    Returns:
        JSONResponse with status "ok".
    """
    return JSONResponse({"status": "ok"})


def create_app(static_dir: Optional[Path] = None) -> Starlette:
    """Create Starlette application with SSE endpoint.

    Creates a web application with:
    - /api/deploy/stream: SSE endpoint for deployment narration
    - /api/catalogue: JSON endpoint for catalogue data
    - /api/health: Health check endpoint
    - /: Static files (if static_dir exists)

    Args:
        static_dir: Optional directory for static files.
                   If provided and exists, static files are served at root.

    Returns:
        Configured Starlette application.

    Example:
        >>> app = create_app()
        >>> app = create_app(Path("static"))
    """
    routes = [
        Route("/api/deploy/stream", deployment_stream),
        Route("/api/catalogue", catalogue_data),
        Route("/api/health", health_check),
    ]

    # Add static files if directory exists
    if static_dir is not None and static_dir.exists():
        routes.append(
            Mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
        )

    return Starlette(routes=routes, debug=False)
