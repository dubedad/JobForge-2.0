"""TBS schema extension for DIM Occupations.

This module defines the TBS fields that extend the DIM Occupations table
when TBS occupational group data is merged into the gold layer.

These fields enable gold layer queries joining occupations to TBS metadata
including group definitions, evaluation standards, and qualification standards.
"""

from typing import TypedDict


class TBSFieldSpec(TypedDict):
    """Specification for a TBS field in DIM Occupations."""

    name: str
    type: str
    description: str


# TBS fields to add to DIM_Occupations table
# These columns will be populated when TBS data is merged
DIM_OCCUPATIONS_TBS_FIELDS: list[TBSFieldSpec] = [
    {
        "name": "tbs_group_code",
        "type": "TEXT",
        "description": "TBS occupational group numeric code",
    },
    {
        "name": "tbs_group_abbrev",
        "type": "TEXT",
        "description": "TBS group abbreviation (AI, CR, EC, etc.)",
    },
    {
        "name": "tbs_group_name",
        "type": "TEXT",
        "description": "Full TBS occupational group name",
    },
    {
        "name": "tbs_definition_url",
        "type": "TEXT",
        "description": "URL to TBS group definition page",
    },
    {
        "name": "tbs_definition_content",
        "type": "TEXT",
        "description": "Definition text fetched from TBS definition page",
    },
    {
        "name": "tbs_job_eval_standard_url",
        "type": "TEXT",
        "description": "URL to TBS job evaluation standard page",
    },
    {
        "name": "tbs_job_eval_content",
        "type": "TEXT",
        "description": "Content fetched from job evaluation standard page",
    },
    {
        "name": "tbs_qualification_standard_url",
        "type": "TEXT",
        "description": "URL to TBS qualification standard page",
    },
    {
        "name": "tbs_qualification_content",
        "type": "TEXT",
        "description": "Content fetched from qualification standard page",
    },
    {
        "name": "tbs_scraped_at",
        "type": "TIMESTAMP",
        "description": "UTC timestamp when TBS data was scraped",
    },
]

# Field names only (for quick lookup)
DIM_OCCUPATIONS_TBS_FIELD_NAMES = [f["name"] for f in DIM_OCCUPATIONS_TBS_FIELDS]


def get_tbs_field_types() -> dict[str, str]:
    """Get mapping of TBS field names to their SQL types.

    Returns:
        Dictionary mapping field name to SQL type (TEXT, TIMESTAMP).
    """
    return {f["name"]: f["type"] for f in DIM_OCCUPATIONS_TBS_FIELDS}


def get_tbs_field_descriptions() -> dict[str, str]:
    """Get mapping of TBS field names to their descriptions.

    Returns:
        Dictionary mapping field name to human-readable description.
    """
    return {f["name"]: f["description"] for f in DIM_OCCUPATIONS_TBS_FIELDS}
