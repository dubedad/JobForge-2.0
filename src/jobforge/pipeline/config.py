"""Pipeline configuration and paths for medallion architecture."""

from enum import Enum
from pathlib import Path


class Layer(str, Enum):
    """Medallion architecture layers."""

    STAGED = "staged"
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"


class PipelineConfig:
    """Configuration for the data pipeline with path accessors."""

    def __init__(self, data_root: Path | str = Path("data")) -> None:
        """Initialize pipeline configuration.

        Args:
            data_root: Root directory for data storage. Defaults to 'data'.
        """
        self.data_root = Path(data_root)

    def staged_path(self) -> Path:
        """Get path to staged layer directory."""
        return self.data_root / "staged"

    def bronze_path(self) -> Path:
        """Get path to bronze layer directory."""
        return self.data_root / "bronze"

    def silver_path(self) -> Path:
        """Get path to silver layer directory."""
        return self.data_root / "silver"

    def gold_path(self) -> Path:
        """Get path to gold layer directory."""
        return self.data_root / "gold"

    def quarantine_path(self) -> Path:
        """Get path to quarantine directory."""
        return self.data_root / "quarantine"

    def catalog_path(self) -> Path:
        """Get path to catalog directory."""
        return self.data_root / "catalog"

    def catalog_tables_path(self) -> Path:
        """Get path to catalog tables directory."""
        return self.catalog_path() / "tables"

    def catalog_lineage_path(self) -> Path:
        """Get path to catalog lineage directory."""
        return self.catalog_path() / "lineage"

    def catalog_glossary_path(self) -> Path:
        """Get path to catalog glossary directory."""
        return self.catalog_path() / "glossary"

    def catalog_schemas_path(self) -> Path:
        """Get path to catalog schemas directory."""
        return self.catalog_path() / "schemas"

    def layer_path(self, layer: Layer) -> Path:
        """Get path for a specific layer.

        Args:
            layer: The medallion layer.

        Returns:
            Path to the layer directory.
        """
        return self.data_root / layer.value
