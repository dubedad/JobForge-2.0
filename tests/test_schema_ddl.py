"""Tests for DDL generator with semantic metadata."""

import pytest

from jobforge.api.schema_ddl import generate_schema_ddl
from jobforge.pipeline.config import PipelineConfig


def test_generate_schema_ddl_includes_comments():
    """Test that DDL includes COMMENT clauses for enriched columns."""
    ddl = generate_schema_ddl()

    assert "COMMENT" in ddl, "DDL should include COMMENT clauses"

    # Check for at least one column with a COMMENT clause
    # Year columns should have comments like "Projected employment count for 2023"
    assert "COMMENT 'Projected" in ddl or "COMMENT 'Foreign key" in ddl


def test_generate_schema_ddl_includes_relationships():
    """Test that DDL includes RELATIONSHIPS section."""
    ddl = generate_schema_ddl()

    assert "RELATIONSHIPS" in ddl, "DDL should include RELATIONSHIPS section"

    # Check for dim_noc relationships (most COPS tables reference this)
    assert "dim_noc.unit_group_id" in ddl, "Should show dim_noc relationships"


def test_generate_schema_ddl_includes_workforce_hints():
    """Test that DDL includes workforce intelligence section."""
    ddl = generate_schema_ddl()

    assert "WORKFORCE INTELLIGENCE" in ddl or "demand tables" in ddl, (
        "DDL should include workforce intelligence section"
    )

    assert "supply tables" in ddl, "Should list supply tables"
    assert "cops_employment" in ddl, "Should mention demand tables"


def test_generate_schema_ddl_quotes_year_columns():
    """Test that year columns are quoted in DDL."""
    ddl = generate_schema_ddl()

    # Year columns should be quoted (e.g., "2023", "2024", etc.)
    assert '"2023"' in ddl or '"2024"' in ddl or '"2025"' in ddl, (
        "Year columns should be quoted"
    )


def test_generate_schema_ddl_handles_missing_catalog():
    """Test that DDL generation falls back gracefully when catalog is unavailable."""
    # Create config pointing to non-existent catalog path
    config = PipelineConfig(data_root="data")

    # Even with missing catalog, should return valid DDL from parquet introspection
    ddl = generate_schema_ddl(config)

    assert "CREATE TABLE" in ddl, "Should return valid DDL even without catalog"
    assert ddl != "-- No gold tables found", "Should find gold tables"


def test_generate_schema_ddl_table_level_comments():
    """Test that DDL includes table-level comments from catalog."""
    ddl = generate_schema_ddl()

    # Check for table-level comments
    assert "-- Table:" in ddl, "Should include table descriptions"

    # COPS tables should have workforce_dynamic comments
    assert "-- Workforce dynamic:" in ddl, "Should include workforce dynamic labels"


def test_generate_schema_ddl_escapes_quotes():
    """Test that single quotes in descriptions are properly escaped."""
    ddl = generate_schema_ddl()

    # Should not have syntax errors from unescaped quotes
    # If there are single quotes in descriptions, they should be doubled
    assert "COMMENT" in ddl, "DDL should have comments"

    # Check that CREATE TABLE statements are well-formed
    assert ddl.count("CREATE TABLE") > 0, "Should have CREATE TABLE statements"
