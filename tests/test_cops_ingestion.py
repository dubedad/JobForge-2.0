"""Tests for COPS forecasting table ingestion."""
from pathlib import Path

import polars as pl
import pytest

from jobforge.pipeline.config import PipelineConfig
from jobforge.ingestion.cops import (
    ingest_cops_table,
    COPS_SUPPLY_TABLES,
    COPS_DEMAND_TABLES,
)


@pytest.fixture
def test_config(tmp_path: Path) -> PipelineConfig:
    """Create a PipelineConfig using temporary directory."""
    return PipelineConfig(data_root=tmp_path / "data")


@pytest.fixture
def sample_cops_csv(tmp_path: Path) -> Path:
    """Create a sample COPS employment CSV for testing."""
    csv_path = tmp_path / "employment.csv"
    csv_content = '''Code,Occupation Name,Nom de la profession,2023,2024,2025
00000,All occupations,Toutes les professions,20000000,20100000,20200000
TEER_0,TEER 0,Professions FEER 0,500000,510000,520000
00010,Legislators,Legislateurs,5000,5100,5150
00011,Senior managers,Cadres superieurs,12000,12100,12200
10010,Financial managers,Directeurs financiers,45000,45500,46000'''
    csv_path.write_text(csv_content, encoding="utf-8")
    return csv_path


class TestCopsIngestion:
    """Tests for COPS ingestion."""

    def test_cops_tables_lists_complete(self) -> None:
        """Verify COPS table lists contain expected tables."""
        assert "employment" in COPS_DEMAND_TABLES
        assert "job_openings" in COPS_DEMAND_TABLES
        assert "school_leavers" in COPS_SUPPLY_TABLES
        assert "immigration" in COPS_SUPPLY_TABLES

    def test_ingest_cops_creates_gold_file(
        self,
        sample_cops_csv: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify ingest_cops_table creates gold parquet file."""
        result = ingest_cops_table(
            source_path=sample_cops_csv,
            table_name="cops_employment",
            config=test_config,
        )

        assert result["gold_path"].exists()

    def test_cops_filters_aggregate_rows(
        self,
        sample_cops_csv: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify aggregate rows (00000, TEER_*) are filtered out."""
        result = ingest_cops_table(
            source_path=sample_cops_csv,
            table_name="cops_employment",
            config=test_config,
            filter_to_unit_groups=True,
        )

        gold_df = pl.read_parquet(result["gold_path"])

        # Sample has 5 rows, but only 3 are unit groups
        assert len(gold_df) == 3
        # All should have unit_group_id
        assert gold_df["unit_group_id"].null_count() == 0

    def test_cops_preserves_aggregates_when_requested(
        self,
        sample_cops_csv: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify aggregates are preserved when filter_to_unit_groups=False."""
        result = ingest_cops_table(
            source_path=sample_cops_csv,
            table_name="cops_employment_all",
            config=test_config,
            filter_to_unit_groups=False,
        )

        gold_df = pl.read_parquet(result["gold_path"])

        # All 5 rows preserved
        assert len(gold_df) == 5
        # Aggregates have null unit_group_id
        assert gold_df["unit_group_id"].null_count() == 2

    def test_cops_has_projection_columns(
        self,
        sample_cops_csv: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify projection year columns are preserved."""
        result = ingest_cops_table(
            source_path=sample_cops_csv,
            table_name="cops_employment",
            config=test_config,
        )

        gold_df = pl.read_parquet(result["gold_path"])

        assert "2023" in gold_df.columns
        assert "2024" in gold_df.columns
        assert "2025" in gold_df.columns

    def test_cops_has_bilingual_names(
        self,
        sample_cops_csv: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify bilingual occupation names are preserved."""
        result = ingest_cops_table(
            source_path=sample_cops_csv,
            table_name="cops_employment",
            config=test_config,
        )

        gold_df = pl.read_parquet(result["gold_path"])

        assert "occupation_name_en" in gold_df.columns
        assert "occupation_name_fr" in gold_df.columns
