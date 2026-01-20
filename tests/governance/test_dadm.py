"""Tests for DADM compliance log generator.

Tests the DADMComplianceLog generator against real WiQ artifacts.
"""

from pathlib import Path

import pytest

from jobforge.governance.compliance.dadm import DADMComplianceLog
from jobforge.governance.compliance.models import ComplianceLog, ComplianceStatus
from jobforge.pipeline.config import PipelineConfig


@pytest.fixture
def config() -> PipelineConfig:
    """Pipeline configuration pointing to real data."""
    return PipelineConfig()


@pytest.fixture
def dadm_generator(config: PipelineConfig) -> DADMComplianceLog:
    """DADM compliance log generator."""
    return DADMComplianceLog(config)


class TestDADMComplianceLog:
    """Tests for DADM compliance log generation."""

    def test_generates_valid_compliance_log(
        self, dadm_generator: DADMComplianceLog
    ) -> None:
        """Verify generator produces valid ComplianceLog."""
        log = dadm_generator.generate()

        assert isinstance(log, ComplianceLog)
        assert log.framework_name == DADMComplianceLog.FRAMEWORK_NAME
        assert "DADM" in log.framework_name

    def test_has_all_dadm_sections(self, dadm_generator: DADMComplianceLog) -> None:
        """Verify all DADM sections 6.1-6.6 are covered."""
        log = dadm_generator.generate()

        requirement_ids = {e.requirement_id for e in log.entries}
        expected_ids = {"DADM-6.1", "DADM-6.2", "DADM-6.3", "DADM-6.4", "DADM-6.5", "DADM-6.6"}

        assert requirement_ids == expected_ids, f"Missing sections: {expected_ids - requirement_ids}"

    def test_section_6_1_not_applicable(self, dadm_generator: DADMComplianceLog) -> None:
        """Verify 6.1 AIA is not applicable (WiQ is decision-support)."""
        log = dadm_generator.generate()

        entry = next(e for e in log.entries if e.requirement_id == "DADM-6.1")

        assert entry.status == ComplianceStatus.NOT_APPLICABLE
        assert "decision-SUPPORT" in entry.notes or "decision-support" in entry.notes.lower()

    def test_section_6_2_compliant_with_evidence(
        self, dadm_generator: DADMComplianceLog
    ) -> None:
        """Verify 6.2 Transparency is compliant with evidence references."""
        log = dadm_generator.generate()

        entry = next(e for e in log.entries if e.requirement_id == "DADM-6.2")

        assert entry.status == ComplianceStatus.COMPLIANT
        assert len(entry.evidence_references) > 0
        assert any("governance" in ref for ref in entry.evidence_references)
        assert any("lineage" in ref for ref in entry.evidence_references)

    def test_section_6_3_compliant_with_evidence(
        self, dadm_generator: DADMComplianceLog
    ) -> None:
        """Verify 6.3 Data Quality is compliant with evidence references."""
        log = dadm_generator.generate()

        entry = next(e for e in log.entries if e.requirement_id == "DADM-6.3")

        assert entry.status == ComplianceStatus.COMPLIANT
        assert len(entry.evidence_references) > 0
        assert any("pipeline" in ref or "catalog" in ref for ref in entry.evidence_references)

    def test_section_6_4_compliant_with_noc_reference(
        self, dadm_generator: DADMComplianceLog
    ) -> None:
        """Verify 6.4 Legal Authority references NOC as authoritative source."""
        log = dadm_generator.generate()

        entry = next(e for e in log.entries if e.requirement_id == "DADM-6.4")

        assert entry.status == ComplianceStatus.COMPLIANT
        assert "NOC" in entry.notes or "National Occupational Classification" in entry.notes
        assert any("dim_noc" in ref for ref in entry.evidence_references)

    def test_section_6_5_not_applicable(self, dadm_generator: DADMComplianceLog) -> None:
        """Verify 6.5 Procedural Fairness is not applicable."""
        log = dadm_generator.generate()

        entry = next(e for e in log.entries if e.requirement_id == "DADM-6.5")

        assert entry.status == ComplianceStatus.NOT_APPLICABLE
        assert "individual" in entry.notes.lower()

    def test_section_6_6_not_applicable(self, dadm_generator: DADMComplianceLog) -> None:
        """Verify 6.6 Recourse is not applicable."""
        log = dadm_generator.generate()

        entry = next(e for e in log.entries if e.requirement_id == "DADM-6.6")

        assert entry.status == ComplianceStatus.NOT_APPLICABLE
        assert "decision-SUPPORT" in entry.notes or "decision-support" in entry.notes.lower()


class TestDADMEvidenceReferences:
    """Tests that DADM evidence references point to real artifacts."""

    def test_evidence_references_exist_or_are_globs(
        self, dadm_generator: DADMComplianceLog
    ) -> None:
        """Verify evidence references are valid paths or glob patterns."""
        log = dadm_generator.generate()

        for entry in log.entries:
            for ref in entry.evidence_references:
                # Skip if reference is a glob pattern
                if "*" in ref:
                    # Verify the base directory exists
                    base_path = Path(ref.split("*")[0].rstrip("/"))
                    assert (
                        base_path.exists() or not base_path.is_absolute()
                    ), f"Base path for glob should exist: {base_path}"
                else:
                    # For non-glob paths, verify they exist relative to project root
                    # or note that they are code paths (src/)
                    if ref.startswith("src/"):
                        # Code reference - verify file exists
                        assert Path(ref).exists(), f"Code reference should exist: {ref}"
                    elif ref.startswith("data/"):
                        # Data reference - may be parquet file
                        assert Path(ref).exists(), f"Data reference should exist: {ref}"

    def test_lineage_artifacts_exist(self, config: PipelineConfig) -> None:
        """Verify lineage log artifacts referenced by DADM exist."""
        lineage_path = config.catalog_lineage_path()
        assert lineage_path.exists(), "Lineage directory should exist"

        lineage_files = list(lineage_path.glob("*.json"))
        assert len(lineage_files) > 0, "Should have lineage log files"

    def test_catalog_tables_exist(self, config: PipelineConfig) -> None:
        """Verify catalog table metadata referenced by DADM exist."""
        tables_path = config.catalog_tables_path()
        assert tables_path.exists(), "Tables catalog directory should exist"

        table_files = list(tables_path.glob("*.json"))
        assert len(table_files) > 0, "Should have table metadata files"


class TestDADMLogSummary:
    """Tests for DADM compliance log summary statistics."""

    def test_summary_has_all_status_types(
        self, dadm_generator: DADMComplianceLog
    ) -> None:
        """Verify summary includes all status types."""
        log = dadm_generator.generate()
        summary = log.summary

        expected_statuses = {"compliant", "partial", "not_applicable", "not_implemented"}
        assert set(summary.keys()) == expected_statuses

    def test_summary_counts_match_entries(
        self, dadm_generator: DADMComplianceLog
    ) -> None:
        """Verify summary counts match actual entries."""
        log = dadm_generator.generate()
        summary = log.summary

        total_from_summary = sum(summary.values())
        assert total_from_summary == len(log.entries)

    def test_compliance_rate_calculated(
        self, dadm_generator: DADMComplianceLog
    ) -> None:
        """Verify compliance rate is calculated correctly."""
        log = dadm_generator.generate()

        # WiQ should have some compliant entries (6.2, 6.3, 6.4)
        # and some not_applicable entries (6.1, 6.5, 6.6)
        assert log.compliance_rate > 0, "Should have some compliance"
        assert log.compliance_rate <= 1.0, "Rate should be <= 1.0"
