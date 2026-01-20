"""Tests for DAMA DMBOK compliance log generator.

Tests the DAMAComplianceLog generator for all 11 knowledge areas.
"""

from pathlib import Path

import pytest

from jobforge.governance.compliance.dama import DAMAComplianceLog
from jobforge.governance.compliance.models import ComplianceLog, ComplianceStatus
from jobforge.pipeline.config import PipelineConfig


@pytest.fixture
def config() -> PipelineConfig:
    """Pipeline configuration pointing to real data."""
    return PipelineConfig()


@pytest.fixture
def dama_generator(config: PipelineConfig) -> DAMAComplianceLog:
    """DAMA compliance log generator."""
    return DAMAComplianceLog(config)


class TestDAMAComplianceLog:
    """Tests for DAMA compliance log generation."""

    def test_generates_valid_compliance_log(
        self, dama_generator: DAMAComplianceLog
    ) -> None:
        """Verify generator produces valid ComplianceLog."""
        log = dama_generator.generate()

        assert isinstance(log, ComplianceLog)
        assert log.framework_name == DAMAComplianceLog.FRAMEWORK_NAME
        assert "DAMA" in log.framework_name
        assert "DMBOK" in log.framework_name

    def test_has_all_11_knowledge_areas(self, dama_generator: DAMAComplianceLog) -> None:
        """Verify all 11 DAMA DMBOK knowledge areas are covered."""
        log = dama_generator.generate()

        requirement_ids = {e.requirement_id for e in log.entries}
        expected_ids = {f"DAMA-{i}" for i in range(1, 12)}

        assert requirement_ids == expected_ids, f"Missing areas: {expected_ids - requirement_ids}"
        assert len(log.entries) == 11

    def test_knowledge_area_1_governance_compliant(
        self, dama_generator: DAMAComplianceLog
    ) -> None:
        """Verify Data Governance knowledge area is compliant."""
        log = dama_generator.generate()
        entry = next(e for e in log.entries if e.requirement_id == "DAMA-1")

        assert entry.status == ComplianceStatus.COMPLIANT
        assert "governance" in entry.section.lower()
        assert any("governance" in ref for ref in entry.evidence_references)

    def test_knowledge_area_2_architecture_compliant(
        self, dama_generator: DAMAComplianceLog
    ) -> None:
        """Verify Data Architecture knowledge area is compliant."""
        log = dama_generator.generate()
        entry = next(e for e in log.entries if e.requirement_id == "DAMA-2")

        assert entry.status == ComplianceStatus.COMPLIANT
        assert "architecture" in entry.section.lower()
        assert any("schema" in ref for ref in entry.evidence_references)

    def test_knowledge_area_5_security_not_applicable(
        self, dama_generator: DAMAComplianceLog
    ) -> None:
        """Verify Data Security is not applicable (no PII in WiQ)."""
        log = dama_generator.generate()
        entry = next(e for e in log.entries if e.requirement_id == "DAMA-5")

        assert entry.status == ComplianceStatus.NOT_APPLICABLE
        assert "security" in entry.section.lower()
        assert "PII" in entry.notes or "public" in entry.notes.lower()

    def test_knowledge_area_7_metadata_compliant(
        self, dama_generator: DAMAComplianceLog
    ) -> None:
        """Verify Metadata Management is compliant with catalog evidence."""
        log = dama_generator.generate()
        entry = next(e for e in log.entries if e.requirement_id == "DAMA-7")

        assert entry.status == ComplianceStatus.COMPLIANT
        assert "metadata" in entry.section.lower()
        assert any("catalog" in ref for ref in entry.evidence_references)
        assert any("lineage" in ref for ref in entry.evidence_references)

    def test_knowledge_area_9_reference_master_compliant(
        self, dama_generator: DAMAComplianceLog
    ) -> None:
        """Verify Reference/Master Data is compliant with NOC evidence."""
        log = dama_generator.generate()
        entry = next(e for e in log.entries if e.requirement_id == "DAMA-9")

        assert entry.status == ComplianceStatus.COMPLIANT
        assert "reference" in entry.section.lower() or "master" in entry.section.lower()
        assert any("dim_noc" in ref for ref in entry.evidence_references)

    def test_knowledge_area_11_document_not_applicable(
        self, dama_generator: DAMAComplianceLog
    ) -> None:
        """Verify Document/Content Management is not applicable."""
        log = dama_generator.generate()
        entry = next(e for e in log.entries if e.requirement_id == "DAMA-11")

        assert entry.status == ComplianceStatus.NOT_APPLICABLE
        assert "document" in entry.section.lower() or "content" in entry.section.lower()
        assert "structured" in entry.notes.lower()


class TestDAMAEvidenceReferences:
    """Tests that DAMA evidence references point to real artifacts."""

    def test_catalog_tables_exist(self, config: PipelineConfig) -> None:
        """Verify catalog table metadata referenced by DAMA exist."""
        tables_path = config.catalog_tables_path()
        assert tables_path.exists(), "Tables catalog directory should exist"

        table_files = list(tables_path.glob("*.json"))
        assert len(table_files) > 0, "Should have table metadata files"

    def test_catalog_lineage_exists(self, config: PipelineConfig) -> None:
        """Verify catalog lineage logs referenced by DAMA exist."""
        lineage_path = config.catalog_lineage_path()
        assert lineage_path.exists(), "Lineage catalog directory should exist"

        lineage_files = list(lineage_path.glob("*.json"))
        assert len(lineage_files) > 0, "Should have lineage log files"

    def test_gold_tables_exist(self, config: PipelineConfig) -> None:
        """Verify gold layer tables referenced by DAMA exist."""
        gold_path = config.gold_path()
        assert gold_path.exists(), "Gold directory should exist"

        gold_tables = list(gold_path.glob("*.parquet"))
        assert len(gold_tables) > 0, "Should have gold parquet files"

    def test_governance_module_exists(self) -> None:
        """Verify governance module referenced by DAMA exists."""
        governance_path = Path("src/jobforge/governance")
        assert governance_path.exists(), "Governance module should exist"

        governance_files = list(governance_path.glob("*.py"))
        assert len(governance_files) > 0, "Should have governance Python files"


class TestDAMALogSummary:
    """Tests for DAMA compliance log summary statistics."""

    def test_summary_has_expected_status_distribution(
        self, dama_generator: DAMAComplianceLog
    ) -> None:
        """Verify DAMA summary has expected status counts."""
        log = dama_generator.generate()
        summary = log.summary

        # 9 compliant, 2 not_applicable (security, document/content)
        assert summary["compliant"] == 9
        assert summary["not_applicable"] == 2
        assert summary["partial"] == 0
        assert summary["not_implemented"] == 0

    def test_compliance_rate_high(self, dama_generator: DAMAComplianceLog) -> None:
        """Verify high compliance rate (9/9 applicable areas)."""
        log = dama_generator.generate()

        # All 9 applicable areas should be compliant
        assert log.compliance_rate == 1.0
