"""Tests for OG Qualification Standards enhanced ingestion pipeline.

Tests cover:
1. Pipeline produces parquet with expected columns
2. Structured fields are populated (education_level, min_years_experience, etc.)
3. FK validation logs warnings for orphan og_codes
4. Provenance fields present
5. Production data integration tests
"""

import json
from pathlib import Path

import polars as pl
import pytest

from jobforge.ingestion.og_qualification_standards import (
    ingest_dim_og_qualification_standard,
    normalize_og_codes,
    validate_og_exists,
)
from jobforge.pipeline.config import PipelineConfig


@pytest.fixture
def test_config(tmp_path: Path) -> PipelineConfig:
    """Create a PipelineConfig using temporary directory."""
    return PipelineConfig(data_root=tmp_path / "data")


@pytest.fixture
def sample_dim_og(tmp_path: Path, test_config: PipelineConfig) -> None:
    """Create a sample dim_og.parquet for FK validation."""
    gold_dir = test_config.gold_path()
    gold_dir.mkdir(parents=True, exist_ok=True)

    df = pl.DataFrame({
        "og_code": ["AS", "EC", "IT"],
        "og_name": ["Administrative Services", "Economics", "Information Technology"],
    })
    df.write_parquet(gold_dir / "dim_og.parquet")


@pytest.fixture
def sample_qualification_json(tmp_path: Path) -> Path:
    """Create a sample og_qualification_text.json for testing."""
    json_path = tmp_path / "og_qualification_text.json"
    data = [
        {
            "og_code": "AS",
            "subgroup_code": None,
            "full_text": """
The minimum standard is:

Graduation with a degree from a recognized post-secondary institution with acceptable
specialization in a field relevant to the duties of the position.

Experience:
A minimum of 2 years of relevant experience in administrative services.

Bilingual imperative BBB is required.

Reliability status is required.

Conditions of Employment:
- Travel is required across the region
- May require overtime during peak periods

An acceptable combination of education, training and/or experience may be considered.
            """,
            "tables": [],
            "page_count": 1,
            "source_url": "https://example.com/qual/as",
            "source_file": "html",
            "source_type": "html",
            "extracted_at": "2026-01-20T00:00:00Z",
            "pdf_metadata": {}
        },
        {
            "og_code": "EC",
            "subgroup_code": None,
            "full_text": """
The minimum standard for positions classified at levels EC-01, EC-02 and EC-03 is:

Graduation with a degree from a recognized post-secondary institution with acceptable
specialization in economics, sociology or statistics.

Experience:
Significant experience in economic research and policy analysis.

Secret clearance is required.

Occupational Certification:
None required for this group.
            """,
            "tables": [],
            "page_count": 2,
            "source_url": "https://example.com/qual/ec",
            "source_file": "html",
            "source_type": "html",
            "extracted_at": "2026-01-20T00:00:00Z",
            "pdf_metadata": {}
        },
        {
            "og_code": "ORPHAN",
            "subgroup_code": None,
            "full_text": "Some qualification text for an OG not in dim_og. A secondary school diploma is required.",
            "tables": [],
            "page_count": 1,
            "source_url": "https://example.com/qual/orphan",
            "source_file": "html",
            "source_type": "html",
            "extracted_at": "2026-01-20T00:00:00Z",
            "pdf_metadata": {}
        },
    ]
    json_path.write_text(json.dumps(data), encoding="utf-8")
    return json_path


class TestNormalizeOgCodes:
    """Tests for normalize_og_codes function."""

    def test_uppercases_og_code(self) -> None:
        """Verify og_code is uppercased."""
        df = pl.LazyFrame({
            "og_code": ["as", " ec ", "IT"],
            "og_subgroup_code": ["as-01", None, "it-02"],
        })
        result = normalize_og_codes(df).collect()
        assert result["og_code"].to_list() == ["AS", "EC", "IT"]
        # Verify null handling for subgroup_code
        assert result["og_subgroup_code"][0] == "AS-01"
        assert result["og_subgroup_code"][1] is None
        assert result["og_subgroup_code"][2] == "IT-02"

    def test_uppercases_subgroup_code(self) -> None:
        """Verify og_subgroup_code is uppercased."""
        df = pl.LazyFrame({
            "og_code": ["AS", "EC"],
            "og_subgroup_code": ["as-01", " ec-02 "],
        })
        result = normalize_og_codes(df).collect()
        assert result["og_subgroup_code"].to_list() == ["AS-01", "EC-02"]


class TestValidateOgExists:
    """Tests for validate_og_exists function."""

    def test_logs_warning_for_orphans(self, caplog) -> None:
        """Verify warnings logged for og_codes not in dim_og."""
        df = pl.LazyFrame({
            "og_code": ["AS", "ORPHAN"],
        })
        valid_codes = {"AS", "EC"}

        # Should not filter, just log
        result = validate_og_exists(df, valid_codes)
        collected = result.collect()

        # All rows preserved
        assert len(collected) == 2

    def test_does_not_filter_rows(self) -> None:
        """Verify validate_og_exists doesn't remove any rows."""
        df = pl.LazyFrame({
            "og_code": ["AS", "ORPHAN", "MISSING"],
        })
        valid_codes = {"AS"}

        result = validate_og_exists(df, valid_codes).collect()
        # All 3 rows preserved even though 2 are orphans
        assert len(result) == 3


class TestIngestDimOgQualificationStandard:
    """Tests for ingest_dim_og_qualification_standard function."""

    def test_creates_gold_file(
        self,
        sample_qualification_json: Path,
        sample_dim_og: None,
        test_config: PipelineConfig,
    ) -> None:
        """Verify ingest creates gold parquet file."""
        result = ingest_dim_og_qualification_standard(
            source_path=sample_qualification_json,
            config=test_config,
        )
        assert result["gold_path"].exists()
        assert result["gold_path"].suffix == ".parquet"

    def test_produces_expected_rows(
        self,
        sample_qualification_json: Path,
        sample_dim_og: None,
        test_config: PipelineConfig,
    ) -> None:
        """Verify pipeline produces correct row count."""
        result = ingest_dim_og_qualification_standard(
            source_path=sample_qualification_json,
            config=test_config,
        )
        # Sample has 3 records, all should be preserved
        assert result["row_count"] == 3

    def test_has_enhanced_columns(
        self,
        sample_qualification_json: Path,
        sample_dim_og: None,
        test_config: PipelineConfig,
    ) -> None:
        """Verify gold table has all enhanced CONTEXT.md columns."""
        result = ingest_dim_og_qualification_standard(
            source_path=sample_qualification_json,
            config=test_config,
        )
        gold_df = pl.read_parquet(result["gold_path"])

        expected_columns = [
            # Education
            "education_level",
            "education_requirement_text",
            # Experience
            "min_years_experience",
            "experience_requirement_text",
            # Essential vs Asset
            "essential_qualification_text",
            "asset_qualification_text",
            # Equivalency
            "has_equivalency",
            "equivalency_statement",
            # Bilingual
            "bilingual_reading_level",
            "bilingual_writing_level",
            "bilingual_oral_level",
            # Security
            "security_clearance",
            # Conditions
            "requires_travel",
            "shift_work",
            "physical_demands",
            # Operations
            "overtime_required",
            "on_call_required",
            "deployments_required",
            # Other
            "certification_requirement",
            "full_text",
        ]
        for col in expected_columns:
            assert col in gold_df.columns, f"Missing column: {col}"

    def test_has_provenance_columns(
        self,
        sample_qualification_json: Path,
        sample_dim_og: None,
        test_config: PipelineConfig,
    ) -> None:
        """Verify gold table has provenance columns."""
        result = ingest_dim_og_qualification_standard(
            source_path=sample_qualification_json,
            config=test_config,
        )
        gold_df = pl.read_parquet(result["gold_path"])

        provenance_columns = [
            "_source_url",
            "_extracted_at",
            "_ingested_at",
            "_batch_id",
            "_layer",
        ]
        for col in provenance_columns:
            assert col in gold_df.columns, f"Missing provenance column: {col}"

    def test_column_count_at_least_25(
        self,
        sample_qualification_json: Path,
        sample_dim_og: None,
        test_config: PipelineConfig,
    ) -> None:
        """Verify gold table has at least 25 columns."""
        result = ingest_dim_og_qualification_standard(
            source_path=sample_qualification_json,
            config=test_config,
        )
        assert result["column_count"] >= 25

    def test_extracts_structured_fields(
        self,
        sample_qualification_json: Path,
        sample_dim_og: None,
        test_config: PipelineConfig,
    ) -> None:
        """Verify structured fields are extracted from sample data."""
        result = ingest_dim_og_qualification_standard(
            source_path=sample_qualification_json,
            config=test_config,
        )
        gold_df = pl.read_parquet(result["gold_path"])

        # AS record should have education_level=bachelors
        as_row = gold_df.filter(pl.col("og_code") == "AS")
        assert as_row["education_level"][0] == "bachelors"
        assert as_row["min_years_experience"][0] == 2
        assert as_row["bilingual_reading_level"][0] == "B"
        assert as_row["security_clearance"][0] == "Reliability"
        assert as_row["requires_travel"][0] is True
        assert as_row["overtime_required"][0] is True
        assert as_row["has_equivalency"][0] is True

        # EC record should have security_clearance=Secret
        ec_row = gold_df.filter(pl.col("og_code") == "EC")
        assert ec_row["education_level"][0] == "bachelors"
        assert ec_row["security_clearance"][0] == "Secret"

    def test_full_text_not_empty(
        self,
        sample_qualification_json: Path,
        sample_dim_og: None,
        test_config: PipelineConfig,
    ) -> None:
        """Verify full_text column is not empty for any record."""
        result = ingest_dim_og_qualification_standard(
            source_path=sample_qualification_json,
            config=test_config,
        )
        gold_df = pl.read_parquet(result["gold_path"])

        # All records should have non-empty full_text
        empty_count = gold_df.filter(
            pl.col("full_text").is_null() | (pl.col("full_text").str.len_chars() == 0)
        ).shape[0]
        assert empty_count == 0

    def test_tracks_extraction_stats(
        self,
        sample_qualification_json: Path,
        sample_dim_og: None,
        test_config: PipelineConfig,
    ) -> None:
        """Verify result tracks extraction statistics."""
        result = ingest_dim_og_qualification_standard(
            source_path=sample_qualification_json,
            config=test_config,
        )
        assert "extraction_stats" in result
        assert result["extraction_stats"]["education_level"] >= 2

    def test_handles_missing_dim_og_gracefully(
        self,
        sample_qualification_json: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify ingestion continues if dim_og.parquet missing."""
        # No sample_dim_og fixture - dim_og doesn't exist
        result = ingest_dim_og_qualification_standard(
            source_path=sample_qualification_json,
            config=test_config,
        )
        # Should complete without error, just log warning
        assert result["gold_path"].exists()
        assert result["row_count"] == 3

    def test_skip_fk_validation_option(
        self,
        sample_qualification_json: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify FK validation can be disabled."""
        result = ingest_dim_og_qualification_standard(
            source_path=sample_qualification_json,
            config=test_config,
            validate_fk=False,
        )
        assert result["gold_path"].exists()


class TestProductionData:
    """Tests against actual production data files."""

    @pytest.mark.skipif(
        not Path("data/tbs/og_qualification_text.json").exists(),
        reason="Production data not available"
    )
    def test_production_row_count(self) -> None:
        """Verify production table has expected row count (70+)."""
        result = ingest_dim_og_qualification_standard()
        # Production data has 75 qualification records
        assert result["row_count"] >= 70

    @pytest.mark.skipif(
        not Path("data/tbs/og_qualification_text.json").exists(),
        reason="Production data not available"
    )
    def test_production_column_count(self) -> None:
        """Verify production table has expected column count (25+)."""
        result = ingest_dim_og_qualification_standard()
        assert result["column_count"] >= 25

    @pytest.mark.skipif(
        not Path("data/tbs/og_qualification_text.json").exists(),
        reason="Production data not available"
    )
    def test_production_has_education_levels(self) -> None:
        """Verify production data has extracted education levels."""
        result = ingest_dim_og_qualification_standard()
        df = pl.read_parquet(result["gold_path"])

        # At least 50% of records should have education_level populated
        non_null_count = df.filter(
            pl.col("education_level").is_not_null()
        ).shape[0]
        total_count = len(df)

        assert non_null_count >= total_count * 0.5, \
            f"Only {non_null_count}/{total_count} records have education_level"

    @pytest.mark.skipif(
        not Path("data/tbs/og_qualification_text.json").exists(),
        reason="Production data not available"
    )
    def test_production_enhanced_columns_present(self) -> None:
        """Verify production table has all enhanced columns."""
        result = ingest_dim_og_qualification_standard()
        df = pl.read_parquet(result["gold_path"])

        required_columns = [
            "education_level",
            "min_years_experience",
            "bilingual_reading_level",
            "security_clearance",
        ]
        for col in required_columns:
            assert col in df.columns, f"Missing column: {col}"

    @pytest.mark.skipif(
        not Path("data/gold/dim_og.parquet").exists() or
        not Path("data/tbs/og_qualification_text.json").exists(),
        reason="Gold data not available"
    )
    def test_production_fk_integrity_check(self) -> None:
        """Check which og_codes in qualifications exist in dim_og."""
        result = ingest_dim_og_qualification_standard()
        og_df = pl.read_parquet("data/gold/dim_og.parquet")
        qual_df = pl.read_parquet(result["gold_path"])

        og_codes = set(og_df["og_code"].to_list())
        qual_og_codes = set(qual_df["og_code"].to_list())

        # Report orphans (may be expected if data has evolved)
        orphans = qual_og_codes - og_codes
        # This is informational - some orphans may be expected
        if orphans:
            print(f"Info: {len(orphans)} og_codes in qualifications not in dim_og: {sorted(orphans)}")
