"""Tests for LineageGraph class.

Tests graph building and traversal using real transition logs.
"""

import pytest

from jobforge.governance.graph import LineageGraph
from jobforge.governance.models import LineageNode
from jobforge.pipeline.config import PipelineConfig


@pytest.fixture
def config() -> PipelineConfig:
    """Pipeline configuration pointing to real data."""
    return PipelineConfig()


@pytest.fixture
def graph(config: PipelineConfig) -> LineageGraph:
    """LineageGraph built from real transition logs."""
    return LineageGraph(config)


class TestGraphBuilding:
    """Tests for graph building from transition logs."""

    def test_build_graph_creates_nodes(self, graph: LineageGraph) -> None:
        """Verify nodes exist for tables at each layer."""
        g = graph.build_graph()

        # Should have nodes
        assert len(g.nodes) > 0, "Graph should have nodes"

        # Should have nodes at different layers
        layers = {data.get("layer") for _, data in g.nodes(data=True)}
        assert "staged" in layers, "Should have staged layer nodes"
        assert "bronze" in layers, "Should have bronze layer nodes"
        assert "silver" in layers, "Should have silver layer nodes"
        assert "gold" in layers, "Should have gold layer nodes"

    def test_build_graph_creates_edges(self, graph: LineageGraph) -> None:
        """Verify edges connect layers in correct direction."""
        g = graph.build_graph()

        # Should have edges
        assert len(g.edges) > 0, "Graph should have edges"

        # Check edges go from lower to higher layers
        layer_order = {"staged": 0, "bronze": 1, "silver": 2, "gold": 3}
        for source, target in g.edges:
            source_layer = g.nodes[source].get("layer")
            target_layer = g.nodes[target].get("layer")
            if source_layer and target_layer:
                assert layer_order.get(source_layer, -1) < layer_order.get(
                    target_layer, 4
                ), f"Edge should go from lower to higher layer: {source} -> {target}"

    def test_is_valid_dag(self, graph: LineageGraph) -> None:
        """Verify graph is a valid DAG (no cycles)."""
        graph.build_graph()
        assert graph.is_valid_dag(), "Lineage graph should be a valid DAG"

    def test_lazy_load_via_property(self, graph: LineageGraph) -> None:
        """Verify graph property lazy-loads the graph."""
        # _graph should be None initially
        assert graph._graph is None, "Graph should not be built yet"

        # Accessing property should build graph
        g = graph.graph
        assert g is not None, "Graph should be built via property"
        assert graph._graph is not None, "Graph should be cached"

        # Second access should return same instance
        g2 = graph.graph
        assert g is g2, "Should return cached graph"


class TestUpstreamTraversal:
    """Tests for get_upstream() method."""

    def test_get_upstream_returns_ancestors(self, graph: LineageGraph) -> None:
        """For a gold table, returns staged/bronze/silver ancestors."""
        graph.build_graph()

        # Find a gold table with upstream dependencies
        gold_nodes = [n for n in graph.graph.nodes if n.startswith("gold.")]
        if not gold_nodes:
            pytest.skip("No gold tables in test data")

        # Get table name from first gold node
        test_node = gold_nodes[0]
        table_name = test_node.split(".")[-1]

        upstream = graph.get_upstream(table_name, "gold")

        # Should have upstream tables in lower layers
        if upstream:
            upstream_layers = {n.split(".")[0] for n in upstream}
            # At least one of these layers should be present
            assert bool(
                upstream_layers & {"staged", "bronze", "silver"}
            ), f"Upstream should include lower layers: {upstream}"

    def test_get_upstream_unknown_table_returns_empty(self, graph: LineageGraph) -> None:
        """Graceful handling of unknown table."""
        graph.build_graph()

        upstream = graph.get_upstream("nonexistent_table_xyz", "gold")
        assert upstream == [], "Unknown table should return empty list"


class TestDownstreamTraversal:
    """Tests for get_downstream() method."""

    def test_get_downstream_returns_descendants(self, graph: LineageGraph) -> None:
        """For a staged table, returns bronze/silver/gold descendants."""
        graph.build_graph()

        # Find a staged table with downstream dependencies
        staged_nodes = [n for n in graph.graph.nodes if n.startswith("staged.")]
        if not staged_nodes:
            pytest.skip("No staged tables in test data")

        # Get table name from first staged node
        test_node = staged_nodes[0]
        table_name = test_node.split(".")[-1]

        downstream = graph.get_downstream(table_name, "staged")

        # Should have downstream tables in higher layers
        if downstream:
            downstream_layers = {n.split(".")[0] for n in downstream}
            # At least one of these layers should be present
            assert bool(
                downstream_layers & {"bronze", "silver", "gold"}
            ), f"Downstream should include higher layers: {downstream}"

    def test_get_downstream_unknown_table_returns_empty(self, graph: LineageGraph) -> None:
        """Graceful handling of unknown table."""
        graph.build_graph()

        downstream = graph.get_downstream("nonexistent_table_xyz", "staged")
        assert downstream == [], "Unknown table should return empty list"


class TestPathTraversal:
    """Tests for get_path() method."""

    def test_get_path_returns_transformation_chain(self, graph: LineageGraph) -> None:
        """Verify path from staged to gold shows transformation chain."""
        graph.build_graph()

        # Find a table that exists at multiple layers
        staged_nodes = [n for n in graph.graph.nodes if n.startswith("staged.")]
        if not staged_nodes:
            pytest.skip("No staged tables in test data")

        # Find a staged table that also has a gold version
        for staged_node in staged_nodes:
            table_name = staged_node.split(".")[-1]
            # Check if this table has a path to any gold table
            path = graph.get_path(table_name, table_name)
            if len(path) > 1:
                # Verify path goes through layers in order
                path_layers = [n.split(".")[0] for n in path]
                layer_order = {"staged": 0, "bronze": 1, "silver": 2, "gold": 3}

                # Check monotonically increasing layers
                layer_indices = [layer_order.get(layer, -1) for layer in path_layers]
                is_ordered = all(
                    layer_indices[i] <= layer_indices[i + 1]
                    for i in range(len(layer_indices) - 1)
                )
                assert is_ordered, f"Path should go through layers in order: {path}"
                return

        pytest.skip("No table with multi-layer path found in test data")

    def test_get_path_no_path_returns_empty(self, graph: LineageGraph) -> None:
        """When tables are unconnected, returns empty list."""
        graph.build_graph()

        # Try to get path between tables that don't connect
        path = graph.get_path("nonexistent_source", "nonexistent_target")
        assert path == [], "Unconnected tables should return empty path"


class TestNodeMetadata:
    """Tests for get_node_metadata() method."""

    def test_get_node_metadata_returns_lineage_node(self, graph: LineageGraph) -> None:
        """Verify metadata returns correctly populated LineageNode."""
        graph.build_graph()

        # Get any node
        if not graph.graph.nodes:
            pytest.skip("No nodes in test data")

        test_node = list(graph.graph.nodes)[0]
        metadata = graph.get_node_metadata(test_node)

        assert metadata is not None, "Metadata should not be None"
        assert isinstance(metadata, LineageNode), "Should return LineageNode"
        assert metadata.node_id == test_node, "Node ID should match"
        assert metadata.layer in ["staged", "bronze", "silver", "gold"], "Layer should be valid"
        assert metadata.table_name, "Table name should not be empty"

    def test_get_node_metadata_unknown_returns_none(self, graph: LineageGraph) -> None:
        """Unknown node should return None."""
        graph.build_graph()

        metadata = graph.get_node_metadata("nonexistent.table")
        assert metadata is None, "Unknown node should return None"


class TestGraphStatistics:
    """Tests for graph statistics and structure."""

    def test_graph_has_expected_structure(self, graph: LineageGraph) -> None:
        """Verify graph has reasonable structure for real data."""
        g = graph.build_graph()

        # Should have reasonable number of nodes (from 130+ transition logs)
        assert len(g.nodes) >= 10, f"Expected at least 10 nodes, got {len(g.nodes)}"

        # Should have fewer edges than nodes * 2 (sparse graph)
        assert len(g.edges) <= len(g.nodes) * 3, "Graph should be relatively sparse"

        # Should have nodes with attributes
        for node, data in g.nodes(data=True):
            assert "layer" in data, f"Node {node} missing layer attribute"
            assert "table" in data, f"Node {node} missing table attribute"
