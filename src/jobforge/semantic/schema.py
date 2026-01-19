"""WiQ semantic schema definition with dimensional relationships.

This module defines the complete WiQ star schema with all table relationships
for Power BI deployment. DIM NOC serves as the hub connecting to all attribute
and fact tables.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from jobforge.pipeline.config import PipelineConfig
from jobforge.semantic.introspect import introspect_all_gold_tables
from jobforge.semantic.models import (
    Cardinality,
    CrossFilterDirection,
    Relationship,
    SemanticSchema,
)


# WiQ relationships: DIM NOC as hub connecting to attribute and fact tables
# All relationships are 1:* (one-to-many) with single cross-filter direction
WIQ_RELATIONSHIPS: list[Relationship] = [
    # DIM NOC -> OASIS attribute tables (skills, abilities, knowledge, etc.)
    Relationship(
        from_table="dim_noc",
        from_column="unit_group_id",
        to_table="oasis_abilities",
        to_column="unit_group_id",
        cardinality=Cardinality.ONE_TO_MANY,
        cross_filter_direction=CrossFilterDirection.SINGLE,
        is_active=True,
    ),
    Relationship(
        from_table="dim_noc",
        from_column="unit_group_id",
        to_table="oasis_knowledges",
        to_column="unit_group_id",
        cardinality=Cardinality.ONE_TO_MANY,
        cross_filter_direction=CrossFilterDirection.SINGLE,
        is_active=True,
    ),
    Relationship(
        from_table="dim_noc",
        from_column="unit_group_id",
        to_table="oasis_skills",
        to_column="unit_group_id",
        cardinality=Cardinality.ONE_TO_MANY,
        cross_filter_direction=CrossFilterDirection.SINGLE,
        is_active=True,
    ),
    Relationship(
        from_table="dim_noc",
        from_column="unit_group_id",
        to_table="oasis_workactivities",
        to_column="unit_group_id",
        cardinality=Cardinality.ONE_TO_MANY,
        cross_filter_direction=CrossFilterDirection.SINGLE,
        is_active=True,
    ),
    Relationship(
        from_table="dim_noc",
        from_column="unit_group_id",
        to_table="oasis_workcontext",
        to_column="unit_group_id",
        cardinality=Cardinality.ONE_TO_MANY,
        cross_filter_direction=CrossFilterDirection.SINGLE,
        is_active=True,
    ),
    # DIM NOC -> Element attribute tables
    Relationship(
        from_table="dim_noc",
        from_column="unit_group_id",
        to_table="element_additional_information",
        to_column="unit_group_id",
        cardinality=Cardinality.ONE_TO_MANY,
        cross_filter_direction=CrossFilterDirection.SINGLE,
        is_active=True,
    ),
    Relationship(
        from_table="dim_noc",
        from_column="unit_group_id",
        to_table="element_employment_requirements",
        to_column="unit_group_id",
        cardinality=Cardinality.ONE_TO_MANY,
        cross_filter_direction=CrossFilterDirection.SINGLE,
        is_active=True,
    ),
    Relationship(
        from_table="dim_noc",
        from_column="unit_group_id",
        to_table="element_example_titles",
        to_column="unit_group_id",
        cardinality=Cardinality.ONE_TO_MANY,
        cross_filter_direction=CrossFilterDirection.SINGLE,
        is_active=True,
    ),
    Relationship(
        from_table="dim_noc",
        from_column="unit_group_id",
        to_table="element_exclusions",
        to_column="unit_group_id",
        cardinality=Cardinality.ONE_TO_MANY,
        cross_filter_direction=CrossFilterDirection.SINGLE,
        is_active=True,
    ),
    Relationship(
        from_table="dim_noc",
        from_column="unit_group_id",
        to_table="element_labels",
        to_column="unit_group_id",
        cardinality=Cardinality.ONE_TO_MANY,
        cross_filter_direction=CrossFilterDirection.SINGLE,
        is_active=True,
    ),
    Relationship(
        from_table="dim_noc",
        from_column="unit_group_id",
        to_table="element_lead_statement",
        to_column="unit_group_id",
        cardinality=Cardinality.ONE_TO_MANY,
        cross_filter_direction=CrossFilterDirection.SINGLE,
        is_active=True,
    ),
    Relationship(
        from_table="dim_noc",
        from_column="unit_group_id",
        to_table="element_main_duties",
        to_column="unit_group_id",
        cardinality=Cardinality.ONE_TO_MANY,
        cross_filter_direction=CrossFilterDirection.SINGLE,
        is_active=True,
    ),
    Relationship(
        from_table="dim_noc",
        from_column="unit_group_id",
        to_table="element_workplaces_employers",
        to_column="unit_group_id",
        cardinality=Cardinality.ONE_TO_MANY,
        cross_filter_direction=CrossFilterDirection.SINGLE,
        is_active=True,
    ),
    # DIM NOC -> COPS fact tables
    Relationship(
        from_table="dim_noc",
        from_column="unit_group_id",
        to_table="cops_employment",
        to_column="unit_group_id",
        cardinality=Cardinality.ONE_TO_MANY,
        cross_filter_direction=CrossFilterDirection.SINGLE,
        is_active=True,
    ),
    Relationship(
        from_table="dim_noc",
        from_column="unit_group_id",
        to_table="cops_employment_growth",
        to_column="unit_group_id",
        cardinality=Cardinality.ONE_TO_MANY,
        cross_filter_direction=CrossFilterDirection.SINGLE,
        is_active=True,
    ),
    Relationship(
        from_table="dim_noc",
        from_column="unit_group_id",
        to_table="cops_immigration",
        to_column="unit_group_id",
        cardinality=Cardinality.ONE_TO_MANY,
        cross_filter_direction=CrossFilterDirection.SINGLE,
        is_active=True,
    ),
    Relationship(
        from_table="dim_noc",
        from_column="unit_group_id",
        to_table="cops_other_replacement",
        to_column="unit_group_id",
        cardinality=Cardinality.ONE_TO_MANY,
        cross_filter_direction=CrossFilterDirection.SINGLE,
        is_active=True,
    ),
    Relationship(
        from_table="dim_noc",
        from_column="unit_group_id",
        to_table="cops_other_seekers",
        to_column="unit_group_id",
        cardinality=Cardinality.ONE_TO_MANY,
        cross_filter_direction=CrossFilterDirection.SINGLE,
        is_active=True,
    ),
    Relationship(
        from_table="dim_noc",
        from_column="unit_group_id",
        to_table="cops_retirement_rates",
        to_column="unit_group_id",
        cardinality=Cardinality.ONE_TO_MANY,
        cross_filter_direction=CrossFilterDirection.SINGLE,
        is_active=True,
    ),
    Relationship(
        from_table="dim_noc",
        from_column="unit_group_id",
        to_table="cops_retirements",
        to_column="unit_group_id",
        cardinality=Cardinality.ONE_TO_MANY,
        cross_filter_direction=CrossFilterDirection.SINGLE,
        is_active=True,
    ),
    Relationship(
        from_table="dim_noc",
        from_column="unit_group_id",
        to_table="cops_school_leavers",
        to_column="unit_group_id",
        cardinality=Cardinality.ONE_TO_MANY,
        cross_filter_direction=CrossFilterDirection.SINGLE,
        is_active=True,
    ),
    # DIM NOC -> Job Architecture (job titles link to NOC via unit_group_id)
    Relationship(
        from_table="dim_noc",
        from_column="unit_group_id",
        to_table="job_architecture",
        to_column="unit_group_id",
        cardinality=Cardinality.ONE_TO_MANY,
        cross_filter_direction=CrossFilterDirection.SINGLE,
        is_active=True,
    ),
]


def build_wiq_schema(config: Optional[PipelineConfig] = None) -> SemanticSchema:
    """Build the complete WiQ semantic schema with all relationships.

    Introspects all gold layer tables and assembles them with the predefined
    WiQ relationships to create a complete semantic model.

    Args:
        config: Pipeline configuration for locating gold files.
                If None, creates a default PipelineConfig().

    Returns:
        SemanticSchema with all tables and relationships.
    """
    # Introspect all gold tables
    tables = introspect_all_gold_tables(config)

    # Mark primary keys on dimension tables
    for table in tables:
        if table.name == "dim_noc":
            table.primary_key = "unit_group_id"
            # Mark the column as primary key
            for col in table.columns:
                if col.name == "unit_group_id":
                    col.is_primary_key = True
                    break
        elif table.name == "dim_occupations":
            table.primary_key = "occupation_group_id"
            # Mark the column as primary key
            for col in table.columns:
                if col.name == "occupation_group_id":
                    col.is_primary_key = True
                    break

    # Mark foreign keys on attribute/fact tables
    for table in tables:
        for col in table.columns:
            if col.name == "unit_group_id" and table.name != "dim_noc":
                col.is_foreign_key = True
                col.references_table = "dim_noc"
                col.references_column = "unit_group_id"
            elif col.name == "occupation_group_id" and table.name != "dim_occupations":
                col.is_foreign_key = True
                col.references_table = "dim_occupations"
                col.references_column = "occupation_group_id"

    # Create schema (not yet validated)
    schema = SemanticSchema(
        name="WiQ",
        tables=tables,
        relationships=WIQ_RELATIONSHIPS,
        validated=False,
        validation_date=None,
    )

    return schema


def export_schema_json(schema: SemanticSchema, output_path: Path) -> Path:
    """Export a semantic schema to JSON file.

    Args:
        schema: The semantic schema to export.
        output_path: Path where JSON file should be written.

    Returns:
        The path written to (same as output_path).
    """
    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write JSON
    output_path.write_text(schema.to_json(), encoding="utf-8")

    return output_path
