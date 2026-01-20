"""Demo orchestrator for SSE-streaming narration.

This module provides the DemoOrchestrator class that reads the WiQ schema
and yields narration events describing what is being deployed.

IMPORTANT ARCHITECTURE NOTE:
The DemoOrchestrator provides NARRATION - it reads schema metadata and yields
events describing what WILL BE / IS BEING deployed. It does NOT invoke MCP
tools or execute any deployment. The actual deployment is triggered externally
by the user running /stagegold in Claude Code (VS Code Pro with MCP access).

Example:
    >>> from jobforge.demo import DemoOrchestrator
    >>> orchestrator = DemoOrchestrator()
    >>> async for event in orchestrator.stream_deployment():
    ...     print(f"{event.event_type.value}: {event.data}")
"""

import asyncio
import time
from pathlib import Path
from typing import AsyncGenerator, Optional

from jobforge.demo.events import DemoEvent, EventType
from jobforge.deployment.deployer import WiQDeployer
from jobforge.deployment.ui import get_table_source


class DemoOrchestrator:
    """Orchestrates SSE narration events for deployment demos.

    Reads the WiQ schema and yields metadata events describing what is being
    deployed. This provides NARRATION for the web UI while the actual
    deployment is executed separately via Claude Code with MCP.

    The orchestrator does NOT:
    - Execute MCP tool calls
    - Trigger actual deployment
    - Modify Power BI models

    The orchestrator DOES:
    - Read WiQ schema metadata
    - Yield START/TABLE/RELATIONSHIP/COMPLETE events
    - Provide timing delays for visual effect

    Attributes:
        schema_path: Optional path to WiQ schema JSON file.
        deployer: WiQDeployer instance for reading schema.

    Example:
        >>> orchestrator = DemoOrchestrator()
        >>> async for event in orchestrator.stream_deployment():
        ...     # Process narration event
        ...     print(event.to_sse_dict())
    """

    def __init__(self, schema_path: Optional[Path] = None) -> None:
        """Initialize the demo orchestrator.

        Args:
            schema_path: Optional path to WiQ schema JSON file.
                        If None, uses default schema location.
        """
        self.schema_path = schema_path
        self.deployer = WiQDeployer()

    async def stream_deployment(self) -> AsyncGenerator[DemoEvent, None]:
        """Stream deployment narration events.

        Yields SSE events describing deployment progress. This is NARRATION
        only - it reads schema metadata and yields descriptive events.
        No actual deployment or MCP calls are made.

        Yields:
            DemoEvent objects for each deployment step.

        Raises:
            FileNotFoundError: If schema file not found.
            ValueError: If schema is invalid.

        Example:
            >>> async for event in orchestrator.stream_deployment():
            ...     if event.event_type == EventType.TABLE:
            ...         print(f"Narrating: {event.data['name']}")
        """
        start_time = time.time()

        try:
            # Load schema
            schema = self.deployer.load_schema(self.schema_path)
            ordered_tables, relationships = self.deployer.get_deployment_order(schema)

            # Yield START event
            yield DemoEvent(
                event_type=EventType.START,
                data={
                    "model_name": schema.name,
                    "total_tables": len(ordered_tables),
                    "total_relationships": len(relationships),
                },
            )
            await asyncio.sleep(0.1)

            # Yield TABLE events
            for idx, table in enumerate(ordered_tables, 1):
                table_type = (
                    table.table_type
                    if isinstance(table.table_type, str)
                    else table.table_type.value
                )
                source = get_table_source(table.name)

                yield DemoEvent(
                    event_type=EventType.TABLE,
                    data={
                        "name": table.name,
                        "table_type": table_type,
                        "source": source,
                        "column_count": len(table.columns),
                        "index": idx,
                        "total": len(ordered_tables),
                    },
                )
                await asyncio.sleep(0.05)  # Small delay for visual effect

            # Yield RELATIONSHIP events
            for idx, rel in enumerate(relationships, 1):
                cardinality = (
                    rel.cardinality
                    if isinstance(rel.cardinality, str)
                    else rel.cardinality.value
                )

                yield DemoEvent(
                    event_type=EventType.RELATIONSHIP,
                    data={
                        "from_table": rel.from_table,
                        "from_column": rel.from_column,
                        "to_table": rel.to_table,
                        "to_column": rel.to_column,
                        "cardinality": cardinality,
                        "index": idx,
                        "total": len(relationships),
                    },
                )
                await asyncio.sleep(0.03)  # Smaller delay for relationships

            # Yield COMPLETE event
            duration_ms = int((time.time() - start_time) * 1000)
            yield DemoEvent(
                event_type=EventType.COMPLETE,
                data={
                    "success": True,
                    "duration_ms": duration_ms,
                    "tables_count": len(ordered_tables),
                    "relationships_count": len(relationships),
                },
            )

        except Exception as e:
            # Yield ERROR event
            yield DemoEvent(
                event_type=EventType.ERROR,
                data={
                    "message": str(e),
                    "error_type": type(e).__name__,
                },
            )

    def get_catalogue_data(self) -> list[dict]:
        """Get catalogue metadata for the Catalogue wizard step.

        Returns a list of table metadata dictionaries suitable for
        displaying in the data catalogue UI.

        Returns:
            List of table metadata dictionaries with name, type, source.
        """
        try:
            schema = self.deployer.load_schema(self.schema_path)
            ordered_tables, _ = self.deployer.get_deployment_order(schema)

            return [
                {
                    "name": table.name,
                    "table_type": (
                        table.table_type
                        if isinstance(table.table_type, str)
                        else table.table_type.value
                    ),
                    "source": get_table_source(table.name),
                    "column_count": len(table.columns),
                    "description": getattr(table, "description", ""),
                }
                for table in ordered_tables
            ]
        except Exception:
            return []
