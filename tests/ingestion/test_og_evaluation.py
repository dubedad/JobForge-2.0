"""Tests for OG Job Evaluation Standards ingestion pipeline."""

import json
import tempfile
from pathlib import Path

import polars as pl
import pytest

from jobforge.ingestion.og_evaluation import (
    ingest_dim_og_job_evaluation_standard,
    normalize_og_codes,
    select_gold_columns,
    validate_og_exists,
)


class TestNormalizeOgCodes:
    """Tests for OG code normalization."""

    def test_uppercase_og_code(self):
        """normalize_og_codes converts og_code to uppercase."""
        df = pl.DataFrame(
            {
                "og_code": ["it", "ec", "fb"],
                "og_subgroup_code": [None, None, None],
            },
            schema={"og_code": pl.Utf8, "og_subgroup_code": pl.Utf8},
        ).lazy()

        result = normalize_og_codes(df).collect()

        assert result["og_code"].to_list() == ["IT", "EC", "FB"]

    def test_strip_whitespace(self):
        """normalize_og_codes strips whitespace from codes."""
        df = pl.DataFrame(
            {
                "og_code": [" IT ", "EC\t", "\nFB"],
                "og_subgroup_code": [None, None, None],
            },
            schema={"og_code": pl.Utf8, "og_subgroup_code": pl.Utf8},
        ).lazy()

        result = normalize_og_codes(df).collect()

        assert result["og_code"].to_list() == ["IT", "EC", "FB"]

    def test_handle_null_subgroup(self):
        """normalize_og_codes handles null subgroup codes."""
        df = pl.DataFrame(
            {
                "og_code": ["IT", "EC"],
                "og_subgroup_code": [None, "ec-02"],
            },
            schema={"og_code": pl.Utf8, "og_subgroup_code": pl.Utf8},
        ).lazy()

        result = normalize_og_codes(df).collect()

        assert result["og_subgroup_code"].to_list() == [None, "EC-02"]


class TestValidateOgExists:
    """Tests for FK validation against dim_og."""

    def test_logs_warning_for_orphan_codes(self):
        """validate_og_exists logs warning for codes not in dim_og."""
        df = pl.DataFrame(
            {"og_code": ["IT", "UNKNOWN", "EC"]},
            schema={"og_code": pl.Utf8},
        ).lazy()

        valid_codes = {"IT", "EC", "FB"}
        result = validate_og_exists(df, valid_codes).collect()

        # Should not filter rows (soft validation)
        assert len(result) == 3

    def test_preserves_all_rows(self):
        """validate_og_exists preserves all rows (soft validation)."""
        df = pl.DataFrame(
            {"og_code": ["INVALID1", "INVALID2"]},
            schema={"og_code": pl.Utf8},
        ).lazy()

        valid_codes = {"IT", "EC"}
        result = validate_og_exists(df, valid_codes).collect()

        # All rows preserved
        assert len(result) == 2


class TestSelectGoldColumns:
    """Tests for gold column selection."""

    def test_selects_expected_columns(self):
        """select_gold_columns returns correct column set."""
        df = pl.DataFrame({
            "og_code": ["IT"],
            "og_subgroup_code": [None],
            "standard_name": ["IT Standard"],
            "standard_type": ["classification_standard"],
            "factor_name": [None],
            "factor_description": [None],
            "factor_points": [None],
            "factor_percentage": [None],
            "factor_level": [None],
            "level_points": [None],
            "level_description": [None],
            "full_text": ["Content"],
            "effective_date": [None],
            "version": [None],
            "_source_url": ["https://example.com"],
            "_scraped_at": ["2026-02-05T10:00:00Z"],
            "_ingested_at": ["2026-02-05T11:00:00Z"],
            "_batch_id": ["batch123"],
            "_layer": ["gold"],
            "extra_column": ["should_be_dropped"],
        }).lazy()

        result = select_gold_columns(df).collect()

        assert "extra_column" not in result.columns
        assert "og_code" in result.columns
        assert "_source_url" in result.columns
        assert len(result.columns) == 19


class TestIngestDimOgJobEvaluationStandard:
    """Tests for the full ingestion pipeline."""

    def test_ingest_creates_parquet_file(self, tmp_path):
        """ingest_dim_og_job_evaluation_standard creates gold parquet file."""
        # Create test source data
        source_data = [
            {
                "og_code": "IT",
                "og_subgroup_code": None,
                "standard_name": "IT Job Evaluation Standard",
                "standard_type": "classification_standard",
                "factor_name": None,
                "factor_description": None,
                "factor_points": None,
                "factor_percentage": None,
                "factor_level": None,
                "level_points": None,
                "level_description": None,
                "full_text": "Standard content here",
                "effective_date": "2020-01-01",
                "version": "1.0",
                "source_url": "https://example.com/it",
                "scraped_at": "2026-02-05T10:00:00Z",
            },
            {
                "og_code": "IT",
                "og_subgroup_code": None,
                "standard_name": "IT Job Evaluation Standard",
                "standard_type": "evaluation_factor",
                "factor_name": "Technical Knowledge",
                "factor_description": "Technical skills required",
                "factor_points": 300,
                "factor_percentage": 30.0,
                "factor_level": None,
                "level_points": None,
                "level_description": None,
                "full_text": "Technical Knowledge: 30%, 300 points",
                "effective_date": "2020-01-01",
                "version": "1.0",
                "source_url": "https://example.com/it",
                "scraped_at": "2026-02-05T10:00:00Z",
            },
        ]

        source_path = tmp_path / "og_evaluation_standards.json"
        with open(source_path, "w") as f:
            json.dump(source_data, f)

        # Create mock config
        from jobforge.pipeline.config import PipelineConfig

        config = PipelineConfig(data_root=tmp_path)
        config.gold_path().mkdir(parents=True, exist_ok=True)

        result = ingest_dim_og_job_evaluation_standard(
            source_path=source_path,
            config=config,
            validate_fk=False,  # Skip FK validation for test
        )

        assert result["gold_path"].exists()
        assert result["row_count"] == 2
        assert result["classification_standards"] == 1
        assert result["evaluation_factors"] == 1

    def test_ingest_produces_expected_schema(self, tmp_path):
        """Ingested table has expected columns."""
        source_data = [
            {
                "og_code": "EC",
                "standard_name": "EC Standard",
                "standard_type": "evaluation_factor",
                "factor_name": "Analysis",
                "factor_points": 200,
                "full_text": "Analysis factor",
                "source_url": "https://example.com",
                "scraped_at": "2026-02-05T10:00:00Z",
            },
        ]

        source_path = tmp_path / "og_evaluation_standards.json"
        with open(source_path, "w") as f:
            json.dump(source_data, f)

        from jobforge.pipeline.config import PipelineConfig

        config = PipelineConfig(data_root=tmp_path)
        config.gold_path().mkdir(parents=True, exist_ok=True)

        result = ingest_dim_og_job_evaluation_standard(
            source_path=source_path, config=config, validate_fk=False
        )

        df = pl.read_parquet(result["gold_path"])

        expected_columns = [
            "og_code",
            "og_subgroup_code",
            "standard_name",
            "standard_type",
            "factor_name",
            "factor_description",
            "factor_points",
            "factor_percentage",
            "factor_level",
            "level_points",
            "level_description",
            "full_text",
            "effective_date",
            "version",
            "_source_url",
            "_scraped_at",
            "_ingested_at",
            "_batch_id",
            "_layer",
        ]
        for col in expected_columns:
            assert col in df.columns, f"Missing column: {col}"

    def test_ingest_has_provenance_columns(self, tmp_path):
        """Ingested table has provenance columns populated."""
        source_data = [
            {
                "og_code": "FB",
                "standard_name": "FB Standard",
                "standard_type": "classification_standard",
                "full_text": "Content",
                "source_url": "https://example.com/fb",
                "scraped_at": "2026-02-05T10:00:00Z",
            },
        ]

        source_path = tmp_path / "og_evaluation_standards.json"
        with open(source_path, "w") as f:
            json.dump(source_data, f)

        from jobforge.pipeline.config import PipelineConfig

        config = PipelineConfig(data_root=tmp_path)
        config.gold_path().mkdir(parents=True, exist_ok=True)

        result = ingest_dim_og_job_evaluation_standard(
            source_path=source_path, config=config, validate_fk=False
        )

        df = pl.read_parquet(result["gold_path"])

        # Check provenance columns are populated
        assert df["_source_url"][0] == "https://example.com/fb"
        assert df["_scraped_at"][0] == "2026-02-05T10:00:00Z"
        assert df["_ingested_at"][0] is not None
        assert df["_batch_id"][0] is not None
        assert df["_layer"][0] == "gold"

    def test_ingest_handles_empty_source(self, tmp_path):
        """ingest handles empty source data gracefully."""
        source_data = []

        source_path = tmp_path / "og_evaluation_standards.json"
        with open(source_path, "w") as f:
            json.dump(source_data, f)

        from jobforge.pipeline.config import PipelineConfig

        config = PipelineConfig(data_root=tmp_path)
        config.gold_path().mkdir(parents=True, exist_ok=True)

        result = ingest_dim_og_job_evaluation_standard(
            source_path=source_path, config=config, validate_fk=False
        )

        assert result["row_count"] == 0

    def test_ingest_normalizes_og_codes(self, tmp_path):
        """Ingested data has normalized OG codes."""
        source_data = [
            {
                "og_code": " it ",
                "standard_name": "IT Standard",
                "standard_type": "classification_standard",
                "full_text": "Content",
                "source_url": "https://example.com",
                "scraped_at": "2026-02-05T10:00:00Z",
            },
        ]

        source_path = tmp_path / "og_evaluation_standards.json"
        with open(source_path, "w") as f:
            json.dump(source_data, f)

        from jobforge.pipeline.config import PipelineConfig

        config = PipelineConfig(data_root=tmp_path)
        config.gold_path().mkdir(parents=True, exist_ok=True)

        result = ingest_dim_og_job_evaluation_standard(
            source_path=source_path, config=config, validate_fk=False
        )

        df = pl.read_parquet(result["gold_path"])
        assert df["og_code"][0] == "IT"


class TestIntegrationWithRealData:
    """Integration tests using real scraped data if available."""

    def test_ingest_from_real_source(self):
        """Integration test with real og_evaluation_standards.json."""
        source_path = Path("data/tbs/og_evaluation_standards.json")
        if not source_path.exists():
            pytest.skip("Source file not available")

        result = ingest_dim_og_job_evaluation_standard(validate_fk=False)

        assert result["gold_path"].exists()
        assert result["row_count"] > 0

        # Should have both classification standards and evaluation factors
        assert result["classification_standards"] > 0
        assert result["evaluation_factors"] > 0

    def test_real_data_has_expected_og_codes(self):
        """Real data should contain expected OG codes."""
        gold_path = Path("data/gold/dim_og_job_evaluation_standard.parquet")
        if not gold_path.exists():
            pytest.skip("Gold file not available")

        df = pl.read_parquet(gold_path)
        og_codes = df["og_code"].unique().to_list()

        # Should have IT (Information Technology) evaluation standard
        assert "IT" in og_codes

        # Should have multiple OG codes
        assert len(og_codes) >= 5

    def test_real_data_has_factor_points(self):
        """Real evaluation factors should have point values."""
        gold_path = Path("data/gold/dim_og_job_evaluation_standard.parquet")
        if not gold_path.exists():
            pytest.skip("Gold file not available")

        df = pl.read_parquet(gold_path)

        # Filter to evaluation factors
        factors = df.filter(pl.col("standard_type") == "evaluation_factor")

        # Should have some factors with points
        factors_with_points = factors.filter(pl.col("factor_points").is_not_null())
        assert len(factors_with_points) > 0

    def test_real_data_has_source_urls(self):
        """Real data should have per-record source URLs."""
        gold_path = Path("data/gold/dim_og_job_evaluation_standard.parquet")
        if not gold_path.exists():
            pytest.skip("Gold file not available")

        df = pl.read_parquet(gold_path)

        # All records should have source URLs
        assert df.filter(pl.col("_source_url").is_null()).height == 0
        assert df.filter(pl.col("_source_url") == "").height == 0

        # URLs should be TBS URLs
        sample_url = df["_source_url"][0]
        assert "canada.ca" in sample_url
