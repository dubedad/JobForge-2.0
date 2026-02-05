"""Catalog enrichment script for adding semantic column descriptions and workforce dynamics.

Extended with DMBOK tagging (table-level knowledge areas, field-level element types) and
governance metadata (data_steward, refresh_frequency, security_classification, etc.).
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jobforge.catalog.dmbok_tagging import (
    add_dmbok_field_tags,
    add_dmbok_table_tags,
)


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


def _enrich_table(table_data: dict[str, Any], table_name: str) -> tuple[int, bool]:
    """
    Enrich a single table's metadata.

    Returns tuple of (columns_enriched, table_modified).
    """
    columns_enriched = 0
    table_modified = False

    # Add table description if available
    if table_name in TABLE_DESCRIPTIONS:
        if table_data.get("description") != TABLE_DESCRIPTIONS[table_name]:
            table_data["description"] = TABLE_DESCRIPTIONS[table_name]
            table_modified = True

    # Add workforce_dynamic field for COPS tables
    workforce_dynamic = _get_workforce_dynamic(table_name)
    if workforce_dynamic:
        if table_data.get("workforce_dynamic") != workforce_dynamic:
            table_data["workforce_dynamic"] = workforce_dynamic
            table_modified = True

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
            table_modified = True

    return columns_enriched, table_modified


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
        enriched_count, table_modified = _enrich_table(table_data, table_name)

        if table_modified:
            tables_updated += 1
            columns_enriched += enriched_count

            # Write back the enriched data
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(table_data, f, indent=2, ensure_ascii=False)

    return {"tables_updated": tables_updated, "columns_enriched": columns_enriched}


# Phase 16 tables for DMBOK enrichment
PHASE_16_TABLES = [
    "dim_og_qualification_standard",
    "dim_og_job_evaluation_standard",
    "fact_og_pay_rates",
    "fact_og_allowances",
    "dim_collective_agreement",
    "fact_caf_training",
    "dim_caf_training_location",
]


def add_governance_metadata(table_metadata: dict[str, Any], table_name: str) -> dict[str, Any]:
    """
    Add governance metadata to table catalog entry.

    Per CONTEXT.md Governance Granularity requirements:
    - data_steward and data_owner based on domain
    - refresh_frequency, retention_period, security_classification
    - intended_consumers for downstream systems

    Args:
        table_metadata: The table catalog metadata dictionary
        table_name: Name of the table

    Returns:
        Updated table_metadata dict with governance object
    """
    # Determine data steward and owner by domain
    domain = table_metadata.get("domain", "")

    if domain == "occupational_groups" or table_name.startswith(("dim_og", "fact_og")):
        data_steward = "OG Data Team"
        data_owner = "Treasury Board Secretariat"
    elif domain in ("caf", "caf_careers") or table_name.startswith(("dim_caf", "fact_caf")):
        data_steward = "CAF Data Team"
        data_owner = "Department of National Defence"
    elif domain == "noc" or table_name.startswith("dim_noc"):
        data_steward = "NOC Data Team"
        data_owner = "Statistics Canada"
    elif "cops" in table_name:
        data_steward = "COPS Data Team"
        data_owner = "Employment and Social Development Canada"
    elif "oasis" in table_name:
        data_steward = "Skills Data Team"
        data_owner = "JobForge"
    else:
        data_steward = "Data Governance Team"
        data_owner = "JobForge"

    table_metadata["governance"] = {
        "data_steward": data_steward,
        "data_owner": data_owner,
        "refresh_frequency": "as_published",  # TBS/CAF update irregularly
        "retention_period": "indefinite",  # Historical data preserved
        "security_classification": "Unclassified",  # All public data
        "intended_consumers": ["JD Builder", "WiQ", "Public API"],
    }

    return table_metadata


def add_quality_metrics(
    table_metadata: dict[str, Any], gold_path: Path | None = None
) -> dict[str, Any]:
    """
    Add data quality metrics to table catalog entry.

    Computes completeness percentage and row count from parquet file if available.

    Args:
        table_metadata: The table catalog metadata dictionary
        gold_path: Optional path to the gold parquet file

    Returns:
        Updated table_metadata dict with quality_metrics object
    """
    completeness_pct = None
    row_count = table_metadata.get("row_count")  # Use existing if present

    if gold_path and gold_path.exists():
        try:
            import polars as pl

            df = pl.read_parquet(gold_path)
            row_count = len(df)

            # Compute completeness as % of non-null values
            if len(df) > 0 and len(df.columns) > 0:
                total_cells = len(df) * len(df.columns)
                non_null_cells = sum(len(df) - df[col].null_count() for col in df.columns)
                completeness_pct = (
                    round(non_null_cells / total_cells * 100, 1) if total_cells > 0 else None
                )
        except Exception:
            pass  # If parquet read fails, continue with None values

    table_metadata["quality_metrics"] = {
        "completeness_pct": completeness_pct,
        "freshness_date": datetime.now(timezone.utc).isoformat(),
        "row_count": row_count,
    }

    return table_metadata


def _enrich_table_with_dmbok(
    table_metadata: dict[str, Any], table_name: str, gold_path: Path | None = None
) -> dict[str, Any]:
    """
    Enrich a table with DMBOK tags and governance metadata.

    Args:
        table_metadata: The table catalog metadata dictionary
        table_name: Name of the table
        gold_path: Optional path to the gold parquet file

    Returns:
        Updated table_metadata with DMBOK and governance fields
    """
    # Add DMBOK table-level tag
    table_metadata = add_dmbok_table_tags(table_metadata, table_name)

    # Add DMBOK field-level tags to columns
    if "columns" in table_metadata:
        table_metadata["columns"] = add_dmbok_field_tags(table_metadata["columns"])

    # Add governance metadata
    table_metadata = add_governance_metadata(table_metadata, table_name)

    # Add quality metrics
    table_metadata = add_quality_metrics(table_metadata, gold_path)

    return table_metadata


def enrich_phase_16_tables(catalog_path: Path | None = None, gold_dir: Path | None = None) -> dict:
    """
    Enrich Phase 16 tables with DMBOK and governance metadata.

    For each Phase 16 table:
    1. Load existing catalog JSON
    2. Add DMBOK table tags (knowledge area)
    3. Add DMBOK field tags to all columns (element types)
    4. Add governance metadata
    5. Add quality metrics
    6. Write updated catalog JSON

    Args:
        catalog_path: Path to catalog tables directory. Defaults to data/catalog/tables.
        gold_dir: Path to gold parquet directory. Defaults to data/gold.

    Returns:
        Dictionary with counts: {"tables_updated": N, "columns_tagged": M, "tables_missing": L}
    """
    if catalog_path is None:
        catalog_path = Path("data/catalog/tables")
    else:
        catalog_path = Path(catalog_path)

    if gold_dir is None:
        gold_dir = Path("data/gold")
    else:
        gold_dir = Path(gold_dir)

    tables_updated = 0
    columns_tagged = 0
    tables_missing = 0

    for table_name in PHASE_16_TABLES:
        json_path = catalog_path / f"{table_name}.json"

        if not json_path.exists():
            tables_missing += 1
            continue

        # Load existing catalog data
        with open(json_path, encoding="utf-8") as f:
            table_data = json.load(f)

        # Determine gold parquet path
        gold_path = gold_dir / f"{table_name}.parquet"

        # Count columns before enrichment
        columns = table_data.get("columns", [])
        if isinstance(columns, list):
            col_count = len(columns)
        elif isinstance(columns, dict):
            col_count = len(columns)
        else:
            col_count = 0

        # Enrich with DMBOK and governance
        table_data = _enrich_table_with_dmbok(table_data, table_name, gold_path)

        # Write back the enriched data
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(table_data, f, indent=2, ensure_ascii=False)

        tables_updated += 1
        columns_tagged += col_count

    return {
        "tables_updated": tables_updated,
        "columns_tagged": columns_tagged,
        "tables_missing": tables_missing,
    }


if __name__ == "__main__":
    results = enrich_catalog()
    print("Enrichment complete:")
    print(f"  Tables updated: {results['tables_updated']}")
    print(f"  Columns enriched: {results['columns_enriched']}")
