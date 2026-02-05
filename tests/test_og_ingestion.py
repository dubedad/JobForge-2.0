"""Tests for OG (Occupational Groups) ingestion."""

import json
from pathlib import Path

import polars as pl
import pytest

from jobforge.ingestion.og import (
    ingest_dim_og,
    ingest_dim_og_subgroup,
    normalize_og_codes,
    normalize_subgroup_codes,
    dedupe_groups,
    dedupe_subgroups,
    validate_required_og_fields,
    validate_parent_exists,
)
from jobforge.pipeline.config import PipelineConfig


@pytest.fixture
def test_config(tmp_path: Path) -> PipelineConfig:
    """Create a PipelineConfig using temporary directory."""
    return PipelineConfig(data_root=tmp_path / "data")


@pytest.fixture
def sample_og_json(tmp_path: Path) -> Path:
    """Create a sample occupational_groups_en.json for testing."""
    json_path = tmp_path / "occupational_groups_en.json"
    data = {
        "url": "https://example.com/og",
        "language": "en",
        "title": "Test OG Data",
        "scraped_at": "2026-01-20T00:00:00Z",
        "rows": [
            {
                "group_abbrev": "AS",
                "group_code": "501",
                "group_name": "Administrative Services(AS)",
                "subgroup": "N/A",
                "definition_url": "https://example.com/def/as",
                "qualification_standard_url": "https://example.com/qual/as",
                "provenance": {
                    "source_url": "https://example.com/og",
                    "scraped_at": "2026-01-20T00:00:00Z"
                }
            },
            {
                "group_abbrev": "AS",
                "group_code": "501",
                "group_name": "Administrative Services(AS)",
                "subgroup": "AS-01",
                "definition_url": "https://example.com/def/as-01",
                "qualification_standard_url": "https://example.com/qual/as",
                "provenance": {
                    "source_url": "https://example.com/og",
                    "scraped_at": "2026-01-20T00:00:00Z"
                }
            },
            {
                "group_abbrev": "FI",
                "group_code": "502",
                "group_name": "Financial Management(FI)",
                "subgroup": "N/A",
                "definition_url": "https://example.com/def/fi",
                "qualification_standard_url": "https://example.com/qual/fi",
                "provenance": {
                    "source_url": "https://example.com/og",
                    "scraped_at": "2026-01-20T00:00:00Z"
                }
            },
            {
                "group_abbrev": "EC",
                "group_code": "304",
                "group_name": "Economics and Social Science Services(EC)",
                "subgroup": "N/A",
                "definition_url": "https://example.com/def/ec",
                "qualification_standard_url": "https://example.com/qual/ec",
                "provenance": {
                    "source_url": "https://example.com/og",
                    "scraped_at": "2026-01-20T00:00:00Z"
                }
            },
        ]
    }
    json_path.write_text(json.dumps(data), encoding="utf-8")
    return json_path


@pytest.fixture
def sample_subgroups_json(tmp_path: Path) -> Path:
    """Create a sample og_subgroups_en.json for testing."""
    json_path = tmp_path / "og_subgroups_en.json"
    data = [
        {
            "og_code": "AS",
            "subgroup_code": "AS-01",
            "subgroup_name": "Level 1",
            "definition_url": "https://example.com/def/as-01",
            "qualification_standard_url": "https://example.com/qual/as",
            "rates_of_pay_url": None,
            "source_url": "https://example.com/og",
            "scraped_at": "2026-01-20T00:00:00Z"
        },
        {
            "og_code": "AS",
            "subgroup_code": "AS-02",
            "subgroup_name": "Level 2",
            "definition_url": "https://example.com/def/as-02",
            "qualification_standard_url": "https://example.com/qual/as",
            "rates_of_pay_url": None,
            "source_url": "https://example.com/og",
            "scraped_at": "2026-01-20T00:00:00Z"
        },
        {
            "og_code": "FI",
            "subgroup_code": "FI-01",
            "subgroup_name": "Financial Level 1",
            "definition_url": "https://example.com/def/fi-01",
            "qualification_standard_url": "https://example.com/qual/fi",
            "rates_of_pay_url": None,
            "source_url": "https://example.com/og",
            "scraped_at": "2026-01-20T00:00:00Z"
        },
        {
            "og_code": "ORPHAN",
            "subgroup_code": "ORPHAN-01",
            "subgroup_name": "Orphan Subgroup",
            "definition_url": "https://example.com/def/orphan",
            "qualification_standard_url": None,
            "rates_of_pay_url": None,
            "source_url": "https://example.com/og",
            "scraped_at": "2026-01-20T00:00:00Z"
        },
    ]
    json_path.write_text(json.dumps(data), encoding="utf-8")
    return json_path


class TestOgTransforms:
    """Tests for OG transform functions."""

    def test_normalize_og_codes_uppercase(self) -> None:
        """Verify normalize_og_codes uppercases and strips codes."""
        df = pl.LazyFrame({
            "og_code": ["as", " FI ", "ec"],
            "og_numeric_code": [" 501 ", "502", "304"],
        })
        result = normalize_og_codes(df).collect()
        assert result["og_code"].to_list() == ["AS", "FI", "EC"]
        assert result["og_numeric_code"].to_list() == ["501", "502", "304"]

    def test_dedupe_groups_keeps_first(self) -> None:
        """Verify dedupe_groups keeps first occurrence."""
        df = pl.LazyFrame({
            "og_code": ["AS", "AS", "FI"],
            "og_name": ["First AS", "Second AS", "First FI"],
        })
        result = dedupe_groups(df).collect()
        assert len(result) == 2
        assert "First AS" in result["og_name"].to_list()
        assert "Second AS" not in result["og_name"].to_list()

    def test_validate_required_og_fields_filters_nulls(self) -> None:
        """Verify validate_required_og_fields removes null codes/names."""
        df = pl.LazyFrame({
            "og_code": ["AS", None, "FI"],
            "og_name": ["Admin", "Missing", None],
        })
        result = validate_required_og_fields(df).collect()
        assert len(result) == 1
        assert result["og_code"][0] == "AS"


class TestSubgroupTransforms:
    """Tests for subgroup transform functions."""

    def test_normalize_subgroup_codes_uppercase(self) -> None:
        """Verify normalize_subgroup_codes uppercases both codes."""
        df = pl.LazyFrame({
            "og_code": ["as", " fi "],
            "og_subgroup_code": [" as-01 ", "fi-02"],
        })
        result = normalize_subgroup_codes(df).collect()
        assert result["og_code"].to_list() == ["AS", "FI"]
        assert result["og_subgroup_code"].to_list() == ["AS-01", "FI-02"]

    def test_dedupe_subgroups_keeps_first(self) -> None:
        """Verify dedupe_subgroups keeps first occurrence."""
        df = pl.LazyFrame({
            "og_subgroup_code": ["AS-01", "AS-01", "FI-01"],
            "og_subgroup_name": ["First", "Second", "FI First"],
        })
        result = dedupe_subgroups(df).collect()
        assert len(result) == 2

    def test_validate_parent_exists_filters_orphans(self) -> None:
        """Verify validate_parent_exists removes orphan subgroups."""
        df = pl.LazyFrame({
            "og_code": ["AS", "FI", "ORPHAN"],
            "og_subgroup_code": ["AS-01", "FI-01", "ORPHAN-01"],
        })
        valid_parents = {"AS", "FI"}
        result = validate_parent_exists(df, valid_parents).collect()
        assert len(result) == 2
        assert "ORPHAN" not in result["og_code"].to_list()


class TestDimOgIngestion:
    """Tests for dim_og ingestion."""

    def test_ingest_dim_og_creates_gold_file(
        self,
        sample_og_json: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify ingest_dim_og creates gold parquet file."""
        result = ingest_dim_og(
            source_path=sample_og_json,
            config=test_config,
        )
        assert result["gold_path"].exists()
        assert result["gold_path"].suffix == ".parquet"

    def test_ingest_dim_og_extracts_unique_groups(
        self,
        sample_og_json: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify only unique groups are in gold table."""
        result = ingest_dim_og(
            source_path=sample_og_json,
            config=test_config,
        )
        gold_df = pl.read_parquet(result["gold_path"])
        # Sample has 3 unique groups (AS appears twice in source)
        assert len(gold_df) == 3
        assert set(gold_df["og_code"].to_list()) == {"AS", "FI", "EC"}

    def test_ingest_dim_og_cleans_group_names(
        self,
        sample_og_json: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify group names have abbreviation suffix removed."""
        result = ingest_dim_og(
            source_path=sample_og_json,
            config=test_config,
        )
        gold_df = pl.read_parquet(result["gold_path"])
        as_row = gold_df.filter(pl.col("og_code") == "AS")
        assert as_row["og_name"][0] == "Administrative Services"

    def test_ingest_dim_og_has_provenance(
        self,
        sample_og_json: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify gold table has provenance columns."""
        result = ingest_dim_og(
            source_path=sample_og_json,
            config=test_config,
        )
        gold_df = pl.read_parquet(result["gold_path"])

        provenance_columns = [
            "_source_url",
            "_scraped_at",
            "_source_file",
            "_ingested_at",
            "_batch_id",
            "_layer",
        ]
        for col in provenance_columns:
            assert col in gold_df.columns, f"Missing provenance column: {col}"

        assert gold_df["_layer"][0] == "gold"
        assert gold_df["_source_url"][0] == "https://example.com/og"

    def test_ingest_dim_og_expected_columns(
        self,
        sample_og_json: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify gold table has expected business columns."""
        result = ingest_dim_og(
            source_path=sample_og_json,
            config=test_config,
        )
        gold_df = pl.read_parquet(result["gold_path"])

        expected_columns = [
            "og_code",
            "og_numeric_code",
            "og_name",
            "definition_url",
            "qualification_standard_url",
            "rates_of_pay_url",
        ]
        for col in expected_columns:
            assert col in gold_df.columns, f"Missing column: {col}"

    def test_ingest_dim_og_no_null_required_fields(
        self,
        sample_og_json: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify no null values in og_code or og_name."""
        result = ingest_dim_og(
            source_path=sample_og_json,
            config=test_config,
        )
        gold_df = pl.read_parquet(result["gold_path"])

        assert gold_df["og_code"].null_count() == 0
        assert gold_df["og_name"].null_count() == 0


class TestDimOgSubgroupIngestion:
    """Tests for dim_og_subgroup ingestion."""

    def test_ingest_dim_og_subgroup_creates_gold_file(
        self,
        sample_og_json: Path,
        sample_subgroups_json: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify ingest_dim_og_subgroup creates gold parquet file."""
        # First create dim_og (FK dependency)
        ingest_dim_og(source_path=sample_og_json, config=test_config)

        result = ingest_dim_og_subgroup(
            source_path=sample_subgroups_json,
            config=test_config,
        )
        assert result["gold_path"].exists()
        assert result["gold_path"].suffix == ".parquet"

    def test_ingest_dim_og_subgroup_filters_orphans(
        self,
        sample_og_json: Path,
        sample_subgroups_json: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify orphan subgroups (invalid og_code) are filtered."""
        # First create dim_og
        ingest_dim_og(source_path=sample_og_json, config=test_config)

        result = ingest_dim_og_subgroup(
            source_path=sample_subgroups_json,
            config=test_config,
        )
        gold_df = pl.read_parquet(result["gold_path"])

        # Sample has 4 subgroups, 1 orphan (ORPHAN og_code)
        assert len(gold_df) == 3
        assert result["orphans_removed"] == 1
        assert "ORPHAN" not in gold_df["og_code"].to_list()

    def test_ingest_dim_og_subgroup_has_provenance(
        self,
        sample_og_json: Path,
        sample_subgroups_json: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify gold table has provenance columns."""
        ingest_dim_og(source_path=sample_og_json, config=test_config)

        result = ingest_dim_og_subgroup(
            source_path=sample_subgroups_json,
            config=test_config,
        )
        gold_df = pl.read_parquet(result["gold_path"])

        provenance_columns = [
            "_source_url",
            "_scraped_at",
            "_source_file",
            "_ingested_at",
            "_batch_id",
            "_layer",
        ]
        for col in provenance_columns:
            assert col in gold_df.columns, f"Missing provenance column: {col}"

    def test_ingest_dim_og_subgroup_expected_columns(
        self,
        sample_og_json: Path,
        sample_subgroups_json: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify gold table has expected business columns."""
        ingest_dim_og(source_path=sample_og_json, config=test_config)

        result = ingest_dim_og_subgroup(
            source_path=sample_subgroups_json,
            config=test_config,
        )
        gold_df = pl.read_parquet(result["gold_path"])

        expected_columns = [
            "og_subgroup_code",
            "og_code",
            "og_subgroup_name",
            "definition_url",
            "qualification_standard_url",
            "rates_of_pay_url",
        ]
        for col in expected_columns:
            assert col in gold_df.columns, f"Missing column: {col}"

    def test_ingest_dim_og_subgroup_fk_integrity(
        self,
        sample_og_json: Path,
        sample_subgroups_json: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify all subgroup og_codes exist in dim_og."""
        ingest_dim_og(source_path=sample_og_json, config=test_config)

        result = ingest_dim_og_subgroup(
            source_path=sample_subgroups_json,
            config=test_config,
        )
        subgroup_df = pl.read_parquet(result["gold_path"])
        og_df = pl.read_parquet(test_config.gold_path() / "dim_og.parquet")

        # All og_codes in subgroups must exist in og
        subgroup_og_codes = set(subgroup_df["og_code"].to_list())
        og_codes = set(og_df["og_code"].to_list())
        assert subgroup_og_codes.issubset(og_codes)

    def test_ingest_dim_og_subgroup_requires_dim_og(
        self,
        sample_subgroups_json: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify ingest_dim_og_subgroup raises if dim_og missing."""
        with pytest.raises(FileNotFoundError, match="dim_og.parquet not found"):
            ingest_dim_og_subgroup(
                source_path=sample_subgroups_json,
                config=test_config,
            )

    def test_ingest_dim_og_subgroup_skip_fk_validation(
        self,
        sample_subgroups_json: Path,
        test_config: PipelineConfig,
    ) -> None:
        """Verify FK validation can be skipped."""
        # Should not raise even without dim_og
        result = ingest_dim_og_subgroup(
            source_path=sample_subgroups_json,
            config=test_config,
            validate_fk=False,
        )
        assert result["gold_path"].exists()
        # All 4 subgroups (including orphan) should be present
        gold_df = pl.read_parquet(result["gold_path"])
        assert len(gold_df) == 4


class TestProductionData:
    """Tests against actual production data files."""

    @pytest.mark.skipif(
        not Path("data/tbs/occupational_groups_en.json").exists(),
        reason="Production data not available"
    )
    def test_production_dim_og_row_count(self) -> None:
        """Verify production dim_og has expected row count."""
        result = ingest_dim_og()
        # Actual data has 31 unique occupational groups
        assert result["row_count"] >= 25  # Allow some flexibility

    @pytest.mark.skipif(
        not Path("data/tbs/og_subgroups_en.json").exists(),
        reason="Production data not available"
    )
    def test_production_dim_og_subgroup_row_count(self) -> None:
        """Verify production dim_og_subgroup has expected row count."""
        # Ensure dim_og exists first
        ingest_dim_og()
        result = ingest_dim_og_subgroup()
        # Actual data has ~111 unique subgroups
        assert result["row_count"] >= 100  # Allow some flexibility

    @pytest.mark.skipif(
        not Path("data/gold/dim_og.parquet").exists(),
        reason="Gold data not available"
    )
    def test_production_fk_integrity(self) -> None:
        """Verify all production subgroup og_codes exist in dim_og."""
        og_df = pl.read_parquet("data/gold/dim_og.parquet")
        subgroup_df = pl.read_parquet("data/gold/dim_og_subgroup.parquet")

        og_codes = set(og_df["og_code"].to_list())
        subgroup_og_codes = set(subgroup_df["og_code"].to_list())

        orphans = subgroup_og_codes - og_codes
        assert len(orphans) == 0, f"Orphan og_codes found: {orphans}"
