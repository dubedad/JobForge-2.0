"""Tests for compliance traceability models.

Tests the Pydantic models used for Requirements Traceability Matrix (RTM)
compliance logs.
"""

from datetime import datetime, timezone

import pytest

from jobforge.governance.compliance.models import (
    ComplianceLog,
    ComplianceStatus,
    TraceabilityEntry,
)


class TestComplianceStatus:
    """Tests for ComplianceStatus enum."""

    def test_status_values(self) -> None:
        """Verify all expected status values exist."""
        assert ComplianceStatus.COMPLIANT.value == "compliant"
        assert ComplianceStatus.PARTIAL.value == "partial"
        assert ComplianceStatus.NOT_APPLICABLE.value == "not_applicable"
        assert ComplianceStatus.NOT_IMPLEMENTED.value == "not_implemented"

    def test_status_is_string_enum(self) -> None:
        """Verify status values can be used as strings."""
        assert str(ComplianceStatus.COMPLIANT) == "ComplianceStatus.COMPLIANT"
        assert ComplianceStatus.COMPLIANT == "compliant"

    def test_all_status_values_count(self) -> None:
        """Verify correct number of status values."""
        assert len(ComplianceStatus) == 4


class TestTraceabilityEntry:
    """Tests for TraceabilityEntry model."""

    @pytest.fixture
    def sample_entry(self) -> TraceabilityEntry:
        """Create a sample TraceabilityEntry for testing."""
        return TraceabilityEntry(
            requirement_id="TEST-1.0",
            requirement_text="Test requirement description",
            section="1.0 Test Section",
            status=ComplianceStatus.COMPLIANT,
            evidence_type="artifact",
            evidence_references=["src/test.py", "data/test.json"],
            notes="Test notes",
            last_verified=datetime(2026, 1, 20, 12, 0, 0, tzinfo=timezone.utc),
        )

    def test_entry_creation(self, sample_entry: TraceabilityEntry) -> None:
        """Verify entry is created with correct values."""
        assert sample_entry.requirement_id == "TEST-1.0"
        assert sample_entry.requirement_text == "Test requirement description"
        assert sample_entry.section == "1.0 Test Section"
        assert sample_entry.status == ComplianceStatus.COMPLIANT
        assert sample_entry.evidence_type == "artifact"
        assert len(sample_entry.evidence_references) == 2
        assert sample_entry.notes == "Test notes"

    def test_entry_validation_required_fields(self) -> None:
        """Verify required fields are enforced."""
        with pytest.raises(ValueError):
            TraceabilityEntry(
                # Missing required fields
                requirement_id="TEST-1.0",
            )

    def test_entry_default_values(self) -> None:
        """Verify default values are applied."""
        entry = TraceabilityEntry(
            requirement_id="TEST-1.0",
            requirement_text="Test",
            section="1.0",
            status=ComplianceStatus.COMPLIANT,
            evidence_type="artifact",
            last_verified=datetime.now(timezone.utc),
        )
        assert entry.evidence_references == []
        assert entry.notes == ""

    def test_entry_serialization(self, sample_entry: TraceabilityEntry) -> None:
        """Verify entry can be serialized to JSON."""
        json_data = sample_entry.model_dump_json()
        assert "TEST-1.0" in json_data
        assert "compliant" in json_data

    def test_entry_deserialization(self, sample_entry: TraceabilityEntry) -> None:
        """Verify entry can be deserialized from JSON."""
        json_data = sample_entry.model_dump_json()
        restored = TraceabilityEntry.model_validate_json(json_data)
        assert restored.requirement_id == sample_entry.requirement_id
        assert restored.status == sample_entry.status


class TestComplianceLog:
    """Tests for ComplianceLog model."""

    @pytest.fixture
    def sample_entries(self) -> list[TraceabilityEntry]:
        """Create sample entries for testing."""
        now = datetime.now(timezone.utc)
        return [
            TraceabilityEntry(
                requirement_id="TEST-1",
                requirement_text="Compliant requirement",
                section="1.0",
                status=ComplianceStatus.COMPLIANT,
                evidence_type="artifact",
                last_verified=now,
            ),
            TraceabilityEntry(
                requirement_id="TEST-2",
                requirement_text="Partial requirement",
                section="2.0",
                status=ComplianceStatus.PARTIAL,
                evidence_type="artifact",
                last_verified=now,
            ),
            TraceabilityEntry(
                requirement_id="TEST-3",
                requirement_text="Not applicable requirement",
                section="3.0",
                status=ComplianceStatus.NOT_APPLICABLE,
                evidence_type="documentation",
                last_verified=now,
            ),
            TraceabilityEntry(
                requirement_id="TEST-4",
                requirement_text="Not implemented requirement",
                section="4.0",
                status=ComplianceStatus.NOT_IMPLEMENTED,
                evidence_type="artifact",
                last_verified=now,
            ),
        ]

    @pytest.fixture
    def sample_log(self, sample_entries: list[TraceabilityEntry]) -> ComplianceLog:
        """Create a sample ComplianceLog for testing."""
        return ComplianceLog(
            framework_name="Test Framework",
            framework_version="1.0",
            generated_at=datetime.now(timezone.utc),
            entries=sample_entries,
        )

    def test_log_creation(self, sample_log: ComplianceLog) -> None:
        """Verify log is created with correct values."""
        assert sample_log.framework_name == "Test Framework"
        assert sample_log.framework_version == "1.0"
        assert len(sample_log.entries) == 4

    def test_log_summary_counts(self, sample_log: ComplianceLog) -> None:
        """Verify summary computes correct status counts."""
        summary = sample_log.summary
        assert summary["compliant"] == 1
        assert summary["partial"] == 1
        assert summary["not_applicable"] == 1
        assert summary["not_implemented"] == 1

    def test_log_compliance_rate(self, sample_log: ComplianceLog) -> None:
        """Verify compliance rate excludes not_applicable."""
        # 1 compliant out of 3 applicable (excludes 1 not_applicable)
        rate = sample_log.compliance_rate
        assert rate == pytest.approx(1 / 3, rel=0.01)

    def test_log_compliance_rate_all_compliant(self) -> None:
        """Verify compliance rate when all applicable are compliant."""
        now = datetime.now(timezone.utc)
        log = ComplianceLog(
            framework_name="Test",
            framework_version="1.0",
            generated_at=now,
            entries=[
                TraceabilityEntry(
                    requirement_id="TEST-1",
                    requirement_text="Compliant",
                    section="1.0",
                    status=ComplianceStatus.COMPLIANT,
                    evidence_type="artifact",
                    last_verified=now,
                ),
                TraceabilityEntry(
                    requirement_id="TEST-2",
                    requirement_text="Not applicable",
                    section="2.0",
                    status=ComplianceStatus.NOT_APPLICABLE,
                    evidence_type="documentation",
                    last_verified=now,
                ),
            ],
        )
        assert log.compliance_rate == 1.0

    def test_log_compliance_rate_empty(self) -> None:
        """Verify compliance rate with no entries returns 1.0."""
        log = ComplianceLog(
            framework_name="Test",
            framework_version="1.0",
            generated_at=datetime.now(timezone.utc),
            entries=[],
        )
        assert log.compliance_rate == 1.0

    def test_log_compliance_rate_all_not_applicable(self) -> None:
        """Verify compliance rate when all are not_applicable."""
        now = datetime.now(timezone.utc)
        log = ComplianceLog(
            framework_name="Test",
            framework_version="1.0",
            generated_at=now,
            entries=[
                TraceabilityEntry(
                    requirement_id="TEST-1",
                    requirement_text="N/A",
                    section="1.0",
                    status=ComplianceStatus.NOT_APPLICABLE,
                    evidence_type="documentation",
                    last_verified=now,
                ),
            ],
        )
        assert log.compliance_rate == 1.0

    def test_log_serialization(self, sample_log: ComplianceLog) -> None:
        """Verify log can be serialized to JSON."""
        json_data = sample_log.model_dump_json(indent=2)
        assert "Test Framework" in json_data
        assert "compliant" in json_data

    def test_log_deserialization(self, sample_log: ComplianceLog) -> None:
        """Verify log can be deserialized from JSON."""
        json_data = sample_log.model_dump_json()
        restored = ComplianceLog.model_validate_json(json_data)
        assert restored.framework_name == sample_log.framework_name
        assert len(restored.entries) == len(sample_log.entries)
