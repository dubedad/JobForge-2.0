"""FastAPI routes for JobForge Query API.

Provides HTTP endpoints for conversational data and metadata queries,
plus compliance log retrieval.
"""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from jobforge.api.data_query import DataQueryResult, DataQueryService
from jobforge.api.errors import QueryError, TableNotFoundError, register_error_handlers
from jobforge.api.metadata_query import MetadataQueryService
from jobforge.pipeline.config import PipelineConfig


class QueryRequest(BaseModel):
    """Request body for query endpoints."""

    question: str


class MetadataQueryResult(BaseModel):
    """Result of a metadata query."""

    question: str
    answer: str


def create_api_app(config: PipelineConfig | None = None) -> FastAPI:
    """Create FastAPI application for query endpoints.

    Args:
        config: Pipeline configuration. Defaults to standard PipelineConfig.

    Returns:
        Configured FastAPI application.
    """
    api_app = FastAPI(
        title="JobForge Query API",
        description="Conversational interface for WiQ data and metadata",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS middleware must be added FIRST (before other middleware)
    # Get allowed origins from environment (comma-separated)
    origins_str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080")
    allowed_origins = [o.strip() for o in origins_str.split(",")]

    api_app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
        max_age=3600,
    )

    # Register RFC 9457 error handlers
    register_error_handlers(api_app)

    config = config or PipelineConfig()
    data_service = DataQueryService(config)
    metadata_service = MetadataQueryService(config)

    # Get the static directory path relative to this file
    static_dir = Path(__file__).parent / "static"

    # Serve landing page at root
    @api_app.get("/", response_class=FileResponse)
    async def landing_page():
        """Serve the landing page HTML."""
        return FileResponse(static_dir / "index.html")

    @api_app.post("/api/query/data", response_model=DataQueryResult)
    async def query_data(request: QueryRequest) -> DataQueryResult:
        """Query WiQ data using natural language.

        Converts the question to SQL using Claude and executes against gold tables.
        Requires ANTHROPIC_API_KEY environment variable.

        Args:
            request: Query request with question field.

        Returns:
            DataQueryResult with SQL, explanation, and results.

        Raises:
            QueryError: If query fails with error (returns RFC 9457 response).
        """
        result = data_service.query(request.question)
        if result.error:
            raise QueryError(
                message=result.error,
                guidance="Check your question syntax and ensure you're asking about available tables.",
            )
        return result

    @api_app.post("/api/query/metadata", response_model=MetadataQueryResult)
    async def query_metadata(request: QueryRequest) -> MetadataQueryResult:
        """Query WiQ metadata using natural language.

        Answers questions about lineage, table structure, and data provenance.
        Does not require external API keys.

        Args:
            request: Query request with question field.

        Returns:
            MetadataQueryResult with answer.
        """
        answer = metadata_service.query(request.question)
        return MetadataQueryResult(question=request.question, answer=answer)

    @api_app.get("/api/compliance/{framework}")
    async def get_compliance(framework: str) -> dict:
        """Get compliance log for a framework.

        Generates a Requirements Traceability Matrix (RTM) showing how WiQ
        artifacts map to governance framework requirements.

        Supported frameworks:
        - dadm: Directive on Automated Decision Making
        - dama: DAMA DMBOK knowledge areas
        - classification: Job classification policy alignment

        Args:
            framework: Framework name (dadm, dama, or classification).

        Returns:
            Compliance log as JSON.

        Raises:
            TableNotFoundError: If framework unknown (returns RFC 9457 response).
            QueryError: If compliance module not available.
        """
        # Note: Compliance module is created in Plan 10-01
        # This endpoint will work once that plan is executed
        try:
            from jobforge.governance.compliance import (
                ClassificationComplianceLog,
                DADMComplianceLog,
                DAMAComplianceLog,
            )

            generators = {
                "dadm": DADMComplianceLog,
                "dama": DAMAComplianceLog,
                "classification": ClassificationComplianceLog,
            }

            if framework.lower() not in generators:
                raise TableNotFoundError(
                    table_name=framework,
                    available_tables=list(generators.keys()),
                )

            generator = generators[framework.lower()](config)
            log = generator.generate()
            return log.model_dump()

        except ImportError:
            raise QueryError(
                message="Compliance module not yet available",
                guidance="Execute Plan 10-01 first to enable compliance features.",
            )

    @api_app.get("/api/health")
    async def health() -> dict:
        """Health check endpoint.

        Returns:
            Status dict indicating API is operational.
        """
        return {"status": "ok"}

    @api_app.get("/api/tables")
    async def list_tables() -> dict:
        """List all available gold tables.

        Returns:
            Dict with list of table names and count.
        """
        gold_path = config.gold_path()
        tables = sorted(p.stem for p in gold_path.glob("*.parquet"))
        return {"tables": tables, "count": len(tables)}

    return api_app


# Export app instance for uvicorn
app = create_api_app()
