"""Tests for demo orchestrator."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jobforge.demo.events import EventType
from jobforge.demo.orchestrator import DemoOrchestrator
from jobforge.semantic.models import (
    Cardinality,
    Column,
    Relationship,
    SemanticSchema,
    Table,
    TableType,
)


def create_mock_schema() -> SemanticSchema:
    """Create a mock schema for testing."""
    return SemanticSchema(
        name="Test WiQ",
        tables=[
            Table(
                name="dim_noc",
                table_type=TableType.DIMENSION,
                columns=[
                    Column(name="unit_group_id", data_type="VARCHAR", is_primary_key=True),
                    Column(name="noc_code", data_type="VARCHAR"),
                    Column(name="class_title", data_type="VARCHAR"),
                ],
            ),
            Table(
                name="oasis_skills",
                table_type=TableType.ATTRIBUTE,
                columns=[
                    Column(
                        name="unit_group_id",
                        data_type="VARCHAR",
                        is_foreign_key=True,
                        references_table="dim_noc",
                        references_column="unit_group_id",
                    ),
                    Column(name="skill_name", data_type="VARCHAR"),
                    Column(name="importance", data_type="FLOAT"),
                ],
            ),
            Table(
                name="cops_employment",
                table_type=TableType.FACT,
                columns=[
                    Column(
                        name="unit_group_id",
                        data_type="VARCHAR",
                        is_foreign_key=True,
                        references_table="dim_noc",
                        references_column="unit_group_id",
                    ),
                    Column(name="year", data_type="INTEGER"),
                    Column(name="value", data_type="INTEGER"),
                ],
            ),
        ],
        relationships=[
            Relationship(
                from_table="oasis_skills",
                from_column="unit_group_id",
                to_table="dim_noc",
                to_column="unit_group_id",
                cardinality=Cardinality.MANY_TO_ONE,
            ),
            Relationship(
                from_table="cops_employment",
                from_column="unit_group_id",
                to_table="dim_noc",
                to_column="unit_group_id",
                cardinality=Cardinality.MANY_TO_ONE,
            ),
        ],
    )


class TestDemoOrchestratorInit:
    """Tests for DemoOrchestrator initialization."""

    def test_instantiation_without_path(self) -> None:
        """Should instantiate without schema path."""
        orchestrator = DemoOrchestrator()
        assert orchestrator.schema_path is None
        assert orchestrator.deployer is not None

    def test_instantiation_with_path(self) -> None:
        """Should accept optional schema path."""
        path = Path("/some/schema.json")
        orchestrator = DemoOrchestrator(schema_path=path)
        assert orchestrator.schema_path == path

    def test_deployer_is_wiq_deployer(self) -> None:
        """Should use WiQDeployer instance."""
        from jobforge.deployment.deployer import WiQDeployer

        orchestrator = DemoOrchestrator()
        assert isinstance(orchestrator.deployer, WiQDeployer)


class TestStreamDeployment:
    """Tests for stream_deployment method."""

    @pytest.mark.asyncio
    async def test_yields_start_event_first(self) -> None:
        """First event should be START with counts."""
        mock_schema = create_mock_schema()
        orchestrator = DemoOrchestrator()

        with patch.object(orchestrator.deployer, "load_schema", return_value=mock_schema):
            events = []
            async for event in orchestrator.stream_deployment():
                events.append(event)
                if event.event_type == EventType.START:
                    break

            assert len(events) >= 1
            assert events[0].event_type == EventType.START
            assert events[0].data["total_tables"] == 3
            assert events[0].data["total_relationships"] == 2

    @pytest.mark.asyncio
    async def test_yields_table_events(self) -> None:
        """Should yield TABLE events for each table."""
        mock_schema = create_mock_schema()
        orchestrator = DemoOrchestrator()

        with patch.object(orchestrator.deployer, "load_schema", return_value=mock_schema):
            table_events = []
            async for event in orchestrator.stream_deployment():
                if event.event_type == EventType.TABLE:
                    table_events.append(event)

            assert len(table_events) == 3
            # Dimension tables first, then attributes, then facts
            assert table_events[0].data["name"] == "dim_noc"
            assert table_events[0].data["table_type"] == "dimension"
            assert table_events[1].data["name"] == "oasis_skills"
            assert table_events[2].data["name"] == "cops_employment"

    @pytest.mark.asyncio
    async def test_yields_relationship_events(self) -> None:
        """Should yield RELATIONSHIP events for each relationship."""
        mock_schema = create_mock_schema()
        orchestrator = DemoOrchestrator()

        with patch.object(orchestrator.deployer, "load_schema", return_value=mock_schema):
            rel_events = []
            async for event in orchestrator.stream_deployment():
                if event.event_type == EventType.RELATIONSHIP:
                    rel_events.append(event)

            assert len(rel_events) == 2
            assert rel_events[0].data["to_table"] == "dim_noc"
            assert rel_events[1].data["to_table"] == "dim_noc"

    @pytest.mark.asyncio
    async def test_yields_complete_event_last(self) -> None:
        """Last event should be COMPLETE with success."""
        mock_schema = create_mock_schema()
        orchestrator = DemoOrchestrator()

        with patch.object(orchestrator.deployer, "load_schema", return_value=mock_schema):
            events = []
            async for event in orchestrator.stream_deployment():
                events.append(event)

            # Last event should be COMPLETE
            assert events[-1].event_type == EventType.COMPLETE
            assert events[-1].data["success"] is True
            assert "duration_ms" in events[-1].data

    @pytest.mark.asyncio
    async def test_event_order(self) -> None:
        """Events should be in order: START, TABLE..., RELATIONSHIP..., COMPLETE."""
        mock_schema = create_mock_schema()
        orchestrator = DemoOrchestrator()

        with patch.object(orchestrator.deployer, "load_schema", return_value=mock_schema):
            event_types = []
            async for event in orchestrator.stream_deployment():
                event_types.append(event.event_type)

            # Expected order: START, 3 TABLEs, 2 RELATIONSHIPs, COMPLETE
            assert event_types[0] == EventType.START
            assert event_types[1:4] == [EventType.TABLE] * 3
            assert event_types[4:6] == [EventType.RELATIONSHIP] * 2
            assert event_types[6] == EventType.COMPLETE

    @pytest.mark.asyncio
    async def test_table_events_include_index(self) -> None:
        """TABLE events should include index and total."""
        mock_schema = create_mock_schema()
        orchestrator = DemoOrchestrator()

        with patch.object(orchestrator.deployer, "load_schema", return_value=mock_schema):
            table_events = []
            async for event in orchestrator.stream_deployment():
                if event.event_type == EventType.TABLE:
                    table_events.append(event)

            assert table_events[0].data["index"] == 1
            assert table_events[0].data["total"] == 3
            assert table_events[2].data["index"] == 3
            assert table_events[2].data["total"] == 3

    @pytest.mark.asyncio
    async def test_yields_error_on_exception(self) -> None:
        """Should yield ERROR event on exception."""
        orchestrator = DemoOrchestrator()

        with patch.object(
            orchestrator.deployer,
            "load_schema",
            side_effect=FileNotFoundError("Schema not found"),
        ):
            events = []
            async for event in orchestrator.stream_deployment():
                events.append(event)

            assert len(events) == 1
            assert events[0].event_type == EventType.ERROR
            assert "Schema not found" in events[0].data["message"]
            assert events[0].data["error_type"] == "FileNotFoundError"

    @pytest.mark.asyncio
    async def test_does_not_import_mcp_client(self) -> None:
        """Orchestrator should not import or use MCPClient (narration only)."""
        # Verify MCPClient is not imported in orchestrator module
        import jobforge.demo.orchestrator as orchestrator_module

        # Get all imported names
        imported_names = dir(orchestrator_module)

        # MCPClient should not be in the imports
        assert "MCPClient" not in imported_names


class TestGetCatalogueData:
    """Tests for get_catalogue_data method."""

    def test_returns_list_of_table_metadata(self) -> None:
        """Should return list of table metadata dictionaries."""
        mock_schema = create_mock_schema()
        orchestrator = DemoOrchestrator()

        with patch.object(orchestrator.deployer, "load_schema", return_value=mock_schema):
            catalogue = orchestrator.get_catalogue_data()

            assert isinstance(catalogue, list)
            assert len(catalogue) == 3

    def test_table_metadata_has_expected_fields(self) -> None:
        """Each table should have name, type, source, column_count."""
        mock_schema = create_mock_schema()
        orchestrator = DemoOrchestrator()

        with patch.object(orchestrator.deployer, "load_schema", return_value=mock_schema):
            catalogue = orchestrator.get_catalogue_data()

            for table in catalogue:
                assert "name" in table
                assert "table_type" in table
                assert "source" in table
                assert "column_count" in table

    def test_returns_empty_list_on_error(self) -> None:
        """Should return empty list if schema loading fails."""
        orchestrator = DemoOrchestrator()

        with patch.object(
            orchestrator.deployer,
            "load_schema",
            side_effect=FileNotFoundError("Not found"),
        ):
            catalogue = orchestrator.get_catalogue_data()
            assert catalogue == []
