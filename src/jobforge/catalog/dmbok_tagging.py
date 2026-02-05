"""DMBOK tagging module for catalog metadata enrichment.

Provides DMBOK knowledge area tagging at table level and DMBOK data element
type tagging at field level per DMBOK 2.0 framework.

Reference: DAMA DMBOK 2.0 Knowledge Areas
- DMBOK-3: Data Modeling and Design
- DMBOK-4: Data Storage and Operations
- DMBOK-7: Metadata Management
- DMBOK-9: Reference and Master Data
"""

from typing import Any


# DMBOK Knowledge Areas by table name
# Tables are categorized by their primary DMBOK knowledge area
DMBOK_KNOWLEDGE_AREAS: dict[str, str] = {
    # Phase 16 tables - Occupational Groups domain
    "dim_og_qualification_standard": "Metadata Management",  # DMBOK-7
    "dim_og_job_evaluation_standard": "Metadata Management",  # DMBOK-7
    "fact_og_pay_rates": "Reference and Master Data",  # DMBOK-9
    "fact_og_allowances": "Reference and Master Data",  # DMBOK-9
    "dim_collective_agreement": "Reference and Master Data",  # DMBOK-9
    # Phase 16 tables - CAF domain
    "fact_caf_training": "Metadata Management",  # DMBOK-7
    "dim_caf_training_location": "Reference and Master Data",  # DMBOK-9
    # Existing OG dimension tables
    "dim_og": "Reference and Master Data",  # DMBOK-9
    "dim_og_subgroup": "Reference and Master Data",  # DMBOK-9
    "dim_og_qualifications": "Metadata Management",  # DMBOK-7 (deprecated)
    # Existing NOC tables
    "dim_noc": "Reference and Master Data",  # DMBOK-9
    "dim_occupations": "Reference and Master Data",  # DMBOK-9
    # Existing CAF tables
    "dim_caf_occupation": "Reference and Master Data",  # DMBOK-9
    "dim_caf_job_family": "Reference and Master Data",  # DMBOK-9
    "bridge_caf_noc": "Reference and Master Data",  # DMBOK-9
    "bridge_caf_ja": "Reference and Master Data",  # DMBOK-9
    # Bridge tables
    "bridge_noc_og": "Reference and Master Data",  # DMBOK-9
    # COPS labor market projection tables
    "cops_employment": "Data Storage and Operations",  # DMBOK-4
    "cops_employment_growth": "Data Storage and Operations",  # DMBOK-4
    "cops_retirements": "Data Storage and Operations",  # DMBOK-4
    "cops_retirement_rates": "Data Storage and Operations",  # DMBOK-4
    "cops_other_replacement": "Data Storage and Operations",  # DMBOK-4
    "cops_immigration": "Data Storage and Operations",  # DMBOK-4
    "cops_school_leavers": "Data Storage and Operations",  # DMBOK-4
    "cops_other_seekers": "Data Storage and Operations",  # DMBOK-4
    # OASIS skills/abilities tables
    "oasis_skills": "Reference and Master Data",  # DMBOK-9
    "oasis_abilities": "Reference and Master Data",  # DMBOK-9
    "oasis_knowledges": "Reference and Master Data",  # DMBOK-9
    "oasis_workactivities": "Reference and Master Data",  # DMBOK-9
    "oasis_workcontext": "Reference and Master Data",  # DMBOK-9
    # Element tables (NOC occupation content)
    "element_additional_information": "Metadata Management",  # DMBOK-7
    "element_employment_requirements": "Metadata Management",  # DMBOK-7
    "element_example_titles": "Metadata Management",  # DMBOK-7
    "element_exclusions": "Metadata Management",  # DMBOK-7
    "element_labels": "Metadata Management",  # DMBOK-7
    "element_lead_statement": "Metadata Management",  # DMBOK-7
    "element_main_duties": "Metadata Management",  # DMBOK-7
    "element_workplaces_employers": "Metadata Management",  # DMBOK-7
    # Job architecture
    "job_architecture": "Data Modeling and Design",  # DMBOK-3
}


# DMBOK Data Element Types by column name
# Maps column names to their DMBOK data element classification
DMBOK_DATA_ELEMENT_TYPES: dict[str, str] = {
    # Reference codes (DMBOK-9) - Primary/foreign keys and classification codes
    "og_code": "reference_code",
    "og_subgroup_code": "reference_code",
    "classification_level": "reference_code",
    "caf_occupation_id": "reference_code",
    "training_location_id": "reference_code",
    "agreement_id": "reference_code",
    "allowance_id": "reference_code",
    "unit_group_id": "reference_code",
    "noc_code": "reference_code",
    "career_id": "reference_code",
    "job_family_id": "reference_code",
    # Descriptive metadata (DMBOK-7) - Human-readable text fields
    "full_text": "descriptive_text",
    "education_requirement_text": "descriptive_text",
    "experience_requirement_text": "descriptive_text",
    "factor_description": "descriptive_text",
    "level_description": "descriptive_text",
    "eligibility_criteria": "descriptive_text",
    "essential_qualification_text": "descriptive_text",
    "asset_qualification_text": "descriptive_text",
    "equivalency_statement": "descriptive_text",
    "certification_requirement": "descriptive_text",
    "class_definition": "descriptive_text",
    "class_title": "descriptive_text",
    "description": "descriptive_text",
    "location_name": "descriptive_text",
    "agreement_name": "descriptive_text",
    "allowance_name": "descriptive_text",
    "standard_name": "descriptive_text",
    "duration_text": "descriptive_text",
    "training_location_text": "descriptive_text",
    "civilian_equivalency_text": "descriptive_text",
    # Numeric attributes (DMBOK-3) - Quantitative values
    "min_years_experience": "numeric_attribute",
    "factor_points": "numeric_attribute",
    "level_points": "numeric_attribute",
    "factor_percentage": "numeric_attribute",
    "annual_rate": "numeric_attribute",
    "hourly_rate": "numeric_attribute",
    "duration_weeks": "numeric_attribute",
    "amount": "numeric_attribute",
    "percentage": "numeric_attribute",
    "step": "numeric_attribute",
    "row_count": "numeric_attribute",
    "column_count": "numeric_attribute",
    # Categorical attributes (DMBOK-3) - Constrained value sets
    "education_level": "categorical_attribute",
    "security_clearance": "categorical_attribute",
    "bilingual_reading_level": "categorical_attribute",
    "bilingual_writing_level": "categorical_attribute",
    "bilingual_oral_level": "categorical_attribute",
    "training_type": "categorical_attribute",
    "allowance_type": "categorical_attribute",
    "standard_type": "categorical_attribute",
    "rate_type": "categorical_attribute",
    "pay_progression_type": "categorical_attribute",
    "civilian_credential_level": "categorical_attribute",
    "factor_level": "categorical_attribute",
    "base_type": "categorical_attribute",
    "province": "categorical_attribute",
    "country": "categorical_attribute",
    "minimum_rank": "categorical_attribute",
    "layer": "categorical_attribute",
    "domain": "categorical_attribute",
    # Boolean flags - Binary decision fields
    "has_equivalency": "boolean_flag",
    "requires_travel": "boolean_flag",
    "is_represented": "boolean_flag",
    "recertification_required": "boolean_flag",
    "shift_work": "boolean_flag",
    "physical_demands": "boolean_flag",
    "overtime_required": "boolean_flag",
    "on_call_required": "boolean_flag",
    "deployments_required": "boolean_flag",
    "nullable": "boolean_flag",
    "primary_key": "boolean_flag",
    # Temporal data (DMBOK-4) - Date/time fields
    "effective_date": "temporal_effective",
    "expiry_date": "temporal_expiry",
    "signing_date": "temporal_effective",
    "extracted_at": "temporal_provenance",
    "_extracted_at": "temporal_provenance",
    "_ingested_at": "temporal_provenance",
    "_scraped_at": "temporal_provenance",
    "freshness_date": "temporal_provenance",
    # Provenance identifiers (DMBOK-9) - Audit trail fields
    "source_url": "provenance_identifier",
    "_source_url": "provenance_identifier",
    "_batch_id": "provenance_identifier",
    "_source_file": "provenance_identifier",
    "_source": "provenance_identifier",
    "_layer": "provenance_marker",
    # Structured data - JSON arrays/objects
    "certifications_awarded": "structured_array",
    "qualifications_awarded": "structured_array",
    "prerequisite_courses": "structured_array",
    "og_subgroup_codes": "structured_array",
    "recertification_frequency": "structured_array",
    "example_values": "structured_array",
    # Relational metadata
    "foreign_key": "relationship_reference",
    "bargaining_agent": "descriptive_text",
    "employer": "descriptive_text",
    "collective_agreement": "descriptive_text",
    "collective_agreement_id": "reference_code",
    "version": "version_identifier",
}


def add_dmbok_table_tags(table_metadata: dict[str, Any], table_name: str) -> dict[str, Any]:
    """
    Add DMBOK knowledge area tag to table metadata.

    Args:
        table_metadata: The table catalog metadata dictionary
        table_name: Name of the table (used for lookup)

    Returns:
        Updated table_metadata dict with dmbok_knowledge_area field
    """
    knowledge_area = DMBOK_KNOWLEDGE_AREAS.get(table_name, "Data Storage and Operations")
    table_metadata["dmbok_knowledge_area"] = knowledge_area
    return table_metadata


def add_dmbok_field_tags(columns: list[dict[str, Any]] | dict[str, Any]) -> list[dict[str, Any]] | dict[str, Any]:
    """
    Add DMBOK data element type to each column in the schema.

    Handles both list-style columns (newer format) and dict-style columns (older format).

    Args:
        columns: Either a list of column dicts or a dict of column_name -> column_info

    Returns:
        Updated columns with dmbok_element_type field added to each column
    """
    if isinstance(columns, list):
        # List format: [{"name": "col1", "type": "VARCHAR", ...}, ...]
        for column in columns:
            column_name = column.get("name", "")
            element_type = DMBOK_DATA_ELEMENT_TYPES.get(column_name, "data_attribute")
            column["dmbok_element_type"] = element_type
        return columns
    elif isinstance(columns, dict):
        # Dict format: {"col1": {"type": "VARCHAR", ...}, ...}
        for column_name, column_info in columns.items():
            if isinstance(column_info, dict):
                element_type = DMBOK_DATA_ELEMENT_TYPES.get(column_name, "data_attribute")
                column_info["dmbok_element_type"] = element_type
        return columns
    else:
        return columns


def get_dmbok_knowledge_area(table_name: str) -> str:
    """
    Get the DMBOK knowledge area for a given table.

    Args:
        table_name: Name of the table

    Returns:
        DMBOK knowledge area string, defaults to "Data Storage and Operations"
    """
    return DMBOK_KNOWLEDGE_AREAS.get(table_name, "Data Storage and Operations")


def get_dmbok_element_type(column_name: str) -> str:
    """
    Get the DMBOK data element type for a given column.

    Args:
        column_name: Name of the column

    Returns:
        DMBOK data element type string, defaults to "data_attribute"
    """
    return DMBOK_DATA_ELEMENT_TYPES.get(column_name, "data_attribute")


def validate_phase_16_coverage() -> dict[str, bool]:
    """
    Validate that all Phase 16 tables have DMBOK knowledge area mappings.

    Returns:
        Dict of table_name -> has_mapping boolean
    """
    phase_16_tables = [
        "dim_og_qualification_standard",
        "dim_og_job_evaluation_standard",
        "fact_og_pay_rates",
        "fact_og_allowances",
        "dim_collective_agreement",
        "fact_caf_training",
        "dim_caf_training_location",
    ]
    return {table: table in DMBOK_KNOWLEDGE_AREAS for table in phase_16_tables}
