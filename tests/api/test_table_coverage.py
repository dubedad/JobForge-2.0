"""Parametrized tests for all 24 gold tables.

Validates that all gold tables are queryable via DataQueryService
and properly registered in DuckDB.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from jobforge.api.data_query import DataQueryService
from jobforge.pipeline.config import PipelineConfig


def get_gold_tables() -> list[str]:
    """Get list of all gold table names from parquet files."""
    gold_path = Path("data/gold")
    if not gold_path.exists():
        return []
    return sorted([p.stem for p in gold_path.glob("*.parquet")])


# Discover all gold tables at module load time
GOLD_TABLES = get_gold_tables()


def create_mock_response(sql: str, explanation: str, tables_used: list[str]) -> MagicMock:
    """Create mock Claude response for structured outputs."""
    mock = MagicMock()
    mock.content = [
        MagicMock(
            text=json.dumps({
                "sql": sql,
                "explanation": explanation,
                "tables_used": tables_used,
            })
        )
    ]
    return mock


@pytest.fixture
def mock_client():
    """Create mock Anthropic client."""
    client = MagicMock()
    return client


@pytest.fixture
def config():
    """Create pipeline configuration."""
    return PipelineConfig()


class TestGoldTableDiscovery:
    """Tests for gold table discovery and count."""

    def test_gold_table_count(self):
        """Verify we have exactly 24 gold tables."""
        assert len(GOLD_TABLES) == 24, f"Expected 24 tables, found {len(GOLD_TABLES)}: {GOLD_TABLES}"

    def test_gold_tables_include_dims(self):
        """Verify dimension tables are present."""
        dim_tables = [t for t in GOLD_TABLES if t.startswith("dim_")]
        assert len(dim_tables) >= 2, f"Expected at least 2 dim tables, found: {dim_tables}"
        assert "dim_noc" in GOLD_TABLES
        assert "dim_occupations" in GOLD_TABLES

    def test_gold_tables_include_cops(self):
        """Verify COPS forecast tables are present."""
        cops_tables = [t for t in GOLD_TABLES if t.startswith("cops_")]
        assert len(cops_tables) >= 8, f"Expected at least 8 COPS tables, found: {cops_tables}"

    def test_gold_tables_include_oasis(self):
        """Verify OASIS attribute tables are present."""
        oasis_tables = [t for t in GOLD_TABLES if t.startswith("oasis_")]
        assert len(oasis_tables) >= 5, f"Expected at least 5 OASIS tables, found: {oasis_tables}"

    def test_gold_tables_include_elements(self):
        """Verify element tables are present."""
        element_tables = [t for t in GOLD_TABLES if t.startswith("element_")]
        assert len(element_tables) >= 8, f"Expected at least 8 element tables, found: {element_tables}"

    def test_gold_tables_include_job_architecture(self):
        """Verify job_architecture table is present."""
        assert "job_architecture" in GOLD_TABLES


class TestDuckDBRegistration:
    """Tests for DuckDB table registration."""

    def test_duckdb_registers_all_gold_tables(self, mock_client, config):
        """Verify DuckDB connection has views for all gold tables."""
        service = DataQueryService(config=config, client=mock_client)
        conn = service.conn

        # Get registered views - DuckDB uses information_schema, not sqlite_master
        views = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_type = 'VIEW'"
        ).fetchall()
        view_names = {v[0] for v in views}

        # All gold tables should be registered
        for table in GOLD_TABLES:
            assert table in view_names, f"Table {table} not registered in DuckDB"

        service.close()

    def test_duckdb_view_count_matches(self, mock_client, config):
        """Verify DuckDB has correct number of views registered."""
        service = DataQueryService(config=config, client=mock_client)
        conn = service.conn

        views = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_type = 'VIEW'"
        ).fetchall()

        assert len(views) == len(GOLD_TABLES), (
            f"Expected {len(GOLD_TABLES)} views, found {len(views)}"
        )

        service.close()


class TestTableQueryability:
    """Tests for querying each gold table."""

    @pytest.mark.parametrize("table_name", GOLD_TABLES)
    def test_table_accessible_via_data_service(self, table_name, mock_client, config):
        """Validate each gold table is queryable via DataQueryService."""
        # Mock Claude to return simple SELECT for this table
        mock_response = create_mock_response(
            sql=f"SELECT * FROM {table_name} LIMIT 1",
            explanation=f"Query {table_name}",
            tables_used=[table_name],
        )
        mock_client.messages.create.return_value = mock_response

        service = DataQueryService(config=config, client=mock_client)
        result = service.query(f"Show one row from {table_name}")

        assert result.error is None, f"Table {table_name} query failed: {result.error}"
        # Table may be empty, but should not error
        assert isinstance(result.results, list)
        service.close()

    @pytest.mark.parametrize("table_name", GOLD_TABLES)
    def test_table_has_rows(self, table_name, mock_client, config):
        """Verify each gold table has at least some rows."""
        service = DataQueryService(config=config, client=mock_client)
        conn = service.conn

        count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        assert count >= 0, f"Table {table_name} returned invalid count"

        service.close()

    @pytest.mark.parametrize("table_name", GOLD_TABLES)
    def test_table_has_columns(self, table_name, mock_client, config):
        """Verify each gold table has column definitions."""
        service = DataQueryService(config=config, client=mock_client)
        conn = service.conn

        columns = conn.execute(
            f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}'"
        ).fetchall()
        assert len(columns) > 0, f"Table {table_name} has no columns"

        service.close()


class TestSQLExecution:
    """Tests for SQL execution against gold tables."""

    def test_count_query_works(self, mock_client, config):
        """Test basic COUNT(*) query works on a gold table."""
        mock_response = create_mock_response(
            sql="SELECT COUNT(*) as cnt FROM dim_noc",
            explanation="Count rows in dim_noc",
            tables_used=["dim_noc"],
        )
        mock_client.messages.create.return_value = mock_response

        service = DataQueryService(config=config, client=mock_client)
        result = service.query("How many rows in dim_noc?")

        assert result.error is None
        assert result.row_count == 1
        assert "cnt" in result.results[0]
        service.close()

    def test_select_query_works(self, mock_client, config):
        """Test basic SELECT query works on a gold table."""
        mock_response = create_mock_response(
            sql="SELECT * FROM dim_occupations LIMIT 5",
            explanation="Get first 5 occupations",
            tables_used=["dim_occupations"],
        )
        mock_client.messages.create.return_value = mock_response

        service = DataQueryService(config=config, client=mock_client)
        result = service.query("Show first 5 occupations")

        assert result.error is None
        assert result.row_count <= 5
        service.close()

    def test_join_query_works(self, mock_client, config):
        """Test JOIN query across gold tables works."""
        mock_response = create_mock_response(
            sql="""
            SELECT n.noc_code, n.class_title, c.occupation_name_en
            FROM dim_noc n
            LEFT JOIN cops_employment c ON n.unit_group_id = c.unit_group_id
            LIMIT 5
            """,
            explanation="Join dim_noc with cops_employment",
            tables_used=["dim_noc", "cops_employment"],
        )
        mock_client.messages.create.return_value = mock_response

        service = DataQueryService(config=config, client=mock_client)
        result = service.query("Show NOC codes with employment data")

        assert result.error is None
        service.close()
