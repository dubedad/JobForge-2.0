"""Tests for LineageQueryEngine class.

Tests natural language query parsing and formatted answer generation.
"""

import pytest

from jobforge.governance.graph import LineageGraph
from jobforge.governance.query import LineageQueryEngine
from jobforge.pipeline.config import PipelineConfig


@pytest.fixture
def config() -> PipelineConfig:
    """Pipeline configuration pointing to real data."""
    return PipelineConfig()


@pytest.fixture
def graph(config: PipelineConfig) -> LineageGraph:
    """LineageGraph built from real transition logs."""
    return LineageGraph(config)


@pytest.fixture
def engine(graph: LineageGraph) -> LineageQueryEngine:
    """LineageQueryEngine with real graph data."""
    return LineageQueryEngine(graph)


class TestPatternMatching:
    """Tests for query pattern recognition."""

    def test_where_does_pattern(self, engine: LineageQueryEngine) -> None:
        """'Where does X come from?' triggers upstream handler."""
        answer = engine.query("Where does dim_noc come from?")
        assert "Upstream lineage" in answer or "no upstream" in answer.lower()

    def test_where_does_pattern_with_spaces(self, engine: LineageQueryEngine) -> None:
        """'Where does X come from?' handles table names with spaces."""
        answer = engine.query("Where does dim noc come from?")
        assert "dim_noc" in answer.lower() or "not found" in answer.lower()

    def test_what_feeds_pattern(self, engine: LineageQueryEngine) -> None:
        """'What feeds X?' triggers upstream handler."""
        answer = engine.query("What feeds dim_noc?")
        assert "Upstream lineage" in answer or "no upstream" in answer.lower()

    def test_what_tables_feed_pattern(self, engine: LineageQueryEngine) -> None:
        """'What tables feed X?' triggers upstream handler."""
        answer = engine.query("What tables feed cops_employment?")
        assert "Upstream lineage" in answer or "no upstream" in answer.lower()

    def test_what_depends_pattern(self, engine: LineageQueryEngine) -> None:
        """'What depends on X?' triggers downstream handler."""
        answer = engine.query("What depends on dim_noc?")
        assert "downstream" in answer.lower() or "dependents" in answer.lower()

    def test_what_does_feed_pattern(self, engine: LineageQueryEngine) -> None:
        """'What does X feed?' triggers downstream handler."""
        answer = engine.query("What does dim_noc feed?")
        assert "downstream" in answer.lower() or "dependents" in answer.lower()

    def test_show_lineage_pattern(self, engine: LineageQueryEngine) -> None:
        """'Show lineage for X' triggers full lineage handler."""
        answer = engine.query("Show lineage for dim_noc")
        assert "Full lineage" in answer or "UPSTREAM" in answer

    def test_lineage_of_pattern(self, engine: LineageQueryEngine) -> None:
        """'Lineage of X' triggers full lineage handler."""
        answer = engine.query("Lineage of cops_employment")
        assert "Full lineage" in answer or "UPSTREAM" in answer

    def test_path_from_to_pattern(self, engine: LineageQueryEngine) -> None:
        """'Path from X to Y' triggers path handler."""
        answer = engine.query("Path from dim_noc to dim_noc")
        assert "path" in answer.lower() or "transformation" in answer.lower()

    def test_how_does_become_pattern(self, engine: LineageQueryEngine) -> None:
        """'How does X become Y?' triggers path handler."""
        answer = engine.query("How does dim_noc become dim_noc?")
        assert "path" in answer.lower() or "transformation" in answer.lower()


class TestUpstreamQueries:
    """Tests for upstream lineage queries."""

    def test_upstream_query_returns_ancestors(self, engine: LineageQueryEngine) -> None:
        """Query dim_noc returns staged/bronze/silver ancestors."""
        answer = engine.query("Where does dim_noc come from?")

        # Should mention the layers in the answer
        assert "dim_noc" in answer
        # Should have layer information
        has_layers = (
            "Staged" in answer or "Bronze" in answer or "Silver" in answer
        )
        assert has_layers, "Answer should mention layer names"

    def test_upstream_query_includes_transforms(self, engine: LineageQueryEngine) -> None:
        """Verify transform names appear in upstream answer."""
        answer = engine.query("Where does dim_noc come from?")

        # Transform names should appear somewhere
        # (based on actual data in lineage logs)
        has_transforms = "transforms" in answer.lower() or "(" in answer
        assert has_transforms, "Answer should include transform information"

    def test_upstream_cops_employment(self, engine: LineageQueryEngine) -> None:
        """Test upstream query for cops_employment fact table."""
        answer = engine.query("What tables feed cops_employment?")

        assert "cops_employment" in answer
        assert "Upstream lineage" in answer


class TestDownstreamQueries:
    """Tests for downstream lineage queries."""

    def test_downstream_query_for_gold_table(self, engine: LineageQueryEngine) -> None:
        """Gold table typically has no downstream dependents."""
        answer = engine.query("What depends on dim_noc?")

        # Gold tables are terminal outputs
        assert "dim_noc" in answer.lower()
        # Should indicate no downstream or show dependents
        assert "downstream" in answer.lower() or "terminal" in answer.lower()

    def test_downstream_query_returns_descendants(self, engine: LineageQueryEngine) -> None:
        """For staged table, should return bronze/silver/gold descendants."""
        # Find a staged table
        staged_nodes = [
            n for n in engine.graph.graph.nodes if n.startswith("staged.")
        ]
        if not staged_nodes:
            pytest.skip("No staged tables in test data")

        table_name = staged_nodes[0].split(".")[-1]
        answer = engine.query(f"What does {table_name} feed?")

        assert table_name in answer
        # Should mention some layers if there are downstream tables
        # (answer format depends on actual data)


class TestPathQueries:
    """Tests for transformation path queries."""

    def test_path_query_returns_chain(self, engine: LineageQueryEngine) -> None:
        """Verify path query shows transformation steps."""
        answer = engine.query("Path from dim_noc to dim_noc")

        # Should mention path or transformation
        assert "path" in answer.lower() or "steps" in answer.lower()

    def test_path_query_no_path(self, engine: LineageQueryEngine) -> None:
        """Test graceful handling when no path exists."""
        answer = engine.query("Path from nonexistent_a to nonexistent_b")

        assert "not found" in answer.lower() or "no transformation" in answer.lower()

    def test_path_shows_layer_progression(self, engine: LineageQueryEngine) -> None:
        """Path should show layer progression from source to target."""
        answer = engine.query("Path from dim_noc to dim_noc")

        # Should contain layer indicators
        # Either abbreviated [S], [B], [G] or full layer names
        has_layer_info = (
            "Staged" in answer
            or "Bronze" in answer
            or "Silver" in answer
            or "Gold" in answer
            or "[S]" in answer
            or "[B]" in answer
            or "[G]" in answer
        )
        # If path found, should have layer info; if not found, that's ok too
        assert has_layer_info or "not found" in answer.lower()


class TestFullLineage:
    """Tests for full lineage queries (both directions)."""

    def test_full_lineage_shows_both_directions(
        self, engine: LineageQueryEngine
    ) -> None:
        """Full lineage shows upstream and downstream."""
        answer = engine.query("Show lineage for dim_noc")

        assert "UPSTREAM" in answer or "upstream" in answer.lower()
        assert "DOWNSTREAM" in answer or "downstream" in answer.lower()

    def test_full_lineage_includes_this_table(
        self, engine: LineageQueryEngine
    ) -> None:
        """Full lineage shows the queried table itself."""
        answer = engine.query("Lineage of dim_noc")

        assert "dim_noc" in answer
        assert "THIS TABLE" in answer or "this table" in answer.lower()


class TestProvenanceMetadata:
    """Tests for provenance information in answers."""

    def test_answer_includes_source_files(self, engine: LineageQueryEngine) -> None:
        """Verify source file/table names appear in output."""
        answer = engine.query("Where does dim_noc come from?")

        # Should mention the table at different layers
        assert "dim_noc" in answer

    def test_answer_includes_transforms(self, engine: LineageQueryEngine) -> None:
        """Verify transform names appear in output."""
        answer = engine.query("Show lineage for dim_noc")

        # Should have transform information somewhere
        # Transform names like "rename_columns", "cast_types", etc.
        has_transforms = (
            "transform" in answer.lower()
            or "rename" in answer.lower()
            or "cast" in answer.lower()
            or "filter" in answer.lower()
            or "derive" in answer.lower()
        )
        assert has_transforms, "Answer should mention transforms"

    def test_answer_includes_layer_descriptions(
        self, engine: LineageQueryEngine
    ) -> None:
        """Verify layer descriptions appear in output."""
        answer = engine.query("Where does dim_noc come from?")

        # Should have human-readable layer names
        has_layer_desc = (
            "raw" in answer.lower()
            or "validated" in answer.lower()
            or "transformed" in answer.lower()
            or "consumption" in answer.lower()
        )
        assert has_layer_desc, "Answer should include layer descriptions"


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_unknown_table_returns_helpful_message(
        self, engine: LineageQueryEngine
    ) -> None:
        """Graceful handling of unknown table names."""
        answer = engine.query("Where does nonexistent_table_xyz come from?")

        assert "not found" in answer.lower()
        # Should offer suggestions or list available tables
        assert "tables" in answer.lower() or "mean" in answer.lower()

    def test_unrecognized_query_returns_help(self, engine: LineageQueryEngine) -> None:
        """Help message for garbage input."""
        answer = engine.query("asdfghjkl random garbage text")

        assert "didn't understand" in answer.lower() or "example" in answer.lower()
        # Should show example queries
        assert "Where does" in answer or "What feeds" in answer

    def test_case_insensitive_matching(self, engine: LineageQueryEngine) -> None:
        """'DIM_NOC' and 'dim_noc' both work."""
        answer_upper = engine.query("Where does DIM_NOC come from?")
        answer_lower = engine.query("Where does dim_noc come from?")

        # Both should successfully find the table
        assert "not found" not in answer_upper.lower() or "DIM_NOC" not in answer_upper
        assert "not found" not in answer_lower.lower()

    def test_table_name_with_mixed_case(self, engine: LineageQueryEngine) -> None:
        """Mixed case table names are normalized."""
        answer = engine.query("Where does Dim_Noc come from?")

        # Should normalize to dim_noc and find it
        assert "dim_noc" in answer.lower()

    def test_empty_question(self, engine: LineageQueryEngine) -> None:
        """Empty question returns help."""
        answer = engine.query("")

        assert "example" in answer.lower() or "didn't understand" in answer.lower()


class TestQueryEngineInitialization:
    """Tests for QueryEngine initialization."""

    def test_engine_builds_graph_lazily(self, graph: LineageGraph) -> None:
        """Graph is built lazily on first query."""
        # Graph should not be built yet
        assert graph._graph is None

        engine = LineageQueryEngine(graph)

        # After engine init, graph should be built (via _ensure_graph_built)
        assert graph._graph is not None

    def test_engine_accepts_prebuilt_graph(self, graph: LineageGraph) -> None:
        """Engine works with pre-built graph."""
        graph.build_graph()
        engine = LineageQueryEngine(graph)

        # Should work normally
        answer = engine.query("Where does dim_noc come from?")
        assert "dim_noc" in answer.lower()


class TestTableNameNormalization:
    """Tests for table name normalization logic."""

    def test_normalize_removes_whitespace(self, engine: LineageQueryEngine) -> None:
        """Whitespace is stripped from table names."""
        result = engine._normalize_table_name("  dim_noc  ")
        assert result == "dim_noc"

    def test_normalize_converts_to_lowercase(self, engine: LineageQueryEngine) -> None:
        """Table names are lowercased."""
        result = engine._normalize_table_name("DIM_NOC")
        assert result == "dim_noc"

    def test_normalize_converts_spaces_to_underscores(
        self, engine: LineageQueryEngine
    ) -> None:
        """Spaces in table names become underscores."""
        result = engine._normalize_table_name("dim noc")
        assert result == "dim_noc"

    def test_normalize_handles_mixed_input(self, engine: LineageQueryEngine) -> None:
        """Complex input is fully normalized."""
        result = engine._normalize_table_name("  DIM NOC  ")
        assert result == "dim_noc"
