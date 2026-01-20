"""Demo infrastructure for live deployment narration.

This module provides SSE-based real-time narration for deployment demos.
The DemoOrchestrator yields metadata events describing what is being deployed,
while the actual deployment is executed externally via Claude Code with MCP.

Architecture:
- DemoOrchestrator reads WiQ schema and yields narration events
- Starlette app serves SSE endpoint for web UI
- Actual deployment is triggered by user running /stagegold in Claude Code
- Web UI provides visual feedback synchronized with external deployment

Example:
    >>> from jobforge.demo import DemoOrchestrator, create_app
    >>> app = create_app()  # Creates Starlette app with SSE endpoint
"""

from jobforge.demo.events import DemoEvent, EventType
from jobforge.demo.orchestrator import DemoOrchestrator

__all__ = ["DemoEvent", "EventType", "DemoOrchestrator"]
