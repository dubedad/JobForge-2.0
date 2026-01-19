"""Tests for NOC attribute ingestion (OASIS and Element tables)."""
from pathlib import Path

import polars as pl
import pytest

from jobforge.pipeline.config import PipelineConfig
from jobforge.ingestion.oasis import ingest_oasis_table, OASIS_TABLES
from jobforge.ingestion.element import ingest_element_table, ELEMENT_TABLES


@pytest.fixture
def test_config(tmp_path: Path) -> PipelineConfig:
    """Create a PipelineConfig using temporary directory."""
    return PipelineConfig(data_root=tmp_path / "data")


@pytest.fixture
def sample_oasis_csv(tmp_path: Path) -> Path:
    """Create a sample OASIS skills CSV for testing."""
    csv_path = tmp_path / "skills_oasis.csv"
    csv_content = '''OaSIS Code - Final,OaSIS Label - Final,Reading,Writing,Numeracy
00010.00,Legislators,4,4,3
00011.00,Senior government managers,5,5,4
10010.00,Financial managers,4,4,5
10010.01,Financial managers (variant),4,4,5'''
    csv_path.write_text(csv_content, encoding="utf-8")
    return csv_path


@pytest.fixture
def sample_element_csv(tmp_path: Path) -> Path:
    """Create a sample Element main duties CSV for testing."""
    csv_path = tmp_path / "main_duties.csv"
    csv_content = '''OaSIS profile code,Main Duty
00010.00,Participate in debates
00010.00,Propose legislation
00011.00,Plan objectives
00011.00,Authorize budgets
10010.00,Develop policies'''
    csv_path.write_text(csv_content, encoding="utf-8")
    return csv_path


class TestOasisIngestion:
    """Tests for OASIS attribute ingestion."""

    def test_oasis_tables_list_complete(self) -> None:
        """Verify OASIS_TABLES contains expected tables."""
        expected = ["skills", "abilities", "personal_attributes", "knowledges",
                    "workactivities", "workcontext"]
        for table in expected:
            assert table in OASIS_TABLES

    def test_ingest_oasis_creates_gold_file(
        self,
        sample_oasis_csv: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify ingest_oasis_table creates gold parquet file."""
        result = ingest_oasis_table(
            source_path=sample_oasis_csv,
            table_name="oasis_skills",
            config=test_config,
        )

        assert result["gold_path"].exists()

    def test_oasis_has_unit_group_id(
        self,
        sample_oasis_csv: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify OASIS gold table has unit_group_id derived from OaSIS code."""
        result = ingest_oasis_table(
            source_path=sample_oasis_csv,
            table_name="oasis_skills",
            config=test_config,
        )

        gold_df = pl.read_parquet(result["gold_path"])

        assert "unit_group_id" in gold_df.columns
        # Check derivation: 00010.00 -> 00010
        row = gold_df.filter(pl.col("oasis_code") == "00010.00")
        assert row["unit_group_id"][0] == "00010"

    def test_oasis_has_noc_element_code(
        self,
        sample_oasis_csv: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify OASIS gold table has noc_element_code derived from OaSIS code."""
        result = ingest_oasis_table(
            source_path=sample_oasis_csv,
            table_name="oasis_skills",
            config=test_config,
        )

        gold_df = pl.read_parquet(result["gold_path"])

        assert "noc_element_code" in gold_df.columns
        # Check derivation: 00010.00 -> 00, 10010.01 -> 01
        row1 = gold_df.filter(pl.col("oasis_code") == "00010.00")
        assert row1["noc_element_code"][0] == "00"
        row2 = gold_df.filter(pl.col("oasis_code") == "10010.01")
        assert row2["noc_element_code"][0] == "01"

    def test_oasis_preserves_proficiency_columns(
        self,
        sample_oasis_csv: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify proficiency columns are preserved in gold table."""
        result = ingest_oasis_table(
            source_path=sample_oasis_csv,
            table_name="oasis_skills",
            config=test_config,
        )

        gold_df = pl.read_parquet(result["gold_path"])

        assert "Reading" in gold_df.columns
        assert "Writing" in gold_df.columns
        assert "Numeracy" in gold_df.columns


class TestElementIngestion:
    """Tests for Element attribute ingestion."""

    def test_element_tables_list_complete(self) -> None:
        """Verify ELEMENT_TABLES contains expected tables."""
        expected = ["labels", "main_duties", "employment_requirements",
                    "example_titles", "lead_statement"]
        for table in expected:
            assert table in ELEMENT_TABLES

    def test_ingest_element_creates_gold_file(
        self,
        sample_element_csv: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify ingest_element_table creates gold parquet file."""
        result = ingest_element_table(
            source_path=sample_element_csv,
            table_name="element_main_duties",
            config=test_config,
        )

        assert result["gold_path"].exists()

    def test_element_has_unit_group_id(
        self,
        sample_element_csv: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify Element gold table has unit_group_id."""
        result = ingest_element_table(
            source_path=sample_element_csv,
            table_name="element_main_duties",
            config=test_config,
        )

        gold_df = pl.read_parquet(result["gold_path"])

        assert "unit_group_id" in gold_df.columns
        assert "00010" in gold_df["unit_group_id"].to_list()

    def test_element_preserves_multiple_rows(
        self,
        sample_element_csv: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify Element tables preserve multiple rows per occupation."""
        result = ingest_element_table(
            source_path=sample_element_csv,
            table_name="element_main_duties",
            config=test_config,
        )

        gold_df = pl.read_parquet(result["gold_path"])

        # 00010 has 2 duties in sample
        duties_00010 = gold_df.filter(pl.col("unit_group_id") == "00010")
        assert len(duties_00010) == 2

    def test_element_has_provenance(
        self,
        sample_element_csv: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify Element gold table has provenance columns."""
        result = ingest_element_table(
            source_path=sample_element_csv,
            table_name="element_main_duties",
            config=test_config,
        )

        gold_df = pl.read_parquet(result["gold_path"])

        assert "_source_file" in gold_df.columns
        assert "_layer" in gold_df.columns
        assert gold_df["_layer"][0] == "gold"


class TestAttributeForeignKeys:
    """Tests for foreign key relationships to DIM NOC."""

    def test_oasis_unit_group_ids_valid_format(
        self,
        sample_oasis_csv: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify all unit_group_id values are 5-digit format."""
        result = ingest_oasis_table(
            source_path=sample_oasis_csv,
            table_name="oasis_skills",
            config=test_config,
        )

        gold_df = pl.read_parquet(result["gold_path"])

        for uid in gold_df["unit_group_id"]:
            assert len(uid) == 5, f"unit_group_id {uid} is not 5 digits"

    def test_element_unit_group_ids_valid_format(
        self,
        sample_element_csv: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify all unit_group_id values are 5-digit format."""
        result = ingest_element_table(
            source_path=sample_element_csv,
            table_name="element_main_duties",
            config=test_config,
        )

        gold_df = pl.read_parquet(result["gold_path"])

        for uid in gold_df["unit_group_id"]:
            assert len(uid) == 5, f"unit_group_id {uid} is not 5 digits"
