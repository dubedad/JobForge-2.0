"""Deployment orchestrator for WiQ semantic model to Power BI.

This module provides the WiQDeployer class that coordinates schema loading,
MCP specification generation, and UI updates for deployment demos.

IMPORTANT ARCHITECTURE DECISION:
The deployer does NOT call MCP tools directly. Instead, it:
1. Loads the WiQ schema
2. Generates TableSpec and RelationshipSpec objects (via MCPClient)
3. Outputs the deployment plan as structured data
4. Claude Code (the AI) executes the actual MCP tool calls

This design allows the deployment to work with Claude Code's MCP integration.
"""

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from jobforge.deployment.mcp_client import MCPClient, RelationshipSpec, TableSpec
from jobforge.deployment.ui import DeploymentUI, get_table_source
from jobforge.semantic.models import Relationship, SemanticSchema, Table, TableType


@dataclass
class DeploymentResult:
    """Result of a deployment operation.

    Attributes:
        success: Whether the operation completed successfully.
        tables_deployed: List of table names that were deployed.
        relationships_created: Number of relationships created.
        errors: List of error messages (if any).
        duration_seconds: Total deployment duration.
    """

    success: bool
    tables_deployed: list[str]
    relationships_created: int
    errors: list[str]
    duration_seconds: float


class WiQDeployer:
    """Orchestrates WiQ semantic model deployment to Power BI.

    The deployer generates deployment specifications from the WiQ schema.
    Actual MCP tool execution is performed by Claude Code using these specs.

    Example:
        >>> from jobforge.deployment import WiQDeployer
        >>> deployer = WiQDeployer()
        >>> schema = deployer.load_schema()
        >>> tables, rels = deployer.get_deployment_order(schema)
        >>> print(f"Deployment: {len(tables)} tables, {len(rels)} relationships")
    """

    def __init__(self, ui: Optional[DeploymentUI] = None) -> None:
        """Initialize the deployer.

        Args:
            ui: DeploymentUI instance for progress display.
                If None, creates a new DeploymentUI.
        """
        self.ui = ui or DeploymentUI()
        self.mcp_client = MCPClient()

    def load_schema(self, schema_path: Optional[Path] = None) -> SemanticSchema:
        """Load WiQ schema from JSON or build from code.

        Args:
            schema_path: Path to schema JSON file.
                        If None, uses default location or builds from code.

        Returns:
            SemanticSchema loaded from JSON or built fresh.

        Raises:
            FileNotFoundError: If specified path doesn't exist.
            ValueError: If JSON is invalid.
        """
        # Default schema path
        if schema_path is None:
            # Try default location first (relative to project root)
            # Use package location to find project root
            project_root = Path(__file__).parent.parent.parent.parent
            default_path = project_root / "data" / "catalog" / "schemas" / "wiq_schema.json"
            if default_path.exists():
                schema_path = default_path
            else:
                # Also try current working directory
                cwd_path = Path("data/catalog/schemas/wiq_schema.json")
                if cwd_path.exists():
                    schema_path = cwd_path
                else:
                    # Fallback: build from code
                    from jobforge.semantic.schema import build_wiq_schema
                    from jobforge.pipeline.config import PipelineConfig
                    # Use project root for config
                    config = PipelineConfig(data_root=project_root / "data")
                    return build_wiq_schema(config)

        # Load from JSON
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")

        data = json.loads(schema_path.read_text(encoding="utf-8"))
        return SemanticSchema.model_validate(data)

    def get_deployment_order(
        self, schema: SemanticSchema
    ) -> tuple[list[Table], list[Relationship]]:
        """Get tables and relationships in deployment order.

        Deployment order is critical for avoiding errors:
        1. Dimension tables first (they're the 'one' side of relationships)
        2. Attribute tables next (they reference dimensions)
        3. Fact tables last (they reference dimensions)
        4. All relationships after all tables exist

        Args:
            schema: The semantic schema to order.

        Returns:
            Tuple of (ordered_tables, relationships).
        """
        # Separate tables by type
        dimensions = [t for t in schema.tables if t.table_type == TableType.DIMENSION]
        attributes = [t for t in schema.tables if t.table_type == TableType.ATTRIBUTE]
        facts = [t for t in schema.tables if t.table_type == TableType.FACT]

        # Deployment order: dimensions -> attributes -> facts
        ordered_tables = dimensions + attributes + facts

        # All relationships after all tables
        return ordered_tables, list(schema.relationships)

    def generate_table_specs(self, schema: SemanticSchema) -> list[TableSpec]:
        """Generate MCP table specifications for all tables.

        Args:
            schema: The semantic schema to convert.

        Returns:
            List of TableSpec objects in deployment order.
        """
        ordered_tables, _ = self.get_deployment_order(schema)
        return [self.mcp_client.table_to_spec(t) for t in ordered_tables]

    def generate_relationship_specs(
        self, schema: SemanticSchema
    ) -> list[RelationshipSpec]:
        """Generate MCP relationship specifications for all relationships.

        Args:
            schema: The semantic schema to convert.

        Returns:
            List of RelationshipSpec objects.
        """
        return [self.mcp_client.relationship_to_spec(r) for r in schema.relationships]

    def generate_deployment_script(
        self, schema_path: Optional[Path] = None
    ) -> str:
        """Generate human-readable deployment script.

        Returns a markdown-formatted script showing all tables and
        relationships to be created. This is what Claude Code uses
        to execute the actual MCP tool calls.

        Args:
            schema_path: Optional path to schema JSON file.

        Returns:
            Markdown-formatted deployment script.
        """
        schema = self.load_schema(schema_path)
        ordered_tables, relationships = self.get_deployment_order(schema)
        table_specs = self.generate_table_specs(schema)
        rel_specs = self.generate_relationship_specs(schema)

        lines: list[str] = []
        lines.append("# WiQ Semantic Model Deployment Script")
        lines.append("")
        lines.append(f"**Model:** {schema.name}")
        lines.append(f"**Tables:** {len(ordered_tables)}")
        lines.append(f"**Relationships:** {len(relationships)}")
        lines.append("")

        # Group tables by source for better narration
        lines.append("## Tables to Create")
        lines.append("")

        # Dimension tables
        dim_tables = [t for t in ordered_tables if t.table_type == TableType.DIMENSION]
        if dim_tables:
            lines.append("### Dimension Tables (deploy first)")
            lines.append("")
            for table in dim_tables:
                source = get_table_source(table.name)
                lines.append(f"- **{table.name}** ({len(table.columns)} columns) - {source}")
            lines.append("")

        # Attribute tables
        attr_tables = [t for t in ordered_tables if t.table_type == TableType.ATTRIBUTE]
        if attr_tables:
            lines.append("### Attribute Tables")
            lines.append("")
            for table in attr_tables:
                source = get_table_source(table.name)
                lines.append(f"- **{table.name}** ({len(table.columns)} columns) - {source}")
            lines.append("")

        # Fact tables
        fact_tables = [t for t in ordered_tables if t.table_type == TableType.FACT]
        if fact_tables:
            lines.append("### Fact Tables")
            lines.append("")
            for table in fact_tables:
                source = get_table_source(table.name)
                lines.append(f"- **{table.name}** ({len(table.columns)} columns) - {source}")
            lines.append("")

        # Relationships
        lines.append("## Relationships to Create")
        lines.append("")
        lines.append("Create these after ALL tables exist:")
        lines.append("")
        for rel in relationships:
            cardinality = rel.cardinality if isinstance(rel.cardinality, str) else rel.cardinality.value
            lines.append(
                f"- {rel.from_table}.{rel.from_column} -> "
                f"{rel.to_table}.{rel.to_column} ({cardinality})"
            )
        lines.append("")

        # MCP Tool Specifications section
        lines.append("## MCP Tool Specifications")
        lines.append("")
        lines.append("### Table Specifications")
        lines.append("")
        lines.append("```json")
        for spec in table_specs:
            spec_dict = {
                "name": spec.name,
                "columns": spec.columns,
            }
            lines.append(json.dumps(spec_dict, indent=2))
            lines.append("")
        lines.append("```")
        lines.append("")

        lines.append("### Relationship Specifications")
        lines.append("")
        lines.append("```json")
        for spec in rel_specs:
            spec_dict = {
                "from_table": spec.from_table,
                "from_column": spec.from_column,
                "to_table": spec.to_table,
                "to_column": spec.to_column,
                "cardinality": spec.cardinality,
                "cross_filter_direction": spec.cross_filter_direction,
            }
            lines.append(json.dumps(spec_dict, indent=2))
        lines.append("```")

        return "\n".join(lines)

    def run_with_ui(
        self, schema_path: Optional[Path] = None
    ) -> DeploymentResult:
        """Run deployment with UI narration.

        This method demonstrates the deployment flow with Rich UI output.
        It shows what will happen during actual MCP deployment.

        Args:
            schema_path: Optional path to schema JSON file.

        Returns:
            DeploymentResult with deployment information.
        """
        start_time = time.time()
        errors: list[str] = []

        try:
            # Load schema
            schema = self.load_schema(schema_path)
            ordered_tables, relationships = self.get_deployment_order(schema)

            # Show header
            self.ui.show_header()

            # Show tables
            self.ui.show_section_header("Deploying Tables")
            for table in ordered_tables:
                table_type = table.table_type if isinstance(table.table_type, str) else table.table_type.value
                source = get_table_source(table.name)
                self.ui.show_deploying_table(table.name, table_type, source)
                self.ui.show_table_complete(table.name, len(table.columns))

            # Show relationships
            self.ui.show_section_header("Creating Relationships")
            for rel in relationships:
                cardinality = rel.cardinality if isinstance(rel.cardinality, str) else rel.cardinality.value
                self.ui.show_deploying_relationship(rel.from_table, rel.to_table)
                self.ui.show_relationship_complete(rel.from_table, rel.to_table, cardinality)

            # Show summary
            duration = time.time() - start_time
            tables_deployed = [t.name for t in ordered_tables]
            self.ui.show_summary(tables_deployed, len(relationships), duration)

            return DeploymentResult(
                success=True,
                tables_deployed=tables_deployed,
                relationships_created=len(relationships),
                errors=errors,
                duration_seconds=duration,
            )

        except Exception as e:
            errors.append(str(e))
            self.ui.show_error(str(e))
            return DeploymentResult(
                success=False,
                tables_deployed=[],
                relationships_created=0,
                errors=errors,
                duration_seconds=time.time() - start_time,
            )
