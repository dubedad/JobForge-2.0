"""SSE event models for demo narration.

This module defines the event types and data models for Server-Sent Events
used in the demo infrastructure. Events carry deployment METADATA describing
what is being deployed, not triggers for actual deployment.

Example:
    >>> from jobforge.demo.events import DemoEvent, EventType
    >>> event = DemoEvent(
    ...     event_type=EventType.TABLE,
    ...     data={"name": "dim_noc", "table_type": "dimension", "columns": 9}
    ... )
    >>> event.to_sse_dict()
    {'event': 'table', 'data': '{"name": "dim_noc", ...}'}
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class EventType(Enum):
    """Types of SSE events for deployment narration.

    Events describe deployment progress as metadata, not execution triggers.

    Attributes:
        START: Deployment starting - includes total counts
        TABLE: Table being deployed - includes name, type, source
        RELATIONSHIP: Relationship being created - includes from/to tables
        MEASURE: Measure being created - includes name, folder
        COMPLETE: Deployment completed - includes success status, duration
        ERROR: Error occurred - includes error message
        HEARTBEAT: Keep-alive event for long-running operations
    """

    START = "start"
    TABLE = "table"
    RELATIONSHIP = "relationship"
    MEASURE = "measure"
    COMPLETE = "complete"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


@dataclass
class DemoEvent:
    """SSE event for deployment narration.

    Represents a single event in the deployment narration stream.
    Events carry metadata about deployment progress, not execution triggers.

    Attributes:
        event_type: Type of event (START, TABLE, RELATIONSHIP, etc.)
        data: JSON-serializable payload with event-specific data
        timestamp: When the event occurred (defaults to now)

    Example:
        >>> event = DemoEvent(
        ...     event_type=EventType.START,
        ...     data={"total_tables": 24, "total_relationships": 23}
        ... )
        >>> sse = event.to_sse_dict()
        >>> sse["event"]
        'start'
    """

    event_type: EventType
    data: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)

    def to_sse_dict(self) -> dict[str, str]:
        """Convert to SSE-compatible dictionary.

        Returns a dictionary with 'event' and 'data' keys suitable for
        use with sse-starlette's EventSourceResponse.

        Returns:
            Dictionary with event name and JSON-serialized data.

        Example:
            >>> event = DemoEvent(EventType.TABLE, {"name": "dim_noc"})
            >>> sse = event.to_sse_dict()
            >>> sse["event"]
            'table'
        """
        return {
            "event": self.event_type.value,
            "data": json.dumps(self.data),
        }
