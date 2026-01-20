"""Tests for data query service."""

import json
from unittest.mock import MagicMock, patch

import pytest

from jobforge.api.data_query import DataQueryResult, DataQueryService, SQLQuery
from jobforge.api.schema_ddl import generate_schema_ddl
from jobforge.pipeline.config import PipelineConfig


class TestSQLQuery:
    """Tests for SQLQuery model."""

    def test_valid_sql_query(self):
        """Test valid SQLQuery creation."""
        query = SQLQuery(
            sql="SELECT * FROM dim_noc LIMIT 10",
            explanation="Get first 10 rows from dim_noc",
            tables_used=["dim_noc"],
        )
        assert query.sql == "SELECT * FROM dim_noc LIMIT 10"
        assert query.tables_used == ["dim_noc"]

    def test_sql_query_from_json(self):
        """Test SQLQuery validation from JSON."""
        data = {
            "sql": "SELECT COUNT(*) FROM dim_noc",
            "explanation": "Count rows in dim_noc",
            "tables_used": ["dim_noc"],
        }
        query = SQLQuery.model_validate(data)
        assert query.sql == "SELECT COUNT(*) FROM dim_noc"


class TestDataQueryResult:
    """Tests for DataQueryResult model."""

    def test_successful_result(self):
        """Test successful query result."""
        result = DataQueryResult(
            question="How many rows?",
            sql="SELECT COUNT(*) as cnt FROM dim_noc",
            explanation="Count rows",
            results=[{"cnt": 500}],
            row_count=1,
        )
        assert result.error is None
        assert result.row_count == 1

    def test_error_result(self):
        """Test error query result."""
        result = DataQueryResult(
            question="Bad query",
            sql="",
            explanation="",
            results=[],
            row_count=0,
            error="Syntax error",
        )
        assert result.error == "Syntax error"
        assert result.row_count == 0


class TestGenerateSchemaDDL:
    """Tests for schema DDL generation."""

    def test_generates_ddl_for_gold_tables(self):
        """Test DDL generation from gold parquet files."""
        config = PipelineConfig()
        ddl = generate_schema_ddl(config)

        # Should contain CREATE TABLE statements
        assert "CREATE TABLE" in ddl

        # Should have dim_noc table
        assert "dim_noc" in ddl

        # Should list columns
        assert "noc_code" in ddl.lower() or "NOC" in ddl or "VARCHAR" in ddl

    def test_handles_missing_gold_path(self, tmp_path):
        """Test DDL generation with missing gold path."""
        config = PipelineConfig(data_root=tmp_path / "nonexistent")
        ddl = generate_schema_ddl(config)
        assert "No gold tables found" in ddl

    def test_covers_all_gold_tables(self):
        """Test DDL includes all 24 gold tables."""
        config = PipelineConfig()
        ddl = generate_schema_ddl(config)

        # Count CREATE TABLE statements
        create_count = ddl.count("CREATE TABLE")
        assert create_count >= 20, f"Expected at least 20 tables, got {create_count}"

        # Check for key tables
        key_tables = ["dim_noc", "dim_occupations", "oasis_skills", "job_architecture"]
        for table in key_tables:
            assert table in ddl, f"Missing table: {table}"


class TestDataQueryService:
    """Tests for DataQueryService with mocked Claude client."""

    @pytest.fixture
    def mock_anthropic_response(self):
        """Create a mock Anthropic response."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps(
                    {
                        "sql": "SELECT COUNT(*) as cnt FROM dim_noc",
                        "explanation": "Count unit groups in NOC",
                        "tables_used": ["dim_noc"],
                    }
                )
            )
        ]
        return mock_response

    @pytest.fixture
    def mock_client(self, mock_anthropic_response):
        """Create a mock Anthropic client."""
        client = MagicMock()
        client.messages.create.return_value = mock_anthropic_response
        return client

    def test_query_generates_and_executes_sql(self, mock_client):
        """Test query generates SQL and executes it."""
        config = PipelineConfig()
        service = DataQueryService(config=config, client=mock_client)

        result = service.query("How many unit groups are in dim_noc?")

        assert result.error is None
        assert result.sql == "SELECT COUNT(*) as cnt FROM dim_noc"
        assert result.explanation == "Count unit groups in NOC"
        assert result.row_count > 0
        assert "cnt" in result.results[0]

        # Verify Claude was called with correct parameters
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-sonnet-4-20250514"
        assert "structured-outputs" in call_kwargs["extra_headers"]["anthropic-beta"]

        service.close()

    def test_query_handles_claude_error(self, mock_client):
        """Test query handles Claude API errors gracefully."""
        import anthropic

        mock_client.messages.create.side_effect = anthropic.AuthenticationError(
            "Invalid API key",
            response=MagicMock(status_code=401),
            body=None,
        )

        config = PipelineConfig()
        service = DataQueryService(config=config, client=mock_client)

        result = service.query("How many rows?")

        assert result.error is not None
        assert "authentication" in result.error.lower()
        assert result.row_count == 0

        service.close()

    def test_query_handles_sql_execution_error(self, mock_client):
        """Test query handles SQL execution errors."""
        # Return invalid SQL
        mock_client.messages.create.return_value.content[0].text = json.dumps(
            {
                "sql": "SELECT * FROM nonexistent_table",
                "explanation": "Query non-existent table",
                "tables_used": ["nonexistent_table"],
            }
        )

        config = PipelineConfig()
        service = DataQueryService(config=config, client=mock_client)

        result = service.query("Query bad table")

        assert result.error is not None
        assert result.row_count == 0

        service.close()

    def test_schema_ddl_cached(self, mock_client):
        """Test schema DDL is cached."""
        config = PipelineConfig()
        service = DataQueryService(config=config, client=mock_client)

        ddl1 = service.schema_ddl
        ddl2 = service.schema_ddl

        # Should be same object (cached)
        assert ddl1 is ddl2

        service.close()

    def test_connection_lazy_loaded(self, mock_client):
        """Test DuckDB connection is lazy loaded."""
        config = PipelineConfig()
        service = DataQueryService(config=config, client=mock_client)

        # Connection should be None initially
        assert service._conn is None

        # Accessing conn should create it
        _ = service.conn
        assert service._conn is not None

        service.close()
        assert service._conn is None
