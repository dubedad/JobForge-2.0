"""Pydantic models for lineage graph nodes and edges."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class LineageNode(BaseModel):
    """Represents a table at a specific layer in the lineage graph.

    Node ID format: "{layer}.{table_name}" (e.g., "gold.dim_noc")
    """

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
    )

    node_id: str = Field(description="Unique node identifier: {layer}.{table_name}")
    layer: str = Field(description="Medallion layer (staged, bronze, silver, gold)")
    table_name: str = Field(description="Table name without layer prefix")
    row_count: Optional[int] = Field(
        default=None,
        ge=0,
        description="Number of rows in this table at this layer",
    )
    transforms: list[str] = Field(
        default_factory=list,
        description="Transform functions applied to create this node",
    )


class LineageEdge(BaseModel):
    """Represents a layer transition (edge) in the lineage graph.

    Connects a source node to a target node, recording the transition metadata.
    """

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
    )

    source_node: str = Field(description="Source node ID ({layer}.{table_name})")
    target_node: str = Field(description="Target node ID ({layer}.{table_name})")
    transition_id: str = Field(description="Unique transition identifier (UUID)")
    transforms: list[str] = Field(
        default_factory=list,
        description="Transform functions applied during this transition",
    )
    timestamp: datetime = Field(description="When this transition occurred (UTC)")
