"""Tests for DIM NOC ingestion."""

from pathlib import Path

import polars as pl
import pytest

from jobforge.ingestion import ingest_dim_noc
from jobforge.ingestion.transforms import (
    derive_unit_group_id,
    filter_unit_groups,
    normalize_noc_code,
)
from jobforge.pipeline.config import PipelineConfig


@pytest.fixture
def test_config(tmp_path: Path) -> PipelineConfig:
    """Create a PipelineConfig using temporary directory."""
    return PipelineConfig(data_root=tmp_path / "data")


@pytest.fixture
def sample_noc_csv(tmp_path: Path) -> Path:
    """Create a sample NOC structure CSV for testing."""
    csv_path = tmp_path / "noc_structure.csv"
    csv_content = """Level,Hierarchical structure,Code - NOC 2021 V1.0,Class title,Class definition
1,Broad occupational category,0,Legislative and senior management occupations,This broad category includes legislative and management roles
2,Major group,00,Senior management occupations,This major group includes senior management roles
5,Unit group,00010,Legislators,Legislators include elected officials
5,Unit group,00011,Senior government managers,Senior government managers plan operations
5,Unit group,00012,Senior managers - financial,Senior managers in financial services
5,Unit group,00013,Senior managers - trade,Senior managers in trade organizations
5,Unit group,10010,Financial managers,Financial managers plan operations"""
    csv_path.write_text(csv_content, encoding="utf-8")
    return csv_path


class TestTransforms:
    """Tests for transform functions."""

    def test_filter_unit_groups(self) -> None:
        """Verify filter_unit_groups keeps only Level 5."""
        df = pl.LazyFrame(
            {
                "level": [1, 2, 3, 4, 5, 5, 5],
                "noc_code": ["0", "00", "001", "0010", "00010", "00011", "10010"],
            }
        )
        result = filter_unit_groups(df).collect()
        assert len(result) == 3
        assert all(result["level"] == 5)

    def test_derive_unit_group_id(self) -> None:
        """Verify derive_unit_group_id zero-pads codes."""
        df = pl.LazyFrame(
            {
                "noc_code": ["10", "00010", "12345"],
            }
        )
        result = derive_unit_group_id(df).collect()
        assert result["unit_group_id"].to_list() == ["00010", "00010", "12345"]

    def test_normalize_noc_code_strips_decimal(self) -> None:
        """Verify normalize_noc_code handles OaSIS-style codes."""
        df = pl.LazyFrame(
            {
                "Code": ["00010.00", "12345.01", "10"],
            }
        )
        result = normalize_noc_code(df).collect()
        assert result["unit_group_id"].to_list() == ["00010", "12345", "00010"]


class TestDimNocIngestion:
    """Tests for DIM NOC ingestion."""

    def test_ingest_dim_noc_creates_gold_file(
        self,
        sample_noc_csv: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify ingest_dim_noc creates gold parquet file."""
        result = ingest_dim_noc(
            source_path=sample_noc_csv,
            config=test_config,
        )

        assert result["gold_path"].exists()
        assert result["gold_path"].suffix == ".parquet"

    def test_ingest_dim_noc_filters_to_unit_groups(
        self,
        sample_noc_csv: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify only unit groups (Level 5) are in gold table."""
        result = ingest_dim_noc(
            source_path=sample_noc_csv,
            config=test_config,
        )

        gold_df = pl.read_parquet(result["gold_path"])

        # Sample has 5 unit groups (Level 5)
        assert len(gold_df) == 5

    def test_ingest_dim_noc_has_unit_group_id(
        self,
        sample_noc_csv: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify gold table has unit_group_id column."""
        result = ingest_dim_noc(
            source_path=sample_noc_csv,
            config=test_config,
        )

        gold_df = pl.read_parquet(result["gold_path"])

        assert "unit_group_id" in gold_df.columns
        # All unit_group_ids should be 5 characters
        assert all(len(uid) == 5 for uid in gold_df["unit_group_id"])

    def test_ingest_dim_noc_has_provenance(
        self,
        sample_noc_csv: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify gold table has provenance columns."""
        result = ingest_dim_noc(
            source_path=sample_noc_csv,
            config=test_config,
        )

        gold_df = pl.read_parquet(result["gold_path"])

        assert "_source_file" in gold_df.columns
        assert "_ingested_at" in gold_df.columns
        assert "_batch_id" in gold_df.columns
        assert "_layer" in gold_df.columns
        assert gold_df["_layer"][0] == "gold"

    def test_ingest_dim_noc_expected_columns(
        self,
        sample_noc_csv: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify gold table has expected business columns."""
        result = ingest_dim_noc(
            source_path=sample_noc_csv,
            config=test_config,
        )

        gold_df = pl.read_parquet(result["gold_path"])

        expected_columns = [
            "unit_group_id",
            "noc_code",
            "class_title",
            "class_definition",
            "hierarchical_structure",
        ]
        for col in expected_columns:
            assert col in gold_df.columns, f"Missing column: {col}"
