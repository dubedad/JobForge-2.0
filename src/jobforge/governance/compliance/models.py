"""Pydantic models for compliance traceability logs.

Implements the Requirements Traceability Matrix (RTM) pattern for mapping
external framework requirements to WiQ artifacts demonstrating compliance.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ComplianceStatus(str, Enum):
    """Compliance status for a requirement."""

    COMPLIANT = "compliant"
    PARTIAL = "partial"
    NOT_APPLICABLE = "not_applicable"
    NOT_IMPLEMENTED = "not_implemented"


class TraceabilityEntry(BaseModel):
    """Single requirement-to-evidence mapping in the traceability matrix.

    Maps an external framework requirement to WiQ artifacts that demonstrate
    compliance, with status tracking and verification metadata.
    """

    requirement_id: str = Field(
        description="External requirement ID (e.g., DADM-6.2.3, DAMA-7)"
    )
    requirement_text: str = Field(
        description="Requirement description from source framework"
    )
    section: str = Field(
        description="Chapter/section in source framework (e.g., '6.2 Transparency')"
    )
    status: ComplianceStatus = Field(description="Current compliance status")
    evidence_type: str = Field(
        description="Type of evidence: artifact, process, documentation"
    )
    evidence_references: list[str] = Field(
        default_factory=list,
        description="Paths or IDs of artifacts demonstrating compliance",
    )
    notes: str = Field(default="", description="Additional context or implementation notes")
    last_verified: datetime = Field(description="When compliance was last verified")


class ComplianceLog(BaseModel):
    """Complete compliance traceability log for a framework.

    Contains all requirement mappings for a governance framework with
    summary statistics for quick compliance assessment.
    """

    framework_name: str = Field(description="Name of the compliance framework")
    framework_version: str = Field(description="Version of the framework being mapped")
    generated_at: datetime = Field(description="When this log was generated")
    entries: list[TraceabilityEntry] = Field(
        default_factory=list, description="List of requirement mappings"
    )

    @property
    def summary(self) -> dict[str, int]:
        """Compute summary counts by compliance status.

        Returns:
            Dictionary mapping status values to counts.
        """
        counts = {s.value: 0 for s in ComplianceStatus}
        for entry in self.entries:
            counts[entry.status.value] += 1
        return counts

    @property
    def compliance_rate(self) -> float:
        """Calculate overall compliance rate.

        Returns:
            Percentage of requirements that are compliant (0.0 to 1.0).
            Not applicable requirements are excluded from calculation.
        """
        total = len(self.entries)
        not_applicable = sum(
            1 for e in self.entries if e.status == ComplianceStatus.NOT_APPLICABLE
        )
        applicable = total - not_applicable
        if applicable == 0:
            return 1.0
        compliant = sum(
            1 for e in self.entries if e.status == ComplianceStatus.COMPLIANT
        )
        return compliant / applicable
