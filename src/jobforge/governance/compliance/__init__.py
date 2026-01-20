"""Compliance traceability logging for governance frameworks.

Provides Requirements Traceability Matrix (RTM) based compliance logs for:
- DADM (Directive on Automated Decision-Making)
- DAMA DMBOK (Data Management Body of Knowledge)
- Classification Policy (NOC-based job classification)

Each log generator produces a ComplianceLog with TraceabilityEntry mappings
from framework requirements to WiQ artifacts demonstrating compliance.
"""

from jobforge.governance.compliance.classification import ClassificationComplianceLog
from jobforge.governance.compliance.dadm import DADMComplianceLog
from jobforge.governance.compliance.dama import DAMAComplianceLog
from jobforge.governance.compliance.models import (
    ComplianceLog,
    ComplianceStatus,
    TraceabilityEntry,
)

__all__ = [
    "ComplianceStatus",
    "TraceabilityEntry",
    "ComplianceLog",
    "DADMComplianceLog",
    "DAMAComplianceLog",
    "ClassificationComplianceLog",
]
