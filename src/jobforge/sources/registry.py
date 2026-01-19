"""Source registry for managing data source metadata."""

import json
from pathlib import Path

from jobforge.sources.models import SourceMetadata


class SourceRegistry:
    """Registry of data sources with metadata."""

    def __init__(self, sources: list[SourceMetadata]) -> None:
        """Initialize the registry with sources.

        Args:
            sources: List of source metadata objects.
        """
        self._sources = {s.source_id: s for s in sources}

    @classmethod
    def load(cls, path: Path) -> "SourceRegistry":
        """Load registry from sources.json file.

        Args:
            path: Path to the sources.json file.

        Returns:
            SourceRegistry instance with loaded sources.
        """
        data = json.loads(path.read_text(encoding="utf-8"))
        sources = [SourceMetadata.model_validate(s) for s in data.get("sources", [])]
        return cls(sources)

    def get_source(self, source_id: str) -> SourceMetadata:
        """Get source metadata by ID.

        Args:
            source_id: The unique source identifier.

        Returns:
            The source metadata for the given ID.

        Raises:
            KeyError: If the source ID is not found.
        """
        if source_id not in self._sources:
            raise KeyError(f"Unknown source: {source_id}")
        return self._sources[source_id]

    def list_sources(self) -> list[str]:
        """List all source IDs.

        Returns:
            List of all source IDs in the registry.
        """
        return list(self._sources.keys())
