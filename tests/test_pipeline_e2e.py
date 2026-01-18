"""End-to-end tests for pipeline infrastructure.

Verifies all Phase 1 success criteria:
1. Pipeline can accept a source file and write it through all four layers
2. Each layer produces parquet files with provenance columns
3. Layer transitions are logged and queryable
4. Gold layer output is queryable via DuckDB SQL
"""

import shutil
from pathlib import Path

import polars as pl
import pytest

from jobforge.pipeline.catalog import CatalogManager
from jobforge.pipeline.config import PipelineConfig
from jobforge.pipeline.engine import PipelineEngine
from jobforge.pipeline.query import GoldQueryEngine


@pytest.fixture
def test_config(tmp_path: Path) -> PipelineConfig:
    """Create a PipelineConfig using temporary directory."""
    return PipelineConfig(data_root=tmp_path / "data")


@pytest.fixture
def sample_csv_path() -> Path:
    """Get path to sample NOC CSV fixture."""
    return Path(__file__).parent / "fixtures" / "sample_noc.csv"


@pytest.fixture
def pipeline(test_config: PipelineConfig) -> PipelineEngine:
    """Create a PipelineEngine with test config."""
    return PipelineEngine(config=test_config)


class TestFullPipelineFlow:
    """Tests for complete pipeline flow from source to gold."""

    def test_full_pipeline_flow(
        self,
        pipeline: PipelineEngine,
        sample_csv_path: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify pipeline processes source file through all four layers."""
        # Run full pipeline
        result = pipeline.run_full_pipeline(
            source_path=sample_csv_path,
            table_name="noc_codes",
            domain="noc",
        )

        # Assert staged file exists with provenance columns
        staged_path = result["staged_path"]
        assert staged_path.exists(), "Staged file should exist"
        staged_df = pl.read_parquet(staged_path)
        assert "_source_file" in staged_df.columns
        assert "_batch_id" in staged_df.columns
        assert "_ingested_at" in staged_df.columns
        assert "_layer" in staged_df.columns

        # Assert bronze file exists with provenance columns
        bronze_path = result["bronze_path"]
        assert bronze_path.exists(), "Bronze file should exist"
        bronze_df = pl.read_parquet(bronze_path)
        assert "_source_file" in bronze_df.columns
        assert "_layer" in bronze_df.columns
        assert bronze_df["_layer"][0] == "bronze"

        # Assert silver file exists with provenance columns
        silver_path = result["silver_path"]
        assert silver_path.exists(), "Silver file should exist"
        silver_df = pl.read_parquet(silver_path)
        assert "_source_file" in silver_df.columns
        assert "_layer" in silver_df.columns
        assert silver_df["_layer"][0] == "silver"

        # Assert gold file exists with provenance columns
        gold_path = result["gold_path"]
        assert gold_path.exists(), "Gold file should exist"
        gold_df = pl.read_parquet(gold_path)
        assert "_source_file" in gold_df.columns
        assert "_layer" in gold_df.columns
        assert gold_df["_layer"][0] == "gold"

        # Assert all parquet files have all provenance columns
        required_cols = ["_source_file", "_ingested_at", "_batch_id", "_layer"]
        for layer_df in [staged_df, bronze_df, silver_df, gold_df]:
            for col in required_cols:
                assert col in layer_df.columns, f"Missing column: {col}"


class TestLayerTransitionsLogged:
    """Tests for layer transition logging."""

    def test_layer_transitions_logged(
        self,
        pipeline: PipelineEngine,
        sample_csv_path: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify layer transitions are logged and queryable."""
        # Run pipeline
        result = pipeline.run_full_pipeline(
            source_path=sample_csv_path,
            table_name="noc_codes",
            domain="noc",
        )

        # Use CatalogManager to get lineage logs
        catalog = CatalogManager(test_config)
        batch_id = result["batch_id"]
        logs = catalog.get_lineage_logs(batch_id=batch_id)

        # Assert logs exist for each transition
        assert len(logs) >= 3, "Should have at least 3 transition logs"

        # Check transitions exist: staged->bronze, bronze->silver, silver->gold
        transitions = [(log.source_layer, log.target_layer) for log in logs]
        assert ("staged", "bronze") in transitions, "Missing staged->bronze transition"
        assert ("bronze", "silver") in transitions, "Missing bronze->silver transition"
        assert ("silver", "gold") in transitions, "Missing silver->gold transition"

        # Assert logs contain correct row counts
        for log in logs:
            assert log.row_count_in > 0, "Row count in should be positive"
            assert log.row_count_out > 0, "Row count out should be positive"
            assert log.status == "success", "All transitions should succeed"


class TestGoldQueryable:
    """Tests for DuckDB queryability of gold layer."""

    def test_gold_queryable_via_duckdb(
        self,
        pipeline: PipelineEngine,
        sample_csv_path: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify gold layer is queryable via DuckDB SQL."""
        # Run pipeline
        result = pipeline.run_full_pipeline(
            source_path=sample_csv_path,
            table_name="noc_codes",
            domain="noc",
        )

        # Create GoldQueryEngine and register tables
        engine = GoldQueryEngine(test_config)
        tables = engine.register_gold_tables()

        # Assert table was registered
        assert len(tables) >= 1, "Should have at least one gold table"
        assert "noc_codes" in tables, "noc_codes table should be registered"

        # Execute COUNT query
        count_result = engine.query("SELECT COUNT(*) as cnt FROM noc_codes")
        assert count_result["cnt"][0] == 10, "Should have 10 rows"

        # Execute provenance query
        source_result = engine.query(
            "SELECT DISTINCT _source_file FROM noc_codes"
        )
        assert len(source_result) == 1, "Should have one source file"
        assert "sample_noc.csv" in source_result["_source_file"][0]


class TestProvenanceColumns:
    """Tests for provenance column presence and values."""

    def test_provenance_columns_present(
        self,
        pipeline: PipelineEngine,
        sample_csv_path: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify provenance columns are present with correct values."""
        # Run pipeline
        result = pipeline.run_full_pipeline(
            source_path=sample_csv_path,
            table_name="noc_codes",
            domain="noc",
        )

        # Read gold parquet
        gold_df = pl.read_parquet(result["gold_path"])

        # Assert provenance columns exist
        assert "_source_file" in gold_df.columns
        assert "_ingested_at" in gold_df.columns
        assert "_batch_id" in gold_df.columns
        assert "_layer" in gold_df.columns

        # Assert _layer value is 'gold'
        assert gold_df["_layer"][0] == "gold"

        # Assert _source_file contains original filename
        assert "sample_noc.csv" in gold_df["_source_file"][0]

        # Assert _batch_id is a UUID-like string
        batch_id = gold_df["_batch_id"][0]
        assert len(batch_id) == 36, "Batch ID should be UUID format"
        assert batch_id.count("-") == 4, "UUID should have 4 hyphens"


class TestPipelineIntegration:
    """Additional integration tests for pipeline robustness."""

    def test_multiple_runs_independent(
        self,
        pipeline: PipelineEngine,
        sample_csv_path: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify multiple pipeline runs produce independent batches."""
        # Run pipeline twice
        result1 = pipeline.run_full_pipeline(
            source_path=sample_csv_path,
            table_name="noc_codes_v1",
            domain="noc",
        )
        result2 = pipeline.run_full_pipeline(
            source_path=sample_csv_path,
            table_name="noc_codes_v2",
            domain="noc",
        )

        # Assert different batch IDs
        assert result1["batch_id"] != result2["batch_id"]

        # Assert different output files
        assert result1["gold_path"] != result2["gold_path"]

    def test_catalog_tracks_metadata(
        self,
        pipeline: PipelineEngine,
        sample_csv_path: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify catalog manager can query lineage after pipeline run."""
        # Run pipeline
        result = pipeline.run_full_pipeline(
            source_path=sample_csv_path,
            table_name="noc_codes",
            domain="noc",
        )

        # Query all lineage logs
        catalog = CatalogManager(test_config)
        all_logs = catalog.get_lineage_logs()

        # Should have logs from this run
        assert len(all_logs) >= 3

        # Logs should be sorted by time
        for i in range(1, len(all_logs)):
            assert all_logs[i].started_at >= all_logs[i - 1].started_at
