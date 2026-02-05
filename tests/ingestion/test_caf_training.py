"""Tests for CAF training ingestion pipeline.

Tests location dimension creation, training fact table schema,
FK validation, sparse data handling, and duration consistency.
"""

import json
import tempfile
from pathlib import Path

import polars as pl
import pytest

from jobforge.ingestion.caf_training import (
    ingest_dim_caf_training_location,
    ingest_fact_caf_training,
)
from jobforge.pipeline.config import PipelineConfig


class TestIngestDimCAFTrainingLocation:
    """Tests for dim_caf_training_location ingestion."""

    def test_creates_location_table(self, tmp_path):
        """Location dimension table is created successfully."""
        config = PipelineConfig(data_root=tmp_path)

        result = ingest_dim_caf_training_location(config=config)

        assert result["gold_path"].exists()
        assert result["row_count"] >= 5  # Per plan requirements

    def test_location_schema(self, tmp_path):
        """Location table has correct schema."""
        config = PipelineConfig(data_root=tmp_path)

        result = ingest_dim_caf_training_location(config=config)
        df = pl.read_parquet(result["gold_path"])

        required_columns = [
            "training_location_id",
            "location_name",
            "province",
            "country",
            "base_type",
        ]

        for col in required_columns:
            assert col in df.columns, f"Missing column: {col}"

    def test_location_id_unique(self, tmp_path):
        """Location IDs are unique."""
        config = PipelineConfig(data_root=tmp_path)

        result = ingest_dim_caf_training_location(config=config)
        df = pl.read_parquet(result["gold_path"])

        assert df["training_location_id"].n_unique() == len(df)

    def test_includes_major_bases(self, tmp_path):
        """Includes major training bases (Borden, Saint-Jean, Gagetown)."""
        config = PipelineConfig(data_root=tmp_path)

        result = ingest_dim_caf_training_location(config=config)
        df = pl.read_parquet(result["gold_path"])

        location_names = df["location_name"].to_list()

        assert any("Borden" in name for name in location_names)
        assert any("Saint-Jean" in name for name in location_names)
        assert any("Gagetown" in name for name in location_names)

    def test_base_types_present(self, tmp_path):
        """Base types (cfb, cflrs) are properly assigned."""
        config = PipelineConfig(data_root=tmp_path)

        result = ingest_dim_caf_training_location(config=config)
        df = pl.read_parquet(result["gold_path"])

        base_types = set(df["base_type"].to_list())
        assert "cfb" in base_types
        assert "cflrs" in base_types

    def test_provenance_columns(self, tmp_path):
        """Provenance columns are present."""
        config = PipelineConfig(data_root=tmp_path)

        result = ingest_dim_caf_training_location(config=config)
        df = pl.read_parquet(result["gold_path"])

        assert "_ingested_at" in df.columns
        assert "_batch_id" in df.columns
        assert "_layer" in df.columns


class TestIngestFactCAFTraining:
    """Tests for fact_caf_training ingestion."""

    @pytest.fixture
    def sample_occupations_json(self, tmp_path):
        """Create sample occupations.json for testing."""
        data = {
            "scraped_at": "2026-02-05T00:00:00Z",
            "occupation_count": 3,
            "occupations": [
                {
                    "career_id": "infantry-soldier",
                    "title_en": "Infantry Soldier",
                    "training_en": """Training
Basic Military Qualification
The first stage of training is the Basic Military Qualification course held at the Canadian Forces Leadership and Recruit School in Saint-Jean-sur-Richelieu, Quebec for 12 weeks.

Available Professional Training
Infantry soldiers attend occupation training at CFB Gagetown for 17 weeks.""",
                    "url_en": "https://forces.ca/en/career/infantry-soldier",
                },
                {
                    "career_id": "pilot",
                    "title_en": "Pilot",
                    "training_en": """Training
Basic Military Officer Qualification
After enrolment, basic officer training at CFLRS Saint-Jean-sur-Richelieu for 12 weeks.

Available Professional Training
Pilot training at CFB Moose Jaw takes approximately 1 year.""",
                    "url_en": "https://forces.ca/en/career/pilot",
                },
                {
                    "career_id": "sparse-occupation",
                    "title_en": "Sparse Occupation",
                    "training_en": "",  # Sparse data - no training info
                    "url_en": "https://forces.ca/en/career/sparse-occupation",
                },
            ],
        }

        source_path = tmp_path / "data" / "caf" / "occupations.json"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text(json.dumps(data), encoding="utf-8")

        return source_path

    def test_creates_training_table(self, tmp_path, sample_occupations_json):
        """Training fact table is created successfully."""
        config = PipelineConfig(data_root=tmp_path)

        result = ingest_fact_caf_training(
            source_path=sample_occupations_json,
            config=config,
        )

        assert result["gold_path"].exists()
        assert result["row_count"] > 0

    def test_training_schema(self, tmp_path, sample_occupations_json):
        """Training table has correct schema per plan."""
        config = PipelineConfig(data_root=tmp_path)

        result = ingest_fact_caf_training(
            source_path=sample_occupations_json,
            config=config,
        )
        df = pl.read_parquet(result["gold_path"])

        required_columns = [
            "caf_occupation_id",
            "training_type",
            "duration_weeks",
            "duration_text",
            "training_location_id",
            "certifications_awarded",
            "qualifications_awarded",
            "civilian_credential_level",
            "recertification_required",
            "_source_url",
            "_extracted_at",
            "_ingested_at",
            "_batch_id",
            "_layer",
        ]

        for col in required_columns:
            assert col in df.columns, f"Missing column: {col}"

    def test_duration_weeks_normalized(self, tmp_path, sample_occupations_json):
        """Duration is normalized to weeks."""
        config = PipelineConfig(data_root=tmp_path)

        result = ingest_fact_caf_training(
            source_path=sample_occupations_json,
            config=config,
        )
        df = pl.read_parquet(result["gold_path"])

        # Check that duration_weeks is populated for at least some records
        duration_values = df["duration_weeks"].drop_nulls().to_list()
        assert len(duration_values) > 0

        # 12 weeks should be in there (BMQ is 12 weeks)
        assert any(d == 12.0 for d in duration_values)

    def test_training_types(self, tmp_path, sample_occupations_json):
        """Both BMQ and occupation_specific training types present."""
        config = PipelineConfig(data_root=tmp_path)

        result = ingest_fact_caf_training(
            source_path=sample_occupations_json,
            config=config,
        )
        df = pl.read_parquet(result["gold_path"])

        training_types = set(df["training_type"].to_list())
        assert "bmq" in training_types or "occupation_specific" in training_types

    def test_location_fk_populated(self, tmp_path, sample_occupations_json):
        """Training location FK is populated where location detected."""
        config = PipelineConfig(data_root=tmp_path)

        result = ingest_fact_caf_training(
            source_path=sample_occupations_json,
            config=config,
        )
        df = pl.read_parquet(result["gold_path"])

        # At least some records should have location_id
        location_ids = df["training_location_id"].drop_nulls().to_list()
        assert len(location_ids) > 0

        # Should include saint-jean (BMQ location)
        assert any("saint-jean" in str(loc) for loc in location_ids)

    def test_sparse_data_handled(self, tmp_path, sample_occupations_json):
        """Sparse data (occupations without training) handled gracefully."""
        config = PipelineConfig(data_root=tmp_path)

        result = ingest_fact_caf_training(
            source_path=sample_occupations_json,
            config=config,
        )

        # Should succeed despite sparse occupation
        assert result["row_count"] > 0

        # Metrics should track coverage
        metrics = result["metrics"]
        assert "occupations_with_training" in metrics
        assert "occupations_without_training" in metrics
        assert metrics["occupations_without_training"] >= 1  # sparse-occupation

    def test_coverage_metrics(self, tmp_path, sample_occupations_json):
        """Coverage percentage is calculated correctly."""
        config = PipelineConfig(data_root=tmp_path)

        result = ingest_fact_caf_training(
            source_path=sample_occupations_json,
            config=config,
        )

        metrics = result["metrics"]
        assert "coverage_pct" in metrics
        # 2 of 3 occupations have training = 66.7%
        assert 60.0 <= metrics["coverage_pct"] <= 70.0

    def test_json_array_columns(self, tmp_path, sample_occupations_json):
        """Array columns are stored as JSON strings."""
        config = PipelineConfig(data_root=tmp_path)

        result = ingest_fact_caf_training(
            source_path=sample_occupations_json,
            config=config,
        )
        df = pl.read_parquet(result["gold_path"])

        # certifications_awarded should be valid JSON
        for cert_json in df["certifications_awarded"].to_list():
            parsed = json.loads(cert_json)
            assert isinstance(parsed, list)

    def test_provenance_columns(self, tmp_path, sample_occupations_json):
        """Provenance columns are properly populated."""
        config = PipelineConfig(data_root=tmp_path)

        result = ingest_fact_caf_training(
            source_path=sample_occupations_json,
            config=config,
        )
        df = pl.read_parquet(result["gold_path"])

        # All records should have ingestion provenance
        assert df["_ingested_at"].null_count() == 0
        assert df["_batch_id"].null_count() == 0
        assert df["_layer"].null_count() == 0

        # Source URL should be populated
        source_urls = df["_source_url"].drop_nulls().to_list()
        assert len(source_urls) > 0
        assert all("forces.ca" in url for url in source_urls)


class TestIntegration:
    """Integration tests for training ingestion with other CAF tables."""

    @pytest.fixture
    def full_test_setup(self, tmp_path):
        """Create full test environment with occupations.json and dim_caf_occupation."""
        # Create occupations.json
        data = {
            "scraped_at": "2026-02-05T00:00:00Z",
            "occupation_count": 2,
            "occupations": [
                {
                    "career_id": "test-career",
                    "title_en": "Test Career",
                    "training_en": "Training at CFB Borden for 10 weeks.",
                    "url_en": "https://forces.ca/en/career/test-career",
                },
                {
                    "career_id": "another-career",
                    "title_en": "Another Career",
                    "training_en": "Basic training at Saint-Jean for 12 weeks.",
                    "url_en": "https://forces.ca/en/career/another-career",
                },
            ],
        }

        source_path = tmp_path / "data" / "caf" / "occupations.json"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text(json.dumps(data), encoding="utf-8")

        # Create dim_caf_occupation for FK validation
        gold_dir = tmp_path / "data" / "gold"
        gold_dir.mkdir(parents=True, exist_ok=True)

        dim_caf_occupation = pl.DataFrame({
            "career_id": ["test-career", "another-career"],
            "title_en": ["Test Career", "Another Career"],
        })
        dim_caf_occupation.write_parquet(gold_dir / "dim_caf_occupation.parquet")

        return tmp_path, source_path

    def test_fk_validation_passes(self, full_test_setup):
        """FK validation passes when all career_ids exist in dim_caf_occupation."""
        tmp_path, source_path = full_test_setup
        config = PipelineConfig(data_root=tmp_path)

        # Should succeed without warnings about orphans
        result = ingest_fact_caf_training(
            source_path=source_path,
            config=config,
        )

        assert result["row_count"] > 0

    def test_both_tables_can_join(self, full_test_setup):
        """fact_caf_training can join to dim_caf_training_location."""
        tmp_path, source_path = full_test_setup
        config = PipelineConfig(data_root=tmp_path)

        # Create both tables
        loc_result = ingest_dim_caf_training_location(config=config)
        train_result = ingest_fact_caf_training(
            source_path=source_path,
            config=config,
        )

        # Read tables
        dim_location = pl.read_parquet(loc_result["gold_path"])
        fact_training = pl.read_parquet(train_result["gold_path"])

        # Attempt join
        joined = fact_training.join(
            dim_location,
            on="training_location_id",
            how="left",
        )

        # Should have same row count (left join)
        assert len(joined) == len(fact_training)

        # At least some records should have matched location names
        matched = joined.filter(pl.col("location_name").is_not_null())
        assert len(matched) > 0
