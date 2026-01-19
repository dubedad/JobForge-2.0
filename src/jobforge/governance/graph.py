"""Lineage graph for queryable DAG traversal.

Aggregates transition logs into a NetworkX DAG for upstream/downstream queries.
"""

from pathlib import Path

import networkx as nx

from jobforge.governance.models import LineageNode
from jobforge.pipeline.config import PipelineConfig
from jobforge.pipeline.models import LayerTransitionLog


class LineageGraph:
    """Aggregates transition logs into queryable NetworkX DAG.

    Builds a directed acyclic graph from layer transition logs, enabling
    lineage queries like "what are the upstream dependencies of this table?"
    or "what tables does this feed into?"

    Node ID format: "{layer}.{table_name}" (e.g., "gold.dim_noc")
    """

    def __init__(self, config: PipelineConfig) -> None:
        """Initialize the lineage graph.

        Args:
            config: Pipeline configuration for accessing lineage log paths.
        """
        self.config = config
        self._graph: nx.DiGraph | None = None

    def build_graph(self) -> nx.DiGraph:
        """Build DAG from all transition log JSON files.

        Deduplicates by logical path (source_layer + target_layer + target_table),
        keeping only the most recent transition for each path.

        Returns:
            NetworkX DiGraph with nodes for each table at each layer,
            and edges for each transition.
        """
        G = nx.DiGraph()
        lineage_dir = self.config.catalog_lineage_path()

        if not lineage_dir.exists():
            self._graph = G
            return G

        # Load all transition logs
        transitions: list[LayerTransitionLog] = []
        for json_file in lineage_dir.glob("*.json"):
            try:
                log = LayerTransitionLog.model_validate_json(
                    json_file.read_text(encoding="utf-8")
                )
                transitions.append(log)
            except Exception:
                # Skip invalid files
                continue

        # Deduplicate by logical path, keeping most recent
        seen_paths: dict[tuple[str, str, str], LayerTransitionLog] = {}
        for log in sorted(transitions, key=lambda x: x.started_at, reverse=True):
            target_table = Path(log.target_file).stem
            path_key = (log.source_layer, log.target_layer, target_table)

            if path_key not in seen_paths:
                seen_paths[path_key] = log

        # Build graph from deduplicated transitions
        for log in seen_paths.values():
            target_table = Path(log.target_file).stem
            target_node = f"{log.target_layer}.{target_table}"

            # Add target node with metadata
            G.add_node(
                target_node,
                layer=log.target_layer,
                table=target_table,
                row_count=log.row_count_out,
                transforms=log.transforms_applied,
            )

            # Add edges from each source
            for source_file in log.source_files:
                source_table = Path(source_file).stem
                source_node = f"{log.source_layer}.{source_table}"

                # Add source node if not already present
                if source_node not in G:
                    G.add_node(
                        source_node,
                        layer=log.source_layer,
                        table=source_table,
                        row_count=log.row_count_in,
                        transforms=[],
                    )

                # Add edge with transition metadata
                G.add_edge(
                    source_node,
                    target_node,
                    transition_id=log.transition_id,
                    transforms=log.transforms_applied,
                    timestamp=log.started_at,
                )

        self._graph = G
        return G

    @property
    def graph(self) -> nx.DiGraph:
        """Lazy-load graph on first access.

        Returns:
            The built NetworkX DiGraph.
        """
        if self._graph is None:
            self._graph = self.build_graph()
        return self._graph

    def get_upstream(self, table: str, layer: str = "gold") -> list[str]:
        """Get all upstream dependencies using nx.ancestors().

        Args:
            table: Table name to query (without layer prefix).
            layer: Layer of the table (default: "gold").

        Returns:
            List of upstream node IDs (e.g., ["staged.noc_structure", "bronze.noc_structure"]).
        """
        node = f"{layer}.{table}"
        if node not in self.graph:
            return []
        return sorted(nx.ancestors(self.graph, node))

    def get_downstream(self, table: str, layer: str = "staged") -> list[str]:
        """Get all downstream dependents using nx.descendants().

        Args:
            table: Table name to query (without layer prefix).
            layer: Layer of the table (default: "staged").

        Returns:
            List of downstream node IDs (e.g., ["bronze.noc", "silver.noc", "gold.dim_noc"]).
        """
        node = f"{layer}.{table}"
        if node not in self.graph:
            return []
        return sorted(nx.descendants(self.graph, node))

    def get_path(self, source_table: str, target_table: str) -> list[str]:
        """Get transformation path between tables using nx.shortest_path().

        Searches for paths between any layer combination of source and target.

        Args:
            source_table: Source table name (without layer prefix).
            target_table: Target table name (without layer prefix).

        Returns:
            List of node IDs in path order (e.g., ["staged.noc", "bronze.noc", ...]).
            Empty list if no path exists.
        """
        # Find all nodes matching source and target tables
        source_nodes = [n for n in self.graph.nodes if n.endswith(f".{source_table}")]
        target_nodes = [n for n in self.graph.nodes if n.endswith(f".{target_table}")]

        for src in source_nodes:
            for tgt in target_nodes:
                try:
                    return list(nx.shortest_path(self.graph, src, tgt))
                except nx.NetworkXNoPath:
                    continue

        return []

    def get_node_metadata(self, node_id: str) -> LineageNode | None:
        """Get metadata for a specific node.

        Args:
            node_id: Node identifier in "{layer}.{table}" format.

        Returns:
            LineageNode with metadata, or None if node doesn't exist.
        """
        if node_id not in self.graph:
            return None

        data = self.graph.nodes[node_id]
        return LineageNode(
            node_id=node_id,
            layer=data.get("layer", ""),
            table_name=data.get("table", ""),
            row_count=data.get("row_count"),
            transforms=data.get("transforms", []),
        )

    def is_valid_dag(self) -> bool:
        """Check if graph is a valid DAG (no cycles).

        Returns:
            True if graph is a valid directed acyclic graph.
        """
        return nx.is_directed_acyclic_graph(self.graph)
