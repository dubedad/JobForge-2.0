"""Integration tests for CAF Phase 15 success criteria.

Tests validate all success criteria from ROADMAP.md Phase 15:
1. User can query all CAF occupations with full metadata (88 actual)
2. User can query CAF job families (11 families)
3. User can look up civilian equivalents for any CAF occupation
4. User can find NOC codes associated with CAF occupations
5. User can find Job Architecture matches with confidence scores
6. All tables have full provenance

Note: ROADMAP.md mentions 107 occupations, but actual forces.ca sitemap
yields 88 unique careers (per 15-01, 15-02, 15-03 summaries).
"""

import json
from pathlib import Path

import polars as pl
import pytest


# =============================================================================
# Fixture: Load gold tables once per test session
# =============================================================================


@pytest.fixture(scope="module")
def gold_dir():
    """Path to gold directory."""
    return Path("data/gold")


@pytest.fixture(scope="module")
def dim_caf_occupation(gold_dir):
    """Load dim_caf_occupation table."""
    path = gold_dir / "dim_caf_occupation.parquet"
    if not path.exists():
        pytest.skip("dim_caf_occupation.parquet not available")
    return pl.read_parquet(path)


@pytest.fixture(scope="module")
def dim_caf_job_family(gold_dir):
    """Load dim_caf_job_family table."""
    path = gold_dir / "dim_caf_job_family.parquet"
    if not path.exists():
        pytest.skip("dim_caf_job_family.parquet not available")
    return pl.read_parquet(path)


@pytest.fixture(scope="module")
def bridge_caf_noc(gold_dir):
    """Load bridge_caf_noc table."""
    path = gold_dir / "bridge_caf_noc.parquet"
    if not path.exists():
        pytest.skip("bridge_caf_noc.parquet not available")
    return pl.read_parquet(path)


@pytest.fixture(scope="module")
def bridge_caf_ja(gold_dir):
    """Load bridge_caf_ja table."""
    path = gold_dir / "bridge_caf_ja.parquet"
    if not path.exists():
        pytest.skip("bridge_caf_ja.parquet not available")
    return pl.read_parquet(path)


@pytest.fixture(scope="module")
def wiq_schema():
    """Load WiQ schema."""
    path = Path("data/catalog/schemas/wiq_schema.json")
    if not path.exists():
        pytest.skip("wiq_schema.json not available")
    return json.loads(path.read_text())


# =============================================================================
# Success Criterion 1: User can query all CAF occupations with full metadata
# =============================================================================


class TestQueryCafOccupations:
    """Tests for Success Criterion 1: Query all CAF occupations."""

    def test_occupation_count(self, dim_caf_occupation):
        """All 88 CAF occupations are queryable."""
        assert len(dim_caf_occupation) == 88

    def test_occupation_has_career_id(self, dim_caf_occupation):
        """Every occupation has a career_id (primary key)."""
        assert dim_caf_occupation["career_id"].null_count() == 0

    def test_occupation_has_bilingual_titles(self, dim_caf_occupation):
        """Every occupation has both EN and FR titles."""
        assert dim_caf_occupation["title_en"].null_count() == 0
        # Per 15-02: 100% bilingual coverage
        assert dim_caf_occupation["title_fr"].null_count() == 0

    def test_occupation_has_job_family(self, dim_caf_occupation):
        """Every occupation has a job_family_id."""
        assert dim_caf_occupation["job_family_id"].null_count() == 0

    def test_occupation_has_overview(self, dim_caf_occupation):
        """Most occupations have overview content."""
        # Allow some nulls but most should have content
        # Note: Some CAF pages don't have overview sections (86% coverage observed)
        en_coverage = (len(dim_caf_occupation) - dim_caf_occupation["overview_en"].null_count()) / len(dim_caf_occupation)
        assert en_coverage > 0.8, f"Only {en_coverage:.0%} have EN overview"

    def test_occupation_has_urls(self, dim_caf_occupation):
        """Every occupation has source URLs."""
        assert dim_caf_occupation["url_en"].null_count() == 0

    def test_occupation_unique_career_ids(self, dim_caf_occupation):
        """Career IDs are unique."""
        unique_count = dim_caf_occupation["career_id"].n_unique()
        total_count = len(dim_caf_occupation)
        assert unique_count == total_count


# =============================================================================
# Success Criterion 2: User can query CAF job families
# =============================================================================


class TestQueryCafJobFamilies:
    """Tests for Success Criterion 2: Query CAF job families."""

    def test_job_family_count(self, dim_caf_job_family):
        """All 11 job families are queryable."""
        assert len(dim_caf_job_family) == 11

    def test_job_family_has_id(self, dim_caf_job_family):
        """Every job family has an ID."""
        assert dim_caf_job_family["job_family_id"].null_count() == 0

    def test_job_family_has_name(self, dim_caf_job_family):
        """Every job family has a name."""
        assert dim_caf_job_family["job_family_name"].null_count() == 0

    def test_job_family_has_career_count(self, dim_caf_job_family):
        """Every job family has a career count."""
        assert dim_caf_job_family["career_count"].null_count() == 0

    def test_job_family_career_counts_sum_to_88(self, dim_caf_job_family):
        """Job family career counts sum to 88 (total occupations)."""
        total = dim_caf_job_family["career_count"].sum()
        assert total == 88

    def test_expected_job_families_present(self, dim_caf_job_family):
        """Expected job families are all present."""
        expected = {
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
        actual = set(dim_caf_job_family["job_family_id"].to_list())
        assert actual == expected


# =============================================================================
# Success Criterion 3: User can look up civilian equivalents
# =============================================================================


class TestCivilianEquivalents:
    """Tests for Success Criterion 3: Look up civilian equivalents."""

    def test_occupations_have_related_civilian(self, dim_caf_occupation):
        """Most occupations have related_civilian_occupations."""
        # This is a JSON array column; check it's not all empty
        non_empty = 0
        for val in dim_caf_occupation["related_civilian_occupations"].to_list():
            if val and val != "[]":
                non_empty += 1
        coverage = non_empty / len(dim_caf_occupation)
        # Per 15-02, related_civilian comes from forces.ca pages
        assert coverage > 0.5, f"Only {coverage:.0%} have related civilian occupations"

    def test_pilot_has_civilian_equivalents(self, dim_caf_occupation):
        """Pilot occupation has civilian equivalents."""
        pilot = dim_caf_occupation.filter(pl.col("career_id") == "pilot")
        if len(pilot) == 0:
            pytest.skip("pilot occupation not found")
        related = pilot["related_civilian_occupations"][0]
        assert related is not None
        assert related != "[]"

    def test_civilian_equivalents_are_json_arrays(self, dim_caf_occupation):
        """related_civilian_occupations are valid JSON arrays."""
        for val in dim_caf_occupation["related_civilian_occupations"].to_list():
            if val:
                parsed = json.loads(val)
                assert isinstance(parsed, list)


# =============================================================================
# Success Criterion 4: User can find NOC codes for CAF occupations
# =============================================================================


class TestCafToNoc:
    """Tests for Success Criterion 4: Find NOC codes for CAF occupations."""

    def test_bridge_has_mappings(self, bridge_caf_noc):
        """Bridge table has mappings."""
        assert len(bridge_caf_noc) > 0

    def test_bridge_has_880_mappings(self, bridge_caf_noc):
        """Bridge table has expected 880 mappings (10 per occupation)."""
        assert len(bridge_caf_noc) == 880

    def test_all_88_caf_occupations_have_noc_mappings(self, bridge_caf_noc):
        """All 88 CAF occupations have NOC mappings."""
        unique_caf = bridge_caf_noc["caf_occupation_id"].n_unique()
        assert unique_caf == 88

    def test_bridge_has_required_columns(self, bridge_caf_noc):
        """Bridge table has all required columns."""
        required = [
            "caf_occupation_id",
            "noc_unit_group_id",
            "noc_title",
            "caf_title",
            "confidence_score",
            "match_method",
            "rationale",
        ]
        for col in required:
            assert col in bridge_caf_noc.columns, f"Missing column: {col}"

    def test_pilot_has_noc_matches(self, bridge_caf_noc):
        """Pilot occupation has NOC matches."""
        pilot_matches = bridge_caf_noc.filter(pl.col("caf_occupation_id") == "pilot")
        assert len(pilot_matches) > 0

    def test_confidence_scores_in_range(self, bridge_caf_noc):
        """Confidence scores are in valid range 0.0-1.0."""
        scores = bridge_caf_noc["confidence_score"]
        assert scores.min() >= 0.0
        assert scores.max() <= 1.0

    def test_match_methods_are_valid(self, bridge_caf_noc):
        """Match methods are one of expected values."""
        valid_methods = {"related_civilian", "title_fuzzy", "best_guess"}
        actual_methods = set(bridge_caf_noc["match_method"].unique().to_list())
        assert actual_methods.issubset(valid_methods)


# =============================================================================
# Success Criterion 5: User can find Job Architecture matches with confidence
# =============================================================================


class TestCafToJa:
    """Tests for Success Criterion 5: Find JA matches with confidence scores."""

    def test_bridge_has_mappings(self, bridge_caf_ja):
        """Bridge table has mappings."""
        assert len(bridge_caf_ja) > 0

    def test_bridge_has_880_mappings(self, bridge_caf_ja):
        """Bridge table has expected 880 mappings (10 per occupation)."""
        assert len(bridge_caf_ja) == 880

    def test_all_88_caf_occupations_have_ja_mappings(self, bridge_caf_ja):
        """All 88 CAF occupations have JA mappings."""
        unique_caf = bridge_caf_ja["caf_occupation_id"].n_unique()
        assert unique_caf == 88

    def test_bridge_has_required_columns(self, bridge_caf_ja):
        """Bridge table has all required columns."""
        required = [
            "caf_occupation_id",
            "ja_job_title_id",
            "ja_job_title_en",
            "caf_title_en",
            "confidence_score",
            "match_method",
            "rationale",
        ]
        for col in required:
            assert col in bridge_caf_ja.columns, f"Missing column: {col}"

    def test_bridge_has_ja_context_columns(self, bridge_caf_ja):
        """Bridge table has JA context columns (per 15-05)."""
        context_cols = ["ja_job_function_en", "ja_job_family_en"]
        for col in context_cols:
            assert col in bridge_caf_ja.columns, f"Missing JA context column: {col}"

    def test_confidence_scores_in_range(self, bridge_caf_ja):
        """Confidence scores are in valid range 0.0-1.0."""
        scores = bridge_caf_ja["confidence_score"]
        assert scores.min() >= 0.0
        assert scores.max() <= 1.0

    def test_match_methods_are_valid(self, bridge_caf_ja):
        """Match methods are one of expected values."""
        valid_methods = {"related_civilian", "title_fuzzy", "best_guess"}
        actual_methods = set(bridge_caf_ja["match_method"].unique().to_list())
        assert actual_methods.issubset(valid_methods)


# =============================================================================
# Success Criterion 6: All tables have full provenance
# =============================================================================


class TestProvenance:
    """Tests for Success Criterion 6: Full provenance on all tables."""

    def test_occupation_has_provenance(self, dim_caf_occupation):
        """dim_caf_occupation has provenance columns."""
        provenance_cols = [
            "_source_url_en",
            "_scraped_at",
            "_source_file",
            "_ingested_at",
            "_batch_id",
            "_layer",
        ]
        for col in provenance_cols:
            assert col in dim_caf_occupation.columns, f"Missing: {col}"

    def test_occupation_provenance_not_null(self, dim_caf_occupation):
        """Provenance columns are populated."""
        assert dim_caf_occupation["_scraped_at"].null_count() == 0
        assert dim_caf_occupation["_batch_id"].null_count() == 0
        assert dim_caf_occupation["_layer"].null_count() == 0

    def test_job_family_has_provenance(self, dim_caf_job_family):
        """dim_caf_job_family has provenance columns."""
        provenance_cols = [
            "_generated_at",
            "_source_file",
            "_ingested_at",
            "_batch_id",
            "_layer",
        ]
        for col in provenance_cols:
            assert col in dim_caf_job_family.columns, f"Missing: {col}"

    def test_noc_bridge_has_provenance(self, bridge_caf_noc):
        """bridge_caf_noc has provenance columns."""
        provenance_cols = [
            "_source_file",
            "_ingested_at",
            "_batch_id",
            "_layer",
        ]
        for col in provenance_cols:
            assert col in bridge_caf_noc.columns, f"Missing: {col}"

    def test_noc_bridge_has_audit_trail(self, bridge_caf_noc):
        """bridge_caf_noc has audit trail columns."""
        audit_cols = ["algorithm_version", "matched_at", "rationale"]
        for col in audit_cols:
            assert col in bridge_caf_noc.columns, f"Missing audit column: {col}"

    def test_ja_bridge_has_provenance(self, bridge_caf_ja):
        """bridge_caf_ja has provenance columns."""
        provenance_cols = [
            "_source_file",
            "_ingested_at",
            "_batch_id",
            "_layer",
        ]
        for col in provenance_cols:
            assert col in bridge_caf_ja.columns, f"Missing: {col}"

    def test_ja_bridge_has_audit_trail(self, bridge_caf_ja):
        """bridge_caf_ja has audit trail columns."""
        audit_cols = ["algorithm_version", "matched_at", "rationale"]
        for col in audit_cols:
            assert col in bridge_caf_ja.columns, f"Missing audit column: {col}"


# =============================================================================
# WiQ Schema Integration Tests
# =============================================================================


class TestWiqSchemaIntegration:
    """Tests for WiQ schema integration."""

    def test_schema_has_caf_tables(self, wiq_schema):
        """WiQ schema includes all 4 CAF tables."""
        table_names = [t["name"] for t in wiq_schema["tables"]]
        caf_tables = [
            "dim_caf_occupation",
            "dim_caf_job_family",
            "bridge_caf_noc",
            "bridge_caf_ja",
        ]
        for table in caf_tables:
            assert table in table_names, f"Missing CAF table: {table}"

    def test_schema_has_caf_relationships(self, wiq_schema):
        """WiQ schema includes CAF relationships."""
        relationships = wiq_schema.get("relationships", [])

        # Check for key relationships
        expected_rels = [
            ("dim_caf_occupation", "dim_caf_job_family"),
            ("bridge_caf_noc", "dim_caf_occupation"),
            ("bridge_caf_noc", "dim_noc"),
            ("bridge_caf_ja", "dim_caf_occupation"),
            ("bridge_caf_ja", "job_architecture"),
        ]

        actual_rels = [(r["from_table"], r["to_table"]) for r in relationships]

        for expected in expected_rels:
            assert expected in actual_rels, f"Missing relationship: {expected}"

    def test_dim_caf_occupation_is_dimension(self, wiq_schema):
        """dim_caf_occupation is typed as dimension."""
        for t in wiq_schema["tables"]:
            if t["name"] == "dim_caf_occupation":
                assert t["table_type"] == "dimension"
                return
        pytest.fail("dim_caf_occupation not found in schema")

    def test_bridge_tables_are_bridge_type(self, wiq_schema):
        """Bridge tables are typed as bridge."""
        for t in wiq_schema["tables"]:
            if t["name"] in ("bridge_caf_noc", "bridge_caf_ja"):
                assert t["table_type"] == "bridge", f"{t['name']} should be bridge type"


# =============================================================================
# Foreign Key Integrity Tests
# =============================================================================


class TestForeignKeyIntegrity:
    """Tests for FK integrity between CAF tables."""

    def test_occupation_job_family_fk_valid(self, dim_caf_occupation, dim_caf_job_family):
        """All occupation job_family_ids exist in job_family table."""
        occ_family_ids = set(dim_caf_occupation["job_family_id"].unique().to_list())
        valid_family_ids = set(dim_caf_job_family["job_family_id"].to_list())

        orphan_ids = occ_family_ids - valid_family_ids
        assert len(orphan_ids) == 0, f"Orphan job_family_ids: {orphan_ids}"

    def test_noc_bridge_caf_fk_valid(self, bridge_caf_noc, dim_caf_occupation):
        """All bridge caf_occupation_ids exist in occupation table."""
        bridge_caf_ids = set(bridge_caf_noc["caf_occupation_id"].unique().to_list())
        valid_caf_ids = set(dim_caf_occupation["career_id"].to_list())

        orphan_ids = bridge_caf_ids - valid_caf_ids
        assert len(orphan_ids) == 0, f"Orphan caf_occupation_ids in bridge_caf_noc: {orphan_ids}"

    def test_ja_bridge_caf_fk_valid(self, bridge_caf_ja, dim_caf_occupation):
        """All JA bridge caf_occupation_ids exist in occupation table."""
        bridge_caf_ids = set(bridge_caf_ja["caf_occupation_id"].unique().to_list())
        valid_caf_ids = set(dim_caf_occupation["career_id"].to_list())

        orphan_ids = bridge_caf_ids - valid_caf_ids
        assert len(orphan_ids) == 0, f"Orphan caf_occupation_ids in bridge_caf_ja: {orphan_ids}"


# =============================================================================
# CLI Integration Tests
# =============================================================================


class TestCliIntegration:
    """Tests for CLI command integration."""

    def test_caf_command_group_imports(self):
        """CAF command group can be imported."""
        from jobforge.cli.commands import caf_app
        assert caf_app is not None

    def test_caf_refresh_function_exists(self):
        """caf_refresh function exists."""
        from jobforge.cli.commands import caf_refresh
        assert callable(caf_refresh)

    def test_caf_status_function_exists(self):
        """caf_status function exists."""
        from jobforge.cli.commands import caf_status
        assert callable(caf_status)
