"""MCP client wrapper for Power BI MCP Server operations.

This module provides specification classes and conversion utilities for
interfacing with the Power BI Modeling MCP Server. The actual MCP tool
calls are made by Claude Code using these specifications.

The MCPClient class converts WiQ semantic model objects (Table, Relationship)
into MCP-compatible specifications that can be used for tool invocations.
"""

from dataclasses import dataclass, field
from typing import Optional

from jobforge.deployment.types import get_summarize_by, map_duckdb_to_powerbi
from jobforge.semantic.models import Relationship, Table


@dataclass
class MCPToolResult:
    """Result from an MCP tool invocation.

    Attributes:
        success: Whether the operation completed successfully.
        data: Response data from the MCP server (if any).
        error: Error message (if operation failed).
    """

    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


@dataclass
class TableSpec:
    """Specification for creating a Power BI table.

    This class captures all parameters needed to create a table via
    the Power BI MCP Server's table_operations tool.

    Attributes:
        name: Table name in Power BI.
        columns: List of column specifications, each containing:
                 - name: Column name
                 - dataType: Power BI data type
                 - summarizeBy: Default aggregation method
    """

    name: str
    columns: list[dict] = field(default_factory=list)


@dataclass
class RelationshipSpec:
    """Specification for creating a Power BI relationship.

    This class captures all parameters needed to create a relationship via
    the Power BI MCP Server's relationship_operations tool.

    Attributes:
        from_table: Source table name (typically the 'one' side).
        from_column: Source column name.
        to_table: Target table name (typically the 'many' side).
        to_column: Target column name.
        cardinality: MCP cardinality string (OneToMany, ManyToOne, etc.).
        cross_filter_direction: Filter propagation direction (Single or Both).
    """

    from_table: str
    from_column: str
    to_table: str
    to_column: str
    cardinality: str  # "OneToMany", "ManyToOne", "OneToOne", "ManyToMany"
    cross_filter_direction: str  # "Single" or "Both"


# Mapping from WiQ cardinality notation to MCP Server notation
WIQ_TO_MCP_CARDINALITY: dict[str, str] = {
    "1:*": "OneToMany",
    "*:1": "ManyToOne",
    "1:1": "OneToOne",
    "*:*": "ManyToMany",
}


class MCPClient:
    """Interface specification for Power BI MCP Server operations.

    This class defines the operations needed for deployment. The actual
    MCP tool calls are made by Claude Code using these specifications.

    The MCPClient converts WiQ semantic model objects into specifications
    that match the Power BI MCP Server's expected parameters.

    Example:
        >>> from jobforge.semantic import build_wiq_schema
        >>> from jobforge.deployment import MCPClient
        >>>
        >>> schema = build_wiq_schema()
        >>> client = MCPClient()
        >>>
        >>> # Convert a table to MCP specification
        >>> table_spec = client.table_to_spec(schema.tables[0])
        >>> print(f"Table: {table_spec.name}")
        >>>
        >>> # Convert a relationship to MCP specification
        >>> rel_spec = client.relationship_to_spec(schema.relationships[0])
        >>> print(f"Cardinality: {rel_spec.cardinality}")
    """

    def table_to_spec(self, table: Table) -> TableSpec:
        """Convert a WiQ Table to an MCP table specification.

        Maps all columns from DuckDB types to Power BI types and adds
        the appropriate summarize_by setting for each column.

        Args:
            table: WiQ Table object from the semantic model.

        Returns:
            TableSpec with name and columns ready for MCP tool invocation.

        Example:
            >>> table = Table(name="dim_noc", table_type="dimension", columns=[...])
            >>> spec = client.table_to_spec(table)
            >>> print(spec.name)
            'dim_noc'
        """
        columns = []
        for col in table.columns:
            powerbi_type = map_duckdb_to_powerbi(col.data_type)
            columns.append({
                "name": col.name,
                "dataType": powerbi_type,
                "summarizeBy": get_summarize_by(powerbi_type),
            })

        return TableSpec(name=table.name, columns=columns)

    def relationship_to_spec(self, rel: Relationship) -> RelationshipSpec:
        """Convert a WiQ Relationship to an MCP relationship specification.

        Maps the cardinality notation from WiQ format (1:*, *:1, etc.)
        to MCP Server format (OneToMany, ManyToOne, etc.).

        Args:
            rel: WiQ Relationship object from the semantic model.

        Returns:
            RelationshipSpec ready for MCP tool invocation.

        Example:
            >>> rel = Relationship(
            ...     from_table="dim_noc",
            ...     from_column="unit_group_id",
            ...     to_table="oasis_skills",
            ...     to_column="unit_group_id",
            ...     cardinality="1:*",
            ...     cross_filter_direction="Single"
            ... )
            >>> spec = client.relationship_to_spec(rel)
            >>> print(spec.cardinality)
            'OneToMany'
        """
        # Cardinality may be an enum value or already a string
        cardinality_str = (
            rel.cardinality.value
            if hasattr(rel.cardinality, "value")
            else str(rel.cardinality)
        )

        # Cross filter direction may be an enum value or string
        cross_filter_str = (
            rel.cross_filter_direction.value
            if hasattr(rel.cross_filter_direction, "value")
            else str(rel.cross_filter_direction)
        )

        return RelationshipSpec(
            from_table=rel.from_table,
            from_column=rel.from_column,
            to_table=rel.to_table,
            to_column=rel.to_column,
            cardinality=self.get_cardinality_for_mcp(cardinality_str),
            cross_filter_direction=cross_filter_str,
        )

    def get_cardinality_for_mcp(self, cardinality: str) -> str:
        """Map WiQ cardinality notation to MCP Server notation.

        Args:
            cardinality: WiQ cardinality string ("1:*", "*:1", "1:1", "*:*").

        Returns:
            MCP cardinality string ("OneToMany", "ManyToOne", "OneToOne", "ManyToMany").

        Raises:
            ValueError: If cardinality is not a recognized WiQ notation.

        Example:
            >>> client.get_cardinality_for_mcp("1:*")
            'OneToMany'
            >>> client.get_cardinality_for_mcp("*:1")
            'ManyToOne'
        """
        mcp_cardinality = WIQ_TO_MCP_CARDINALITY.get(cardinality)
        if mcp_cardinality is None:
            raise ValueError(
                f"Unknown cardinality: {cardinality!r}. "
                f"Expected one of: {list(WIQ_TO_MCP_CARDINALITY.keys())}"
            )
        return mcp_cardinality
