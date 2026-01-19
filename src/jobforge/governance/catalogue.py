"""Data Catalogue generation from WiQ schema and physical parquet files.

Satisfies GOV-01 by producing comprehensive table and column documentation
with source system, data types, and business descriptions.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import polars as pl
import structlog

from jobforge.pipeline.catalog import CatalogManager
from jobforge.pipeline.config import PipelineConfig
from jobforge.pipeline.models import ColumnMetadata, TableMetadata

logger = structlog.get_logger(__name__)


# Table type to domain mapping
TABLE_TYPE_DOMAINS = {
    "fact": "forecasting",
    "dimension": "reference",
    "dim": "reference",  # alias
    "bridge": "relationship",
}

# Table type to business description mapping
TABLE_TYPE_DESCRIPTIONS = {
    "fact": "Forecasting and projection data",
    "dimension": "Reference dimension data",
    "dim": "Reference dimension data",  # alias
    "bridge": "Relationship mapping data",
}

# Table type to business purpose mapping
TABLE_TYPE_PURPOSES = {
    "fact": "Supports workforce forecasting and labour market analysis",
    "dimension": "Provides reference data for dimensional analysis",
    "dim": "Provides reference data for dimensional analysis",  # alias
    "bridge": "Maps relationships between entities",
}


class CatalogueGenerator:
    """Generates Data Catalogue from WiQ schema and physical files.

    Reads the WiQ schema definition and physical parquet metadata to produce
    comprehensive table catalogues per DAMA DMBOK Chapter 5 requirements.
    """

    SOURCE_SYSTEM = "JobForge WiQ Pipeline"
    SCHEMA_VERSION = "1.0.0"

    def __init__(self, config: PipelineConfig) -> None:
        """Initialize the catalogue generator.

        Args:
            config: Pipeline configuration for paths.
        """
        self.config = config
        self.catalog_manager = CatalogManager(config)

    def generate(self) -> list[TableMetadata]:
        """Generate catalogue for all WiQ tables.

        1. Load WiQ schema from data/catalog/schemas/wiq_schema.json
        2. For each table in schema:
           a. Get physical metadata from parquet file (row count, file size)
           b. Map schema columns to ColumnMetadata
           c. Create TableMetadata with business descriptions
           d. Save to data/catalog/tables/{table_name}.json
        3. Return list of generated TableMetadata

        Returns:
            List of generated TableMetadata objects.
        """
        logger.info("Starting catalogue generation")

        schema = self._load_wiq_schema()
        tables = schema.get("tables", [])

        generated: list[TableMetadata] = []

        for table_def in tables:
            table_name = table_def.get("name", "")
            if not table_name:
                logger.warning("Skipping table with no name", table_def=table_def)
                continue

            # Find corresponding parquet file
            parquet_path = self._find_parquet_file(table_name)

            # Generate metadata
            try:
                metadata = self._generate_table_metadata(table_def, parquet_path)
                # Save to catalog
                self.catalog_manager.save_table_metadata(metadata)
                generated.append(metadata)
                logger.info(
                    "Generated catalogue entry",
                    table=table_name,
                    columns=len(metadata.columns),
                    row_count=metadata.row_count,
                )
            except Exception as e:
                logger.error(
                    "Failed to generate catalogue for table",
                    table=table_name,
                    error=str(e),
                )
                raise

        logger.info("Catalogue generation complete", table_count=len(generated))
        return generated

    def _load_wiq_schema(self) -> dict[str, Any]:
        """Load WiQ schema JSON.

        Returns:
            Parsed WiQ schema dictionary.

        Raises:
            FileNotFoundError: If schema file doesn't exist.
        """
        schema_path = self.config.catalog_schemas_path() / "wiq_schema.json"
        if not schema_path.exists():
            raise FileNotFoundError(f"WiQ schema not found: {schema_path}")
        return json.loads(schema_path.read_text(encoding="utf-8"))

    def _find_parquet_file(self, table_name: str) -> Path | None:
        """Find the parquet file for a table.

        Args:
            table_name: Name of the table.

        Returns:
            Path to parquet file, or None if not found.
        """
        parquet_path = self.config.gold_path() / f"{table_name}.parquet"
        if parquet_path.exists():
            return parquet_path
        logger.warning("Parquet file not found", table=table_name, path=str(parquet_path))
        return None

    def _generate_table_metadata(
        self,
        table_def: dict[str, Any],
        parquet_path: Path | None,
    ) -> TableMetadata:
        """Generate TableMetadata for a single table.

        Args:
            table_def: Table definition from WiQ schema.
            parquet_path: Path to parquet file, or None if missing.

        Returns:
            Populated TableMetadata object.
        """
        table_name = table_def["name"]
        table_type = table_def.get("table_type", "fact")
        schema_columns = table_def.get("columns", [])

        # Physical metadata from parquet
        row_count = 0
        file_size_bytes = 0
        sample_values_by_column: dict[str, list[str]] = {}

        if parquet_path and parquet_path.exists():
            try:
                lazy_frame = pl.scan_parquet(parquet_path)
                row_count = lazy_frame.select(pl.len()).collect().item()
                file_size_bytes = os.path.getsize(parquet_path)

                # Get sample values (first 3 rows)
                sample_df = lazy_frame.head(3).collect()
                for col in sample_df.columns:
                    sample_values_by_column[col] = [
                        str(v) if v is not None else ""
                        for v in sample_df[col].to_list()
                    ]
            except Exception as e:
                logger.warning(
                    "Error reading parquet metadata",
                    table=table_name,
                    error=str(e),
                )

        # Map columns to ColumnMetadata
        columns: list[ColumnMetadata] = []
        for col_def in schema_columns:
            sample_vals = sample_values_by_column.get(col_def["name"], [])
            col_meta = self._map_column_metadata(col_def, sample_vals)
            columns.append(col_meta)

        now = datetime.now(timezone.utc)
        domain = TABLE_TYPE_DOMAINS.get(table_type, "general")
        description = table_def.get("description", "") or TABLE_TYPE_DESCRIPTIONS.get(
            table_type, "Data table"
        )
        business_purpose = TABLE_TYPE_PURPOSES.get(table_type, "General data storage")

        return TableMetadata(
            table_name=table_name,
            layer="gold",
            domain=domain,
            file_path=str(parquet_path) if parquet_path else "",
            row_count=row_count,
            column_count=len(columns),
            file_size_bytes=file_size_bytes,
            schema_version=self.SCHEMA_VERSION,
            created_at=now,
            updated_at=now,
            description=description,
            business_purpose=business_purpose,
            data_owner=self.SOURCE_SYSTEM,
            columns=columns,
        )

    def _map_column_metadata(
        self,
        col_def: dict[str, Any],
        sample_values: list[str] | None = None,
    ) -> ColumnMetadata:
        """Map schema column to ColumnMetadata.

        Args:
            col_def: Column definition from WiQ schema.
            sample_values: Sample values from parquet file.

        Returns:
            Populated ColumnMetadata object.
        """
        col_name = col_def["name"]
        data_type = col_def.get("data_type", "VARCHAR")
        is_pk = col_def.get("is_primary_key", False)
        is_fk = col_def.get("is_foreign_key", False)
        references_table = col_def.get("references_table")
        references_column = col_def.get("references_column")

        # Build description based on column role
        description_parts = []
        if is_pk:
            description_parts.append("Primary key")
        if is_fk and references_table:
            description_parts.append(
                f"Foreign key referencing {references_table}.{references_column}"
            )
        if not description_parts:
            description_parts.append(f"Column of type {data_type}")

        description = ". ".join(description_parts)

        # Source columns for FK relationships
        source_columns = []
        if is_fk and references_table and references_column:
            source_columns.append(f"{references_table}.{references_column}")

        return ColumnMetadata(
            name=col_name,
            data_type=data_type,
            nullable=not is_pk,  # Primary keys are not nullable
            description=description,
            source_columns=source_columns,
            example_values=sample_values or [],
        )


def generate_catalogue(config: PipelineConfig | None = None) -> list[TableMetadata]:
    """Generate and save catalogue for all WiQ tables.

    Convenience function for CLI and scripts.

    Args:
        config: Optional pipeline configuration. Defaults to PipelineConfig().

    Returns:
        List of generated TableMetadata objects.
    """
    if config is None:
        config = PipelineConfig()
    generator = CatalogueGenerator(config)
    return generator.generate()
