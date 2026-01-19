"""Data governance modules for DAMA DMBOK compliance.

Provides:
- LineageGraph: NetworkX DAG for lineage traversal queries
- LineageQueryEngine: Natural language query interface for lineage
- CatalogueGenerator: Data Catalogue generation from WiQ schema
- Pydantic models: LineageNode, LineageEdge for graph representation
"""

from jobforge.governance.catalogue import CatalogueGenerator, generate_catalogue
from jobforge.governance.graph import LineageGraph
from jobforge.governance.models import LineageEdge, LineageNode
from jobforge.governance.query import LineageQueryEngine

__all__ = [
    "LineageGraph",
    "LineageQueryEngine",
    "LineageNode",
    "LineageEdge",
    "CatalogueGenerator",
    "generate_catalogue",
]
