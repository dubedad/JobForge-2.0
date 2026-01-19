"""Tests for Job Architecture and DIM Occupations ingestion."""
from pathlib import Path

import polars as pl
import pytest

from jobforge.pipeline.config import PipelineConfig
from jobforge.ingestion.job_architecture import (
    ingest_job_architecture,
    extract_dim_occupations,
    ingest_job_architecture_with_dim_occupations,
)


@pytest.fixture
def test_config(tmp_path: Path) -> PipelineConfig:
    """Create a PipelineConfig using temporary directory."""
    return PipelineConfig(data_root=tmp_path / "data")


@pytest.fixture
def sample_job_arch_csv(tmp_path: Path) -> Path:
    """Create a sample Job Architecture CSV for testing."""
    csv_path = tmp_path / "job_architecture.csv"
    csv_content = '''JT_ID,Job_Title,Titre_de_poste,Job_Function,Fonction_professionnelle,Job_Family,Famille_d'emplois,Managerial_Level,Niveau_de_gestion,2021_NOC_UID,2021_NOC_Title
1,Senior Analyst,Analyste principal,Policy,Politiques,Policy Analysis,Analyse des politiques,Employee,Employe,41400,Policy analysts
2,Director Finance,Directeur finances,Finance,Finance,Financial Mgmt,Gestion financiere,Director,Directeur,10010,Financial managers
3,HR Advisor,Conseiller RH,HR,RH,HR Advisory,Conseil RH,Employee,Employe,11200,HR professionals
4,Junior Analyst,Analyste junior,Policy,Politiques,Policy Analysis,Analyse des politiques,Employee,Employe,41400,Policy analysts'''
    csv_path.write_text(csv_content, encoding="utf-8")
    return csv_path


class TestJobArchitectureIngestion:
    """Tests for Job Architecture ingestion."""

    def test_ingest_creates_gold_file(
        self,
        sample_job_arch_csv: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify ingest_job_architecture creates gold parquet file."""
        result = ingest_job_architecture(
            source_path=sample_job_arch_csv,
            config=test_config,
        )

        assert result["gold_path"].exists()

    def test_job_arch_has_unit_group_id(
        self,
        sample_job_arch_csv: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify unit_group_id is derived from NOC 2021 code."""
        result = ingest_job_architecture(
            source_path=sample_job_arch_csv,
            config=test_config,
        )

        gold_df = pl.read_parquet(result["gold_path"])

        assert "unit_group_id" in gold_df.columns
        # Check derivation: 10010 -> 10010
        # jt_id may be inferred as int64, so cast to string for comparison
        row = gold_df.filter(pl.col("jt_id").cast(pl.Utf8) == "2")
        assert row["unit_group_id"][0] == "10010"

    def test_job_arch_has_bilingual_columns(
        self,
        sample_job_arch_csv: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify bilingual columns are preserved."""
        result = ingest_job_architecture(
            source_path=sample_job_arch_csv,
            config=test_config,
        )

        gold_df = pl.read_parquet(result["gold_path"])

        assert "job_title_en" in gold_df.columns
        assert "job_title_fr" in gold_df.columns
        assert "job_function_en" in gold_df.columns
        assert "job_function_fr" in gold_df.columns

    def test_job_arch_preserves_all_rows(
        self,
        sample_job_arch_csv: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify all job title rows are preserved."""
        result = ingest_job_architecture(
            source_path=sample_job_arch_csv,
            config=test_config,
        )

        gold_df = pl.read_parquet(result["gold_path"])

        assert len(gold_df) == 4


class TestDimOccupationsExtraction:
    """Tests for DIM Occupations extraction."""

    def test_extract_dim_occupations_creates_file(
        self,
        sample_job_arch_csv: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify extract_dim_occupations creates gold parquet file."""
        # First ingest Job Architecture
        job_arch_result = ingest_job_architecture(
            source_path=sample_job_arch_csv,
            config=test_config,
        )

        # Then extract DIM Occupations
        result = extract_dim_occupations(
            job_arch_gold_path=job_arch_result["gold_path"],
            config=test_config,
        )

        assert result["gold_path"].exists()

    def test_dim_occupations_unique_families(
        self,
        sample_job_arch_csv: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify DIM Occupations contains unique job families."""
        job_arch_result = ingest_job_architecture(
            source_path=sample_job_arch_csv,
            config=test_config,
        )

        result = extract_dim_occupations(
            job_arch_gold_path=job_arch_result["gold_path"],
            config=test_config,
        )

        gold_df = pl.read_parquet(result["gold_path"])

        # Sample has 3 unique families (Policy Analysis x2 deduped)
        assert len(gold_df) == 3
        assert "job_family_en" in gold_df.columns
        assert "job_function_en" in gold_df.columns

    def test_combined_ingestion(
        self,
        sample_job_arch_csv: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify combined ingestion creates both tables."""
        result = ingest_job_architecture_with_dim_occupations(
            source_path=sample_job_arch_csv,
            config=test_config,
        )

        assert result["job_architecture"]["gold_path"].exists()
        assert result["dim_occupations"]["gold_path"].exists()


class TestJobArchForeignKeys:
    """Tests for foreign key relationships."""

    def test_unit_group_ids_valid_format(
        self,
        sample_job_arch_csv: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify all unit_group_id values are 5-digit format."""
        result = ingest_job_architecture(
            source_path=sample_job_arch_csv,
            config=test_config,
        )

        gold_df = pl.read_parquet(result["gold_path"])

        for uid in gold_df["unit_group_id"]:
            if uid is not None:
                assert len(uid) == 5, f"unit_group_id {uid} is not 5 digits"
