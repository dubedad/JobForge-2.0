"""Tests for catalog enrichment functionality."""

import json
from pathlib import Path

import pytest

from jobforge.catalog.enrich import enrich_catalog


def test_enrich_catalog_returns_counts(tmp_path: Path) -> None:
    """Test that enrich_catalog returns proper counts dictionary."""
    # Create a sample catalog file
    sample_table = {
        "table_name": "cops_employment",
        "description": "Old description",
        "columns": [
            {
                "name": "unit_group_id",
                "data_type": "VARCHAR",
                "description": "Column of type VARCHAR",
            },
            {
                "name": "2025",
                "data_type": "VARCHAR",
                "description": "Column of type VARCHAR",
            },
        ],
    }

    catalog_dir = tmp_path / "catalog"
    catalog_dir.mkdir()
    with open(catalog_dir / "cops_employment.json", "w") as f:
        json.dump(sample_table, f)

    # Run enrichment
    results = enrich_catalog(catalog_dir)

    # Verify results structure
    assert isinstance(results, dict)
    assert "tables_updated" in results
    assert "columns_enriched" in results
    assert isinstance(results["tables_updated"], int)
    assert isinstance(results["columns_enriched"], int)
    assert results["tables_updated"] >= 0
    assert results["columns_enriched"] >= 0


def test_enrichment_adds_workforce_dynamic(tmp_path: Path) -> None:
    """Test that enrichment adds workforce_dynamic field to COPS tables."""
    # Create COPS employment table without workforce_dynamic
    sample_table = {
        "table_name": "cops_employment",
        "description": "Test table",
        "columns": [],
    }

    catalog_dir = tmp_path / "catalog"
    catalog_dir.mkdir()
    table_file = catalog_dir / "cops_employment.json"
    with open(table_file, "w") as f:
        json.dump(sample_table, f)

    # Run enrichment
    enrich_catalog(catalog_dir)

    # Load result and verify workforce_dynamic added
    with open(table_file, "r") as f:
        enriched = json.load(f)

    assert "workforce_dynamic" in enriched
    assert enriched["workforce_dynamic"] == "demand"


def test_enrichment_adds_workforce_dynamic_supply(tmp_path: Path) -> None:
    """Test that enrichment correctly classifies supply tables."""
    # Create COPS immigration table (supply)
    sample_table = {
        "table_name": "cops_immigration",
        "description": "Test table",
        "columns": [],
    }

    catalog_dir = tmp_path / "catalog"
    catalog_dir.mkdir()
    table_file = catalog_dir / "cops_immigration.json"
    with open(table_file, "w") as f:
        json.dump(sample_table, f)

    # Run enrichment
    enrich_catalog(catalog_dir)

    # Load result and verify workforce_dynamic added
    with open(table_file, "r") as f:
        enriched = json.load(f)

    assert "workforce_dynamic" in enriched
    assert enriched["workforce_dynamic"] == "supply"


def test_enrichment_updates_column_descriptions(tmp_path: Path) -> None:
    """Test that enrichment replaces generic descriptions with semantic ones."""
    # Create table with generic column description
    sample_table = {
        "table_name": "cops_employment",
        "description": "Test table",
        "columns": [
            {
                "name": "unit_group_id",
                "data_type": "VARCHAR",
                "description": "Column of type VARCHAR",
            },
            {
                "name": "2025",
                "data_type": "VARCHAR",
                "description": "Column of type VARCHAR",
            },
        ],
    }

    catalog_dir = tmp_path / "catalog"
    catalog_dir.mkdir()
    table_file = catalog_dir / "cops_employment.json"
    with open(table_file, "w") as f:
        json.dump(sample_table, f)

    # Run enrichment
    enrich_catalog(catalog_dir)

    # Load result and verify descriptions updated
    with open(table_file, "r") as f:
        enriched = json.load(f)

    unit_group_col = enriched["columns"][0]
    year_col = enriched["columns"][1]

    assert unit_group_col["description"] != "Column of type VARCHAR"
    assert "NOC" in unit_group_col["description"]
    assert year_col["description"] != "Column of type VARCHAR"
    assert "employment" in year_col["description"].lower()
    assert "2025" in year_col["description"]


def test_enrichment_preserves_existing_fields(tmp_path: Path) -> None:
    """Test that enrichment preserves custom fields in catalog JSON."""
    # Create table with custom field
    sample_table = {
        "table_name": "cops_employment",
        "description": "Test table",
        "custom_field": "preserve_me",
        "another_custom": {"nested": "value"},
        "columns": [
            {
                "name": "unit_group_id",
                "data_type": "VARCHAR",
                "description": "Column of type VARCHAR",
                "custom_col_field": "also_preserve",
            }
        ],
    }

    catalog_dir = tmp_path / "catalog"
    catalog_dir.mkdir()
    table_file = catalog_dir / "cops_employment.json"
    with open(table_file, "w") as f:
        json.dump(sample_table, f)

    # Run enrichment
    enrich_catalog(catalog_dir)

    # Load result and verify custom fields preserved
    with open(table_file, "r") as f:
        enriched = json.load(f)

    assert "custom_field" in enriched
    assert enriched["custom_field"] == "preserve_me"
    assert "another_custom" in enriched
    assert enriched["another_custom"] == {"nested": "value"}
    assert "custom_col_field" in enriched["columns"][0]
    assert enriched["columns"][0]["custom_col_field"] == "also_preserve"


def test_enrichment_dim_noc_specific_descriptions(tmp_path: Path) -> None:
    """Test that dim_noc gets table-specific descriptions, not COPS generic ones."""
    # Create dim_noc table
    sample_table = {
        "table_name": "dim_noc",
        "description": "Test table",
        "columns": [
            {
                "name": "unit_group_id",
                "data_type": "VARCHAR",
                "description": "Column of type VARCHAR",
            },
            {
                "name": "class_title",
                "data_type": "VARCHAR",
                "description": "Column of type VARCHAR",
            },
        ],
    }

    catalog_dir = tmp_path / "catalog"
    catalog_dir.mkdir()
    table_file = catalog_dir / "dim_noc.json"
    with open(table_file, "w") as f:
        json.dump(sample_table, f)

    # Run enrichment
    enrich_catalog(catalog_dir)

    # Load result and verify dim_noc-specific descriptions
    with open(table_file, "r") as f:
        enriched = json.load(f)

    unit_group_col = enriched["columns"][0]
    class_title_col = enriched["columns"][1]

    # Should get primary key description, not foreign key
    assert "Primary key" in unit_group_col["description"]
    assert "Foreign key" not in unit_group_col["description"]
    assert "Official NOC occupation title" in class_title_col["description"]


def test_enrichment_year_columns_vary_by_table(tmp_path: Path) -> None:
    """Test that year column descriptions vary based on table type."""
    # Create two different COPS tables
    employment_table = {
        "table_name": "cops_employment",
        "columns": [{"name": "2025", "data_type": "VARCHAR", "description": "old"}],
    }
    immigration_table = {
        "table_name": "cops_immigration",
        "columns": [{"name": "2025", "data_type": "VARCHAR", "description": "old"}],
    }

    catalog_dir = tmp_path / "catalog"
    catalog_dir.mkdir()

    with open(catalog_dir / "cops_employment.json", "w") as f:
        json.dump(employment_table, f)
    with open(catalog_dir / "cops_immigration.json", "w") as f:
        json.dump(immigration_table, f)

    # Run enrichment
    enrich_catalog(catalog_dir)

    # Load results
    with open(catalog_dir / "cops_employment.json", "r") as f:
        emp = json.load(f)
    with open(catalog_dir / "cops_immigration.json", "r") as f:
        imm = json.load(f)

    # Verify different descriptions
    emp_desc = emp["columns"][0]["description"]
    imm_desc = imm["columns"][0]["description"]

    assert emp_desc != imm_desc
    assert "employment count" in emp_desc
    assert "immigrant workers" in imm_desc
