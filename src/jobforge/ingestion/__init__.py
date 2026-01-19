"""Data ingestion module for source-specific ingestion logic."""

from jobforge.ingestion.noc import ingest_dim_noc
from jobforge.ingestion.transforms import (
    derive_noc_element_code,
    derive_unit_group_from_oasis,
    derive_unit_group_id,
    filter_unit_groups,
    normalize_noc_code,
)

__all__ = [
    "ingest_dim_noc",
    "filter_unit_groups",
    "derive_unit_group_id",
    "normalize_noc_code",
    "derive_noc_element_code",
    "derive_unit_group_from_oasis",
]
