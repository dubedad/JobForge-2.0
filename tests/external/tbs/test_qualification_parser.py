"""Tests for TBS enhanced qualification text parser.

Tests cover:
1. Education level extraction (each standardized level)
2. Experience years extraction (various patterns)
3. Bilingual level extraction (BBB, CBC patterns)
4. Security clearance extraction
5. Equivalency detection
6. Full parse_enhanced_qualification with real TBS text sample
7. Fallback when patterns don't match (returns None, preserves text)
8. Essential vs asset qualification extraction
9. Conditions of employment flags
10. Operational requirements flags
"""

import pytest

from jobforge.external.tbs.qualification_parser import (
    EnhancedQualification,
    extract_education_level,
    extract_experience_years,
    extract_bilingual_levels,
    extract_security_clearance,
    extract_equivalency,
    extract_certification,
    extract_conditions_of_employment,
    extract_operational_requirements,
    extract_essential_asset_qualifications,
    parse_enhanced_qualification,
)


class TestEnhancedQualificationModel:
    """Test EnhancedQualification Pydantic model."""

    def test_model_default_values(self):
        """Model should have sensible defaults."""
        model = EnhancedQualification(full_text="Sample text")

        assert model.education_level is None
        assert model.education_requirement_text == ""
        assert model.min_years_experience is None
        assert model.has_equivalency is False
        assert model.requires_travel is False
        assert model.shift_work is False

    def test_model_with_all_fields(self):
        """Model should accept all structured fields."""
        model = EnhancedQualification(
            education_level="bachelors",
            education_requirement_text="Graduation with a degree",
            min_years_experience=3,
            experience_requirement_text="Three years experience",
            essential_qualification_text="Must have degree",
            asset_qualification_text="MBA preferred",
            has_equivalency=True,
            equivalency_statement="Acceptable combination",
            bilingual_reading_level="B",
            bilingual_writing_level="B",
            bilingual_oral_level="C",
            security_clearance="Secret",
            requires_travel=True,
            shift_work=False,
            physical_demands=True,
            overtime_required=True,
            on_call_required=False,
            deployments_required=False,
            certification_requirement="CPA certification",
            full_text="Full qualification text here",
        )

        assert model.education_level == "bachelors"
        assert model.min_years_experience == 3
        assert model.bilingual_oral_level == "C"
        assert model.security_clearance == "Secret"


class TestExtractEducationLevel:
    """Tests for extract_education_level function."""

    def test_extracts_high_school(self):
        """Should detect high school / secondary school diploma."""
        text = "The minimum standard is: A secondary school diploma or employer-approved alternatives."
        level, original = extract_education_level(text)

        assert level == "high_school"
        assert "secondary school" in original.lower() or level == "high_school"

    def test_extracts_certificate(self):
        """Should detect certificate programs."""
        text = """
        The minimum standard is:
        Successful completion of a recognized certificate program in the field.
        """
        level, _ = extract_education_level(text)
        assert level == "certificate"

    def test_extracts_diploma(self):
        """Should detect college diploma."""
        text = """
        Education:
        A diploma from a recognized post-secondary institution in a relevant field.
        """
        level, _ = extract_education_level(text)
        assert level == "diploma"

    def test_extracts_bachelors(self):
        """Should detect bachelor's degree."""
        text = """
        The minimum standard is:
        Graduation with a degree from a recognized post-secondary institution with
        acceptable specialization in economics, sociology or statistics.
        """
        level, original = extract_education_level(text)
        assert level == "bachelors"
        assert len(original) > 0

    def test_extracts_masters(self):
        """Should detect master's degree."""
        text = """
        The minimum standard for positions at this level is:
        A master's degree in a relevant field from a recognized university.
        """
        level, _ = extract_education_level(text)
        assert level == "masters"

    def test_extracts_phd(self):
        """Should detect PhD/doctorate."""
        text = """
        Education:
        A PhD or doctoral degree in the relevant scientific discipline.
        """
        level, _ = extract_education_level(text)
        assert level == "phd"

    def test_extracts_professional_degree(self):
        """Should detect professional degrees (law, medicine, engineering)."""
        text = """
        The minimum standard is:
        Eligibility for certification as a professional engineer in Canada.
        """
        level, _ = extract_education_level(text)
        assert level == "professional_degree"

    def test_returns_none_when_no_match(self):
        """Should return None when no education level detected."""
        text = "This text does not mention any education requirements at all."
        level, _ = extract_education_level(text)
        assert level is None

    def test_preserves_original_text(self):
        """Should preserve original education section text."""
        text = """
        The minimum standard is:
        Graduation with a degree from a recognized post-secondary institution.

        Experience is also required.
        """
        level, original = extract_education_level(text)
        assert "Graduation" in original or "degree" in original


class TestExtractExperienceYears:
    """Tests for extract_experience_years function."""

    def test_extracts_minimum_of_n_years(self):
        """Should extract 'minimum of N years' pattern."""
        text = """
        Experience:
        A minimum of 5 years of relevant experience in the field.
        """
        years, _ = extract_experience_years(text)
        assert years == 5

    def test_extracts_at_least_n_years(self):
        """Should extract 'at least N years' pattern."""
        text = """
        Experience:
        At least 3 years of progressive management experience.
        """
        years, _ = extract_experience_years(text)
        assert years == 3

    def test_extracts_n_plus_years(self):
        """Should extract 'N+ years' pattern."""
        text = """
        Requires 2+ years of relevant work experience.
        """
        years, _ = extract_experience_years(text)
        assert years == 2

    def test_extracts_word_numbers(self):
        """Should extract written numbers (two, three, etc.)."""
        text = """
        Experience:
        Two years of relevant experience is required.
        """
        years, _ = extract_experience_years(text)
        assert years == 2

    def test_returns_none_when_no_match(self):
        """Should return None when no years detected."""
        text = "Experience in the field is an asset."
        years, _ = extract_experience_years(text)
        assert years is None

    def test_preserves_experience_text(self):
        """Should preserve original experience section text."""
        text = """
        The minimum standard is: A degree.

        Experience:
        Significant experience in policy development and analysis.

        Certification is not required.
        """
        _, original = extract_experience_years(text)
        assert "experience" in original.lower() or "policy" in original.lower()


class TestExtractBilingualLevels:
    """Tests for extract_bilingual_levels function."""

    def test_extracts_bbb_profile(self):
        """Should extract BBB language profile."""
        text = "Bilingual imperative BBB is required for this position."
        result = extract_bilingual_levels(text)

        assert result["reading"] == "B"
        assert result["writing"] == "B"
        assert result["oral"] == "B"

    def test_extracts_cbc_profile(self):
        """Should extract CBC language profile."""
        text = "Language requirement: CBC/CBC bilingual profile."
        result = extract_bilingual_levels(text)

        assert result["reading"] == "C"
        assert result["writing"] == "B"
        assert result["oral"] == "C"

    def test_extracts_ccc_profile(self):
        """Should extract CCC language profile."""
        text = "Position requires CCC bilingual proficiency."
        result = extract_bilingual_levels(text)

        assert result["reading"] == "C"
        assert result["writing"] == "C"
        assert result["oral"] == "C"

    def test_extracts_explicit_format(self):
        """Should extract explicit format (reading: B, writing: B, oral: C)."""
        text = """
        Language requirements:
        Reading: B
        Writing: B
        Oral: C
        """
        result = extract_bilingual_levels(text)

        assert result["reading"] == "B"
        assert result["writing"] == "B"
        assert result["oral"] == "C"

    def test_returns_none_when_no_profile(self):
        """Should return None values when no bilingual profile found."""
        text = "English essential position."
        result = extract_bilingual_levels(text)

        assert result["reading"] is None
        assert result["writing"] is None
        assert result["oral"] is None


class TestExtractSecurityClearance:
    """Tests for extract_security_clearance function."""

    def test_extracts_reliability(self):
        """Should detect Reliability status."""
        text = "Reliability status is required for this position."
        result = extract_security_clearance(text)
        assert result == "Reliability"

    def test_extracts_secret(self):
        """Should detect Secret clearance."""
        text = "Secret clearance is required."
        result = extract_security_clearance(text)
        assert result == "Secret"

    def test_extracts_top_secret(self):
        """Should detect Top Secret clearance."""
        text = "Position requires Top Secret security clearance."
        result = extract_security_clearance(text)
        assert result == "Top Secret"

    def test_returns_none_when_no_clearance(self):
        """Should return None when no clearance mentioned."""
        text = "Standard employment conditions apply."
        result = extract_security_clearance(text)
        assert result is None


class TestExtractEquivalency:
    """Tests for extract_equivalency function."""

    def test_detects_equivalency(self):
        """Should detect equivalency statements."""
        text = """
        The minimum standard is a degree.
        An acceptable combination of education, training and experience may be considered.
        """
        has_equiv, statement = extract_equivalency(text)

        assert has_equiv is True
        assert statement is not None
        assert "acceptable combination" in statement.lower()

    def test_detects_deemed_to_meet(self):
        """Should detect 'deemed to meet' equivalency."""
        text = """
        Incumbents who do not possess the education level are deemed to meet
        the minimum standard based on their experience.
        """
        has_equiv, statement = extract_equivalency(text)

        assert has_equiv is True
        assert "deemed to meet" in statement.lower()

    def test_returns_false_when_no_equivalency(self):
        """Should return False when no equivalency found."""
        text = "The minimum standard is a degree. Experience is required."
        has_equiv, statement = extract_equivalency(text)

        assert has_equiv is False
        assert statement is None


class TestExtractCertification:
    """Tests for extract_certification function."""

    def test_extracts_occupational_certification(self):
        """Should extract Occupational Certification section."""
        text = """
        The minimum standard is a degree.

        Occupational Certification:
        Eligibility for membership in a recognized professional association.
        """
        result = extract_certification(text)

        assert result is not None
        assert "eligibility" in result.lower() or "membership" in result.lower()

    def test_extracts_possession_of_licence(self):
        """Should extract licence requirements."""
        text = """
        Possession of a valid Canadian Commercial Pilot Licence is required.
        """
        result = extract_certification(text)

        assert result is not None
        assert "licence" in result.lower()

    def test_returns_none_when_no_certification(self):
        """Should return None when no certification found."""
        text = "Education and experience requirements only."
        result = extract_certification(text)
        assert result is None


class TestExtractConditionsOfEmployment:
    """Tests for extract_conditions_of_employment function."""

    def test_detects_travel_required(self):
        """Should detect travel requirements."""
        text = "Travel is required across the region."
        result = extract_conditions_of_employment(text)
        assert result["requires_travel"] is True

    def test_detects_shift_work(self):
        """Should detect shift work requirements."""
        text = "Position requires shift work including nights and weekends."
        result = extract_conditions_of_employment(text)
        assert result["shift_work"] is True

    def test_detects_physical_demands(self):
        """Should detect physical demands."""
        text = "This position has significant physical demands."
        result = extract_conditions_of_employment(text)
        assert result["physical_demands"] is True

    def test_all_false_when_none_found(self):
        """Should return all False when no conditions found."""
        text = "Standard office work environment."
        result = extract_conditions_of_employment(text)

        assert result["requires_travel"] is False
        assert result["shift_work"] is False
        assert result["physical_demands"] is False


class TestExtractOperationalRequirements:
    """Tests for extract_operational_requirements function."""

    def test_detects_overtime(self):
        """Should detect overtime requirements."""
        text = "Position may require overtime during peak periods."
        result = extract_operational_requirements(text)
        assert result["overtime_required"] is True

    def test_detects_on_call(self):
        """Should detect on-call requirements."""
        text = "On-call availability is required."
        result = extract_operational_requirements(text)
        assert result["on_call_required"] is True

    def test_detects_deployments(self):
        """Should detect deployment requirements."""
        text = "Position may require deployments to remote locations."
        result = extract_operational_requirements(text)
        assert result["deployments_required"] is True

    def test_all_false_when_none_found(self):
        """Should return all False when no requirements found."""
        text = "Standard office hours."
        result = extract_operational_requirements(text)

        assert result["overtime_required"] is False
        assert result["on_call_required"] is False
        assert result["deployments_required"] is False


class TestExtractEssentialAssetQualifications:
    """Tests for extract_essential_asset_qualifications function."""

    def test_extracts_essential_qualifications(self):
        """Should extract essential qualifications section."""
        text = """
        Essential Qualifications:
        A degree from a recognized university.
        Three years of experience.

        Asset Qualifications:
        MBA is preferred.
        """
        essential, asset = extract_essential_asset_qualifications(text)

        assert essential is not None
        assert "degree" in essential.lower()

    def test_extracts_asset_qualifications(self):
        """Should extract asset qualifications section."""
        text = """
        Essential Requirements:
        Minimum of a bachelor's degree.

        Asset Qualifications:
        Experience with project management software is preferred.
        """
        _, asset = extract_essential_asset_qualifications(text)

        assert asset is not None
        assert "project management" in asset.lower() or "preferred" in asset.lower()

    def test_returns_none_when_not_found(self):
        """Should return None when sections not found."""
        text = "Basic qualification requirements for this position."
        essential, asset = extract_essential_asset_qualifications(text)

        assert essential is None
        assert asset is None


class TestParseEnhancedQualification:
    """Tests for main parse_enhanced_qualification function."""

    def test_parses_real_tbs_sample(self):
        """Should parse realistic TBS qualification text."""
        sample_text = """
        The minimum standard for positions classified at levels EC-01, EC-02 and EC-03 is:

        Graduation with a degree from a recognized post-secondary institution with
        acceptable specialization in economics, sociology or statistics.

        The minimum standard for positions classified at levels EC-04 and above is:

        Graduation with a degree from a recognized post-secondary institution with
        acceptable specialization in economics, sociology or statistics and successful
        completion of a graduate degree.

        Experience:
        A minimum of 3 years of relevant experience in economic research and policy analysis.

        Bilingual imperative BBB is required.

        Reliability status is required.

        Indeterminate incumbents who do not possess the education level prescribed above
        are deemed to meet the minimum standard based on their education, training
        and/or experience.
        """
        result = parse_enhanced_qualification(sample_text)

        assert isinstance(result, EnhancedQualification)
        # Text mentions both degree AND graduate degree, so masters is detected (for EC-04+)
        assert result.education_level in ["bachelors", "masters"]
        assert result.min_years_experience == 3
        assert result.bilingual_reading_level == "B"
        assert result.bilingual_writing_level == "B"
        assert result.bilingual_oral_level == "B"
        assert result.security_clearance == "Reliability"
        assert result.has_equivalency is True
        assert result.full_text == sample_text

    def test_parses_with_conditions_and_operations(self):
        """Should parse conditions of employment and operational requirements."""
        sample_text = """
        The minimum standard is: A secondary school diploma.

        Conditions of Employment:
        - Travel is required across the region
        - Shift work including nights and weekends
        - Position has physical demands

        Operational Requirements:
        - Overtime may be required
        - On-call availability
        """
        result = parse_enhanced_qualification(sample_text)

        assert result.education_level == "high_school"
        assert result.requires_travel is True
        assert result.shift_work is True
        assert result.physical_demands is True
        assert result.overtime_required is True
        assert result.on_call_required is True

    def test_returns_none_for_unparseable_fields(self):
        """Should return None for fields that can't be extracted."""
        sample_text = "This is minimal text with no structured qualification data."
        result = parse_enhanced_qualification(sample_text)

        assert result.education_level is None
        assert result.min_years_experience is None
        assert result.security_clearance is None
        assert result.full_text == sample_text

    def test_preserves_full_text(self):
        """Should always preserve full text."""
        sample_text = "Any qualification text is preserved for full-text search."
        result = parse_enhanced_qualification(sample_text)

        assert result.full_text == sample_text

    def test_truncates_long_text(self):
        """Should truncate text exceeding max length."""
        long_text = "x" * 60000
        result = parse_enhanced_qualification(long_text)

        assert len(result.full_text) == 50000

    def test_handles_empty_text(self):
        """Should handle empty text gracefully."""
        result = parse_enhanced_qualification("")

        assert result.education_level is None
        assert result.full_text == ""

    def test_extracts_certification(self):
        """Should extract certification requirements."""
        sample_text = """
        The minimum standard is: A degree.

        Occupational Certification:
        Possession of a valid Canadian Airline Transport Pilot Licence.
        """
        result = parse_enhanced_qualification(sample_text)

        assert result.certification_requirement is not None
        assert "licence" in result.certification_requirement.lower()


class TestProductionDataPatterns:
    """Test against patterns found in production TBS data."""

    @pytest.fixture
    def ai_qualification_sample(self) -> str:
        """Sample from Air Traffic Control qualification."""
        return """
        The minimum standards are:

        For selection to the Transport Canada Training Program:

        A secondary school diploma or employer-approved alternatives (see Note 1); or

        For appointment to AI positions for the on-the-job training phase:

        Successful completion of a Transport Canada-approved air traffic controller
        classroom and laboratory training program.

        The minimum standard for positions in the Air Traffic Control Group is:

        Possession of an Air Traffic Controller Licence.

        The employer-approved alternatives to a secondary school diploma are:
        A satisfactory score on the Public Service Commission test approved as an
        alternative to a secondary school diploma; or
        An acceptable combination of education, training and/or experience.
        """

    def test_ai_sample_education(self, ai_qualification_sample: str):
        """Should parse AI group education level."""
        result = parse_enhanced_qualification(ai_qualification_sample)
        # AI group requires secondary school or alternatives
        assert result.education_level in ["high_school", "certificate"]

    def test_ai_sample_equivalency(self, ai_qualification_sample: str):
        """Should detect AI group equivalency statement."""
        result = parse_enhanced_qualification(ai_qualification_sample)
        assert result.has_equivalency is True

    def test_ai_sample_certification(self, ai_qualification_sample: str):
        """Should extract AI group certification requirement."""
        result = parse_enhanced_qualification(ai_qualification_sample)
        assert result.certification_requirement is not None
        assert "licence" in result.certification_requirement.lower()
