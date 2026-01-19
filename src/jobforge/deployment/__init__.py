"""Power BI deployment module for WiQ semantic model.

This module provides utilities for deploying the WiQ semantic model to Power BI
via the Power BI Modeling MCP Server.

Example:
    >>> from jobforge.deployment import WiQDeployer, DeploymentUI
    >>>
    >>> # Create deployer with UI
    >>> ui = DeploymentUI()
    >>> deployer = WiQDeployer(ui=ui)
    >>>
    >>> # Load schema and get deployment order
    >>> schema = deployer.load_schema()
    >>> tables, rels = deployer.get_deployment_order(schema)
    >>>
    >>> # Generate deployment script for Claude Code
    >>> print(deployer.generate_deployment_script())
"""

from jobforge.deployment.deployer import DeploymentResult, WiQDeployer
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
from jobforge.deployment.ui import DeploymentUI, get_table_source

__all__ = [
    # Deployer classes
    "WiQDeployer",
    "DeploymentResult",
    # UI classes
    "DeploymentUI",
    "get_table_source",
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
