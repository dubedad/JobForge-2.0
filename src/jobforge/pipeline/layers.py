"""Layer classes for medallion architecture data processing.

Each layer has specific responsibilities per DAMA DMBOK:
- Staged: Ingest raw data, add provenance, NO modifications
- Bronze: Type standardization, schema enforcement, NO business logic
- Silver: Data cleaning, harmonization, deduplication, validation
- Gold: Business models, derived fields, analytics-ready
"""

from pathlib import Path
from typing import Callable, Optional

import polars as pl

from jobforge.pipeline.config import PipelineConfig
from jobforge.pipeline.provenance import (
    add_provenance_columns,
    generate_batch_id,
    update_layer_column,
)


class StagedLayer:
    """Staged layer: raw data ingestion with provenance.

    MUST NOT modify source data in any way.
    Only adds provenance columns and converts to parquet format.
    """

    name = "staged"

    def ingest(
        self,
        source_path: Path,
        config: PipelineConfig,
        table_name: Optional[str] = None,
        batch_id: Optional[str] = None,
    ) -> tuple[Path, str, int]:
        """Ingest source file to staged layer.

        Reads source file, adds provenance columns, writes to staged/.

        Args:
            source_path: Path to source file (CSV, Excel, JSON, or Parquet).
            config: Pipeline configuration with path accessors.
            table_name: Optional table name (defaults to source filename stem).
            batch_id: Optional batch ID (defaults to new UUID).

        Returns:
            Tuple of (staged_path, batch_id, row_count).

        Raises:
            ValueError: If source file format is not supported.
        """
        source_path = Path(source_path)
        if batch_id is None:
            batch_id = generate_batch_id()
        if table_name is None:
            table_name = source_path.stem

        # Read source file based on extension
        suffix = source_path.suffix.lower()
        if suffix == ".csv":
            df = pl.scan_csv(source_path)
        elif suffix in (".xlsx", ".xls"):
            # Excel requires eager read, then convert to lazy
            df = pl.read_excel(source_path).lazy()
        elif suffix == ".json":
            df = pl.scan_ndjson(source_path)
        elif suffix == ".parquet":
            df = pl.scan_parquet(source_path)
        else:
            raise ValueError(f"Unsupported source format: {suffix}")

        # Add provenance columns (this is ALL we do - no data modification)
        df = add_provenance_columns(df, str(source_path), batch_id, self.name)

        # Write to staged directory
        staged_dir = config.staged_path()
        staged_dir.mkdir(parents=True, exist_ok=True)
        output_path = staged_dir / f"{table_name}.parquet"

        # Collect and write with compression
        result = df.collect()
        result.write_parquet(output_path, compression="zstd")

        return output_path, batch_id, len(result)


class BronzeLayer:
    """Bronze layer: type standardization and schema enforcement.

    NO business logic - only technical transformations:
    - Column renames
    - Type casts
    - Schema validation
    """

    name = "bronze"

    def process(
        self,
        staged_path: Path,
        config: PipelineConfig,
        schema: Optional[dict] = None,
    ) -> tuple[Path, str, int, int]:
        """Process staged data to bronze layer.

        Applies schema transformations if provided, updates provenance.

        Args:
            staged_path: Path to staged parquet file.
            config: Pipeline configuration with path accessors.
            schema: Optional schema dict with keys:
                - rename: dict of {old_name: new_name} column renames
                - cast: dict of {column: polars_type} type casts

        Returns:
            Tuple of (bronze_path, batch_id, rows_in, rows_out).
        """
        staged_path = Path(staged_path)

        # Use scan_parquet for lazy evaluation
        df = pl.scan_parquet(staged_path)

        # Get row count before transforms
        rows_in = df.select(pl.len()).collect().item()

        # Extract batch_id from existing provenance
        batch_id = (
            df.select("_batch_id").first().collect().item()
        )

        # Apply schema transformations if provided
        if schema:
            # Column renames
            if "rename" in schema and schema["rename"]:
                df = df.rename(schema["rename"])

            # Type casts
            if "cast" in schema and schema["cast"]:
                cast_exprs = [
                    pl.col(col).cast(dtype) for col, dtype in schema["cast"].items()
                ]
                df = df.with_columns(cast_exprs)

        # Update layer provenance
        df = update_layer_column(df, self.name)

        # Write to bronze directory
        bronze_dir = config.bronze_path()
        bronze_dir.mkdir(parents=True, exist_ok=True)
        output_path = bronze_dir / staged_path.name

        # Collect and write
        result = df.collect()
        result.write_parquet(output_path, compression="zstd")
        rows_out = len(result)

        return output_path, batch_id, rows_in, rows_out


class SilverLayer:
    """Silver layer: data cleaning and harmonization.

    Transformations allowed:
    - Deduplication
    - Null handling
    - Value normalization
    - Data validation
    - Quality rules
    """

    name = "silver"

    def process(
        self,
        bronze_path: Path,
        config: PipelineConfig,
        transforms: Optional[list[Callable[[pl.LazyFrame], pl.LazyFrame]]] = None,
    ) -> tuple[Path, str, int, int, list[str]]:
        """Process bronze data to silver layer.

        Applies cleaning transforms if provided, updates provenance.

        Args:
            bronze_path: Path to bronze parquet file.
            config: Pipeline configuration with path accessors.
            transforms: Optional list of transform functions.
                Each function takes LazyFrame and returns LazyFrame.

        Returns:
            Tuple of (silver_path, batch_id, rows_in, rows_out, transform_names).
        """
        bronze_path = Path(bronze_path)

        # Use scan_parquet for lazy evaluation
        df = pl.scan_parquet(bronze_path)

        # Get row count before transforms
        rows_in = df.select(pl.len()).collect().item()

        # Extract batch_id from existing provenance
        batch_id = (
            df.select("_batch_id").first().collect().item()
        )

        # Apply transforms if provided
        transform_names = []
        if transforms:
            for transform in transforms:
                df = transform(df)
                transform_names.append(transform.__name__)

        # Update layer provenance
        df = update_layer_column(df, self.name)

        # Write to silver directory
        silver_dir = config.silver_path()
        silver_dir.mkdir(parents=True, exist_ok=True)
        output_path = silver_dir / bronze_path.name

        # Collect and write
        result = df.collect()
        result.write_parquet(output_path, compression="zstd")
        rows_out = len(result)

        return output_path, batch_id, rows_in, rows_out, transform_names


class GoldLayer:
    """Gold layer: business models and analytics-ready data.

    Transformations allowed:
    - Derived fields / calculated columns
    - Business aggregations
    - Dimensional modeling
    - Analytics-specific structures
    """

    name = "gold"

    def process(
        self,
        silver_path: Path,
        config: PipelineConfig,
        transforms: Optional[list[Callable[[pl.LazyFrame], pl.LazyFrame]]] = None,
    ) -> tuple[Path, str, int, int, list[str]]:
        """Process silver data to gold layer.

        Applies business transforms if provided, updates provenance.

        Args:
            silver_path: Path to silver parquet file.
            config: Pipeline configuration with path accessors.
            transforms: Optional list of transform functions.
                Each function takes LazyFrame and returns LazyFrame.

        Returns:
            Tuple of (gold_path, batch_id, rows_in, rows_out, transform_names).
        """
        silver_path = Path(silver_path)

        # Use scan_parquet for lazy evaluation
        df = pl.scan_parquet(silver_path)

        # Get row count before transforms
        rows_in = df.select(pl.len()).collect().item()

        # Extract batch_id from existing provenance
        batch_id = (
            df.select("_batch_id").first().collect().item()
        )

        # Apply transforms if provided
        transform_names = []
        if transforms:
            for transform in transforms:
                df = transform(df)
                transform_names.append(transform.__name__)

        # Update layer provenance
        df = update_layer_column(df, self.name)

        # Write to gold directory
        gold_dir = config.gold_path()
        gold_dir.mkdir(parents=True, exist_ok=True)
        output_path = gold_dir / silver_path.name

        # Collect and write
        result = df.collect()
        result.write_parquet(output_path, compression="zstd")
        rows_out = len(result)

        return output_path, batch_id, rows_in, rows_out, transform_names
