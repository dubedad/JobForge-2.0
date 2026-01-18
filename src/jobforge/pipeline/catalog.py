"""Metadata catalog management per DAMA DMBOK Chapter 5."""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import polars as pl

from jobforge.pipeline.config import PipelineConfig
from jobforge.pipeline.models import (
    ColumnMetadata,
    LayerTransitionLog,
    TableMetadata,
)


def generate_table_metadata(
    parquet_path: Path,
    layer: str,
    domain: str,
    description: str = "",
    business_purpose: str = "",
    upstream_tables: Optional[list[str]] = None,
) -> TableMetadata:
    """Generate TableMetadata from a parquet file.

    Reads the parquet file schema and statistics to populate metadata.

    Args:
        parquet_path: Path to the parquet file.
        layer: Medallion layer (staged, bronze, silver, gold).
        domain: Data domain (e.g., 'noc', 'job_architecture').
        description: Business description of the table.
        business_purpose: Business use case for this table.
        upstream_tables: List of upstream table names.

    Returns:
        Populated TableMetadata model.
    """
    parquet_path = Path(parquet_path)

    # Use scan_parquet for lazy schema inspection
    lazy_frame = pl.scan_parquet(parquet_path)
    schema = lazy_frame.collect_schema()

    # Get row count by collecting just the count
    row_count = lazy_frame.select(pl.len()).collect().item()

    # Get file size
    file_size_bytes = os.path.getsize(parquet_path)

    # Build column metadata
    columns = []
    for col_name, col_dtype in schema.items():
        columns.append(
            ColumnMetadata(
                name=col_name,
                data_type=str(col_dtype),
                nullable=True,  # Parquet doesn't expose nullability easily
                description="",  # Can be enriched later
            )
        )

    # Derive table name from file path
    table_name = parquet_path.stem

    now = datetime.now(timezone.utc)

    return TableMetadata(
        table_name=table_name,
        layer=layer,
        domain=domain,
        file_path=str(parquet_path),
        row_count=row_count,
        column_count=len(columns),
        file_size_bytes=file_size_bytes,
        schema_version="1.0.0",
        created_at=now,
        updated_at=now,
        description=description or f"Table {table_name} in {layer} layer",
        business_purpose=business_purpose or f"Data from {domain} domain",
        data_owner="system",
        upstream_tables=upstream_tables or [],
        columns=columns,
    )


class CatalogManager:
    """Manages the metadata catalog for tables and lineage.

    Provides methods to save, load, and query table metadata
    and lineage logs per DAMA DMBOK Chapter 5.
    """

    def __init__(self, config: PipelineConfig) -> None:
        """Initialize the catalog manager.

        Args:
            config: Pipeline configuration for paths.
        """
        self.config = config

    def save_table_metadata(self, metadata: TableMetadata) -> Path:
        """Save table metadata to catalog.

        Args:
            metadata: TableMetadata to save.

        Returns:
            Path to the saved metadata file.
        """
        tables_dir = self.config.catalog_tables_path()
        tables_dir.mkdir(parents=True, exist_ok=True)

        metadata_path = tables_dir / f"{metadata.table_name}.json"
        metadata_path.write_text(metadata.model_dump_json(indent=2))

        return metadata_path

    def load_table_metadata(self, table_name: str) -> TableMetadata:
        """Load table metadata from catalog.

        Args:
            table_name: Name of the table to load.

        Returns:
            TableMetadata model.

        Raises:
            FileNotFoundError: If table metadata doesn't exist.
        """
        metadata_path = self.config.catalog_tables_path() / f"{table_name}.json"

        if not metadata_path.exists():
            raise FileNotFoundError(f"Table metadata not found: {table_name}")

        return TableMetadata.model_validate_json(metadata_path.read_text())

    def list_tables(self, layer: Optional[str] = None) -> list[str]:
        """List all tables in the catalog.

        Args:
            layer: Optional filter by medallion layer.

        Returns:
            List of table names.
        """
        tables_dir = self.config.catalog_tables_path()

        if not tables_dir.exists():
            return []

        table_names = []
        for json_file in tables_dir.glob("*.json"):
            if layer is not None:
                # Load and check layer
                metadata = TableMetadata.model_validate_json(json_file.read_text())
                if metadata.layer == layer:
                    table_names.append(json_file.stem)
            else:
                table_names.append(json_file.stem)

        return sorted(table_names)

    def get_lineage_logs(
        self, batch_id: Optional[str] = None
    ) -> list[LayerTransitionLog]:
        """Get lineage logs from catalog.

        Args:
            batch_id: Optional filter by batch ID.

        Returns:
            List of LayerTransitionLog models.
        """
        lineage_dir = self.config.catalog_lineage_path()

        if not lineage_dir.exists():
            return []

        logs = []
        for json_file in lineage_dir.glob("*.json"):
            log = LayerTransitionLog.model_validate_json(json_file.read_text())
            if batch_id is None or log.batch_id == batch_id:
                logs.append(log)

        # Sort by started_at
        return sorted(logs, key=lambda x: x.started_at)


def update_catalog_on_transition(
    catalog: CatalogManager,
    transition_log: LayerTransitionLog,
    target_path: Path,
    domain: str,
) -> TableMetadata:
    """Update catalog after a layer transition.

    Called after each layer transition to generate and save
    metadata for the newly created file.

    Args:
        catalog: CatalogManager instance.
        transition_log: The transition log for this operation.
        target_path: Path to the new parquet file.
        domain: Data domain for the table.

    Returns:
        The generated and saved TableMetadata.
    """
    # Generate metadata from the new file
    metadata = generate_table_metadata(
        parquet_path=target_path,
        layer=transition_log.target_layer,
        domain=domain,
        upstream_tables=transition_log.source_files,
    )

    # Save to catalog
    catalog.save_table_metadata(metadata)

    return metadata
