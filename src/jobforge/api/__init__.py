"""JobForge Query API package.

Provides HTTP API endpoints for conversational data and metadata queries,
enabling Orbit integration for natural language access to WiQ data.

Usage:
    # Start API server
    jobforge api

    # Or programmatically
    from jobforge.api import create_api_app
    app = create_api_app()
"""

# Core data query components
from jobforge.api.data_query import DataQueryResult, DataQueryService, SQLQuery
from jobforge.api.metadata_query import MetadataQueryService
from jobforge.api.routes import app, create_api_app
from jobforge.api.schema_ddl import generate_schema_ddl

__all__ = [
    "create_api_app",
    "app",
    "DataQueryService",
    "SQLQuery",
    "DataQueryResult",
    "MetadataQueryService",
    "generate_schema_ddl",
]
