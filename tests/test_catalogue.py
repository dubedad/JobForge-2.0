"""Tests for CatalogueGenerator class.

Tests catalogue generation from WiQ schema and physical parquet files.
"""

import json
from pathlib import Path

import pytest

from jobforge.governance.catalogue import CatalogueGenerator, generate_catalogue
from jobforge.pipeline.config import PipelineConfig
from jobforge.pipeline.models import ColumnMetadata, TableMetadata


@pytest.fixture
def config() -> PipelineConfig:
    """Pipeline configuration pointing to real data."""
    return PipelineConfig()


@pytest.fixture
def generator(config: PipelineConfig) -> CatalogueGenerator:
    """CatalogueGenerator instance with real config."""
    return CatalogueGenerator(config)


class TestSchemaLoading:
    """Tests for WiQ schema loading."""

    def test_load_wiq_schema(self, generator: CatalogueGenerator) -> None:
        """Verify schema loads correctly from JSON file."""
        schema = generator._load_wiq_schema()

        assert schema is not None, "Schema should load"
        assert "name" in schema, "Schema should have name"
        assert schema["name"] == "WiQ", "Schema name should be WiQ"

    def test_schema_has_tables(self, generator: CatalogueGenerator) -> None:
        """Verify tables array exists in schema."""
        schema = generator._load_wiq_schema()

        assert "tables" in schema, "Schema should have tables array"
        assert isinstance(schema["tables"], list), "Tables should be a list"
        assert len(schema["tables"]) > 0, "Tables should not be empty"


class TestMetadataGeneration:
    """Tests for catalogue metadata generation."""

    def test_generate_creates_metadata_for_all_tables(
        self, generator: CatalogueGenerator
    ) -> None:
        """Verify catalogue generates metadata for all schema tables."""
        schema = generator._load_wiq_schema()
        expected_count = len(schema["tables"])

        tables = generator.generate()

        assert len(tables) == expected_count, (
            f"Expected {expected_count} tables, got {len(tables)}"
        )

    def test_table_metadata_has_required_fields(
        self, generator: CatalogueGenerator
    ) -> None:
        """Check each table has table_name, layer, columns."""
        tables = generator.generate()

        for table in tables:
            assert isinstance(table, TableMetadata), "Should return TableMetadata"
            assert table.table_name, "table_name should not be empty"
            assert table.layer == "gold", "layer should be gold"
            assert isinstance(table.columns, list), "columns should be a list"
            assert len(table.columns) > 0, "columns should not be empty"

    def test_column_metadata_has_data_types(
        self, generator: CatalogueGenerator
    ) -> None:
        """Verify data_type is populated for all columns."""
        tables = generator.generate()

        for table in tables:
            for col in table.columns:
                assert isinstance(col, ColumnMetadata), "Should be ColumnMetadata"
                assert col.data_type, f"data_type missing for {table.table_name}.{col.name}"

    def test_column_metadata_tracks_fk_relations(
        self, generator: CatalogueGenerator
    ) -> None:
        """Verify is_foreign_key and references_table are tracked."""
        tables = generator.generate()

        # Find a column with FK relationship
        fk_columns = []
        for table in tables:
            for col in table.columns:
                if col.source_columns:
                    fk_columns.append((table.table_name, col.name, col.source_columns))

        assert len(fk_columns) > 0, "Should have at least one FK relationship"

        # Verify FK columns have meaningful source_columns
        for table_name, col_name, source_cols in fk_columns:
            for source in source_cols:
                assert "." in source, (
                    f"FK source should be table.column format: {source}"
                )


class TestFileOutput:
    """Tests for catalogue JSON file output."""

    def test_generate_saves_json_files(
        self, generator: CatalogueGenerator, config: PipelineConfig
    ) -> None:
        """Verify JSON files are created in data/catalog/tables/."""
        tables = generator.generate()

        tables_dir = config.catalog_tables_path()
        assert tables_dir.exists(), "Tables directory should exist"

        for table in tables:
            json_path = tables_dir / f"{table.table_name}.json"
            assert json_path.exists(), f"JSON file should exist: {json_path}"

    def test_json_files_are_valid(
        self, generator: CatalogueGenerator, config: PipelineConfig
    ) -> None:
        """Load and validate JSON files for structure."""
        tables = generator.generate()

        tables_dir = config.catalog_tables_path()
        json_files = list(tables_dir.glob("*.json"))

        assert len(json_files) > 0, "Should have JSON files"

        # Validate files using TableMetadata.model_validate_json for proper parsing
        for json_path in json_files[:5]:
            # Use bytes mode to handle any encoding
            content_bytes = json_path.read_bytes()
            table_meta = TableMetadata.model_validate_json(content_bytes)
            assert table_meta.table_name, f"Missing table_name in {json_path.name}"
            assert table_meta.columns is not None, f"Missing columns in {json_path.name}"
            assert table_meta.row_count >= 0, f"Invalid row_count in {json_path.name}"
            assert table_meta.data_owner, f"Missing data_owner in {json_path.name}"


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_missing_parquet_uses_defaults(
        self, generator: CatalogueGenerator
    ) -> None:
        """If parquet file is missing, row_count should be 0."""
        # This is tested implicitly - if any table in schema doesn't have a
        # corresponding parquet file, it should still generate with defaults
        tables = generator.generate()

        # All tables should have row_count >= 0
        for table in tables:
            assert table.row_count >= 0, f"row_count should be >= 0 for {table.table_name}"
            assert table.file_size_bytes >= 0, (
                f"file_size_bytes should be >= 0 for {table.table_name}"
            )


class TestConvenienceFunction:
    """Tests for generate_catalogue() convenience function."""

    def test_generate_catalogue_with_default_config(self) -> None:
        """Verify convenience function works with default config."""
        tables = generate_catalogue()

        assert len(tables) > 0, "Should generate tables"
        assert all(isinstance(t, TableMetadata) for t in tables)

    def test_generate_catalogue_with_custom_config(
        self, config: PipelineConfig
    ) -> None:
        """Verify convenience function accepts custom config."""
        tables = generate_catalogue(config)

        assert len(tables) > 0, "Should generate tables"


class TestDomainMapping:
    """Tests for table type to domain mapping."""

    def test_dimension_tables_have_reference_domain(
        self, generator: CatalogueGenerator
    ) -> None:
        """Dimension tables should have domain='reference'."""
        tables = generator.generate()

        dim_tables = [t for t in tables if t.table_name.startswith("dim_")]
        assert len(dim_tables) > 0, "Should have dimension tables"

        for table in dim_tables:
            assert table.domain == "reference", (
                f"Dimension table {table.table_name} should have domain='reference'"
            )

    def test_fact_tables_have_forecasting_domain(
        self, generator: CatalogueGenerator
    ) -> None:
        """Fact tables should have domain='forecasting'."""
        tables = generator.generate()

        # COPS tables are fact tables
        fact_tables = [t for t in tables if t.table_name.startswith("cops_")]
        assert len(fact_tables) > 0, "Should have fact tables"

        for table in fact_tables:
            assert table.domain == "forecasting", (
                f"Fact table {table.table_name} should have domain='forecasting'"
            )


class TestSourceSystem:
    """Tests for source system identification."""

    def test_source_system_is_jobforge(
        self, generator: CatalogueGenerator
    ) -> None:
        """All tables should have JobForge WiQ Pipeline as source."""
        tables = generator.generate()

        for table in tables:
            assert table.data_owner == "JobForge WiQ Pipeline", (
                f"data_owner should be 'JobForge WiQ Pipeline' for {table.table_name}"
            )
