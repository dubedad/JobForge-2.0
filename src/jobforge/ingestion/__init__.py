"""Data ingestion module for source-specific ingestion logic."""

from jobforge.ingestion.noc import ingest_dim_noc
from jobforge.ingestion.oasis import (
    ingest_oasis_table,
    ingest_all_oasis_tables,
    OASIS_TABLES,
)
from jobforge.ingestion.element import (
    ingest_element_table,
    ingest_all_element_tables,
    ELEMENT_TABLES,
)
from jobforge.ingestion.cops import (
    ingest_cops_table,
    ingest_all_cops_tables,
    COPS_SUPPLY_TABLES,
    COPS_DEMAND_TABLES,
    COPS_SUMMARY_TABLES,
    COPS_TABLES,
)
from jobforge.ingestion.job_architecture import (
    ingest_job_architecture,
    extract_dim_occupations,
    ingest_job_architecture_with_dim_occupations,
)
from jobforge.ingestion.transforms import (
    derive_noc_element_code,
    derive_unit_group_from_oasis,
    derive_unit_group_id,
    filter_unit_groups,
    normalize_noc_code,
)

__all__ = [
    # NOC ingestion
    "ingest_dim_noc",
    # OASIS ingestion
    "ingest_oasis_table",
    "ingest_all_oasis_tables",
    "OASIS_TABLES",
    # Element ingestion
    "ingest_element_table",
    "ingest_all_element_tables",
    "ELEMENT_TABLES",
    # COPS ingestion
    "ingest_cops_table",
    "ingest_all_cops_tables",
    "COPS_SUPPLY_TABLES",
    "COPS_DEMAND_TABLES",
    "COPS_SUMMARY_TABLES",
    "COPS_TABLES",
    # Job Architecture ingestion
    "ingest_job_architecture",
    "extract_dim_occupations",
    "ingest_job_architecture_with_dim_occupations",
    # Transform functions
    "filter_unit_groups",
    "derive_unit_group_id",
    "normalize_noc_code",
    "derive_noc_element_code",
    "derive_unit_group_from_oasis",
]
