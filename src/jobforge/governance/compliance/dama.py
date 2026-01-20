"""DAMA DMBOK (Data Management Body of Knowledge) compliance log generator.

Generates a Requirements Traceability Matrix mapping WiQ artifacts to
the 11 DAMA DMBOK knowledge areas.

Reference: https://dama.org/learning-resources/dama-data-management-body-of-knowledge-dmbok/
"""

from datetime import datetime, timezone
from pathlib import Path

from jobforge.governance.compliance.models import (
    ComplianceLog,
    ComplianceStatus,
    TraceabilityEntry,
)
from jobforge.pipeline.config import PipelineConfig


class DAMAComplianceLog:
    """Generator for DAMA DMBOK compliance traceability log.

    Maps WiQ artifacts to the 11 DAMA DMBOK knowledge areas:
    1. Data Governance
    2. Data Architecture
    3. Data Modeling and Design
    4. Data Storage and Operations
    5. Data Security
    6. Data Integration and Interoperability
    7. Metadata Management
    8. Data Quality
    9. Reference and Master Data
    10. Data Warehousing and Business Intelligence
    11. Document and Content Management
    """

    FRAMEWORK_NAME = "DAMA DMBOK - Data Management Body of Knowledge"
    FRAMEWORK_VERSION = "DAMA-DMBOK2 (2017)"

    def __init__(self, config: PipelineConfig) -> None:
        """Initialize DAMA compliance log generator.

        Args:
            config: Pipeline configuration for accessing artifact paths.
        """
        self.config = config

    def generate(self) -> ComplianceLog:
        """Generate DAMA DMBOK compliance traceability log.

        Returns:
            ComplianceLog with entries for all 11 knowledge areas.
        """
        now = datetime.now(timezone.utc)
        entries = [
            self._entry_1_governance(now),
            self._entry_2_architecture(now),
            self._entry_3_modeling(now),
            self._entry_4_storage(now),
            self._entry_5_security(now),
            self._entry_6_integration(now),
            self._entry_7_metadata(now),
            self._entry_8_quality(now),
            self._entry_9_reference_master(now),
            self._entry_10_warehousing_bi(now),
            self._entry_11_document_content(now),
        ]

        return ComplianceLog(
            framework_name=self.FRAMEWORK_NAME,
            framework_version=self.FRAMEWORK_VERSION,
            generated_at=now,
            entries=entries,
        )

    def _entry_1_governance(self, now: datetime) -> TraceabilityEntry:
        """1. Data Governance knowledge area."""
        governance_files = list(Path("src/jobforge/governance").glob("*.py"))

        return TraceabilityEntry(
            requirement_id="DAMA-1",
            requirement_text=(
                "Data Governance: Planning, oversight, and control over management "
                "of data and the use of data and data-related resources"
            ),
            section="1. Data Governance",
            status=ComplianceStatus.COMPLIANT,
            evidence_type="artifact",
            evidence_references=[
                "src/jobforge/governance/",
                "src/jobforge/governance/graph.py",
                "src/jobforge/governance/query.py",
                "src/jobforge/governance/catalogue.py",
            ],
            notes=(
                f"WiQ implements data governance through the governance module "
                f"({len(governance_files)} Python modules) including lineage graph "
                "traversal, natural language query interface, and data catalogue "
                "generation."
            ),
            last_verified=now,
        )

    def _entry_2_architecture(self, now: datetime) -> TraceabilityEntry:
        """2. Data Architecture knowledge area."""
        schema_path = self.config.catalog_schemas_path()
        schema_exists = (schema_path / "wiq_schema.json").exists() if schema_path.exists() else False

        return TraceabilityEntry(
            requirement_id="DAMA-2",
            requirement_text=(
                "Data Architecture: Defining the blueprint for managing data assets "
                "by aligning with organizational strategy"
            ),
            section="2. Data Architecture",
            status=ComplianceStatus.COMPLIANT,
            evidence_type="artifact",
            evidence_references=[
                "data/catalog/schemas/wiq_schema.json",
                "src/jobforge/pipeline/config.py",
            ],
            notes=(
                f"WiQ uses a star schema architecture documented in wiq_schema.json "
                f"(present: {schema_exists}). The medallion architecture (staged -> "
                "bronze -> silver -> gold) provides clear data flow layers with "
                "defined transformation boundaries."
            ),
            last_verified=now,
        )

    def _entry_3_modeling(self, now: datetime) -> TraceabilityEntry:
        """3. Data Modeling and Design knowledge area."""
        schema_path = self.config.catalog_schemas_path()
        schema_files = list(schema_path.glob("*.json")) if schema_path.exists() else []

        return TraceabilityEntry(
            requirement_id="DAMA-3",
            requirement_text=(
                "Data Modeling and Design: Discovering, analyzing, representing, "
                "and communicating data requirements in the form of data models"
            ),
            section="3. Data Modeling and Design",
            status=ComplianceStatus.COMPLIANT,
            evidence_type="artifact",
            evidence_references=[
                "data/catalog/schemas/",
                "src/jobforge/pipeline/models.py",
            ],
            notes=(
                f"WiQ maintains {len(schema_files)} schema file(s) documenting the "
                "star schema design. Pydantic models in pipeline/models.py provide "
                "type-safe data representations with validation."
            ),
            last_verified=now,
        )

    def _entry_4_storage(self, now: datetime) -> TraceabilityEntry:
        """4. Data Storage and Operations knowledge area."""
        gold_path = self.config.gold_path()
        gold_tables = list(gold_path.glob("*.parquet")) if gold_path.exists() else []

        return TraceabilityEntry(
            requirement_id="DAMA-4",
            requirement_text=(
                "Data Storage and Operations: Design, implementation, and support "
                "of stored data to maximize its value"
            ),
            section="4. Data Storage and Operations",
            status=ComplianceStatus.COMPLIANT,
            evidence_type="artifact",
            evidence_references=[
                "data/gold/*.parquet",
                "src/jobforge/pipeline/",
            ],
            notes=(
                f"WiQ stores {len(gold_tables)} gold-layer Parquet tables optimized "
                "for analytical queries. The pipeline module manages data "
                "ingestion, transformation, and layer transitions with full "
                "provenance tracking."
            ),
            last_verified=now,
        )

    def _entry_5_security(self, now: datetime) -> TraceabilityEntry:
        """5. Data Security knowledge area."""
        return TraceabilityEntry(
            requirement_id="DAMA-5",
            requirement_text=(
                "Data Security: Planning, development, and execution of security "
                "policies and procedures to ensure proper data authentication, "
                "authorization, access, and auditing"
            ),
            section="5. Data Security",
            status=ComplianceStatus.NOT_APPLICABLE,
            evidence_type="documentation",
            evidence_references=[],
            notes=(
                "WiQ uses exclusively public occupational data from Statistics "
                "Canada (NOC, COPS, OASIS). No personally identifiable information "
                "(PII) or sensitive data is processed. Data security controls are "
                "inherited from deployment environment."
            ),
            last_verified=now,
        )

    def _entry_6_integration(self, now: datetime) -> TraceabilityEntry:
        """6. Data Integration and Interoperability knowledge area."""
        ingestion_path = Path("src/jobforge/ingestion")
        external_path = Path("src/jobforge/external")

        ingestion_modules = list(ingestion_path.glob("*.py")) if ingestion_path.exists() else []
        external_modules = list(external_path.glob("*.py")) if external_path.exists() else []

        return TraceabilityEntry(
            requirement_id="DAMA-6",
            requirement_text=(
                "Data Integration and Interoperability: Processes related to the "
                "movement and consolidation of data within and between systems"
            ),
            section="6. Data Integration and Interoperability",
            status=ComplianceStatus.COMPLIANT,
            evidence_type="artifact",
            evidence_references=[
                "src/jobforge/ingestion/",
                "src/jobforge/external/",
            ],
            notes=(
                f"WiQ integrates data from multiple sources through ingestion "
                f"({len(ingestion_modules)} modules) and external adapters "
                f"({len(external_modules)} modules). Sources include Statistics "
                "Canada (NOC, COPS), OASIS attributes, and O*NET crosswalk data."
            ),
            last_verified=now,
        )

    def _entry_7_metadata(self, now: datetime) -> TraceabilityEntry:
        """7. Metadata Management knowledge area."""
        tables_path = self.config.catalog_tables_path()
        lineage_path = self.config.catalog_lineage_path()

        table_files = list(tables_path.glob("*.json")) if tables_path.exists() else []
        lineage_files = list(lineage_path.glob("*.json")) if lineage_path.exists() else []

        return TraceabilityEntry(
            requirement_id="DAMA-7",
            requirement_text=(
                "Metadata Management: Collecting, categorizing, maintaining, "
                "integrating, controlling, managing, and delivering metadata"
            ),
            section="7. Metadata Management",
            status=ComplianceStatus.COMPLIANT,
            evidence_type="artifact",
            evidence_references=[
                "data/catalog/tables/*.json",
                "data/catalog/lineage/*.json",
            ],
            notes=(
                f"WiQ maintains extensive metadata: {len(table_files)} table "
                f"metadata files in data/catalog/tables/ and {len(lineage_files)} "
                "lineage logs in data/catalog/lineage/. TableMetadata includes "
                "column definitions, row counts, and layer attribution."
            ),
            last_verified=now,
        )

    def _entry_8_quality(self, now: datetime) -> TraceabilityEntry:
        """8. Data Quality knowledge area."""
        return TraceabilityEntry(
            requirement_id="DAMA-8",
            requirement_text=(
                "Data Quality: Planning and implementation of quality management "
                "techniques to measure, assess, and improve data quality"
            ),
            section="8. Data Quality",
            status=ComplianceStatus.COMPLIANT,
            evidence_type="artifact",
            evidence_references=[
                "src/jobforge/pipeline/layers.py",
                "src/jobforge/pipeline/provenance.py",
            ],
            notes=(
                "WiQ implements data quality through the medallion architecture "
                "with validation at each layer transition. Layer transforms apply "
                "type checks, schema validation, and row count tracking. "
                "Provenance logging records all transformations applied."
            ),
            last_verified=now,
        )

    def _entry_9_reference_master(self, now: datetime) -> TraceabilityEntry:
        """9. Reference and Master Data knowledge area."""
        gold_path = self.config.gold_path()
        dim_noc_exists = (gold_path / "dim_noc.parquet").exists() if gold_path.exists() else False
        dim_occ_exists = (gold_path / "dim_occupations.parquet").exists() if gold_path.exists() else False

        return TraceabilityEntry(
            requirement_id="DAMA-9",
            requirement_text=(
                "Reference and Master Data: Managing shared data to meet "
                "organizational goals, reduce redundancy, and ensure consistency"
            ),
            section="9. Reference and Master Data",
            status=ComplianceStatus.COMPLIANT,
            evidence_type="artifact",
            evidence_references=[
                "data/gold/dim_noc.parquet",
                "data/gold/dim_occupations.parquet",
            ],
            notes=(
                f"WiQ uses NOC as the authoritative reference for occupational "
                "classification. dim_noc (present: {dim_noc_exists}) provides the "
                "5-level NOC hierarchy. dim_occupations (present: {dim_occ_exists}) "
                "contains occupation details with NOC linkage."
            ),
            last_verified=now,
        )

    def _entry_10_warehousing_bi(self, now: datetime) -> TraceabilityEntry:
        """10. Data Warehousing and Business Intelligence knowledge area."""
        gold_path = self.config.gold_path()
        gold_tables = list(gold_path.glob("*.parquet")) if gold_path.exists() else []
        deployment_path = Path("src/jobforge/deployment")
        deployment_exists = deployment_path.exists()

        return TraceabilityEntry(
            requirement_id="DAMA-10",
            requirement_text=(
                "Data Warehousing and Business Intelligence: Managing analytical "
                "data processing and enabling access to decision support data"
            ),
            section="10. Data Warehousing and Business Intelligence",
            status=ComplianceStatus.COMPLIANT,
            evidence_type="artifact",
            evidence_references=[
                "data/gold/",
                "src/jobforge/deployment/",
            ],
            notes=(
                f"WiQ implements a star schema with {len(gold_tables)} gold tables "
                "optimized for BI consumption. The deployment module (present: "
                f"{deployment_exists}) enables Power BI semantic model deployment "
                "for self-service analytics."
            ),
            last_verified=now,
        )

    def _entry_11_document_content(self, now: datetime) -> TraceabilityEntry:
        """11. Document and Content Management knowledge area."""
        return TraceabilityEntry(
            requirement_id="DAMA-11",
            requirement_text=(
                "Document and Content Management: Planning, implementation, and "
                "control activities for managing unstructured data"
            ),
            section="11. Document and Content Management",
            status=ComplianceStatus.NOT_APPLICABLE,
            evidence_type="documentation",
            evidence_references=[],
            notes=(
                "WiQ focuses exclusively on structured occupational data. "
                "Unstructured documents and content are outside the scope of "
                "the WiQ semantic model. Source documents (NOC PDFs, COPS "
                "reports) are managed by their respective publishers."
            ),
            last_verified=now,
        )
