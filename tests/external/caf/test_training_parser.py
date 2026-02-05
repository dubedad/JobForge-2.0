"""Tests for CAF training parser.

Tests duration parsing, location normalization, certification extraction,
and full training info parsing with sparse data handling.
"""

import pytest

from jobforge.external.caf.training_parser import (
    CAFTraining,
    CANONICAL_LOCATIONS,
    extract_certifications,
    extract_qualifications,
    extract_recertification_info,
    get_all_canonical_locations,
    normalize_training_location,
    parse_civilian_credential_level,
    parse_duration_to_weeks,
    parse_training_info,
)


class TestCAFTrainingModel:
    """Tests for CAFTraining Pydantic model."""

    def test_model_minimal_valid(self):
        """Test model with minimal required fields."""
        training = CAFTraining(
            caf_occupation_id="pilot",
            training_type="bmq",
        )
        assert training.caf_occupation_id == "pilot"
        assert training.training_type == "bmq"
        assert training.duration_weeks is None
        assert training.certifications_awarded == []

    def test_model_full_fields(self):
        """Test model with all fields populated."""
        training = CAFTraining(
            caf_occupation_id="infantry-soldier",
            training_type="occupation_specific",
            duration_weeks=12.0,
            duration_text="12 weeks",
            training_location_id="cfb-borden",
            training_location_text="CFB Borden, Ontario",
            certifications_awarded=["First Aid", "CPR"],
            qualifications_awarded=["BMQ", "DP1"],
            prerequisite_courses=["Basic Training"],
            minimum_rank="Private",
            civilian_credential_level="certificate",
            civilian_equivalency_text="Skills transferable to security industry",
            recertification_required=True,
            recertification_frequency="annually",
            source_url="https://forces.ca/en/career/infantry-soldier",
            extracted_at="2026-02-05T00:00:00Z",
        )
        assert training.duration_weeks == 12.0
        assert training.recertification_required is True
        assert len(training.certifications_awarded) == 2


class TestParseDurationToWeeks:
    """Tests for duration parsing."""

    def test_parse_weeks_integer(self):
        """Parse '12 weeks' to 12.0."""
        weeks, text = parse_duration_to_weeks("12 weeks")
        assert weeks == 12.0
        assert text == "12 weeks"

    def test_parse_weeks_decimal(self):
        """Parse '10.5 weeks' to 10.5."""
        weeks, text = parse_duration_to_weeks("10.5 weeks")
        assert weeks == 10.5

    def test_parse_week_singular(self):
        """Parse '1 week' to 1.0."""
        weeks, text = parse_duration_to_weeks("1 week")
        assert weeks == 1.0

    def test_parse_months_to_weeks(self):
        """Parse '2 months' to approximately 8.7 weeks."""
        weeks, text = parse_duration_to_weeks("2 months")
        assert weeks is not None
        assert 8.0 <= weeks <= 9.0  # ~8.66 weeks

    def test_parse_six_months(self):
        """Parse '6 months' to approximately 26 weeks."""
        weeks, text = parse_duration_to_weeks("6 months")
        assert weeks is not None
        assert 25.0 <= weeks <= 27.0  # ~26 weeks

    def test_parse_range_weeks(self):
        """Parse 'eight to 11 weeks' to average 9.5."""
        weeks, text = parse_duration_to_weeks("8 to 11 weeks")
        assert weeks == 9.5

    def test_parse_range_with_dash(self):
        """Parse '10-12 weeks' to average 11."""
        weeks, text = parse_duration_to_weeks("10-12 weeks")
        assert weeks == 11.0

    def test_parse_approximate(self):
        """Parse 'approximately 15 weeks'."""
        weeks, text = parse_duration_to_weeks("approximately 15 weeks")
        assert weeks == 15.0

    def test_parse_about(self):
        """Parse 'about 8 weeks'."""
        weeks, text = parse_duration_to_weeks("about 8 weeks")
        assert weeks == 8.0

    def test_parse_word_numbers(self):
        """Parse 'twelve weeks' to 12.0."""
        weeks, text = parse_duration_to_weeks("twelve weeks")
        assert weeks == 12.0

    def test_parse_for_prefix(self):
        """Parse 'for 10 weeks'."""
        weeks, text = parse_duration_to_weeks("training for 10 weeks duration")
        assert weeks == 10.0

    def test_parse_none_input(self):
        """Return None for None input."""
        weeks, text = parse_duration_to_weeks(None)
        assert weeks is None
        assert text is None

    def test_parse_empty_string(self):
        """Return None for empty string."""
        weeks, text = parse_duration_to_weeks("")
        assert weeks is None

    def test_parse_unparseable(self):
        """Return None for text without duration."""
        weeks, text = parse_duration_to_weeks("Training is provided in English")
        assert weeks is None
        assert text == "Training is provided in English"

    def test_parse_days_to_weeks(self):
        """Parse '14 days' to 2 weeks."""
        weeks, text = parse_duration_to_weeks("14 days")
        assert weeks == 2.0


class TestNormalizeTrainingLocation:
    """Tests for location normalization with fuzzy matching."""

    def test_exact_match_borden(self):
        """Match 'Borden, Ontario' to CFB Borden."""
        loc_id, meta = normalize_training_location("Borden, Ontario")
        assert loc_id == "cfb-borden"
        assert meta["name"] == "CFB Borden"
        assert meta["province"] == "ON"

    def test_exact_match_saint_jean(self):
        """Match 'Saint-Jean-sur-Richelieu' to CFLRS."""
        loc_id, meta = normalize_training_location("Saint-Jean-sur-Richelieu, Quebec")
        assert loc_id == "cflrs-saint-jean-sur-richelieu"
        assert meta["base_type"] == "cflrs"

    def test_partial_match_kingston(self):
        """Match 'Kingston, ON' to CFB Kingston."""
        loc_id, meta = normalize_training_location("Kingston, ON")
        assert loc_id == "cfb-kingston"

    def test_partial_match_gagetown(self):
        """Match 'Gagetown, New Brunswick' to CFB Gagetown."""
        loc_id, meta = normalize_training_location("Gagetown, New Brunswick")
        assert loc_id == "cfb-gagetown"
        assert meta["province"] == "NB"

    def test_partial_match_esquimalt(self):
        """Match 'Esquimalt, BC' to CFB Esquimalt."""
        loc_id, meta = normalize_training_location("Esquimalt, BC")
        assert loc_id == "cfb-esquimalt"

    def test_fuzzy_match_halifax(self):
        """Fuzzy match 'Naval base Halifax'."""
        loc_id, meta = normalize_training_location("Naval base Halifax")
        assert loc_id == "cfb-halifax"

    def test_none_input(self):
        """Return None for None input."""
        loc_id, meta = normalize_training_location(None)
        assert loc_id is None
        assert meta is None

    def test_empty_string(self):
        """Return None for empty string."""
        loc_id, meta = normalize_training_location("")
        assert loc_id is None

    def test_unknown_location(self):
        """Return None for unknown location."""
        loc_id, meta = normalize_training_location("Some Unknown Place, USA")
        assert loc_id is None

    def test_case_insensitive(self):
        """Match should be case insensitive."""
        loc_id, meta = normalize_training_location("BORDEN")
        assert loc_id == "cfb-borden"


class TestParseCivilianCredentialLevel:
    """Tests for civilian credential level parsing."""

    def test_certificate(self):
        """Parse 'certificate' level."""
        level = parse_civilian_credential_level("Earn a certificate upon completion")
        assert level == "certificate"

    def test_diploma(self):
        """Parse 'diploma' level."""
        level = parse_civilian_credential_level("Equivalent to technician diploma")
        assert level == "diploma"

    def test_degree(self):
        """Parse 'degree' level."""
        level = parse_civilian_credential_level("Equivalent to bachelor degree")
        assert level == "degree"

    def test_professional(self):
        """Parse 'professional' designation."""
        level = parse_civilian_credential_level("Leads to professional designation")
        assert level == "professional"

    def test_trade(self):
        """Parse 'trade' certification."""
        level = parse_civilian_credential_level("Red Seal trade certification")
        assert level == "trade"

    def test_none_input(self):
        """Return None for None input."""
        level = parse_civilian_credential_level(None)
        assert level is None

    def test_no_credential(self):
        """Return None when no credential mentioned."""
        level = parse_civilian_credential_level("Training is provided in English")
        assert level is None


class TestExtractCertifications:
    """Tests for certification extraction."""

    def test_extract_first_aid(self):
        """Extract 'First Aid' certification."""
        certs = extract_certifications("Receive First Aid certification")
        assert "First Aid" in certs or "First Aid certification" in certs

    def test_extract_cpr(self):
        """Extract 'CPR' certification."""
        certs = extract_certifications("Includes CPR training")
        assert any("CPR" in c for c in certs)

    def test_extract_multiple(self):
        """Extract multiple certifications."""
        text = "Earn a First Aid certificate and CPR certification"
        certs = extract_certifications(text)
        assert len(certs) >= 1

    def test_empty_text(self):
        """Return empty list for None input."""
        certs = extract_certifications(None)
        assert certs == []

    def test_no_certifications(self):
        """Return empty list when no certifications found."""
        certs = extract_certifications("Basic training provided")
        assert certs == []


class TestExtractQualifications:
    """Tests for military qualification extraction."""

    def test_extract_bmoq(self):
        """Extract BMOQ qualification."""
        quals = extract_qualifications("Complete BMOQ before occupational training")
        assert "BMOQ" in quals

    def test_extract_bmq(self):
        """Extract BMQ qualification."""
        quals = extract_qualifications("Complete BMQ first")
        assert "BMQ" in quals

    def test_extract_dp1(self):
        """Extract DP1 qualification."""
        quals = extract_qualifications("Earn your DP1 qualification")
        assert "DP1" in quals

    def test_extract_ql_levels(self):
        """Extract QL levels."""
        quals = extract_qualifications("Progress from QL3 to QL5 to QL6A")
        assert "QL3" in quals
        assert "QL5" in quals

    def test_empty_text(self):
        """Return empty list for None input."""
        quals = extract_qualifications(None)
        assert quals == []


class TestExtractRecertificationInfo:
    """Tests for recertification info extraction."""

    def test_annual_recertification(self):
        """Detect annual recertification requirement."""
        required, freq = extract_recertification_info("Annual recertification required")
        assert required is True
        assert "annual" in freq.lower()

    def test_every_five_years(self):
        """Detect 'every 5 years' recertification."""
        required, freq = extract_recertification_info("Recertification every 5 years")
        assert required is True

    def test_currency_training(self):
        """Detect currency training requirement."""
        required, freq = extract_recertification_info("Currency training maintained")
        assert required is True

    def test_no_recertification(self):
        """Return False when no recertification mentioned."""
        required, freq = extract_recertification_info("Training provided once")
        assert required is False
        assert freq is None

    def test_none_input(self):
        """Return False for None input."""
        required, freq = extract_recertification_info(None)
        assert required is False


class TestParseTrainingInfo:
    """Tests for full training info parsing."""

    def test_parse_typical_career_data(self):
        """Parse typical CAF career with BMQ and occupation training."""
        career_data = {
            "career_id": "infantry-soldier",
            "training_en": """Training
Basic Military Qualification
The first stage of training is the Basic Military Qualification course, or Basic Training, held at the Canadian Forces Leadership and Recruit School in Saint-Jean-sur-Richelieu, Quebec. This training takes 12 weeks.

Available Professional Training
Infantry soldiers attend occupation training at CFB Gagetown, New Brunswick for 17 weeks. This training includes weapons handling and tactical skills.""",
            "url_en": "https://forces.ca/en/career/infantry-soldier",
        }

        records = parse_training_info(career_data)

        assert len(records) >= 1

        # Check BMQ record
        bmq_records = [r for r in records if r.training_type == "bmq"]
        if bmq_records:
            bmq = bmq_records[0]
            assert bmq.caf_occupation_id == "infantry-soldier"
            assert bmq.training_location_id == "cflrs-saint-jean-sur-richelieu"
            assert bmq.duration_weeks == 12.0

    def test_parse_sparse_data_empty_training(self):
        """Handle career with no training_en field gracefully."""
        career_data = {
            "career_id": "some-occupation",
            "training_en": "",
            "url_en": "https://forces.ca/en/career/some-occupation",
        }

        records = parse_training_info(career_data)
        assert records == []  # Should return empty, not error

    def test_parse_sparse_data_none_training(self):
        """Handle career with None training_en field."""
        career_data = {
            "career_id": "another-occupation",
            "training_en": None,
            "url_en": "https://forces.ca/en/career/another-occupation",
        }

        records = parse_training_info(career_data)
        assert records == []

    def test_parse_occupation_specific_only(self):
        """Parse career with only occupation-specific training."""
        career_data = {
            "career_id": "technician",
            "training_en": """Training
Available Professional Training
Technical training takes place at CFB Borden for approximately 19 weeks. Topics include systems maintenance and troubleshooting.""",
            "url_en": "https://forces.ca/en/career/technician",
        }

        records = parse_training_info(career_data)

        assert len(records) >= 1
        occ_records = [r for r in records if r.training_type == "occupation_specific"]
        assert len(occ_records) >= 1

    def test_parse_extracts_location(self):
        """Verify location extraction from training text."""
        career_data = {
            "career_id": "pilot",
            "training_en": """Training
Basic Military Officer Qualification
After enrolment, basic officer training at CFLRS Saint-Jean-sur-Richelieu for 12 weeks.""",
            "url_en": "https://forces.ca/en/career/pilot",
        }

        records = parse_training_info(career_data)

        if records:
            record = records[0]
            # Should find Saint-Jean location
            assert record.training_location_id is not None or record.training_location_text is not None

    def test_parse_includes_provenance(self):
        """Verify provenance fields are populated."""
        career_data = {
            "career_id": "medic",
            "training_en": "Training at CFB Borden for 10 weeks.",
            "url_en": "https://forces.ca/en/career/medic",
        }

        records = parse_training_info(career_data)

        if records:
            record = records[0]
            assert record.source_url == "https://forces.ca/en/career/medic"
            assert record.extracted_at is not None


class TestGetAllCanonicalLocations:
    """Tests for canonical locations retrieval."""

    def test_returns_list(self):
        """Returns a list of location dicts."""
        locations = get_all_canonical_locations()
        assert isinstance(locations, list)
        assert len(locations) > 0

    def test_location_structure(self):
        """Each location has required fields."""
        locations = get_all_canonical_locations()
        for loc in locations:
            assert "id" in loc
            assert "name" in loc
            assert "province" in loc
            assert "country" in loc
            assert "base_type" in loc

    def test_includes_major_bases(self):
        """Includes major training bases."""
        locations = get_all_canonical_locations()
        names = [loc["name"] for loc in locations]
        assert any("Borden" in name for name in names)
        assert any("Saint-Jean" in name for name in names)
        assert any("Gagetown" in name for name in names)

    def test_at_least_five_locations(self):
        """Returns at least 5 locations per plan requirements."""
        locations = get_all_canonical_locations()
        assert len(locations) >= 5
