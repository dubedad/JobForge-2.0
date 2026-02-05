"""Tests for DMBOK tagging module."""

import pytest

from jobforge.catalog.dmbok_tagging import (
    DMBOK_DATA_ELEMENT_TYPES,
    DMBOK_KNOWLEDGE_AREAS,
    add_dmbok_field_tags,
    add_dmbok_table_tags,
    get_dmbok_element_type,
    get_dmbok_knowledge_area,
    validate_phase_16_coverage,
)


# Phase 16 table names
PHASE_16_TABLES = [
    "dim_og_qualification_standard",
    "dim_og_job_evaluation_standard",
    "fact_og_pay_rates",
    "fact_og_allowances",
    "dim_collective_agreement",
    "fact_caf_training",
    "dim_caf_training_location",
]


class TestDMBOKKnowledgeAreas:
    """Tests for table-level DMBOK knowledge area mappings."""

    @pytest.mark.parametrize(
        "table_name,expected_area",
        [
            ("dim_og_qualification_standard", "Metadata Management"),
            ("dim_og_job_evaluation_standard", "Metadata Management"),
            ("fact_og_pay_rates", "Reference and Master Data"),
            ("fact_og_allowances", "Reference and Master Data"),
            ("dim_collective_agreement", "Reference and Master Data"),
            ("fact_caf_training", "Metadata Management"),
            ("dim_caf_training_location", "Reference and Master Data"),
        ],
    )
    def test_phase_16_tables_have_knowledge_areas(self, table_name: str, expected_area: str):
        """Each Phase 16 table should have a DMBOK knowledge area mapping."""
        assert table_name in DMBOK_KNOWLEDGE_AREAS
        assert DMBOK_KNOWLEDGE_AREAS[table_name] == expected_area

    def test_all_phase_16_tables_mapped(self):
        """All Phase 16 tables should be in the mapping."""
        for table in PHASE_16_TABLES:
            assert table in DMBOK_KNOWLEDGE_AREAS, f"{table} not in DMBOK_KNOWLEDGE_AREAS"

    def test_validate_phase_16_coverage(self):
        """validate_phase_16_coverage should return all True for Phase 16 tables."""
        coverage = validate_phase_16_coverage()
        assert all(coverage.values()), f"Missing coverage: {[k for k, v in coverage.items() if not v]}"

    def test_get_dmbok_knowledge_area_known_table(self):
        """get_dmbok_knowledge_area should return correct area for known tables."""
        assert get_dmbok_knowledge_area("dim_og") == "Reference and Master Data"
        assert get_dmbok_knowledge_area("fact_caf_training") == "Metadata Management"

    def test_get_dmbok_knowledge_area_unknown_table(self):
        """get_dmbok_knowledge_area should return default for unknown tables."""
        assert get_dmbok_knowledge_area("unknown_table") == "Data Storage and Operations"


class TestAddDMBOKTableTags:
    """Tests for add_dmbok_table_tags function."""

    def test_adds_knowledge_area_to_metadata(self):
        """Should add dmbok_knowledge_area to table metadata."""
        metadata = {"table_name": "fact_og_pay_rates", "domain": "occupational_groups"}
        result = add_dmbok_table_tags(metadata, "fact_og_pay_rates")

        assert "dmbok_knowledge_area" in result
        assert result["dmbok_knowledge_area"] == "Reference and Master Data"

    def test_preserves_existing_metadata(self):
        """Should preserve existing metadata fields."""
        metadata = {
            "table_name": "dim_collective_agreement",
            "domain": "occupational_groups",
            "source": "TBS",
        }
        result = add_dmbok_table_tags(metadata, "dim_collective_agreement")

        assert result["table_name"] == "dim_collective_agreement"
        assert result["domain"] == "occupational_groups"
        assert result["source"] == "TBS"
        assert result["dmbok_knowledge_area"] == "Reference and Master Data"

    def test_uses_default_for_unknown_table(self):
        """Should use default knowledge area for unmapped tables."""
        metadata = {"table_name": "some_new_table"}
        result = add_dmbok_table_tags(metadata, "some_new_table")

        assert result["dmbok_knowledge_area"] == "Data Storage and Operations"


class TestDMBOKDataElementTypes:
    """Tests for field-level DMBOK data element type mappings."""

    def test_reference_codes_mapped(self):
        """Reference code columns should be mapped."""
        reference_codes = ["og_code", "caf_occupation_id", "training_location_id", "agreement_id"]
        for col in reference_codes:
            assert DMBOK_DATA_ELEMENT_TYPES.get(col) == "reference_code", f"{col} not mapped to reference_code"

    def test_descriptive_text_mapped(self):
        """Descriptive text columns should be mapped."""
        descriptive = ["full_text", "education_requirement_text", "factor_description", "level_description"]
        for col in descriptive:
            assert DMBOK_DATA_ELEMENT_TYPES.get(col) == "descriptive_text", f"{col} not mapped to descriptive_text"

    def test_numeric_attributes_mapped(self):
        """Numeric attribute columns should be mapped."""
        numeric = ["min_years_experience", "factor_points", "annual_rate", "duration_weeks"]
        for col in numeric:
            assert DMBOK_DATA_ELEMENT_TYPES.get(col) == "numeric_attribute", f"{col} not mapped to numeric_attribute"

    def test_boolean_flags_mapped(self):
        """Boolean flag columns should be mapped."""
        booleans = ["has_equivalency", "requires_travel", "is_represented", "recertification_required"]
        for col in booleans:
            assert DMBOK_DATA_ELEMENT_TYPES.get(col) == "boolean_flag", f"{col} not mapped to boolean_flag"

    def test_temporal_provenance_mapped(self):
        """Temporal provenance columns should be mapped."""
        temporal = ["_ingested_at", "_scraped_at", "_extracted_at"]
        for col in temporal:
            assert DMBOK_DATA_ELEMENT_TYPES.get(col) == "temporal_provenance", f"{col} not mapped to temporal_provenance"

    def test_get_dmbok_element_type_known_column(self):
        """get_dmbok_element_type should return correct type for known columns."""
        assert get_dmbok_element_type("og_code") == "reference_code"
        assert get_dmbok_element_type("annual_rate") == "numeric_attribute"

    def test_get_dmbok_element_type_unknown_column(self):
        """get_dmbok_element_type should return default for unknown columns."""
        assert get_dmbok_element_type("unknown_column") == "data_attribute"


class TestAddDMBOKFieldTags:
    """Tests for add_dmbok_field_tags function."""

    def test_tags_list_format_columns(self):
        """Should tag columns in list format."""
        columns = [
            {"name": "og_code", "type": "VARCHAR"},
            {"name": "annual_rate", "type": "DOUBLE"},
            {"name": "_ingested_at", "type": "TIMESTAMP"},
        ]
        result = add_dmbok_field_tags(columns)

        assert result[0]["dmbok_element_type"] == "reference_code"
        assert result[1]["dmbok_element_type"] == "numeric_attribute"
        assert result[2]["dmbok_element_type"] == "temporal_provenance"

    def test_tags_dict_format_columns(self):
        """Should tag columns in dict format."""
        columns = {
            "og_code": {"type": "VARCHAR", "description": "OG code"},
            "annual_rate": {"type": "DOUBLE", "description": "Annual rate"},
            "_batch_id": {"type": "VARCHAR", "description": "Batch ID"},
        }
        result = add_dmbok_field_tags(columns)

        assert result["og_code"]["dmbok_element_type"] == "reference_code"
        assert result["annual_rate"]["dmbok_element_type"] == "numeric_attribute"
        assert result["_batch_id"]["dmbok_element_type"] == "provenance_identifier"

    def test_preserves_existing_column_metadata(self):
        """Should preserve existing column metadata."""
        columns = [
            {
                "name": "og_code",
                "type": "VARCHAR",
                "description": "OG code",
                "nullable": False,
            }
        ]
        result = add_dmbok_field_tags(columns)

        assert result[0]["name"] == "og_code"
        assert result[0]["type"] == "VARCHAR"
        assert result[0]["description"] == "OG code"
        assert result[0]["nullable"] is False
        assert result[0]["dmbok_element_type"] == "reference_code"

    def test_uses_default_for_unknown_columns(self):
        """Should use default element type for unmapped columns."""
        columns = [{"name": "custom_field", "type": "VARCHAR"}]
        result = add_dmbok_field_tags(columns)

        assert result[0]["dmbok_element_type"] == "data_attribute"

    def test_handles_empty_columns(self):
        """Should handle empty column list."""
        result = add_dmbok_field_tags([])
        assert result == []

    def test_handles_empty_dict_columns(self):
        """Should handle empty column dict."""
        result = add_dmbok_field_tags({})
        assert result == {}


class TestPhase16ColumnCoverage:
    """Tests to ensure Phase 16 columns have appropriate DMBOK element types."""

    # Sample columns from Phase 16 tables
    PHASE_16_COLUMNS = [
        # dim_og_qualification_standard
        "og_code",
        "og_subgroup_code",
        "education_level",
        "education_requirement_text",
        "min_years_experience",
        "experience_requirement_text",
        "essential_qualification_text",
        "asset_qualification_text",
        "has_equivalency",
        "equivalency_statement",
        "bilingual_reading_level",
        "bilingual_writing_level",
        "bilingual_oral_level",
        "security_clearance",
        "requires_travel",
        "shift_work",
        "full_text",
        "_source_url",
        "_extracted_at",
        "_ingested_at",
        "_batch_id",
        "_layer",
        # dim_og_job_evaluation_standard
        "standard_name",
        "standard_type",
        "factor_name",
        "factor_description",
        "factor_points",
        "factor_percentage",
        "factor_level",
        "level_points",
        "level_description",
        "effective_date",
        "version",
        # fact_og_pay_rates
        "classification_level",
        "step",
        "annual_rate",
        "hourly_rate",
        "is_represented",
        "collective_agreement_id",
        "pay_progression_type",
        # fact_og_allowances
        "allowance_id",
        "allowance_type",
        "allowance_name",
        "amount",
        "rate_type",
        "percentage",
        "eligibility_criteria",
        # dim_collective_agreement
        "agreement_id",
        "agreement_name",
        "og_subgroup_codes",
        "bargaining_agent",
        "employer",
        "signing_date",
        "expiry_date",
        # fact_caf_training
        "caf_occupation_id",
        "training_type",
        "duration_weeks",
        "duration_text",
        "training_location_id",
        "training_location_text",
        "certifications_awarded",
        "qualifications_awarded",
        "prerequisite_courses",
        "minimum_rank",
        "civilian_credential_level",
        "civilian_equivalency_text",
        "recertification_required",
        "recertification_frequency",
        # dim_caf_training_location
        "location_name",
        "province",
        "country",
        "base_type",
        "_source",
    ]

    def test_all_phase_16_columns_have_element_types(self):
        """All Phase 16 columns should have a DMBOK element type mapping or get default."""
        for col in self.PHASE_16_COLUMNS:
            element_type = get_dmbok_element_type(col)
            assert element_type is not None, f"{col} returned None element type"
            assert isinstance(element_type, str), f"{col} element type is not a string"

    def test_phase_16_reference_codes_properly_typed(self):
        """Reference code columns should be typed as reference_code."""
        reference_columns = [
            "og_code",
            "og_subgroup_code",
            "caf_occupation_id",
            "training_location_id",
            "agreement_id",
            "allowance_id",
            "classification_level",
            "collective_agreement_id",
        ]
        for col in reference_columns:
            assert get_dmbok_element_type(col) == "reference_code", f"{col} should be reference_code"

    def test_phase_16_provenance_columns_properly_typed(self):
        """Provenance columns should be typed appropriately."""
        provenance_cols = ["_source_url", "_batch_id", "_source_file", "_source"]
        for col in provenance_cols:
            element_type = get_dmbok_element_type(col)
            assert element_type in ["provenance_identifier", "provenance_marker"], f"{col} should be provenance type"
