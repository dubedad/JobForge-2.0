"""Pipeline module for medallion architecture data processing."""

from jobforge.pipeline.catalog import (
    CatalogManager,
    generate_table_metadata,
    update_catalog_on_transition,
)
from jobforge.pipeline.config import Layer, PipelineConfig
from jobforge.pipeline.engine import PipelineEngine
from jobforge.pipeline.layers import BronzeLayer, GoldLayer, SilverLayer, StagedLayer
from jobforge.pipeline.models import (
    ColumnMetadata,
    LayerTransitionLog,
    ProvenanceColumns,
    TableMetadata,
)
from jobforge.pipeline.provenance import (
    add_provenance_columns,
    generate_batch_id,
    update_layer_column,
)
from jobforge.pipeline.query import GoldQueryEngine

__all__ = [
    # Config
    "Layer",
    "PipelineConfig",
    # Engine
    "PipelineEngine",
    # Layer classes
    "StagedLayer",
    "BronzeLayer",
    "SilverLayer",
    "GoldLayer",
    # Catalog
    "CatalogManager",
    "generate_table_metadata",
    "update_catalog_on_transition",
    # Query
    "GoldQueryEngine",
    # Models
    "ProvenanceColumns",
    "LayerTransitionLog",
    "ColumnMetadata",
    "TableMetadata",
    # Provenance helpers
    "add_provenance_columns",
    "generate_batch_id",
    "update_layer_column",
]
