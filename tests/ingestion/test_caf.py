"""Tests for CAF gold table ingestion pipeline.

Tests validate:
- Row counts match expected (88 occupations, 11 job families)
- Bilingual columns present (title_en/fr, overview_en/fr, etc.)
- Provenance columns on all records
- FK relationship valid (occupation.job_family_id -> job_family.job_family_id)
- Silver transforms (normalize, dedupe, validate)
"""

from pathlib import Path

import polars as pl
import pytest

from jobforge.ingestion.caf import (
    dedupe_job_families,
    dedupe_occupations,
    ingest_dim_caf_job_family,
    ingest_dim_caf_occupation,
    normalize_caf_occupation_codes,
    normalize_job_family_codes,
    validate_required_job_family_fields,
    validate_required_occupation_fields,
)


class TestSilverTransforms:
    """Tests for silver layer transform functions."""

    def test_normalize_occupation_codes_lowercase(self):
        """normalize_caf_occupation_codes converts to lowercase."""
        df = pl.DataFrame({
            "career_id": ["PILOT", "Infantry-Soldier"],
            "job_family_id": ["Combat-Operations", "COMBAT-OPERATIONS"],
        }).lazy()

        result = normalize_caf_occupation_codes(df).collect()

        assert result["career_id"].to_list() == ["pilot", "infantry-soldier"]
        assert result["job_family_id"].to_list() == ["combat-operations", "combat-operations"]

    def test_dedupe_occupations_removes_duplicates(self):
        """dedupe_occupations removes duplicate career_ids."""
        df = pl.DataFrame({
            "career_id": ["pilot", "pilot", "infantry-soldier"],
            "title_en": ["Pilot", "Pilot (Dup)", "Infantry Soldier"],
        }).lazy()

        result = dedupe_occupations(df).collect()

        assert len(result) == 2
        # Check both expected values are present (order not guaranteed)
        assert set(result["career_id"].to_list()) == {"pilot", "infantry-soldier"}
        # First occurrence kept for the duplicate
        pilot_row = result.filter(pl.col("career_id") == "pilot")
        assert pilot_row["title_en"][0] == "Pilot"

    def test_validate_required_occupation_fields(self):
        """validate_required_occupation_fields removes nulls."""
        df = pl.DataFrame({
            "career_id": ["pilot", None, "infantry-soldier"],
            "title_en": ["Pilot", "No ID", None],
        }).lazy()

        result = validate_required_occupation_fields(df).collect()

        # Only the first row has both career_id and title_en not null
        assert len(result) == 1
        assert result["career_id"][0] == "pilot"

    def test_normalize_job_family_codes_lowercase(self):
        """normalize_job_family_codes converts to lowercase."""
        df = pl.DataFrame({
            "job_family_id": ["Medical-Health", "COMBAT-OPERATIONS"],
        }).lazy()

        result = normalize_job_family_codes(df).collect()

        assert result["job_family_id"].to_list() == ["medical-health", "combat-operations"]

    def test_dedupe_job_families_removes_duplicates(self):
        """dedupe_job_families removes duplicate job_family_ids."""
        df = pl.DataFrame({
            "job_family_id": ["medical-health", "medical-health", "combat-operations"],
            "job_family_name": ["Medical Health", "Medical Health (Dup)", "Combat Operations"],
        }).lazy()

        result = dedupe_job_families(df).collect()

        assert len(result) == 2
        # Check both expected values are present (order not guaranteed)
        assert set(result["job_family_id"].to_list()) == {"medical-health", "combat-operations"}

    def test_validate_required_job_family_fields(self):
        """validate_required_job_family_fields removes nulls."""
        df = pl.DataFrame({
            "job_family_id": ["medical-health", None, "combat-operations"],
            "job_family_name": ["Medical Health", "No ID", None],
        }).lazy()

        result = validate_required_job_family_fields(df).collect()

        assert len(result) == 1
        assert result["job_family_id"][0] == "medical-health"


class TestIngestDimCafOccupation:
    """Integration tests for dim_caf_occupation ingestion."""

    def test_ingest_creates_parquet_file(self):
        """ingest_dim_caf_occupation creates gold parquet file."""
        source_path = Path("data/caf/occupations.json")
        if not source_path.exists():
            pytest.skip("Source file not available")

        result = ingest_dim_caf_occupation()

        assert result["gold_path"].exists()
        assert result["row_count"] == 88

    def test_ingest_row_count_matches_expected(self):
        """Ingested table has expected row count."""
        gold_path = Path("data/gold/dim_caf_occupation.parquet")
        if not gold_path.exists():
            pytest.skip("Gold file not available")

        df = pl.read_parquet(gold_path)

        assert len(df) == 88

    def test_ingest_has_bilingual_columns(self):
        """Ingested table has bilingual content columns."""
        gold_path = Path("data/gold/dim_caf_occupation.parquet")
        if not gold_path.exists():
            pytest.skip("Gold file not available")

        df = pl.read_parquet(gold_path)

        bilingual_columns = [
            "title_en", "title_fr",
            "overview_en", "overview_fr",
            "work_environment_en", "work_environment_fr",
            "training_en", "training_fr",
            "entry_plans_en", "entry_plans_fr",
            "part_time_options_en", "part_time_options_fr",
        ]
        for col in bilingual_columns:
            assert col in df.columns, f"Missing bilingual column: {col}"

    def test_ingest_has_provenance_columns(self):
        """Ingested table has provenance columns."""
        gold_path = Path("data/gold/dim_caf_occupation.parquet")
        if not gold_path.exists():
            pytest.skip("Gold file not available")

        df = pl.read_parquet(gold_path)

        provenance_columns = [
            "_source_url_en",
            "_source_url_fr",
            "_content_hash_en",
            "_content_hash_fr",
            "_scraped_at",
            "_source_file",
            "_ingested_at",
            "_batch_id",
            "_layer",
        ]
        for col in provenance_columns:
            assert col in df.columns, f"Missing provenance column: {col}"

    def test_ingest_all_titles_bilingual(self):
        """All occupations have both EN and FR titles."""
        gold_path = Path("data/gold/dim_caf_occupation.parquet")
        if not gold_path.exists():
            pytest.skip("Gold file not available")

        df = pl.read_parquet(gold_path)

        # All rows should have title_en
        assert df.filter(pl.col("title_en").is_null()).height == 0

        # All rows should have title_fr (88 bilingual occupations per 15-02)
        assert df.filter(pl.col("title_fr").is_null()).height == 0

    def test_ingest_all_have_job_family(self):
        """All occupations have a job_family_id."""
        gold_path = Path("data/gold/dim_caf_occupation.parquet")
        if not gold_path.exists():
            pytest.skip("Gold file not available")

        df = pl.read_parquet(gold_path)

        assert df.filter(pl.col("job_family_id").is_null()).height == 0


class TestIngestDimCafJobFamily:
    """Integration tests for dim_caf_job_family ingestion."""

    def test_ingest_creates_parquet_file(self):
        """ingest_dim_caf_job_family creates gold parquet file."""
        source_path = Path("data/caf/job_families.json")
        if not source_path.exists():
            pytest.skip("Source file not available")

        result = ingest_dim_caf_job_family()

        assert result["gold_path"].exists()
        assert result["row_count"] == 11

    def test_ingest_row_count_matches_expected(self):
        """Ingested table has expected row count."""
        gold_path = Path("data/gold/dim_caf_job_family.parquet")
        if not gold_path.exists():
            pytest.skip("Gold file not available")

        df = pl.read_parquet(gold_path)

        assert len(df) == 11

    def test_ingest_has_expected_columns(self):
        """Ingested table has expected columns."""
        gold_path = Path("data/gold/dim_caf_job_family.parquet")
        if not gold_path.exists():
            pytest.skip("Gold file not available")

        df = pl.read_parquet(gold_path)

        expected_columns = [
            "job_family_id",
            "job_family_name",
            "description",
            "career_count",
        ]
        for col in expected_columns:
            assert col in df.columns

    def test_ingest_has_provenance_columns(self):
        """Ingested table has provenance columns."""
        gold_path = Path("data/gold/dim_caf_job_family.parquet")
        if not gold_path.exists():
            pytest.skip("Gold file not available")

        df = pl.read_parquet(gold_path)

        provenance_columns = [
            "_generated_at",
            "_source_file",
            "_ingested_at",
            "_batch_id",
            "_layer",
        ]
        for col in provenance_columns:
            assert col in df.columns


class TestForeignKeyIntegrity:
    """Tests for FK integrity between occupation and job family tables."""

    def test_occupation_job_family_fk_valid(self):
        """All occupation job_family_ids exist in job_family table."""
        occ_path = Path("data/gold/dim_caf_occupation.parquet")
        fam_path = Path("data/gold/dim_caf_job_family.parquet")

        if not occ_path.exists() or not fam_path.exists():
            pytest.skip("Gold files not available")

        occ_df = pl.read_parquet(occ_path)
        fam_df = pl.read_parquet(fam_path)

        occ_family_ids = set(occ_df["job_family_id"].unique().to_list())
        valid_family_ids = set(fam_df["job_family_id"].to_list())

        orphan_ids = occ_family_ids - valid_family_ids
        assert len(orphan_ids) == 0, f"Orphan job_family_ids: {orphan_ids}"

    def test_job_family_career_counts_reasonable(self):
        """Job family career counts are reasonable (sum close to 88)."""
        fam_path = Path("data/gold/dim_caf_job_family.parquet")

        if not fam_path.exists():
            pytest.skip("Gold file not available")

        fam_df = pl.read_parquet(fam_path)

        total_careers = fam_df["career_count"].sum()
        # Should be exactly 88 (from 15-02-SUMMARY)
        assert total_careers == 88

    def test_expected_job_families_present(self):
        """Expected job families are present in the table."""
        fam_path = Path("data/gold/dim_caf_job_family.parquet")

        if not fam_path.exists():
            pytest.skip("Gold file not available")

        fam_df = pl.read_parquet(fam_path)
        family_ids = set(fam_df["job_family_id"].to_list())

        # Per 15-02-SUMMARY: 11 families
        expected_families = {
            "engineering-technical",
            "medical-health",
            "combat-operations",
            "intelligence-signals",
            "administration-hr",
            "support-logistics",
            "police-security",
            "officer-general",
            "music",
            "ncm-general",
            "training-development",
        }

        assert family_ids == expected_families


class TestBilingualContentStorage:
    """Tests validating bilingual storage pattern (EN/FR in same record)."""

    def test_no_row_duplication_for_languages(self):
        """Each career_id appears exactly once (not duplicated for EN/FR)."""
        gold_path = Path("data/gold/dim_caf_occupation.parquet")

        if not gold_path.exists():
            pytest.skip("Gold file not available")

        df = pl.read_parquet(gold_path)

        # Count unique career_ids
        unique_count = df["career_id"].n_unique()
        total_count = len(df)

        # No duplicates means unique == total
        assert unique_count == total_count, "Found duplicate career_ids"

    def test_en_and_fr_in_same_record(self):
        """EN and FR content are in the same record, not separate rows."""
        gold_path = Path("data/gold/dim_caf_occupation.parquet")

        if not gold_path.exists():
            pytest.skip("Gold file not available")

        df = pl.read_parquet(gold_path)

        # Sample a record that has both EN and FR titles
        sample = df.filter(
            pl.col("title_en").is_not_null() & pl.col("title_fr").is_not_null()
        ).head(1)

        assert len(sample) > 0, "Expected at least one record with both EN and FR titles"

        # The record should have both EN and FR URLs in the same row
        assert sample["url_en"][0] is not None or sample["url_en"].is_null().any() is False
        # title_fr should be in the same record
        assert sample["title_fr"][0] is not None
