"""Data governance modules for DAMA DMBOK compliance.

Provides:
- LineageGraph: NetworkX DAG for lineage traversal queries
- CatalogueGenerator: Data Catalogue generation from WiQ schema
- Pydantic models: LineageNode, LineageEdge for graph representation
"""

from jobforge.governance.catalogue import CatalogueGenerator, generate_catalogue
from jobforge.governance.graph import LineageGraph
from jobforge.governance.models import LineageEdge, LineageNode

__all__ = [
    "LineageGraph",
    "LineageNode",
    "LineageEdge",
    "CatalogueGenerator",
    "generate_catalogue",
]
