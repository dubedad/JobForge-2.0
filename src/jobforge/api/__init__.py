"""JobForge Query API package.

Provides HTTP API endpoints for conversational data and metadata queries,
enabling Orbit integration for natural language access to WiQ data.
"""

# Core data query components
from jobforge.api.data_query import DataQueryResult, DataQueryService, SQLQuery
from jobforge.api.schema_ddl import generate_schema_ddl

__all__ = [
    "DataQueryService",
    "SQLQuery",
    "DataQueryResult",
    "generate_schema_ddl",
]


def __getattr__(name: str):
    """Lazy import for components created in later tasks."""
    if name == "MetadataQueryService":
        from jobforge.api.metadata_query import MetadataQueryService

        return MetadataQueryService
    if name in ("create_api_app", "app"):
        from jobforge.api import routes

        return getattr(routes, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
