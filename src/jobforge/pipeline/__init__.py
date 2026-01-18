"""Pipeline module for medallion architecture data processing."""

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
