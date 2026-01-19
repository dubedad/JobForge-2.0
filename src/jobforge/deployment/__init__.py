"""Power BI deployment module for WiQ semantic model.

This module provides utilities for deploying the WiQ semantic model to Power BI
via the Power BI Modeling MCP Server.

Example:
    >>> from jobforge.deployment import MCPClient, TableSpec, RelationshipSpec
    >>> from jobforge.semantic import build_wiq_schema
    >>>
    >>> schema = build_wiq_schema()
    >>> client = MCPClient()
    >>>
    >>> # Convert schema to MCP specifications
    >>> table_specs = [client.table_to_spec(t) for t in schema.tables]
    >>> rel_specs = [client.relationship_to_spec(r) for r in schema.relationships]
"""

from jobforge.deployment.mcp_client import (
    MCPClient,
    MCPToolResult,
    RelationshipSpec,
    TableSpec,
    WIQ_TO_MCP_CARDINALITY,
)
from jobforge.deployment.types import (
    DUCKDB_TO_POWERBI_TYPES,
    POWERBI_NUMERIC_TYPES,
    get_summarize_by,
    map_duckdb_to_powerbi,
)

__all__ = [
    # MCP Client classes
    "MCPClient",
    "MCPToolResult",
    "TableSpec",
    "RelationshipSpec",
    # Type mapping
    "map_duckdb_to_powerbi",
    "get_summarize_by",
    "DUCKDB_TO_POWERBI_TYPES",
    "POWERBI_NUMERIC_TYPES",
    # Cardinality mapping
    "WIQ_TO_MCP_CARDINALITY",
]
