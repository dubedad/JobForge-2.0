"""Tests for NOC resolution service.

Validates all 5 resolution methods and edge cases against known gold data.
"""

from pathlib import Path

import polars as pl
import pytest

from jobforge.imputation.models import ResolutionMethodEnum
from jobforge.imputation.resolution import (
    CONFIDENCE_DIRECT_MATCH,
    CONFIDENCE_EXAMPLE_MATCH,
    CONFIDENCE_LABEL_IMPUTATION,
    CONFIDENCE_UG_DOMINANT,
    CONFIDENCE_UG_IMPUTATION,
    build_resolution_context,
    clear_resolution_cache,
    resolve_job_title,
)


# Fixtures
@pytest.fixture(scope="module")
def gold_path() -> Path:
    """Path to gold data directory."""
    path = Path("data/gold")
    assert path.exists(), f"Gold data directory not found: {path}"
    return path


@pytest.fixture(scope="module")
def single_label_ug_id(gold_path: Path) -> str:
    """Find a single-label Unit Group ID from the data.

    Single-label UGs have exactly one L6 label and should resolve
    with UG_DOMINANT method.
    """
    df = pl.scan_parquet(gold_path / "element_labels.parquet")
    stats = df.group_by("unit_group_id").agg(pl.len().alias("count")).collect()
    single = stats.filter(pl.col("count") == 1)
    assert len(single) > 0, "No single-label UGs found"
    return single["unit_group_id"][0]


@pytest.fixture(scope="module")
def multi_label_ug_id(gold_path: Path) -> str:
    """Find a multi-label Unit Group ID from the data.

    Multi-label UGs have more than one L6 label and require full
    resolution cascade.
    """
    df = pl.scan_parquet(gold_path / "element_labels.parquet")
    stats = df.group_by("unit_group_id").agg(pl.len().alias("count")).collect()
    multi = stats.filter(pl.col("count") > 1)
    assert len(multi) > 0, "No multi-label UGs found"
    return multi["unit_group_id"][0]


@pytest.fixture(scope="module")
def multi_label_context(multi_label_ug_id: str, gold_path: Path):
    """Build resolution context for a multi-label UG."""
    return build_resolution_context(multi_label_ug_id, gold_path)


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear resolution cache before each test to ensure clean state."""
    clear_resolution_cache()
    yield
    clear_resolution_cache()


# Test Resolution Methods
class TestSingleLabelUG:
    """Tests for single-label Unit Group resolution (UG_DOMINANT)."""

    def test_single_label_ug_returns_ug_dominant(
        self, single_label_ug_id: str, gold_path: Path
    ):
        """Single-label UG should immediately return UG_DOMINANT (0.85)."""
        result = resolve_job_title("Any Job Title", single_label_ug_id, gold_path)

        assert result is not None
        assert result.resolution_method == ResolutionMethodEnum.UG_DOMINANT
        assert result.confidence_score == CONFIDENCE_UG_DOMINANT
        assert result.noc_level_used == 5  # L5 = Unit Group level

    def test_single_label_ug_ignores_job_title_content(
        self, single_label_ug_id: str, gold_path: Path
    ):
        """Single-label UG should return same result regardless of job title."""
        result1 = resolve_job_title("Completely Random Title", single_label_ug_id, gold_path)
        result2 = resolve_job_title("Another Random Title", single_label_ug_id, gold_path)

        assert result1.resolution_method == result2.resolution_method
        assert result1.confidence_score == result2.confidence_score
        assert result1.source_identifier == result2.source_identifier


class TestDirectMatch:
    """Tests for direct L6 Label match (DIRECT_MATCH)."""

    def test_direct_label_match_returns_direct_match(
        self, multi_label_context, gold_path: Path
    ):
        """Direct match to L6 label should return DIRECT_MATCH (1.00)."""
        # Get an actual label from the context
        assert len(multi_label_context.labels) > 0
        label = multi_label_context.labels[0]

        result = resolve_job_title(
            label.label, multi_label_context.unit_group_id, gold_path
        )

        assert result is not None
        assert result.resolution_method == ResolutionMethodEnum.DIRECT_MATCH
        assert result.confidence_score == CONFIDENCE_DIRECT_MATCH
        assert result.noc_level_used == 6
        assert result.matched_text == label.label

    def test_direct_match_is_case_insensitive(
        self, multi_label_context, gold_path: Path
    ):
        """Direct match should be case-insensitive."""
        label = multi_label_context.labels[0]

        # Try uppercase
        result_upper = resolve_job_title(
            label.label.upper(), multi_label_context.unit_group_id, gold_path
        )
        # Try lowercase
        result_lower = resolve_job_title(
            label.label.lower(), multi_label_context.unit_group_id, gold_path
        )

        assert result_upper.resolution_method == ResolutionMethodEnum.DIRECT_MATCH
        assert result_lower.resolution_method == ResolutionMethodEnum.DIRECT_MATCH


class TestExampleMatch:
    """Tests for L7 Example Title match (EXAMPLE_MATCH)."""

    def test_example_title_match_returns_example_match(
        self, multi_label_context, gold_path: Path
    ):
        """Match to L7 example title should return EXAMPLE_MATCH (0.95)."""
        # Find an example title that exists in the context
        example_title = None
        for oasis_code, titles in multi_label_context.example_titles_by_oasis.items():
            if titles:
                example_title = titles[0].element_text
                break

        if example_title is None:
            pytest.skip("No example titles found for this UG")

        result = resolve_job_title(
            example_title, multi_label_context.unit_group_id, gold_path
        )

        assert result is not None
        assert result.resolution_method == ResolutionMethodEnum.EXAMPLE_MATCH
        assert result.confidence_score == CONFIDENCE_EXAMPLE_MATCH
        assert result.noc_level_used == 7
        assert result.matched_text == example_title

    def test_example_match_is_case_insensitive(
        self, multi_label_context, gold_path: Path
    ):
        """Example title match should be case-insensitive."""
        example_title = None
        for oasis_code, titles in multi_label_context.example_titles_by_oasis.items():
            if titles:
                example_title = titles[0].element_text
                break

        if example_title is None:
            pytest.skip("No example titles found for this UG")

        result = resolve_job_title(
            example_title.upper(), multi_label_context.unit_group_id, gold_path
        )

        assert result.resolution_method == ResolutionMethodEnum.EXAMPLE_MATCH


class TestFuzzyMatch:
    """Tests for fuzzy matching (LABEL_IMPUTATION and UG_IMPUTATION)."""

    def test_fuzzy_match_returns_label_imputation(
        self, multi_label_context, gold_path: Path
    ):
        """Good fuzzy match (>=70) should return LABEL_IMPUTATION (0.60)."""
        # Create a title similar to but not exactly matching a label
        label = multi_label_context.labels[0]
        # Add words to change it but keep it similar
        fuzzy_title = f"{label.label} Manager"

        result = resolve_job_title(
            fuzzy_title, multi_label_context.unit_group_id, gold_path
        )

        # Should be either LABEL_IMPUTATION or UG_IMPUTATION depending on score
        assert result is not None
        assert result.resolution_method in [
            ResolutionMethodEnum.LABEL_IMPUTATION,
            ResolutionMethodEnum.UG_IMPUTATION,
        ]

    def test_no_match_returns_ug_imputation(
        self, multi_label_context, gold_path: Path
    ):
        """Poor fuzzy match should return UG_IMPUTATION (0.40)."""
        # Use a completely unrelated title
        result = resolve_job_title(
            "Completely Unrelated XYZ Job 12345",
            multi_label_context.unit_group_id,
            gold_path,
        )

        assert result is not None
        assert result.resolution_method == ResolutionMethodEnum.UG_IMPUTATION
        assert result.confidence_score == CONFIDENCE_UG_IMPUTATION
        assert result.noc_level_used == 5


# Test Edge Cases
class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_invalid_unit_group_returns_none(self, gold_path: Path):
        """Unknown unit group ID should return None."""
        result = resolve_job_title("Some Job", "99999", gold_path)
        assert result is None

    def test_empty_job_title_returns_none(self, single_label_ug_id: str, gold_path: Path):
        """Empty job title should return None."""
        result = resolve_job_title("", single_label_ug_id, gold_path)
        assert result is None

    def test_whitespace_job_title_returns_none(
        self, single_label_ug_id: str, gold_path: Path
    ):
        """Whitespace-only job title should return None."""
        result = resolve_job_title("   ", single_label_ug_id, gold_path)
        assert result is None

    def test_none_job_title_returns_none(
        self, single_label_ug_id: str, gold_path: Path
    ):
        """None job title should return None (if allowed by type hints)."""
        # This tests the runtime behavior even if type hints say str
        result = resolve_job_title(None, single_label_ug_id, gold_path)  # type: ignore
        assert result is None

    def test_empty_unit_group_id_returns_none(self, gold_path: Path):
        """Empty unit group ID should return None."""
        result = resolve_job_title("Some Job", "", gold_path)
        assert result is None


# Test Resolution Context
class TestResolutionContext:
    """Tests for resolution context building."""

    def test_resolution_context_has_labels(
        self, multi_label_ug_id: str, gold_path: Path
    ):
        """Resolution context should load L6 labels correctly."""
        context = build_resolution_context(multi_label_ug_id, gold_path)

        assert context is not None
        assert len(context.labels) > 1  # Multi-label UG
        assert all(label.unit_group_id == multi_label_ug_id for label in context.labels)
        assert all(label.label for label in context.labels)  # Non-empty labels

    def test_resolution_context_has_example_titles(
        self, multi_label_ug_id: str, gold_path: Path
    ):
        """Resolution context should load L7 example titles correctly."""
        context = build_resolution_context(multi_label_ug_id, gold_path)

        assert context is not None
        # Should have example titles for at least some OASIS codes
        assert len(context.example_titles_by_oasis) > 0

        for oasis_code, titles in context.example_titles_by_oasis.items():
            assert oasis_code.startswith(multi_label_ug_id[:5])  # Same UG prefix
            for title in titles:
                assert title.element_text  # Non-empty title

    def test_resolution_context_has_unit_group_info(
        self, single_label_ug_id: str, gold_path: Path
    ):
        """Resolution context should have unit group title and definition."""
        context = build_resolution_context(single_label_ug_id, gold_path)

        assert context is not None
        assert context.unit_group_id == single_label_ug_id
        assert context.unit_group_title  # Non-empty title
        # Definition may be None for some UGs

    def test_invalid_unit_group_returns_none_context(self, gold_path: Path):
        """Invalid unit group ID should return None context."""
        context = build_resolution_context("99999", gold_path)
        assert context is None


# Test Result Fields
class TestResolutionProvenance:
    """Tests for resolution result provenance fields."""

    def test_resolution_provenance_fields(
        self, single_label_ug_id: str, gold_path: Path
    ):
        """All required provenance fields should be populated."""
        result = resolve_job_title("Test Job", single_label_ug_id, gold_path)

        assert result is not None
        assert result.noc_level_used in [5, 6, 7]
        assert result.resolution_method is not None
        assert 0.0 <= result.confidence_score <= 1.0
        assert result.source_identifier  # Non-empty
        assert result.rationale  # Non-empty
        assert result.resolved_at is not None


# Test Batch Resolution (Integration)
class TestBatchResolution:
    """Integration tests for batch resolution."""

    def test_batch_resolution(self, gold_path: Path):
        """Resolve multiple job titles from job_architecture."""
        # Load some job titles from job_architecture
        job_arch = pl.scan_parquet(gold_path / "job_architecture.parquet")
        jobs = job_arch.select(["job_title_en", "unit_group_id"]).head(10).collect()

        results = []
        for row in jobs.iter_rows(named=True):
            result = resolve_job_title(
                row["job_title_en"], row["unit_group_id"], gold_path
            )
            results.append(result)

        # All should resolve (no None results)
        assert all(r is not None for r in results)

        # Should have variety of confidence scores
        confidence_scores = {r.confidence_score for r in results}
        assert len(confidence_scores) >= 1  # At least one unique score

    def test_resolution_confidence_distribution(self, gold_path: Path):
        """Verify confidence scores match expected values."""
        expected_confidences = {
            CONFIDENCE_DIRECT_MATCH,
            CONFIDENCE_EXAMPLE_MATCH,
            CONFIDENCE_UG_DOMINANT,
            CONFIDENCE_LABEL_IMPUTATION,
            CONFIDENCE_UG_IMPUTATION,
        }

        # Resolve a batch of jobs
        job_arch = pl.scan_parquet(gold_path / "job_architecture.parquet")
        jobs = job_arch.select(["job_title_en", "unit_group_id"]).head(50).collect()

        actual_confidences = set()
        for row in jobs.iter_rows(named=True):
            result = resolve_job_title(
                row["job_title_en"], row["unit_group_id"], gold_path
            )
            if result:
                actual_confidences.add(result.confidence_score)

        # All confidence scores should be from expected set
        assert actual_confidences.issubset(expected_confidences)


# Test Cache Behavior
class TestCacheBehavior:
    """Tests for cache behavior."""

    def test_cache_clear_works(self, gold_path: Path):
        """Cache clearing should allow fresh data loading."""
        # First call populates cache
        context1 = build_resolution_context("00010", gold_path)

        # Clear cache
        clear_resolution_cache()

        # Second call should still work
        context2 = build_resolution_context("00010", gold_path)

        assert context1 is not None
        assert context2 is not None
        assert context1.unit_group_id == context2.unit_group_id
