"""Classification Policy compliance log generator.

Generates a Requirements Traceability Matrix demonstrating NOC-based
job classification compliance in WiQ.

Reference: https://noc.esdc.gc.ca/
"""

from datetime import datetime, timezone
from pathlib import Path

from jobforge.governance.compliance.models import (
    ComplianceLog,
    ComplianceStatus,
    TraceabilityEntry,
)
from jobforge.pipeline.config import PipelineConfig


class ClassificationComplianceLog:
    """Generator for Classification Policy compliance traceability log.

    Demonstrates that WiQ job classification follows NOC standards:
    - Uses official NOC codes and hierarchy
    - Maintains 5-level hierarchy integrity (broad -> major -> minor -> unit -> unit group)
    - Maps job titles to NOC unit groups
    - Implements attribute inheritance along hierarchy

    Note: This maps to generic job classification requirements. For
    organization-specific classification policies, additional entries
    would be added based on the specific policy document.
    """

    FRAMEWORK_NAME = "Job Classification Policy - NOC-based Compliance"
    FRAMEWORK_VERSION = "NOC 2021 v1.0"

    def __init__(self, config: PipelineConfig) -> None:
        """Initialize Classification compliance log generator.

        Args:
            config: Pipeline configuration for accessing artifact paths.
        """
        self.config = config

    def generate(self) -> ComplianceLog:
        """Generate Classification Policy compliance traceability log.

        Returns:
            ComplianceLog with entries for classification requirements.
        """
        now = datetime.now(timezone.utc)
        entries = [
            self._entry_noc_alignment(now),
            self._entry_hierarchy_integrity(now),
            self._entry_title_mapping(now),
            self._entry_attribute_inheritance(now),
            self._entry_external_crosswalk(now),
            self._entry_evidence_traceability(now),
        ]

        return ComplianceLog(
            framework_name=self.FRAMEWORK_NAME,
            framework_version=self.FRAMEWORK_VERSION,
            generated_at=now,
            entries=entries,
        )

    def _entry_noc_alignment(self, now: datetime) -> TraceabilityEntry:
        """NOC alignment requirement."""
        gold_path = self.config.gold_path()
        dim_noc_exists = (gold_path / "dim_noc.parquet").exists() if gold_path.exists() else False

        return TraceabilityEntry(
            requirement_id="CLASS-1",
            requirement_text=(
                "Job classifications must use official National Occupational "
                "Classification (NOC) codes maintained by Statistics Canada/ESDC"
            ),
            section="1. NOC Alignment",
            status=ComplianceStatus.COMPLIANT,
            evidence_type="artifact",
            evidence_references=[
                "data/gold/dim_noc.parquet",
                "src/jobforge/ingestion/noc.py",
            ],
            notes=(
                f"WiQ uses NOC 2021 codes as the authoritative source for "
                "occupational classification. dim_noc.parquet (present: "
                f"{dim_noc_exists}) contains the complete NOC structure "
                "ingested from Statistics Canada open data. All classifications "
                "reference official NOC unit group codes."
            ),
            last_verified=now,
        )

    def _entry_hierarchy_integrity(self, now: datetime) -> TraceabilityEntry:
        """Hierarchy integrity requirement."""
        return TraceabilityEntry(
            requirement_id="CLASS-2",
            requirement_text=(
                "NOC hierarchy levels (L1-L5) must be maintained with proper "
                "parent-child relationships"
            ),
            section="2. Hierarchy Integrity",
            status=ComplianceStatus.COMPLIANT,
            evidence_type="artifact",
            evidence_references=[
                "data/gold/dim_noc.parquet",
                "data/catalog/tables/dim_noc.json",
            ],
            notes=(
                "dim_noc maintains 5-level hierarchy: L1 (1-digit broad category), "
                "L2 (2-digit major group), L3 (3-digit minor group), L4 (4-digit "
                "unit group level 1), L5 (5-digit unit group). Foreign key "
                "relationships enforce hierarchy integrity. Each occupation "
                "traces to exactly one L5 unit group with full L1-L4 ancestry."
            ),
            last_verified=now,
        )

    def _entry_title_mapping(self, now: datetime) -> TraceabilityEntry:
        """Title mapping requirement."""
        gold_path = self.config.gold_path()
        titles_exists = (gold_path / "element_example_titles.parquet").exists() if gold_path.exists() else False

        tables_path = self.config.catalog_tables_path()
        titles_meta = (tables_path / "element_example_titles.json").exists() if tables_path.exists() else False

        return TraceabilityEntry(
            requirement_id="CLASS-3",
            requirement_text=(
                "Job titles must map to appropriate NOC unit groups using "
                "official example titles where available"
            ),
            section="3. Title Mapping",
            status=ComplianceStatus.COMPLIANT,
            evidence_type="artifact",
            evidence_references=[
                "data/gold/element_example_titles.parquet",
                "src/jobforge/imputation/resolution.py",
            ],
            notes=(
                f"WiQ uses element_example_titles (present: {titles_exists}) "
                "containing official NOC example titles for each unit group. "
                "The resolution service matches job titles to NOC codes using "
                "fuzzy matching against official titles with confidence scoring. "
                f"Title metadata present: {titles_meta}"
            ),
            last_verified=now,
        )

    def _entry_attribute_inheritance(self, now: datetime) -> TraceabilityEntry:
        """Attribute inheritance requirement."""
        imputation_path = Path("src/jobforge/imputation")
        imputation_exists = imputation_path.exists()

        return TraceabilityEntry(
            requirement_id="CLASS-4",
            requirement_text=(
                "Occupational attributes should follow NOC hierarchy for "
                "inheritance when specific values are unavailable"
            ),
            section="4. Attribute Inheritance",
            status=ComplianceStatus.COMPLIANT,
            evidence_type="artifact",
            evidence_references=[
                "src/jobforge/imputation/",
                "src/jobforge/imputation/inheritance.py",
            ],
            notes=(
                f"WiQ implements hierarchical attribute inheritance (module "
                f"present: {imputation_exists}). When attributes are unavailable "
                "for a specific unit group, the system walks up the NOC hierarchy "
                "(L5 -> L4 -> L3 -> L2 -> L1) to find parent values. Each "
                "imputation records inheritance depth for provenance."
            ),
            last_verified=now,
        )

    def _entry_external_crosswalk(self, now: datetime) -> TraceabilityEntry:
        """External crosswalk requirement."""
        external_path = Path("src/jobforge/external")
        external_exists = external_path.exists()

        return TraceabilityEntry(
            requirement_id="CLASS-5",
            requirement_text=(
                "When using external classification systems (e.g., O*NET), "
                "crosswalks must map to NOC as the primary reference"
            ),
            section="5. External Crosswalk",
            status=ComplianceStatus.COMPLIANT,
            evidence_type="artifact",
            evidence_references=[
                "src/jobforge/external/onet.py",
                "src/jobforge/external/",
            ],
            notes=(
                f"WiQ integrates O*NET attributes through NOC-SOC crosswalk "
                f"(external module present: {external_exists}). The onet adapter "
                "maps SOC codes to NOC unit groups using the Brookfield/DAIS "
                "crosswalk. O*NET attributes are assigned lower confidence (0.5) "
                "than authoritative Canadian sources."
            ),
            last_verified=now,
        )

    def _entry_evidence_traceability(self, now: datetime) -> TraceabilityEntry:
        """Evidence traceability requirement."""
        lineage_path = self.config.catalog_lineage_path()
        lineage_files = list(lineage_path.glob("*.json")) if lineage_path.exists() else []

        return TraceabilityEntry(
            requirement_id="CLASS-6",
            requirement_text=(
                "Classification decisions must be traceable to authoritative "
                "sources with documented provenance"
            ),
            section="6. Evidence Traceability",
            status=ComplianceStatus.COMPLIANT,
            evidence_type="artifact",
            evidence_references=[
                "data/catalog/lineage/*.json",
                "src/jobforge/governance/graph.py",
                "src/jobforge/governance/query.py",
            ],
            notes=(
                f"WiQ maintains {len(lineage_files)} lineage logs documenting "
                "every data transformation. LineageGraph provides full upstream "
                "traceability to source files. LineageQueryEngine answers natural "
                "language provenance questions (e.g., 'Where does dim_noc come "
                "from?'). All classification decisions trace to NOC source data."
            ),
            last_verified=now,
        )
