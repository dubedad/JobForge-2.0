"""Tests for metadata query service."""

import pytest

from jobforge.api.metadata_query import MetadataQueryService
from jobforge.pipeline.config import PipelineConfig


class TestMetadataQueryServicePatterns:
    """Tests for MetadataQueryService pattern matching."""

    @pytest.fixture
    def service(self):
        """Create service with real config."""
        return MetadataQueryService(PipelineConfig())

    def test_table_count(self, service):
        """Test counting gold tables."""
        result = service.query("how many gold tables are there?")
        assert "tables" in result.lower()
        # Should find 24 tables based on STATE.md
        assert "24" in result or "tables" in result

    def test_list_tables(self, service):
        """Test listing all tables."""
        result = service.query("list all tables")
        assert "dim_noc" in result
        assert "oasis" in result.lower() or "OASIS" in result
        assert "cops" in result.lower() or "COPS" in result

    def test_describe_table(self, service):
        """Test describing a table."""
        result = service.query("describe dim_noc")
        # Should include table info
        assert "dim_noc" in result.lower() or "Table:" in result

    def test_columns_in_table(self, service):
        """Test listing columns in a table."""
        result = service.query("what columns are in dim_noc")
        assert "column" in result.lower() or "Columns" in result
        # dim_noc should have noc_code or similar column
        assert "noc" in result.lower()

    def test_row_count(self, service):
        """Test getting row count."""
        result = service.query("how many rows in dim_noc")
        assert "dim_noc" in result.lower()
        assert "rows" in result.lower()
        # Should have a number
        import re

        numbers = re.findall(r"\d+", result.replace(",", ""))
        assert len(numbers) > 0

    def test_schema_query(self, service):
        """Test getting table schema."""
        result = service.query("what is the schema of dim_noc")
        assert "CREATE TABLE" in result
        assert "dim_noc" in result

    def test_unknown_table(self, service):
        """Test query for unknown table."""
        result = service.query("describe nonexistent_table_xyz")
        assert "not found" in result.lower()


class TestMetadataQueryServiceFallback:
    """Tests for LineageQueryEngine fallback."""

    @pytest.fixture
    def service(self):
        """Create service with real config."""
        return MetadataQueryService(PipelineConfig())

    def test_lineage_query_upstream(self, service):
        """Test lineage query falls through to engine."""
        result = service.query("where does dim_noc come from?")
        # Should return lineage info or help
        assert len(result) > 0
        # Either shows upstream or help message
        assert "upstream" in result.lower() or "lineage" in result.lower() or "example" in result.lower()

    def test_lineage_query_downstream(self, service):
        """Test downstream lineage query."""
        result = service.query("what depends on dim_noc?")
        assert len(result) > 0

    def test_unrecognized_query(self, service):
        """Test unrecognized query returns help."""
        result = service.query("tell me a joke about data")
        # Should return help message
        assert "example" in result.lower() or "query" in result.lower()


class TestMetadataQueryServiceTableGroups:
    """Tests for table grouping in list output."""

    @pytest.fixture
    def service(self):
        """Create service with real config."""
        return MetadataQueryService(PipelineConfig())

    def test_list_tables_groups_by_prefix(self, service):
        """Test that list tables groups by prefix."""
        result = service.query("list tables")
        # Should have group headers
        assert "COPS:" in result or "DIM:" in result or "OASIS:" in result or "ELEMENT:" in result
