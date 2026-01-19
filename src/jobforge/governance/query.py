"""Lineage Query Engine for natural language lineage queries.

Implements rule-based natural language parsing to answer lineage questions
like "Where does DIM NOC come from?" with formatted answers including
provenance metadata.
"""

import re
from typing import Callable

from jobforge.governance.graph import LineageGraph
from jobforge.pipeline.config import PipelineConfig


class LineageQueryEngine:
    """Rule-based natural language to lineage query engine.

    Parses natural language questions about data lineage and returns
    human-readable answers with provenance metadata.

    Supported query patterns:
    - "Where does X come from?" - upstream lineage
    - "What feeds X?" / "What tables feed X?" - upstream lineage
    - "What does X feed?" / "What depends on X?" - downstream lineage
    - "Show lineage for X" / "Lineage of X" - full lineage (both directions)
    - "How does X become Y?" / "Path from X to Y" - transformation path
    """

    # Layer ordering for display
    LAYER_ORDER = {"staged": 0, "bronze": 1, "silver": 2, "gold": 3}
    LAYER_NAMES = {
        "staged": "Staged (raw)",
        "bronze": "Bronze (validated)",
        "silver": "Silver (transformed)",
        "gold": "Gold (consumption)",
    }

    def __init__(self, graph: LineageGraph) -> None:
        """Initialize the query engine.

        Args:
            graph: LineageGraph instance for traversal queries.
        """
        self.graph = graph
        self._ensure_graph_built()
        self.patterns: list[tuple[re.Pattern, Callable]] = self._build_patterns()

    def _ensure_graph_built(self) -> None:
        """Lazy-build graph if not already built."""
        _ = self.graph.graph  # Triggers lazy load

    def _build_patterns(self) -> list[tuple[re.Pattern, Callable]]:
        """Build pattern -> handler mappings.

        Returns:
            List of (compiled pattern, handler function) tuples.
        """
        return [
            # "Where does X come from?"
            (
                re.compile(r"where\s+does\s+([a-zA-Z0-9_\s]+?)\s+come\s+from", re.I),
                self._handle_upstream,
            ),
            # "What feeds X?" / "What tables feed X?"
            (
                re.compile(r"what\s+(?:tables?\s+)?feeds?\s+([a-zA-Z0-9_\s]+)", re.I),
                self._handle_upstream,
            ),
            # "What does X feed?"
            (
                re.compile(r"what\s+(?:does\s+)?([a-zA-Z0-9_\s]+?)\s+feed", re.I),
                self._handle_downstream,
            ),
            # "What depends on X?"
            (
                re.compile(r"what\s+depends\s+on\s+([a-zA-Z0-9_\s]+)", re.I),
                self._handle_downstream,
            ),
            # "Show lineage for X" / "Lineage of X"
            (
                re.compile(
                    r"(?:show\s+)?lineage\s+(?:for\s+|of\s+)?([a-zA-Z0-9_\s]+)", re.I
                ),
                self._handle_full_lineage,
            ),
            # "How does X become Y?"
            (
                re.compile(
                    r"how\s+does\s+([a-zA-Z0-9_\s]+?)\s+become\s+([a-zA-Z0-9_\s]+)", re.I
                ),
                self._handle_path,
            ),
            # "Path from X to Y"
            (
                re.compile(
                    r"path\s+from\s+([a-zA-Z0-9_\s]+?)\s+to\s+([a-zA-Z0-9_\s]+)", re.I
                ),
                self._handle_path,
            ),
        ]

    def query(self, question: str) -> str:
        """Process natural language question, return human-readable answer.

        Args:
            question: Natural language question about lineage.

        Returns:
            Formatted answer with provenance metadata, or help message.
        """
        # Try each pattern
        for pattern, handler in self.patterns:
            match = pattern.search(question)
            if match:
                return handler(*match.groups())

        return self._help_message()

    def _normalize_table_name(self, name: str) -> str:
        """Normalize table name for matching.

        Handles:
        - Case conversion (dim_noc, DIM_NOC -> dim_noc)
        - Space to underscore (dim noc -> dim_noc)
        - Strip whitespace

        Args:
            name: Raw table name from user input.

        Returns:
            Normalized table name.
        """
        return name.strip().lower().replace(" ", "_")

    def _find_node(self, table_name: str) -> str | None:
        """Find a node matching the table name in any layer.

        Tries multiple strategies:
        1. Exact match with layer prefix (gold.dim_noc)
        2. Match table suffix across all layers
        3. Fuzzy match without common prefixes

        Args:
            table_name: Normalized table name.

        Returns:
            Node ID if found, None otherwise.
        """
        # Check all nodes
        for node in self.graph.graph.nodes:
            node_table = node.split(".")[-1]
            if node_table == table_name:
                # Prefer gold layer
                if node.startswith("gold."):
                    return node

        # If no gold match, return any match (prefer highest layer)
        for layer in ["gold", "silver", "bronze", "staged"]:
            node = f"{layer}.{table_name}"
            if node in self.graph.graph.nodes:
                return node

        return None

    def _find_all_nodes(self, table_name: str) -> list[str]:
        """Find all nodes matching the table name across layers.

        Args:
            table_name: Normalized table name.

        Returns:
            List of matching node IDs.
        """
        matches = []
        for node in self.graph.graph.nodes:
            node_table = node.split(".")[-1]
            if node_table == table_name:
                matches.append(node)
        return sorted(matches, key=lambda n: self.LAYER_ORDER.get(n.split(".")[0], 99))

    def _get_node_transforms(self, node_id: str) -> list[str]:
        """Get transforms applied to create a node.

        Args:
            node_id: Node identifier.

        Returns:
            List of transform function names.
        """
        data = self.graph.graph.nodes.get(node_id, {})
        return data.get("transforms", [])

    def _get_edge_metadata(self, source: str, target: str) -> dict:
        """Get metadata for an edge (transition).

        Args:
            source: Source node ID.
            target: Target node ID.

        Returns:
            Edge metadata dict with transforms, timestamp, transition_id.
        """
        edge_data = self.graph.graph.edges.get((source, target), {})
        return edge_data

    def _format_node_list(self, nodes: list[str], include_transforms: bool = True) -> str:
        """Format a list of nodes for display.

        Args:
            nodes: List of node IDs.
            include_transforms: Whether to include transform info.

        Returns:
            Formatted string with node information.
        """
        if not nodes:
            return "  (none)"

        lines = []
        for node in nodes:
            layer, table = node.split(".", 1)
            layer_name = self.LAYER_NAMES.get(layer, layer)
            line = f"  - {table} [{layer_name}]"

            if include_transforms:
                transforms = self._get_node_transforms(node)
                if transforms:
                    line += f" (transforms: {', '.join(transforms)})"

            lines.append(line)

        return "\n".join(lines)

    def _handle_upstream(self, table_name: str) -> str:
        """Format upstream lineage answer with provenance.

        Args:
            table_name: Table name from query.

        Returns:
            Formatted answer showing upstream dependencies.
        """
        normalized = self._normalize_table_name(table_name)
        node = self._find_node(normalized)

        if not node:
            return self._table_not_found(normalized)

        layer = node.split(".")[0]
        upstream = self.graph.get_upstream(normalized, layer)

        if not upstream:
            return (
                f"Table '{normalized}' in {self.LAYER_NAMES.get(layer, layer)} "
                f"has no upstream dependencies (it may be a source table)."
            )

        # Group by layer for display
        by_layer: dict[str, list[str]] = {}
        for up_node in upstream:
            up_layer = up_node.split(".")[0]
            if up_layer not in by_layer:
                by_layer[up_layer] = []
            by_layer[up_layer].append(up_node)

        # Build formatted answer
        lines = [
            f"Upstream lineage for '{normalized}' ({self.LAYER_NAMES.get(layer, layer)}):",
            "",
        ]

        # Show in layer order
        for layer_name in ["staged", "bronze", "silver", "gold"]:
            if layer_name in by_layer:
                lines.append(f"{self.LAYER_NAMES.get(layer_name, layer_name)}:")
                lines.append(self._format_node_list(by_layer[layer_name]))
                lines.append("")

        # Add provenance summary
        lines.append("Pipeline path:")
        path = self._build_provenance_path(normalized, node)
        lines.append(path)

        return "\n".join(lines)

    def _handle_downstream(self, table_name: str) -> str:
        """Format downstream lineage answer.

        Args:
            table_name: Table name from query.

        Returns:
            Formatted answer showing downstream dependents.
        """
        normalized = self._normalize_table_name(table_name)
        node = self._find_node(normalized)

        if not node:
            return self._table_not_found(normalized)

        layer = node.split(".")[0]
        downstream = self.graph.get_downstream(normalized, layer)

        if not downstream:
            return (
                f"Table '{normalized}' in {self.LAYER_NAMES.get(layer, layer)} "
                f"has no downstream dependents (it may be a terminal output)."
            )

        # Group by layer for display
        by_layer: dict[str, list[str]] = {}
        for down_node in downstream:
            down_layer = down_node.split(".")[0]
            if down_layer not in by_layer:
                by_layer[down_layer] = []
            by_layer[down_layer].append(down_node)

        # Build formatted answer
        lines = [
            f"Downstream dependents of '{normalized}' ({self.LAYER_NAMES.get(layer, layer)}):",
            "",
        ]

        # Show in layer order
        for layer_name in ["staged", "bronze", "silver", "gold"]:
            if layer_name in by_layer:
                lines.append(f"{self.LAYER_NAMES.get(layer_name, layer_name)}:")
                lines.append(self._format_node_list(by_layer[layer_name]))
                lines.append("")

        return "\n".join(lines)

    def _handle_full_lineage(self, table_name: str) -> str:
        """Show both upstream and downstream.

        Args:
            table_name: Table name from query.

        Returns:
            Formatted answer showing full lineage in both directions.
        """
        normalized = self._normalize_table_name(table_name)
        node = self._find_node(normalized)

        if not node:
            return self._table_not_found(normalized)

        layer = node.split(".")[0]

        lines = [
            f"Full lineage for '{normalized}' ({self.LAYER_NAMES.get(layer, layer)}):",
            "",
        ]

        # Upstream
        upstream = self.graph.get_upstream(normalized, layer)
        lines.append("UPSTREAM (sources):")
        if upstream:
            lines.append(self._format_node_list(upstream))
        else:
            lines.append("  (none - this is a source table)")
        lines.append("")

        # This table
        lines.append("THIS TABLE:")
        lines.append(self._format_node_list([node]))
        lines.append("")

        # Downstream
        downstream = self.graph.get_downstream(normalized, layer)
        lines.append("DOWNSTREAM (dependents):")
        if downstream:
            lines.append(self._format_node_list(downstream))
        else:
            lines.append("  (none - this is a terminal output)")

        return "\n".join(lines)

    def _handle_path(self, source_table: str, target_table: str) -> str:
        """Show transformation path with provenance metadata.

        Args:
            source_table: Source table name.
            target_table: Target table name.

        Returns:
            Formatted answer showing transformation path.
        """
        source_normalized = self._normalize_table_name(source_table)
        target_normalized = self._normalize_table_name(target_table)

        path = self.graph.get_path(source_normalized, target_normalized)

        if not path:
            return (
                f"No transformation path found from '{source_normalized}' "
                f"to '{target_normalized}'.\n\n"
                "This could mean:\n"
                "  - The tables are not connected in the lineage graph\n"
                "  - One or both table names may be incorrect\n"
                "  - The transformation direction might be reversed"
            )

        lines = [
            f"Transformation path from '{source_normalized}' to '{target_normalized}':",
            "",
        ]

        # Show each step in the path
        for i, node in enumerate(path):
            layer, table = node.split(".", 1)
            layer_name = self.LAYER_NAMES.get(layer, layer)
            transforms = self._get_node_transforms(node)

            if i == 0:
                lines.append(f"  1. {table} [{layer_name}] (SOURCE)")
            elif i == len(path) - 1:
                lines.append(f"  {i+1}. {table} [{layer_name}] (TARGET)")
            else:
                lines.append(f"  {i+1}. {table} [{layer_name}]")

            if transforms:
                lines.append(f"       Transforms: {', '.join(transforms)}")

            # Show edge metadata if not last node
            if i < len(path) - 1:
                edge_meta = self._get_edge_metadata(path[i], path[i + 1])
                if edge_meta.get("transforms"):
                    lines.append(f"       -> Applied: {', '.join(edge_meta['transforms'])}")

        lines.append("")
        lines.append(f"Total steps: {len(path) - 1}")

        return "\n".join(lines)

    def _build_provenance_path(self, table_name: str, target_node: str) -> str:
        """Build a concise provenance path string.

        Args:
            table_name: Table name to trace.
            target_node: Target node ID.

        Returns:
            Arrow-formatted path string.
        """
        layer = target_node.split(".")[0]

        # Find the source (staged) node if it exists
        upstream = self.graph.get_upstream(table_name, layer)
        staged_nodes = [n for n in upstream if n.startswith("staged.")]

        if not staged_nodes:
            return f"  {target_node}"

        # Get path from first staged node
        source_table = staged_nodes[0].split(".")[-1]
        path = self.graph.get_path(source_table, table_name)

        if not path:
            return f"  {target_node}"

        # Format as arrow chain
        path_parts = []
        for node in path:
            layer_short = node.split(".")[0][0].upper()  # s, b, s, g
            table = node.split(".")[-1]
            path_parts.append(f"{table}[{layer_short}]")

        return "  " + " -> ".join(path_parts)

    def _table_not_found(self, table_name: str) -> str:
        """Return helpful message when table not found.

        Args:
            table_name: The table name that was searched for.

        Returns:
            Formatted message with suggestions.
        """
        # Find similar table names
        all_tables = set()
        for node in self.graph.graph.nodes:
            all_tables.add(node.split(".")[-1])

        suggestions = [t for t in all_tables if table_name in t or t in table_name][:5]

        lines = [
            f"Table '{table_name}' not found in lineage graph.",
            "",
        ]

        if suggestions:
            lines.append("Did you mean one of these?")
            for s in sorted(suggestions):
                lines.append(f"  - {s}")
        else:
            lines.append("Available tables include:")
            sample_tables = sorted(all_tables)[:10]
            for t in sample_tables:
                lines.append(f"  - {t}")
            if len(all_tables) > 10:
                lines.append(f"  ... and {len(all_tables) - 10} more")

        return "\n".join(lines)

    def _help_message(self) -> str:
        """Return help for unrecognized queries.

        Returns:
            Formatted help message with example queries.
        """
        return """I didn't understand that question. Here are some example queries:

Upstream lineage (where data comes from):
  - "Where does dim_noc come from?"
  - "What feeds cops_employment?"
  - "What tables feed dim_noc?"

Downstream lineage (what uses this data):
  - "What does noc_structure feed?"
  - "What depends on dim_noc?"

Full lineage (both directions):
  - "Show lineage for dim_noc"
  - "Lineage of cops_employment"

Transformation path (how data flows):
  - "How does noc_structure become dim_noc?"
  - "Path from noc_structure to dim_noc"

Tip: Table names are case-insensitive and can use spaces or underscores.
"""
