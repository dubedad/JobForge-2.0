"""Tests for OG allowances ingestion pipeline."""

import json
from decimal import Decimal
from pathlib import Path

import polars as pl
import pytest

from jobforge.ingestion.og_allowances import (
    ingest_fact_og_allowances,
    normalize_allowance_type,
    normalize_og_codes,
    validate_amounts,
)


class TestSilverTransforms:
    """Tests for silver layer transforms."""

    def test_normalize_allowance_type_lowercase(self):
        """normalize_allowance_type converts to lowercase with underscores."""
        df = pl.DataFrame({
            "allowance_type": ["Bilingual Bonus", "SUPERVISORY", "isolated_post"],
        }).lazy()

        result = normalize_allowance_type(df).collect()

        assert result["allowance_type"].to_list() == [
            "bilingual_bonus",
            "supervisory",
            "isolated_post",
        ]

    def test_validate_amounts_filters_invalid(self):
        """validate_amounts removes rows with non-positive amounts."""
        df = pl.DataFrame({
            "amount": [800.0, -100.0, None, 0.0],
        }).lazy()

        result = validate_amounts(df).collect()

        # Should keep positive and null, filter negative and zero
        amounts = result["amount"].to_list()
        assert 800.0 in amounts
        assert None in amounts
        assert len(result) == 2

    def test_normalize_og_codes_uppercase(self):
        """normalize_og_codes converts to uppercase, preserves null."""
        df = pl.DataFrame({
            "og_code": ["pe", "AO", None],
        }).lazy()

        result = normalize_og_codes(df).collect()

        codes = result["og_code"].to_list()
        assert "PE" in codes
        assert "AO" in codes
        assert None in codes


class TestIngestFactOgAllowances:
    """Integration tests for the full ingestion pipeline."""

    def test_ingest_creates_parquet_file(self):
        """ingest_fact_og_allowances creates gold parquet file."""
        source_path = Path("data/tbs/og_allowances.json")
        if not source_path.exists():
            pytest.skip("Source file not available")

        result = ingest_fact_og_allowances()

        assert result["gold_path"].exists()
        assert result["row_count"] > 0

    def test_ingest_produces_rows_with_expected_schema(self):
        """Ingested table has expected columns."""
        gold_path = Path("data/gold/fact_og_allowances.parquet")
        if not gold_path.exists():
            # Try to create it
            source_path = Path("data/tbs/og_allowances.json")
            if not source_path.exists():
                pytest.skip("Source file not available")
            ingest_fact_og_allowances()

        df = pl.read_parquet(gold_path)

        expected_columns = [
            "allowance_id",
            "allowance_type",
            "allowance_name",
            "amount",
            "rate_type",
            "og_code",
            "eligibility_criteria",
        ]
        for col in expected_columns:
            assert col in df.columns, f"Missing column: {col}"

    def test_ingest_has_provenance_columns(self):
        """Ingested table has provenance columns."""
        gold_path = Path("data/gold/fact_og_allowances.parquet")
        if not gold_path.exists():
            source_path = Path("data/tbs/og_allowances.json")
            if not source_path.exists():
                pytest.skip("Source file not available")
            ingest_fact_og_allowances()

        df = pl.read_parquet(gold_path)

        provenance_columns = [
            "_source_url",
            "_scraped_at",
            "_source_file",
            "_ingested_at",
            "_batch_id",
            "_layer",
        ]
        for col in provenance_columns:
            assert col in df.columns, f"Missing provenance column: {col}"

    def test_ingest_amounts_positive_or_null(self):
        """Amounts are positive where not null."""
        gold_path = Path("data/gold/fact_og_allowances.parquet")
        if not gold_path.exists():
            source_path = Path("data/tbs/og_allowances.json")
            if not source_path.exists():
                pytest.skip("Source file not available")
            ingest_fact_og_allowances()

        df = pl.read_parquet(gold_path)

        # Check non-null amounts are positive
        amounts = df.filter(pl.col("amount").is_not_null())["amount"]
        if len(amounts) > 0:
            assert all(a > 0 for a in amounts.to_list())


class TestAllowanceTypeCategories:
    """Tests for allowance type validation."""

    def test_multiple_allowance_types_present(self):
        """Fact table contains multiple allowance types."""
        gold_path = Path("data/gold/fact_og_allowances.parquet")
        if not gold_path.exists():
            source_path = Path("data/tbs/og_allowances.json")
            if not source_path.exists():
                pytest.skip("Source file not available")
            ingest_fact_og_allowances()

        df = pl.read_parquet(gold_path)

        allowance_types = df["allowance_type"].unique().to_list()
        # Should have at least bilingual_bonus
        assert "bilingual_bonus" in allowance_types
        # Should have multiple types
        assert len(allowance_types) >= 2

    def test_bilingual_bonus_has_amount(self):
        """Bilingual bonus records have amount populated."""
        gold_path = Path("data/gold/fact_og_allowances.parquet")
        if not gold_path.exists():
            source_path = Path("data/tbs/og_allowances.json")
            if not source_path.exists():
                pytest.skip("Source file not available")
            ingest_fact_og_allowances()

        df = pl.read_parquet(gold_path)

        bilingual = df.filter(
            (pl.col("allowance_type") == "bilingual_bonus") &
            (pl.col("amount").is_not_null())
        )
        # At least one bilingual bonus should have amount
        assert len(bilingual) >= 1


class TestMinimumRecordCount:
    """Tests for minimum record requirements."""

    def test_minimum_10_allowance_records(self):
        """Fact table has at least 10 allowance records."""
        gold_path = Path("data/gold/fact_og_allowances.parquet")
        if not gold_path.exists():
            source_path = Path("data/tbs/og_allowances.json")
            if not source_path.exists():
                pytest.skip("Source file not available")
            ingest_fact_og_allowances()

        df = pl.read_parquet(gold_path)

        assert len(df) >= 10, f"Expected >=10 rows, got {len(df)}"


class TestCatalogMetadata:
    """Tests for catalog metadata file."""

    def test_catalog_exists(self):
        """Catalog metadata file exists."""
        catalog_path = Path("data/catalog/tables/fact_og_allowances.json")
        assert catalog_path.exists(), "Catalog file not found"

    def test_catalog_has_required_fields(self):
        """Catalog has required metadata fields."""
        catalog_path = Path("data/catalog/tables/fact_og_allowances.json")
        if not catalog_path.exists():
            pytest.skip("Catalog file not available")

        with open(catalog_path) as f:
            metadata = json.load(f)

        assert metadata["table_name"] == "fact_og_allowances"
        assert "description" in metadata
        assert "columns" in metadata
        assert "relationships" in metadata

    def test_catalog_has_allowance_type_column(self):
        """Catalog describes allowance_type column."""
        catalog_path = Path("data/catalog/tables/fact_og_allowances.json")
        if not catalog_path.exists():
            pytest.skip("Catalog file not available")

        with open(catalog_path) as f:
            metadata = json.load(f)

        assert "allowance_type" in metadata["columns"]
        assert "description" in metadata["columns"]["allowance_type"]

    def test_catalog_has_og_code_relationship(self):
        """Catalog defines FK relationship to dim_og."""
        catalog_path = Path("data/catalog/tables/fact_og_allowances.json")
        if not catalog_path.exists():
            pytest.skip("Catalog file not available")

        with open(catalog_path) as f:
            metadata = json.load(f)

        relationships = metadata.get("relationships", [])
        dim_og_rel = next(
            (r for r in relationships if r.get("to_table") == "dim_og"),
            None
        )
        assert dim_og_rel is not None, "Missing relationship to dim_og"
        assert dim_og_rel["from_column"] == "og_code"
        assert dim_og_rel["nullable"] is True
