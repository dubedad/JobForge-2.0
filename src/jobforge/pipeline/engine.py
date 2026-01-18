"""Pipeline engine for orchestrating data flow through medallion layers."""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

import polars as pl
import structlog

from jobforge.pipeline.config import PipelineConfig
from jobforge.pipeline.layers import BronzeLayer, GoldLayer, SilverLayer, StagedLayer
from jobforge.pipeline.models import LayerTransitionLog


class PipelineEngine:
    """Orchestrates data flow through medallion architecture layers.

    Manages data movement from staged -> bronze -> silver -> gold,
    creating audit trail logs for each transition.
    """

    def __init__(self, config: Optional[PipelineConfig] = None) -> None:
        """Initialize the pipeline engine.

        Args:
            config: Pipeline configuration. Defaults to PipelineConfig().
        """
        self.config = config or PipelineConfig()
        self.staged = StagedLayer()
        self.bronze = BronzeLayer()
        self.silver = SilverLayer()
        self.gold = GoldLayer()
        self.logger = structlog.get_logger("jobforge.pipeline")

    def _save_transition_log(self, log: LayerTransitionLog) -> Path:
        """Save transition log to catalog/lineage directory.

        Args:
            log: The transition log to save.

        Returns:
            Path to the saved log file.
        """
        lineage_dir = self.config.catalog_lineage_path()
        lineage_dir.mkdir(parents=True, exist_ok=True)
        log_path = lineage_dir / f"{log.transition_id}.json"
        log_path.write_text(log.model_dump_json(indent=2))
        return log_path

    def ingest(
        self,
        source_path: Path,
        table_name: str,
        domain: str = "default",
    ) -> dict:
        """Ingest source file to staged layer.

        Entry point for new data into the pipeline.

        Args:
            source_path: Path to source file.
            table_name: Logical name for the table.
            domain: Data domain for organization.

        Returns:
            Dict with batch_id, staged_path, row_count, log.
        """
        source_path = Path(source_path)
        started_at = datetime.now(timezone.utc)

        self.logger.info(
            "ingesting_source",
            source=str(source_path),
            table_name=table_name,
            domain=domain,
        )

        # Ingest to staged
        staged_path, batch_id, row_count = self.staged.ingest(
            source_path, self.config, table_name=table_name
        )

        completed_at = datetime.now(timezone.utc)

        # Create transition log (source -> staged)
        # Note: For initial ingestion, we use "staged" as source_layer conceptually
        # but the model requires valid enum values, so we log the ingestion specially
        log = LayerTransitionLog(
            transition_id=str(uuid.uuid4()),
            batch_id=batch_id,
            source_layer="staged",  # Initial ingestion marker
            target_layer="bronze",  # We mark as bronze to satisfy enum, but this is ingestion
            source_files=[str(source_path)],
            target_file=str(staged_path),
            row_count_in=row_count,
            row_count_out=row_count,
            transforms_applied=["ingest", "add_provenance"],
            started_at=started_at,
            completed_at=completed_at,
            status="success",
        )

        log_path = self._save_transition_log(log)

        self.logger.info(
            "ingestion_complete",
            staged_path=str(staged_path),
            batch_id=batch_id,
            row_count=row_count,
        )

        return {
            "batch_id": batch_id,
            "staged_path": staged_path,
            "row_count": row_count,
            "log": log,
            "log_path": log_path,
        }

    def promote_to_bronze(
        self,
        staged_path: Path,
        schema: Optional[dict] = None,
    ) -> dict:
        """Promote data from staged to bronze layer.

        Args:
            staged_path: Path to staged parquet file.
            schema: Optional schema dict with 'rename' and 'cast' keys.

        Returns:
            Dict with batch_id, bronze_path, rows_in, rows_out, log.
        """
        staged_path = Path(staged_path)
        started_at = datetime.now(timezone.utc)

        self.logger.info(
            "promoting_to_bronze",
            staged_path=str(staged_path),
        )

        # Process to bronze
        bronze_path, batch_id, rows_in, rows_out = self.bronze.process(
            staged_path, self.config, schema
        )

        completed_at = datetime.now(timezone.utc)

        # Determine transforms applied
        transforms = []
        if schema:
            if schema.get("rename"):
                transforms.append("rename_columns")
            if schema.get("cast"):
                transforms.append("cast_types")

        # Create transition log
        log = LayerTransitionLog(
            transition_id=str(uuid.uuid4()),
            batch_id=batch_id,
            source_layer="staged",
            target_layer="bronze",
            source_files=[str(staged_path)],
            target_file=str(bronze_path),
            row_count_in=rows_in,
            row_count_out=rows_out,
            transforms_applied=transforms or ["passthrough"],
            started_at=started_at,
            completed_at=completed_at,
            status="success",
        )

        log_path = self._save_transition_log(log)

        self.logger.info(
            "bronze_promotion_complete",
            bronze_path=str(bronze_path),
            batch_id=batch_id,
            rows_in=rows_in,
            rows_out=rows_out,
        )

        return {
            "batch_id": batch_id,
            "bronze_path": bronze_path,
            "rows_in": rows_in,
            "rows_out": rows_out,
            "log": log,
            "log_path": log_path,
        }

    def promote_to_silver(
        self,
        bronze_path: Path,
        transforms: Optional[list[Callable[[pl.LazyFrame], pl.LazyFrame]]] = None,
    ) -> dict:
        """Promote data from bronze to silver layer.

        Args:
            bronze_path: Path to bronze parquet file.
            transforms: Optional list of transform functions.

        Returns:
            Dict with batch_id, silver_path, rows_in, rows_out, log.
        """
        bronze_path = Path(bronze_path)
        started_at = datetime.now(timezone.utc)

        self.logger.info(
            "promoting_to_silver",
            bronze_path=str(bronze_path),
        )

        # Process to silver
        silver_path, batch_id, rows_in, rows_out, transform_names = self.silver.process(
            bronze_path, self.config, transforms
        )

        completed_at = datetime.now(timezone.utc)

        # Create transition log
        log = LayerTransitionLog(
            transition_id=str(uuid.uuid4()),
            batch_id=batch_id,
            source_layer="bronze",
            target_layer="silver",
            source_files=[str(bronze_path)],
            target_file=str(silver_path),
            row_count_in=rows_in,
            row_count_out=rows_out,
            transforms_applied=transform_names or ["passthrough"],
            started_at=started_at,
            completed_at=completed_at,
            status="success",
        )

        log_path = self._save_transition_log(log)

        self.logger.info(
            "silver_promotion_complete",
            silver_path=str(silver_path),
            batch_id=batch_id,
            rows_in=rows_in,
            rows_out=rows_out,
        )

        return {
            "batch_id": batch_id,
            "silver_path": silver_path,
            "rows_in": rows_in,
            "rows_out": rows_out,
            "log": log,
            "log_path": log_path,
        }

    def promote_to_gold(
        self,
        silver_path: Path,
        transforms: Optional[list[Callable[[pl.LazyFrame], pl.LazyFrame]]] = None,
    ) -> dict:
        """Promote data from silver to gold layer.

        Args:
            silver_path: Path to silver parquet file.
            transforms: Optional list of transform functions.

        Returns:
            Dict with batch_id, gold_path, rows_in, rows_out, log.
        """
        silver_path = Path(silver_path)
        started_at = datetime.now(timezone.utc)

        self.logger.info(
            "promoting_to_gold",
            silver_path=str(silver_path),
        )

        # Process to gold
        gold_path, batch_id, rows_in, rows_out, transform_names = self.gold.process(
            silver_path, self.config, transforms
        )

        completed_at = datetime.now(timezone.utc)

        # Create transition log
        log = LayerTransitionLog(
            transition_id=str(uuid.uuid4()),
            batch_id=batch_id,
            source_layer="silver",
            target_layer="gold",
            source_files=[str(silver_path)],
            target_file=str(gold_path),
            row_count_in=rows_in,
            row_count_out=rows_out,
            transforms_applied=transform_names or ["passthrough"],
            started_at=started_at,
            completed_at=completed_at,
            status="success",
        )

        log_path = self._save_transition_log(log)

        self.logger.info(
            "gold_promotion_complete",
            gold_path=str(gold_path),
            batch_id=batch_id,
            rows_in=rows_in,
            rows_out=rows_out,
        )

        return {
            "batch_id": batch_id,
            "gold_path": gold_path,
            "rows_in": rows_in,
            "rows_out": rows_out,
            "log": log,
            "log_path": log_path,
        }

    def run_full_pipeline(
        self,
        source_path: Path,
        table_name: str,
        domain: str = "default",
        bronze_schema: Optional[dict] = None,
        silver_transforms: Optional[list[Callable]] = None,
        gold_transforms: Optional[list[Callable]] = None,
    ) -> dict:
        """Run complete pipeline from source to gold.

        Convenience method that runs all four stages in sequence.

        Args:
            source_path: Path to source file.
            table_name: Logical name for the table.
            domain: Data domain for organization.
            bronze_schema: Optional schema for bronze layer.
            silver_transforms: Optional transforms for silver layer.
            gold_transforms: Optional transforms for gold layer.

        Returns:
            Dict with all paths and all logs.
        """
        self.logger.info(
            "running_full_pipeline",
            source=str(source_path),
            table_name=table_name,
            domain=domain,
        )

        # Ingest to staged
        ingest_result = self.ingest(source_path, table_name, domain)

        # Promote to bronze
        bronze_result = self.promote_to_bronze(
            ingest_result["staged_path"], bronze_schema
        )

        # Promote to silver
        silver_result = self.promote_to_silver(
            bronze_result["bronze_path"], silver_transforms
        )

        # Promote to gold
        gold_result = self.promote_to_gold(
            silver_result["silver_path"], gold_transforms
        )

        self.logger.info(
            "full_pipeline_complete",
            table_name=table_name,
            batch_id=ingest_result["batch_id"],
            gold_path=str(gold_result["gold_path"]),
        )

        return {
            "batch_id": ingest_result["batch_id"],
            "staged_path": ingest_result["staged_path"],
            "bronze_path": bronze_result["bronze_path"],
            "silver_path": silver_result["silver_path"],
            "gold_path": gold_result["gold_path"],
            "logs": [
                ingest_result["log"],
                bronze_result["log"],
                silver_result["log"],
                gold_result["log"],
            ],
            "log_paths": [
                ingest_result["log_path"],
                bronze_result["log_path"],
                silver_result["log_path"],
                gold_result["log_path"],
            ],
        }
