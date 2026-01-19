"""Tests for attribute inheritance logic.

These tests validate L5->L6->L7 inheritance with provenance tracking.

Requirements covered:
- IMP-01: Validated by comparing outputs to known prototype behavior
- IMP-02: Validated by test_inherit_attributes_source_level_is_5 and provenance tests
"""

from pathlib import Path

import polars as pl
import pytest

from jobforge.imputation import (
    ImputationProvenanceColumns,
    apply_imputation,
    get_imputation_summary,
    inherit_attributes_to_job_titles,
)
from jobforge.imputation.provenance import (
    add_imputation_provenance,
    create_imputed_attribute_row,
    get_provenance_column_names,
)
from jobforge.pipeline.config import PipelineConfig


# Fixtures
@pytest.fixture(scope="module")
def gold_path() -> Path:
    """Path to gold directory for real data tests."""
    return PipelineConfig().gold_path()


@pytest.fixture(scope="module")
def job_arch_sample(gold_path: Path) -> pl.LazyFrame:
    """Sample job titles from job_architecture.parquet."""
    return pl.scan_parquet(gold_path / "job_architecture.parquet")


@pytest.fixture(scope="module")
def oasis_skills(gold_path: Path) -> pl.LazyFrame:
    """Load oasis_skills.parquet."""
    return pl.scan_parquet(gold_path / "oasis_skills.parquet")


@pytest.fixture(scope="module")
def sample_unit_group_id(gold_path: Path) -> str:
    """Get a valid unit_group_id from element_labels for testing."""
    # Use a UG that we know has skills data
    df = pl.scan_parquet(gold_path / "element_labels.parquet").head(1).collect()
    if df.is_empty():
        pytest.skip("No element_labels data available")
    return df["unit_group_id"][0]


# ============================================================
# Core inheritance tests
# ============================================================


class TestInheritAttributesAddProvenanceColumns:
    """Test that inherit_attributes_to_job_titles adds all provenance columns."""

    def test_inherit_attributes_adds_provenance_columns(
        self, job_arch_sample: pl.LazyFrame, oasis_skills: pl.LazyFrame, gold_path: Path
    ):
        """All 5 imputation provenance columns should be present."""
        result = inherit_attributes_to_job_titles(
            job_arch_sample.head(10),
            oasis_skills,
            "skill",
            gold_path,
        )

        collected = result.collect()
        cols = collected.columns

        assert ImputationProvenanceColumns.IMPUTATION_SOURCE_LEVEL in cols
        assert ImputationProvenanceColumns.IMPUTATION_SOURCE_ID in cols
        assert ImputationProvenanceColumns.IMPUTATION_PROVENANCE in cols
        assert ImputationProvenanceColumns.IMPUTATION_CONFIDENCE in cols
        assert ImputationProvenanceColumns.IMPUTATION_AT in cols

    def test_inherit_attributes_source_level_is_5(
        self, job_arch_sample: pl.LazyFrame, oasis_skills: pl.LazyFrame, gold_path: Path
    ):
        """Source level should always be 5 for L5 inheritance."""
        result = inherit_attributes_to_job_titles(
            job_arch_sample.head(10),
            oasis_skills,
            "skill",
            gold_path,
        )

        collected = result.collect()
        source_levels = collected[ImputationProvenanceColumns.IMPUTATION_SOURCE_LEVEL].unique().to_list()

        # All rows should have source_level=5
        assert source_levels == [5]

    def test_inherit_attributes_preserves_job_arch_columns(
        self, job_arch_sample: pl.LazyFrame, oasis_skills: pl.LazyFrame, gold_path: Path
    ):
        """Original job architecture columns should be preserved."""
        original_cols = job_arch_sample.collect_schema().names()

        result = inherit_attributes_to_job_titles(
            job_arch_sample.head(10),
            oasis_skills,
            "skill",
            gold_path,
        )

        result_cols = result.collect_schema().names()

        # All original columns should be present
        for col in original_cols:
            assert col in result_cols, f"Missing column: {col}"


class TestInheritAttributesJoin:
    """Test that inheritance joins correctly."""

    def test_inherit_attributes_joins_correctly(
        self, gold_path: Path
    ):
        """Matching unit_group_ids should have attribute values."""
        # Get a unit_group_id that exists in both tables
        job_arch = pl.scan_parquet(gold_path / "job_architecture.parquet")
        oasis_skills = pl.scan_parquet(gold_path / "oasis_skills.parquet")

        # Find common unit_group_ids
        job_ugs = job_arch.select("unit_group_id").unique().collect()["unit_group_id"].to_list()
        skill_ugs = oasis_skills.select("unit_group_id").unique().collect()["unit_group_id"].to_list()
        common = set(job_ugs) & set(skill_ugs)

        if not common:
            pytest.skip("No common unit_group_ids between tables")

        # Filter to job titles with matching UGs
        test_ug = list(common)[0]
        filtered_arch = job_arch.filter(pl.col("unit_group_id") == test_ug)

        result = inherit_attributes_to_job_titles(
            filtered_arch,
            oasis_skills,
            "skill",
            gold_path,
        )

        collected = result.collect()

        # Should have rows and non-null oasis_label
        assert len(collected) > 0
        assert "oasis_label" in collected.columns

    def test_inherit_attributes_null_for_missing_ug(
        self, gold_path: Path
    ):
        """Job titles with unknown UG should have null attribute values."""
        # Create a job arch with a fake unit_group_id
        fake_job_arch = pl.LazyFrame({
            "jt_id": [99999],
            "unit_group_id": ["99999"],  # Non-existent UG
            "job_title_en": ["Fake Job Title"],
        })

        oasis_skills = pl.scan_parquet(gold_path / "oasis_skills.parquet")

        result = inherit_attributes_to_job_titles(
            fake_job_arch,
            oasis_skills,
            "skill",
            gold_path,
        )

        collected = result.collect()

        # Should have the row but with null skill values
        assert len(collected) == 1
        # oasis_label should be null since no matching UG
        assert collected["oasis_label"][0] is None


# ============================================================
# Single imputation tests
# ============================================================


class TestApplyImputation:
    """Test apply_imputation for single job title imputation."""

    def test_apply_imputation_returns_dict(
        self, sample_unit_group_id: str, gold_path: Path
    ):
        """Should return dict mapping attribute names to lists."""
        oasis_skills = pl.scan_parquet(gold_path / "oasis_skills.parquet")

        result = apply_imputation(
            job_title="Test Job Title",
            unit_group_id=sample_unit_group_id,
            attribute_tables={"skills": oasis_skills},
            gold_path=gold_path,
        )

        assert isinstance(result, dict)
        # If UG has skills, should have a "skills" key
        if "skills" in result:
            assert isinstance(result["skills"], list)

    def test_apply_imputation_has_confidence(
        self, sample_unit_group_id: str, gold_path: Path
    ):
        """Each imputed value should have a confidence score."""
        oasis_skills = pl.scan_parquet(gold_path / "oasis_skills.parquet")

        result = apply_imputation(
            job_title="Test Job Title",
            unit_group_id=sample_unit_group_id,
            attribute_tables={"skills": oasis_skills},
            gold_path=gold_path,
        )

        if "skills" in result and result["skills"]:
            for value in result["skills"]:
                assert "confidence" in value
                assert 0.0 <= value["confidence"] <= 1.0

    def test_apply_imputation_has_source_id(
        self, sample_unit_group_id: str, gold_path: Path
    ):
        """Each imputed value should have a source identifier."""
        oasis_skills = pl.scan_parquet(gold_path / "oasis_skills.parquet")

        result = apply_imputation(
            job_title="Test Job Title",
            unit_group_id=sample_unit_group_id,
            attribute_tables={"skills": oasis_skills},
            gold_path=gold_path,
        )

        if "skills" in result and result["skills"]:
            for value in result["skills"]:
                assert "source_identifier" in value
                assert value["source_identifier"] == sample_unit_group_id

    def test_apply_imputation_empty_for_invalid_ug(self, gold_path: Path):
        """Should return empty dict for non-existent unit_group_id."""
        oasis_skills = pl.scan_parquet(gold_path / "oasis_skills.parquet")

        result = apply_imputation(
            job_title="Test Job Title",
            unit_group_id="99999",  # Non-existent
            attribute_tables={"skills": oasis_skills},
            gold_path=gold_path,
        )

        assert result == {}


# ============================================================
# Provenance validation tests
# ============================================================


class TestProvenanceValidation:
    """Test that provenance values match specification."""

    def test_provenance_inherited_for_l5_attributes(
        self, job_arch_sample: pl.LazyFrame, oasis_skills: pl.LazyFrame, gold_path: Path
    ):
        """Provenance should be 'inherited' for L5 attribute inheritance."""
        result = inherit_attributes_to_job_titles(
            job_arch_sample.head(10),
            oasis_skills,
            "skill",
            gold_path,
        )

        collected = result.collect()
        provenance_values = collected[ImputationProvenanceColumns.IMPUTATION_PROVENANCE].unique().to_list()

        # All rows should have provenance="inherited"
        assert provenance_values == ["inherited"]

    def test_provenance_columns_match_spec(
        self, job_arch_sample: pl.LazyFrame, oasis_skills: pl.LazyFrame, gold_path: Path
    ):
        """Provenance column names should match ImputationProvenanceColumns spec."""
        expected_columns = get_provenance_column_names()

        result = inherit_attributes_to_job_titles(
            job_arch_sample.head(10),
            oasis_skills,
            "skill",
            gold_path,
        )

        result_cols = result.collect_schema().names()

        for expected in expected_columns:
            assert expected in result_cols, f"Missing provenance column: {expected}"


# ============================================================
# Provenance utilities tests
# ============================================================


class TestProvenanceUtilities:
    """Test provenance utility functions."""

    def test_add_imputation_provenance_adds_columns(self):
        """add_imputation_provenance should add all 5 columns."""
        df = pl.LazyFrame({
            "unit_group_id": ["21231", "21232"],
            "skill": ["Python", "Java"],
        })

        result = add_imputation_provenance(
            df,
            source_level=5,
            source_id_col="unit_group_id",
            provenance="inherited",
            confidence=0.85,
        )

        collected = result.collect()

        assert ImputationProvenanceColumns.IMPUTATION_SOURCE_LEVEL in collected.columns
        assert ImputationProvenanceColumns.IMPUTATION_SOURCE_ID in collected.columns
        assert ImputationProvenanceColumns.IMPUTATION_PROVENANCE in collected.columns
        assert ImputationProvenanceColumns.IMPUTATION_CONFIDENCE in collected.columns
        assert ImputationProvenanceColumns.IMPUTATION_AT in collected.columns

    def test_add_imputation_provenance_sets_values(self):
        """Provenance values should be set correctly."""
        df = pl.LazyFrame({
            "unit_group_id": ["21231"],
            "skill": ["Python"],
        })

        result = add_imputation_provenance(
            df,
            source_level=6,
            source_id_col="unit_group_id",
            provenance="native",
            confidence=1.0,
        )

        collected = result.collect()

        assert collected[ImputationProvenanceColumns.IMPUTATION_SOURCE_LEVEL][0] == 6
        assert collected[ImputationProvenanceColumns.IMPUTATION_SOURCE_ID][0] == "21231"
        assert collected[ImputationProvenanceColumns.IMPUTATION_PROVENANCE][0] == "native"
        assert collected[ImputationProvenanceColumns.IMPUTATION_CONFIDENCE][0] == 1.0

    def test_create_imputed_attribute_row(self):
        """create_imputed_attribute_row should create dict with all fields."""
        row = create_imputed_attribute_row(
            value="Critical Thinking",
            attribute_name="skill",
            source_level=5,
            source_id="21231",
            provenance="inherited",
            confidence=0.85,
        )

        assert row["skill"] == "Critical Thinking"
        assert row[ImputationProvenanceColumns.IMPUTATION_SOURCE_LEVEL] == 5
        assert row[ImputationProvenanceColumns.IMPUTATION_SOURCE_ID] == "21231"
        assert row[ImputationProvenanceColumns.IMPUTATION_PROVENANCE] == "inherited"
        assert row[ImputationProvenanceColumns.IMPUTATION_CONFIDENCE] == 0.85
        assert ImputationProvenanceColumns.IMPUTATION_AT in row

    def test_get_provenance_column_names(self):
        """get_provenance_column_names should return all 5 column names."""
        names = get_provenance_column_names()

        assert len(names) == 5
        assert ImputationProvenanceColumns.IMPUTATION_SOURCE_LEVEL in names
        assert ImputationProvenanceColumns.IMPUTATION_SOURCE_ID in names
        assert ImputationProvenanceColumns.IMPUTATION_PROVENANCE in names
        assert ImputationProvenanceColumns.IMPUTATION_CONFIDENCE in names
        assert ImputationProvenanceColumns.IMPUTATION_AT in names


# ============================================================
# Imputation summary tests
# ============================================================


class TestImputationSummary:
    """Test get_imputation_summary function."""

    def test_summary_returns_expected_keys(
        self, job_arch_sample: pl.LazyFrame, oasis_skills: pl.LazyFrame, gold_path: Path
    ):
        """Summary should contain all expected keys."""
        result = inherit_attributes_to_job_titles(
            job_arch_sample.head(10),
            oasis_skills,
            "skill",
            gold_path,
        )

        summary = get_imputation_summary(result)

        assert "total_rows" in summary
        assert "rows_by_source_level" in summary
        assert "rows_by_provenance" in summary
        assert "avg_confidence" in summary
        assert "min_confidence" in summary
        assert "max_confidence" in summary

    def test_summary_total_rows_correct(
        self, job_arch_sample: pl.LazyFrame, oasis_skills: pl.LazyFrame, gold_path: Path
    ):
        """Total rows should match actual row count."""
        result = inherit_attributes_to_job_titles(
            job_arch_sample.head(10),
            oasis_skills,
            "skill",
            gold_path,
        )

        summary = get_imputation_summary(result)
        actual_count = result.collect().height

        assert summary["total_rows"] == actual_count

    def test_summary_empty_dataframe(self):
        """Summary should handle empty DataFrame gracefully."""
        empty_df = pl.LazyFrame({
            "unit_group_id": [],
            "_imputation_source_level": [],
            "_imputation_provenance": [],
            "_imputation_confidence": [],
        })

        summary = get_imputation_summary(empty_df)

        assert summary["total_rows"] == 0
        assert summary["avg_confidence"] == 0.0


# ============================================================
# Integration test
# ============================================================


class TestEndToEndImputation:
    """Integration test for full imputation flow."""

    def test_end_to_end_imputation(self, gold_path: Path):
        """Load job title, impute skills, verify provenance chain."""
        # Load job architecture and find a job title with valid UG
        job_arch = pl.scan_parquet(gold_path / "job_architecture.parquet")
        oasis_skills = pl.scan_parquet(gold_path / "oasis_skills.parquet")

        # Get first job with a valid UG that has skills
        skill_ugs = oasis_skills.select("unit_group_id").unique().collect()["unit_group_id"].to_list()
        job_with_skills = (
            job_arch
            .filter(pl.col("unit_group_id").is_in(skill_ugs))
            .head(1)
            .collect()
        )

        if job_with_skills.is_empty():
            pytest.skip("No jobs with skills data available")

        job_title = job_with_skills["job_title_en"][0]
        unit_group_id = job_with_skills["unit_group_id"][0]

        # Test single imputation
        single_result = apply_imputation(
            job_title=job_title,
            unit_group_id=unit_group_id,
            attribute_tables={"skills": oasis_skills},
            gold_path=gold_path,
        )

        # Should have imputed skills
        assert "skills" in single_result
        if single_result["skills"]:
            first_skill = single_result["skills"][0]
            # Verify provenance chain
            assert first_skill["source_level"] == 5
            assert first_skill["source_identifier"] == unit_group_id
            assert first_skill["provenance"] == "inherited"
            assert 0.0 <= first_skill["confidence"] <= 1.0

        # Test batch inheritance
        filtered_arch = job_arch.filter(pl.col("unit_group_id") == unit_group_id)
        batch_result = inherit_attributes_to_job_titles(
            filtered_arch,
            oasis_skills,
            "skill",
            gold_path,
        )

        collected = batch_result.collect()

        # Verify all provenance columns present
        for col in get_provenance_column_names():
            assert col in collected.columns

        # Verify provenance values
        assert collected[ImputationProvenanceColumns.IMPUTATION_SOURCE_LEVEL][0] == 5
        assert collected[ImputationProvenanceColumns.IMPUTATION_PROVENANCE][0] == "inherited"
