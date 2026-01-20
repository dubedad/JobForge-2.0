"""Tests for Classification Policy compliance log generator.

Tests the ClassificationComplianceLog generator for NOC-based compliance.
"""

from pathlib import Path

import pytest

from jobforge.governance.compliance.classification import ClassificationComplianceLog
from jobforge.governance.compliance.models import ComplianceLog, ComplianceStatus
from jobforge.pipeline.config import PipelineConfig


@pytest.fixture
def config() -> PipelineConfig:
    """Pipeline configuration pointing to real data."""
    return PipelineConfig()


@pytest.fixture
def classification_generator(config: PipelineConfig) -> ClassificationComplianceLog:
    """Classification compliance log generator."""
    return ClassificationComplianceLog(config)


class TestClassificationComplianceLog:
    """Tests for Classification compliance log generation."""

    def test_generates_valid_compliance_log(
        self, classification_generator: ClassificationComplianceLog
    ) -> None:
        """Verify generator produces valid ComplianceLog."""
        log = classification_generator.generate()

        assert isinstance(log, ComplianceLog)
        assert log.framework_name == ClassificationComplianceLog.FRAMEWORK_NAME
        assert "NOC" in log.framework_name or "Classification" in log.framework_name

    def test_has_all_classification_requirements(
        self, classification_generator: ClassificationComplianceLog
    ) -> None:
        """Verify all classification requirements are covered."""
        log = classification_generator.generate()

        requirement_ids = {e.requirement_id for e in log.entries}
        expected_ids = {f"CLASS-{i}" for i in range(1, 7)}

        assert requirement_ids == expected_ids, f"Missing: {expected_ids - requirement_ids}"
        assert len(log.entries) == 6

    def test_noc_alignment_compliant(
        self, classification_generator: ClassificationComplianceLog
    ) -> None:
        """Verify NOC alignment requirement is compliant."""
        log = classification_generator.generate()
        entry = next(e for e in log.entries if e.requirement_id == "CLASS-1")

        assert entry.status == ComplianceStatus.COMPLIANT
        assert "NOC" in entry.requirement_text or "National" in entry.requirement_text
        assert any("dim_noc" in ref for ref in entry.evidence_references)

    def test_hierarchy_integrity_compliant(
        self, classification_generator: ClassificationComplianceLog
    ) -> None:
        """Verify hierarchy integrity requirement is compliant."""
        log = classification_generator.generate()
        entry = next(e for e in log.entries if e.requirement_id == "CLASS-2")

        assert entry.status == ComplianceStatus.COMPLIANT
        assert "hierarchy" in entry.section.lower()
        # Should mention the 5 levels
        assert "L1" in entry.notes or "5-level" in entry.notes or "5 level" in entry.notes

    def test_title_mapping_compliant(
        self, classification_generator: ClassificationComplianceLog
    ) -> None:
        """Verify title mapping requirement is compliant."""
        log = classification_generator.generate()
        entry = next(e for e in log.entries if e.requirement_id == "CLASS-3")

        assert entry.status == ComplianceStatus.COMPLIANT
        assert "title" in entry.section.lower()
        assert any("title" in ref for ref in entry.evidence_references)

    def test_attribute_inheritance_compliant(
        self, classification_generator: ClassificationComplianceLog
    ) -> None:
        """Verify attribute inheritance requirement is compliant."""
        log = classification_generator.generate()
        entry = next(e for e in log.entries if e.requirement_id == "CLASS-4")

        assert entry.status == ComplianceStatus.COMPLIANT
        assert "inheritance" in entry.section.lower()
        assert any("imputation" in ref for ref in entry.evidence_references)

    def test_external_crosswalk_compliant(
        self, classification_generator: ClassificationComplianceLog
    ) -> None:
        """Verify external crosswalk requirement is compliant."""
        log = classification_generator.generate()
        entry = next(e for e in log.entries if e.requirement_id == "CLASS-5")

        assert entry.status == ComplianceStatus.COMPLIANT
        assert "crosswalk" in entry.section.lower() or "external" in entry.section.lower()
        assert any("external" in ref or "onet" in ref for ref in entry.evidence_references)

    def test_evidence_traceability_compliant(
        self, classification_generator: ClassificationComplianceLog
    ) -> None:
        """Verify evidence traceability requirement is compliant."""
        log = classification_generator.generate()
        entry = next(e for e in log.entries if e.requirement_id == "CLASS-6")

        assert entry.status == ComplianceStatus.COMPLIANT
        assert "traceability" in entry.section.lower() or "evidence" in entry.section.lower()
        assert any("lineage" in ref for ref in entry.evidence_references)


class TestClassificationEvidenceReferences:
    """Tests that Classification evidence references point to real artifacts."""

    def test_dim_noc_exists(self, config: PipelineConfig) -> None:
        """Verify dim_noc table exists."""
        gold_path = config.gold_path()
        dim_noc_path = gold_path / "dim_noc.parquet"
        assert dim_noc_path.exists(), "dim_noc.parquet should exist in gold"

    def test_noc_ingestion_module_exists(self) -> None:
        """Verify NOC ingestion module exists."""
        noc_path = Path("src/jobforge/ingestion/noc.py")
        assert noc_path.exists(), "NOC ingestion module should exist"

    def test_imputation_module_exists(self) -> None:
        """Verify imputation module exists."""
        imputation_path = Path("src/jobforge/imputation")
        assert imputation_path.exists(), "Imputation module should exist"

    def test_external_module_exists(self) -> None:
        """Verify external adapters module exists."""
        external_path = Path("src/jobforge/external")
        assert external_path.exists(), "External adapters module should exist"

    def test_lineage_logs_exist(self, config: PipelineConfig) -> None:
        """Verify lineage logs exist."""
        lineage_path = config.catalog_lineage_path()
        assert lineage_path.exists(), "Lineage directory should exist"

        lineage_files = list(lineage_path.glob("*.json"))
        assert len(lineage_files) > 0, "Should have lineage log files"


class TestClassificationLogSummary:
    """Tests for Classification compliance log summary statistics."""

    def test_all_requirements_compliant(
        self, classification_generator: ClassificationComplianceLog
    ) -> None:
        """Verify all classification requirements are compliant."""
        log = classification_generator.generate()
        summary = log.summary

        # All 6 requirements should be compliant
        assert summary["compliant"] == 6
        assert summary["not_applicable"] == 0
        assert summary["partial"] == 0
        assert summary["not_implemented"] == 0

    def test_compliance_rate_100_percent(
        self, classification_generator: ClassificationComplianceLog
    ) -> None:
        """Verify 100% compliance rate."""
        log = classification_generator.generate()
        assert log.compliance_rate == 1.0
