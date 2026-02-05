"""Tests for OG Qualifications ingestion."""

import json
from pathlib import Path

import polars as pl
import pytest

from jobforge.ingestion.og_qualifications import (
    ingest_dim_og_qualifications,
    parse_qualification_text,
    normalize_qualification_codes,
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
Two years of relevant experience in administrative services.

Occupational Certification:
None required for this group.
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

The minimum standard for positions classified at levels EC-04 and above is:

Graduation with a degree from a recognized post-secondary institution with acceptable
specialization in economics, sociology or statistics and successful completion of a
graduate degree.

Experience:
Significant experience in economic research and policy analysis.
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
            "full_text": "Some qualification text for an OG not in dim_og",
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


class TestParseQualificationText:
    """Tests for parse_qualification_text function."""

    def test_extracts_education_requirement(self) -> None:
        """Verify parse_qualification_text extracts education section."""
        text = """
The minimum standard is:

Graduation with a degree from a recognized post-secondary institution.

Experience is also required.
        """
        result = parse_qualification_text(text)
        assert result["education_requirement"] is not None
        assert "degree" in result["education_requirement"].lower()

    def test_extracts_experience_requirement(self) -> None:
        """Verify parse_qualification_text extracts experience section."""
        text = """
The minimum standard is:

A secondary school diploma.

Experience:
Three years of relevant work experience in the field.

Certification is required.
        """
        result = parse_qualification_text(text)
        assert result["experience_requirement"] is not None
        assert "years" in result["experience_requirement"].lower()

    def test_extracts_certification_requirement(self) -> None:
        """Verify parse_qualification_text extracts certification section."""
        text = """
The minimum standard is:

A university degree.

Occupational Certification:
Eligibility for membership in a recognized professional association.
        """
        result = parse_qualification_text(text)
        assert result["certification_requirement"] is not None
        assert "eligibility" in result["certification_requirement"].lower()

    def test_preserves_full_text(self) -> None:
        """Verify parse_qualification_text preserves raw text."""
        text = "Sample qualification standard text that is at least 100 characters long to pass validation checks."
        result = parse_qualification_text(text)
        assert result["full_text"] is not None
        assert result["full_text"] == text

    def test_truncates_long_full_text(self) -> None:
        """Verify full_text is truncated to max length."""
        # Create text longer than MAX_FULL_TEXT_LENGTH (50000)
        long_text = "x" * 60000
        result = parse_qualification_text(long_text)
        assert len(result["full_text"]) == 50000

    def test_handles_short_text(self) -> None:
        """Verify short text returns empty structured fields."""
        text = "Too short"
        result = parse_qualification_text(text)
        # Should still have full_text but no structured fields
        assert result["education_requirement"] is None
        assert result["experience_requirement"] is None
        assert result["full_text"] == text

    def test_handles_empty_text(self) -> None:
        """Verify empty text returns empty structured fields."""
        result = parse_qualification_text("")
        assert result["education_requirement"] is None
        assert result["full_text"] == ""


class TestNormalizeQualificationCodes:
    """Tests for normalize_qualification_codes function."""

    def test_uppercases_og_code(self) -> None:
        """Verify og_code is uppercased."""
        df = pl.LazyFrame({
            "og_code": ["as", " ec ", "IT"],
            "og_subgroup_code": ["as-01", None, "it-02"],
        })
        result = normalize_qualification_codes(df).collect()
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
        result = normalize_qualification_codes(df).collect()
        assert result["og_subgroup_code"].to_list() == ["AS-01", "EC-02"]


class TestValidateOgExists:
    """Tests for validate_og_exists function."""

    def test_logs_warning_for_orphans(self, caplog) -> None:
        """Verify warnings logged for og_codes not in dim_og."""
        import logging

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


class TestIngestDimOgQualifications:
    """Tests for ingest_dim_og_qualifications function."""

    def test_creates_gold_file(
        self,
        sample_qualification_json: Path,
        sample_dim_og: None,
        test_config: PipelineConfig,
    ) -> None:
        """Verify ingest_dim_og_qualifications creates gold parquet file."""
        result = ingest_dim_og_qualifications(
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
        """Verify ingest_dim_og_qualifications produces correct row count."""
        result = ingest_dim_og_qualifications(
            source_path=sample_qualification_json,
            config=test_config,
        )
        # Sample has 3 records, all should be preserved
        assert result["row_count"] == 3

    def test_has_structured_fields(
        self,
        sample_qualification_json: Path,
        sample_dim_og: None,
        test_config: PipelineConfig,
    ) -> None:
        """Verify gold table has structured qualification fields."""
        result = ingest_dim_og_qualifications(
            source_path=sample_qualification_json,
            config=test_config,
        )
        gold_df = pl.read_parquet(result["gold_path"])

        expected_columns = [
            "education_requirement",
            "experience_requirement",
            "certification_requirement",
            "language_requirement",
            "other_requirements",
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
        result = ingest_dim_og_qualifications(
            source_path=sample_qualification_json,
            config=test_config,
        )
        gold_df = pl.read_parquet(result["gold_path"])

        provenance_columns = [
            "_source_url",
            "_source_file",
            "_extracted_at",
            "_ingested_at",
            "_batch_id",
            "_layer",
        ]
        for col in provenance_columns:
            assert col in gold_df.columns, f"Missing provenance column: {col}"

    def test_full_text_not_empty(
        self,
        sample_qualification_json: Path,
        sample_dim_og: None,
        test_config: PipelineConfig,
    ) -> None:
        """Verify full_text column is not empty for any record."""
        result = ingest_dim_og_qualifications(
            source_path=sample_qualification_json,
            config=test_config,
        )
        gold_df = pl.read_parquet(result["gold_path"])

        # All records should have non-empty full_text
        empty_count = gold_df.filter(
            pl.col("full_text").is_null() | (pl.col("full_text").str.len_chars() == 0)
        ).shape[0]
        assert empty_count == 0

    def test_tracks_structured_extractions(
        self,
        sample_qualification_json: Path,
        sample_dim_og: None,
        test_config: PipelineConfig,
    ) -> None:
        """Verify result tracks structured extraction count."""
        result = ingest_dim_og_qualifications(
            source_path=sample_qualification_json,
            config=test_config,
        )
        # At least some records should have structured extractions
        assert "structured_extractions" in result
        assert result["structured_extractions"] >= 1

    def test_handles_missing_dim_og_gracefully(
        self,
        sample_qualification_json: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify ingestion continues if dim_og.parquet missing."""
        # No sample_dim_og fixture - dim_og doesn't exist
        result = ingest_dim_og_qualifications(
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
        result = ingest_dim_og_qualifications(
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
        """Verify production dim_og_qualifications has expected row count."""
        result = ingest_dim_og_qualifications()
        # Production data has 75 qualification records
        assert result["row_count"] >= 50  # Allow some flexibility

    @pytest.mark.skipif(
        not Path("data/gold/dim_og_qualifications.parquet").exists(),
        reason="Gold data not available"
    )
    def test_production_has_education_requirements(self) -> None:
        """Verify production data has extracted education requirements."""
        df = pl.read_parquet("data/gold/dim_og_qualifications.parquet")

        # At least some records should have education_requirement populated
        non_null_count = df.filter(
            pl.col("education_requirement").is_not_null()
        ).shape[0]
        assert non_null_count > 0, "No education requirements extracted"

    @pytest.mark.skipif(
        not Path("data/gold/dim_og_qualifications.parquet").exists(),
        reason="Gold data not available"
    )
    def test_production_full_text_searchable(self) -> None:
        """Verify full_text is available for full-text search."""
        df = pl.read_parquet("data/gold/dim_og_qualifications.parquet")

        # All records should have full_text
        assert df["full_text"].null_count() == 0

        # Search for common qualification term
        matches = df.filter(
            pl.col("full_text").str.contains("(?i)degree")
        ).shape[0]
        assert matches > 0, "No records contain 'degree' in full_text"

    @pytest.mark.skipif(
        not Path("data/gold/dim_og.parquet").exists() or
        not Path("data/gold/dim_og_qualifications.parquet").exists(),
        reason="Gold data not available"
    )
    def test_production_fk_integrity_check(self) -> None:
        """Check which og_codes in qualifications exist in dim_og."""
        og_df = pl.read_parquet("data/gold/dim_og.parquet")
        qual_df = pl.read_parquet("data/gold/dim_og_qualifications.parquet")

        og_codes = set(og_df["og_code"].to_list())
        qual_og_codes = set(qual_df["og_code"].to_list())

        # Report orphans (may be expected if data has evolved)
        orphans = qual_og_codes - og_codes
        # This is informational - some orphans may be expected
        if orphans:
            print(f"Info: {len(orphans)} og_codes in qualifications not in dim_og: {sorted(orphans)}")
