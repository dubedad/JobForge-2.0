"""Tests for represented pay rates ingestion.

Tests cover:
- Collective agreement ingestion
- Pay rates extension preserves excluded rates
- is_represented flag correctly set
- FK to dim_collective_agreement
- Raises FileNotFoundError if Phase 14-04 output missing
"""

import json
from pathlib import Path
from unittest.mock import patch

import polars as pl
import pytest

from jobforge.ingestion.og_represented_pay import (
    DEFAULT_EXCLUDED_SOURCE,
    extend_fact_og_pay_rates,
    ingest_all,
    ingest_dim_collective_agreement,
    verify_prerequisites,
)


class TestVerifyPrerequisites:
    """Tests for prerequisite verification."""

    def test_raises_if_excluded_missing(self, tmp_path):
        """Test that FileNotFoundError is raised if Phase 14-04 output missing."""
        with patch(
            "jobforge.ingestion.og_represented_pay.DEFAULT_EXCLUDED_SOURCE",
            tmp_path / "nonexistent.parquet",
        ):
            with pytest.raises(FileNotFoundError) as exc_info:
                verify_prerequisites()

            assert "Phase 14-04 output missing" in str(exc_info.value)

    def test_passes_if_excluded_exists(self, tmp_path):
        """Test that verification passes if file exists."""
        # Create mock excluded pay rates file
        excluded_path = tmp_path / "fact_og_pay_rates.parquet"
        df = pl.DataFrame({
            "og_code": ["AS"],
            "annual_rate": [50000.0],
        })
        df.write_parquet(excluded_path)

        with patch(
            "jobforge.ingestion.og_represented_pay.DEFAULT_EXCLUDED_SOURCE",
            excluded_path,
        ):
            # Should not raise
            verify_prerequisites()


class TestIngestDimCollectiveAgreement:
    """Tests for collective agreement ingestion."""

    @pytest.fixture
    def mock_ca_json(self, tmp_path):
        """Create mock collective agreements JSON file."""
        data = [
            {
                "agreement_id": "ca-ec-123",
                "agreement_name": "Economics and Social Science Services (EC)",
                "og_code": "EC",
                "og_subgroup_codes": ["EC"],
                "bargaining_agent": "Canadian Association of Professional Employees",
                "employer": "Treasury Board of Canada Secretariat",
                "signing_date": "2024-06-22",
                "effective_date": "2024-06-22",
                "expiry_date": "2027-06-21",
                "source_url": "https://example.com",
                "scraped_at": "2026-02-05T10:00:00Z",
            },
            {
                "agreement_id": "ca-pa-456",
                "agreement_name": "Program and Administrative Services (PA)",
                "og_code": "PA",
                "og_subgroup_codes": ["AS", "CR", "IS", "PM", "WP"],
                "bargaining_agent": "Public Service Alliance of Canada",
                "employer": "Treasury Board of Canada Secretariat",
                "signing_date": "2024-01-15",
                "effective_date": "2024-01-15",
                "expiry_date": "2027-01-14",
                "source_url": "https://example.com",
                "scraped_at": "2026-02-05T10:00:00Z",
            },
        ]
        ca_file = tmp_path / "collective_agreements.json"
        with open(ca_file, "w") as f:
            json.dump(data, f)
        return ca_file

    def test_ingests_collective_agreements(self, mock_ca_json, tmp_path):
        """Test that collective agreements are ingested to parquet."""
        result = ingest_dim_collective_agreement(
            source_path=mock_ca_json,
            output_dir=tmp_path,
        )

        assert result["gold_path"].exists()
        assert result["row_count"] == 2

        # Verify parquet contents
        df = pl.read_parquet(result["gold_path"])
        assert len(df) == 2
        assert "agreement_id" in df.columns
        assert "bargaining_agent" in df.columns
        assert "expiry_date" in df.columns

    def test_normalizes_og_codes(self, mock_ca_json, tmp_path):
        """Test that OG codes are normalized to uppercase."""
        # Modify to have lowercase
        with open(mock_ca_json) as f:
            data = json.load(f)
        data[0]["og_code"] = "ec"  # lowercase
        with open(mock_ca_json, "w") as f:
            json.dump(data, f)

        result = ingest_dim_collective_agreement(
            source_path=mock_ca_json,
            output_dir=tmp_path,
        )

        df = pl.read_parquet(result["gold_path"])
        assert df.filter(pl.col("og_code") == "EC").height == 1

    def test_raises_if_source_missing(self, tmp_path):
        """Test that FileNotFoundError is raised if source missing."""
        with pytest.raises(FileNotFoundError):
            ingest_dim_collective_agreement(
                source_path=tmp_path / "nonexistent.json",
                output_dir=tmp_path,
            )


class TestExtendFactOgPayRates:
    """Tests for extending fact_og_pay_rates with represented rates."""

    @pytest.fixture
    def mock_excluded_parquet(self, tmp_path):
        """Create mock excluded pay rates parquet file."""
        df = pl.DataFrame({
            "og_subgroup_code": ["AS", "AS", "PM"],
            "og_code": ["AS", "AS", "PM"],
            "classification_level": ["AS-01", "AS-01", "PM-01"],
            "step": pl.Series([1, 2, 1], dtype=pl.Int32),
            "annual_rate": [50000.0, 52000.0, 55000.0],
            "hourly_rate": [None, None, None],
            "effective_date": ["2024-01-01", "2024-01-01", "2024-01-01"],
            "is_represented": [False, False, False],
            "collective_agreement": [None, None, None],
            "_source_url": ["https://example.com"] * 3,
            "_scraped_at": ["2026-02-05T10:00:00Z"] * 3,
            "_source_file": ["data/tbs/og_pay_rates_en.json"] * 3,
            "_ingested_at": ["2026-02-05T10:00:00Z"] * 3,
            "_batch_id": ["batch-123"] * 3,
            "_layer": ["gold"] * 3,
        })
        excluded_path = tmp_path / "fact_og_pay_rates.parquet"
        df.write_parquet(excluded_path)
        return excluded_path

    @pytest.fixture
    def mock_represented_json(self, tmp_path):
        """Create mock represented pay rates JSON file."""
        data = [
            {
                "og_code": "EC",
                "og_subgroup_code": "EC",
                "classification_level": "EC-01",
                "step": 1,
                "annual_rate": 55567.0,
                "hourly_rate": None,
                "effective_date": "2021-06-22",
                "is_represented": True,
                "collective_agreement_id": "ca-ec-123",
                "pay_progression_type": "step",
                "source_url": "https://example.com",
                "scraped_at": "2026-02-05T10:00:00Z",
            },
            {
                "og_code": "EC",
                "og_subgroup_code": "EC",
                "classification_level": "EC-01",
                "step": 2,
                "annual_rate": 57508.0,
                "hourly_rate": None,
                "effective_date": "2021-06-22",
                "is_represented": True,
                "collective_agreement_id": "ca-ec-123",
                "pay_progression_type": "step",
                "source_url": "https://example.com",
                "scraped_at": "2026-02-05T10:00:00Z",
            },
        ]
        rep_file = tmp_path / "og_represented_pay_rates.json"
        with open(rep_file, "w") as f:
            json.dump(data, f)
        return rep_file

    def test_preserves_excluded_rates(
        self, mock_excluded_parquet, mock_represented_json, tmp_path
    ):
        """Test that excluded rates are preserved after extension."""
        result = extend_fact_og_pay_rates(
            excluded_path=mock_excluded_parquet,
            represented_source=mock_represented_json,
            output_dir=tmp_path,
        )

        df = pl.read_parquet(result["gold_path"])

        # Original excluded rates should still be present
        excluded = df.filter(pl.col("is_represented") == False)
        assert excluded.height == 3

    def test_adds_represented_rates(
        self, mock_excluded_parquet, mock_represented_json, tmp_path
    ):
        """Test that represented rates are added."""
        result = extend_fact_og_pay_rates(
            excluded_path=mock_excluded_parquet,
            represented_source=mock_represented_json,
            output_dir=tmp_path,
        )

        df = pl.read_parquet(result["gold_path"])

        # Represented rates should be added
        represented = df.filter(pl.col("is_represented") == True)
        assert represented.height == 2

    def test_is_represented_flag_correct(
        self, mock_excluded_parquet, mock_represented_json, tmp_path
    ):
        """Test that is_represented flag is correctly set."""
        result = extend_fact_og_pay_rates(
            excluded_path=mock_excluded_parquet,
            represented_source=mock_represented_json,
            output_dir=tmp_path,
        )

        df = pl.read_parquet(result["gold_path"])

        # Excluded rates have False
        excluded = df.filter(pl.col("og_code") == "AS")
        assert all(not r for r in excluded["is_represented"].to_list())

        # Represented rates have True
        represented = df.filter(pl.col("og_code") == "EC")
        assert all(r for r in represented["is_represented"].to_list())

    def test_collective_agreement_id_linked(
        self, mock_excluded_parquet, mock_represented_json, tmp_path
    ):
        """Test that collective_agreement_id FK is preserved."""
        result = extend_fact_og_pay_rates(
            excluded_path=mock_excluded_parquet,
            represented_source=mock_represented_json,
            output_dir=tmp_path,
        )

        df = pl.read_parquet(result["gold_path"])

        # Represented rates have collective_agreement_id
        ec_rates = df.filter(pl.col("og_code") == "EC")
        assert all(
            ca_id == "ca-ec-123"
            for ca_id in ec_rates["collective_agreement_id"].to_list()
        )

    def test_row_count_increases(
        self, mock_excluded_parquet, mock_represented_json, tmp_path
    ):
        """Test that row count increases after extension."""
        result = extend_fact_og_pay_rates(
            excluded_path=mock_excluded_parquet,
            represented_source=mock_represented_json,
            output_dir=tmp_path,
        )

        # 3 excluded + 2 represented = 5 total
        assert result["row_count"] == 5
        assert result["excluded_count"] == 3
        assert result["represented_count"] == 2

    def test_handles_missing_represented_source(self, mock_excluded_parquet, tmp_path):
        """Test that extension works without represented source."""
        result = extend_fact_og_pay_rates(
            excluded_path=mock_excluded_parquet,
            represented_source=tmp_path / "nonexistent.json",
            output_dir=tmp_path,
        )

        # Should still have excluded rates
        assert result["row_count"] == 3
        assert result["represented_count"] == 0


class TestIngestAll:
    """Tests for full ingestion pipeline."""

    @pytest.fixture
    def setup_files(self, tmp_path):
        """Set up all required files for full ingestion."""
        # Excluded pay rates
        excluded_df = pl.DataFrame({
            "og_subgroup_code": ["AS"],
            "og_code": ["AS"],
            "classification_level": ["AS-01"],
            "step": pl.Series([1], dtype=pl.Int32),
            "annual_rate": [50000.0],
            "hourly_rate": [None],
            "effective_date": ["2024-01-01"],
            "is_represented": [False],
            "collective_agreement": [None],
            "_source_url": ["https://example.com"],
            "_scraped_at": ["2026-02-05T10:00:00Z"],
            "_source_file": ["data/tbs/og_pay_rates_en.json"],
            "_ingested_at": ["2026-02-05T10:00:00Z"],
            "_batch_id": ["batch-123"],
            "_layer": ["gold"],
        })
        excluded_path = tmp_path / "gold" / "fact_og_pay_rates.parquet"
        excluded_path.parent.mkdir(parents=True, exist_ok=True)
        excluded_df.write_parquet(excluded_path)

        # Collective agreements
        ca_data = [
            {
                "agreement_id": "ca-ec-123",
                "agreement_name": "EC Agreement",
                "og_code": "EC",
                "og_subgroup_codes": ["EC"],
                "bargaining_agent": "CAPE",
                "source_url": "https://example.com",
                "scraped_at": "2026-02-05T10:00:00Z",
            },
        ]
        ca_path = tmp_path / "tbs" / "collective_agreements.json"
        ca_path.parent.mkdir(parents=True, exist_ok=True)
        with open(ca_path, "w") as f:
            json.dump(ca_data, f)

        # Represented pay rates
        rep_data = [
            {
                "og_code": "EC",
                "og_subgroup_code": "EC",
                "classification_level": "EC-01",
                "step": 1,
                "annual_rate": 55567.0,
                "effective_date": "2021-06-22",
                "collective_agreement_id": "ca-ec-123",
                "source_url": "https://example.com",
                "scraped_at": "2026-02-05T10:00:00Z",
            },
        ]
        rep_path = tmp_path / "tbs" / "og_represented_pay_rates.json"
        with open(rep_path, "w") as f:
            json.dump(rep_data, f)

        return {
            "excluded_path": excluded_path,
            "ca_path": ca_path,
            "rep_path": rep_path,
            "tmp_path": tmp_path,
        }

    def test_ingest_all_creates_both_tables(self, setup_files):
        """Test that ingest_all creates both dimension and fact tables."""
        files = setup_files

        with patch(
            "jobforge.ingestion.og_represented_pay.DEFAULT_EXCLUDED_SOURCE",
            files["excluded_path"],
        ), patch(
            "jobforge.ingestion.og_represented_pay.DEFAULT_CA_SOURCE",
            files["ca_path"],
        ), patch(
            "jobforge.ingestion.og_represented_pay.DEFAULT_REPRESENTED_SOURCE",
            files["rep_path"],
        ), patch(
            "jobforge.ingestion.og_represented_pay.GOLD_DIR",
            files["tmp_path"] / "gold",
        ):
            result = ingest_all()

        assert "dim_collective_agreement" in result
        assert "fact_og_pay_rates" in result
        assert result["dim_collective_agreement"]["row_count"] == 1
        assert result["fact_og_pay_rates"]["row_count"] == 2  # 1 excluded + 1 represented
