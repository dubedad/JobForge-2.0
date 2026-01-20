"""DADM (Directive on Automated Decision-Making) compliance log generator.

Generates a Requirements Traceability Matrix mapping WiQ artifacts to
DADM Directive sections 6.1-6.6.

Reference: https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=32592
"""

from datetime import datetime, timezone
from pathlib import Path

from jobforge.governance.compliance.models import (
    ComplianceLog,
    ComplianceStatus,
    TraceabilityEntry,
)
from jobforge.pipeline.config import PipelineConfig


class DADMComplianceLog:
    """Generator for DADM Directive compliance traceability log.

    Maps WiQ artifacts to DADM Directive sections:
    - 6.1 Algorithmic Impact Assessment
    - 6.2 Transparency
    - 6.3 Data Quality
    - 6.4 Legal Authority
    - 6.5 Procedural Fairness
    - 6.6 Recourse

    WiQ is a decision-SUPPORT tool (provides data for human decisions),
    not a decision-MAKING system (automated decisions affecting individuals).
    This distinction affects the applicability of certain DADM requirements.
    """

    FRAMEWORK_NAME = "DADM - Directive on Automated Decision-Making"
    FRAMEWORK_VERSION = "2019-04-01 (last amended 2023-10-01)"

    def __init__(self, config: PipelineConfig) -> None:
        """Initialize DADM compliance log generator.

        Args:
            config: Pipeline configuration for accessing artifact paths.
        """
        self.config = config

    def generate(self) -> ComplianceLog:
        """Generate DADM compliance traceability log.

        Returns:
            ComplianceLog with entries for DADM sections 6.1-6.6.
        """
        now = datetime.now(timezone.utc)
        entries = [
            self._entry_6_1_aia(now),
            self._entry_6_2_transparency(now),
            self._entry_6_3_quality(now),
            self._entry_6_4_legal(now),
            self._entry_6_5_fairness(now),
            self._entry_6_6_recourse(now),
        ]

        return ComplianceLog(
            framework_name=self.FRAMEWORK_NAME,
            framework_version=self.FRAMEWORK_VERSION,
            generated_at=now,
            entries=entries,
        )

    def _entry_6_1_aia(self, now: datetime) -> TraceabilityEntry:
        """6.1 Algorithmic Impact Assessment requirement."""
        return TraceabilityEntry(
            requirement_id="DADM-6.1",
            requirement_text=(
                "Complete an Algorithmic Impact Assessment to determine "
                "the impact level before production"
            ),
            section="6.1 Algorithmic Impact Assessment",
            status=ComplianceStatus.NOT_APPLICABLE,
            evidence_type="documentation",
            evidence_references=[],
            notes=(
                "WiQ is a decision-SUPPORT tool providing occupational data "
                "for human analysts. It does not make automated decisions "
                "affecting individuals. The Directive applies to 'automated "
                "decision systems' that 'recommend or make an administrative "
                "decision'. WiQ provides reference data only, with no "
                "individual-level recommendations or decisions."
            ),
            last_verified=now,
        )

    def _entry_6_2_transparency(self, now: datetime) -> TraceabilityEntry:
        """6.2 Transparency requirements."""
        # Check for actual lineage artifacts
        lineage_path = self.config.catalog_lineage_path()
        lineage_files = list(lineage_path.glob("*.json")) if lineage_path.exists() else []

        evidence_refs = [
            "src/jobforge/governance/graph.py",
            "src/jobforge/governance/query.py",
            "data/catalog/lineage/*.json",
        ]

        return TraceabilityEntry(
            requirement_id="DADM-6.2",
            requirement_text=(
                "Provide a meaningful explanation to clients of how and "
                "why the decision was made"
            ),
            section="6.2 Transparency",
            status=ComplianceStatus.COMPLIANT,
            evidence_type="artifact",
            evidence_references=evidence_refs,
            notes=(
                f"WiQ provides full data provenance through LineageGraph "
                f"({len(lineage_files)} transition logs) and natural language "
                "query interface (LineageQueryEngine). Users can ask 'Where "
                "does dim_noc come from?' and receive detailed transformation "
                "history with source attribution."
            ),
            last_verified=now,
        )

    def _entry_6_3_quality(self, now: datetime) -> TraceabilityEntry:
        """6.3 Data Quality requirements."""
        # Check for actual catalog and transform artifacts
        tables_path = self.config.catalog_tables_path()
        table_files = list(tables_path.glob("*.json")) if tables_path.exists() else []

        evidence_refs = [
            "src/jobforge/pipeline/layers.py",
            "src/jobforge/pipeline/models.py",
            "data/catalog/tables/*.json",
            "data/catalog/schemas/wiq_schema.json",
        ]

        return TraceabilityEntry(
            requirement_id="DADM-6.3",
            requirement_text=(
                "Ensure data quality through established processes "
                "including validation and testing"
            ),
            section="6.3 Data Quality",
            status=ComplianceStatus.COMPLIANT,
            evidence_type="artifact",
            evidence_references=evidence_refs,
            notes=(
                f"WiQ uses a 4-layer medallion architecture (staged -> bronze "
                f"-> silver -> gold) with validation at each transition. "
                f"Table metadata ({len(table_files)} tables) includes row counts, "
                "column definitions, and data quality attributes. Transform "
                "functions apply type validation and structural checks."
            ),
            last_verified=now,
        )

    def _entry_6_4_legal(self, now: datetime) -> TraceabilityEntry:
        """6.4 Legal Authority requirements."""
        # Check for gold dimension tables
        gold_path = self.config.gold_path()
        noc_exists = (gold_path / "dim_noc.parquet").exists() if gold_path.exists() else False

        evidence_refs = [
            "data/gold/dim_noc.parquet",
            "data/gold/dim_occupations.parquet",
            "data/catalog/schemas/wiq_schema.json",
        ]

        return TraceabilityEntry(
            requirement_id="DADM-6.4",
            requirement_text=(
                "Ensure that there is proper legal authority to operate "
                "the automated decision system"
            ),
            section="6.4 Legal Authority",
            status=ComplianceStatus.COMPLIANT,
            evidence_type="artifact",
            evidence_references=evidence_refs,
            notes=(
                "WiQ uses the National Occupational Classification (NOC) as "
                "its authoritative source for occupational taxonomy. NOC is "
                "maintained by Statistics Canada and ESDC. All job "
                "classifications reference NOC codes, providing traceable "
                "authority for occupational data. "
                f"dim_noc.parquet present: {noc_exists}"
            ),
            last_verified=now,
        )

    def _entry_6_5_fairness(self, now: datetime) -> TraceabilityEntry:
        """6.5 Procedural Fairness requirements."""
        return TraceabilityEntry(
            requirement_id="DADM-6.5",
            requirement_text=(
                "Ensure affected individuals have opportunities to be heard "
                "and contest the decision"
            ),
            section="6.5 Procedural Fairness",
            status=ComplianceStatus.NOT_APPLICABLE,
            evidence_type="documentation",
            evidence_references=[],
            notes=(
                "WiQ provides occupational reference data, not individual-level "
                "decisions. No individuals are directly affected by WiQ outputs. "
                "Downstream systems using WiQ data for individual decisions "
                "would need their own procedural fairness controls."
            ),
            last_verified=now,
        )

    def _entry_6_6_recourse(self, now: datetime) -> TraceabilityEntry:
        """6.6 Recourse requirements."""
        return TraceabilityEntry(
            requirement_id="DADM-6.6",
            requirement_text=(
                "Provide affected individuals with clear and accessible "
                "information about avenues for recourse"
            ),
            section="6.6 Recourse",
            status=ComplianceStatus.NOT_APPLICABLE,
            evidence_type="documentation",
            evidence_references=[],
            notes=(
                "As a decision-SUPPORT tool providing aggregate occupational "
                "data, WiQ does not produce decisions requiring individual "
                "recourse mechanisms. Downstream systems making individual "
                "decisions would implement their own recourse procedures."
            ),
            last_verified=now,
        )
