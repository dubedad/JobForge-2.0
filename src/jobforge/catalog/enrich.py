"""Catalog enrichment script for adding semantic column descriptions and workforce dynamics."""

import json
from pathlib import Path
from typing import Any


# COPS column descriptions
COPS_COLUMN_DESCRIPTIONS = {
    "unit_group_id": "Foreign key to dim_noc.unit_group_id - 5-digit NOC 2021 code",
    "code": "NOC code (may include aggregate codes like TEER_0)",
    "occupation_name_en": "English occupation name from COPS source",
    "occupation_name_fr": "French occupation name from COPS source",
}

# Year-specific descriptions per table (metric varies by table)
YEAR_METRICS = {
    "cops_employment": "employment count",
    "cops_employment_growth": "employment growth rate",
    "cops_retirements": "retirement count",
    "cops_retirement_rates": "retirement rate",
    "cops_other_replacement": "other replacement demand count",
    "cops_immigration": "immigrant workers",
    "cops_school_leavers": "school leavers entering workforce",
    "cops_other_seekers": "other job seekers",
}

# Workforce dynamic mapping (demand vs supply)
WORKFORCE_DYNAMIC = {
    "demand": [
        "cops_employment",
        "cops_employment_growth",
        "cops_retirements",
        "cops_retirement_rates",
        "cops_other_replacement",
    ],
    "supply": [
        "cops_immigration",
        "cops_school_leavers",
        "cops_other_seekers",
    ],
}

# Table descriptions
TABLE_DESCRIPTIONS = {
    "cops_employment": "Employment counts by NOC occupation - base employment projection",
    "cops_employment_growth": "Annual employment growth rates by occupation",
    "cops_retirements": "Projected retirement counts by occupation",
    "cops_retirement_rates": "Annual retirement rates by occupation",
    "cops_other_replacement": "Other replacement demand by occupation",
    "cops_immigration": "Immigrant workers entering occupations",
    "cops_school_leavers": "School leavers entering workforce by occupation",
    "cops_other_seekers": "Other job seekers entering workforce by occupation",
}

# dim_noc column descriptions
DIM_NOC_COLUMN_DESCRIPTIONS = {
    "unit_group_id": "Primary key - 5-digit NOC 2021 code, zero-padded (e.g., 00010, 21232)",
    "noc_code": "NOC code without zero-padding",
    "class_title": "Official NOC occupation title",
    "class_definition": "Full text description of the occupation",
    "hierarchical_structure": "Level in NOC hierarchy",
}


def _get_workforce_dynamic(table_name: str) -> str | None:
    """Get workforce dynamic classification for a table."""
    for dynamic, tables in WORKFORCE_DYNAMIC.items():
        if table_name in tables:
            return dynamic
    return None


def _get_year_description(table_name: str, year: str) -> str:
    """Generate year column description based on table type."""
    metric = YEAR_METRICS.get(table_name, "value")
    return f"Projected {metric} for {year}"


def _enrich_table(table_data: dict[str, Any], table_name: str) -> int:
    """
    Enrich a single table's metadata.

    Returns the number of columns enriched.
    """
    columns_enriched = 0

    # Add table description if available
    if table_name in TABLE_DESCRIPTIONS:
        table_data["description"] = TABLE_DESCRIPTIONS[table_name]

    # Add workforce_dynamic field for COPS tables
    workforce_dynamic = _get_workforce_dynamic(table_name)
    if workforce_dynamic:
        table_data["workforce_dynamic"] = workforce_dynamic

    # Enrich column descriptions
    for column in table_data.get("columns", []):
        column_name = column["name"]
        original_description = column.get("description", "")

        # Determine appropriate description
        new_description = None

        # Check if it's a year column
        if column_name.isdigit() and len(column_name) == 4:
            new_description = _get_year_description(table_name, column_name)
        # Check dim_noc column descriptions first (more specific)
        elif table_name == "dim_noc" and column_name in DIM_NOC_COLUMN_DESCRIPTIONS:
            new_description = DIM_NOC_COLUMN_DESCRIPTIONS[column_name]
        # Check COPS column descriptions
        elif column_name in COPS_COLUMN_DESCRIPTIONS:
            new_description = COPS_COLUMN_DESCRIPTIONS[column_name]

        # Update if we found a better description
        if new_description and new_description != original_description:
            column["description"] = new_description
            columns_enriched += 1

    return columns_enriched


def enrich_catalog(catalog_path: Path | None = None) -> dict[str, int]:
    """
    Enrich catalog JSON files with semantic descriptions and workforce dynamics.

    Args:
        catalog_path: Path to catalog tables directory. Defaults to data/catalog/tables.

    Returns:
        Dictionary with counts: {"tables_updated": N, "columns_enriched": M}
    """
    if catalog_path is None:
        catalog_path = Path("data/catalog/tables")
    else:
        catalog_path = Path(catalog_path)

    if not catalog_path.exists():
        raise FileNotFoundError(f"Catalog path does not exist: {catalog_path}")

    tables_updated = 0
    columns_enriched = 0

    # Process all JSON files in the catalog
    for json_file in catalog_path.glob("*.json"):
        table_name = json_file.stem

        # Load existing catalog data
        with open(json_file, "r", encoding="utf-8") as f:
            table_data = json.load(f)

        # Enrich the table
        enriched_count = _enrich_table(table_data, table_name)

        if enriched_count > 0:
            columns_enriched += enriched_count
            tables_updated += 1

            # Write back the enriched data
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(table_data, f, indent=2, ensure_ascii=False)

    return {"tables_updated": tables_updated, "columns_enriched": columns_enriched}


if __name__ == "__main__":
    results = enrich_catalog()
    print(f"Enrichment complete:")
    print(f"  Tables updated: {results['tables_updated']}")
    print(f"  Columns enriched: {results['columns_enriched']}")
