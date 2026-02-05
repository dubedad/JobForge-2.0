"""CAF training information parser.

Extracts structured training information from CAF career pages,
including duration normalization to weeks, location fuzzy matching,
certifications, civilian equivalencies, and recertification requirements.

Per CONTEXT.md:
- Duration: standardized weeks + original text
- Locations: normalized dim_caf_training_location with FK
- Certifications/qualifications: linked to training programs
- Civilian equivalency: mapped to standardized credential levels
- Recurring requirements: recertification_required boolean + frequency
"""

import re
from datetime import datetime, timezone
from typing import Optional

import structlog
from pydantic import BaseModel, Field
from rapidfuzz import fuzz

logger = structlog.get_logger(__name__)


class CAFTraining(BaseModel):
    """CAF training record with structured + original text per CONTEXT.md.

    Captures BMQ (Basic Military Qualification) and occupation-specific
    training with duration normalization and location matching.
    """

    caf_occupation_id: str = Field(description="FK to dim_caf_occupation")
    training_type: str = Field(description="'bmq' or 'occupation_specific'")

    # Duration: standardized + original (CONTEXT.md)
    duration_weeks: float | None = Field(
        default=None, description="Standardized duration in weeks"
    )
    duration_text: str | None = Field(
        default=None, description="Original text (e.g., '10 weeks', '2.5 months')"
    )

    # Location (FK to dim_caf_training_location)
    training_location_id: str | None = Field(
        default=None, description="FK to dim_caf_training_location (slugified)"
    )
    training_location_text: str | None = Field(
        default=None, description="Original location text from source"
    )

    # Certifications awarded (CONTEXT.md)
    certifications_awarded: list[str] = Field(
        default_factory=list, description="Certifications awarded upon completion"
    )
    qualifications_awarded: list[str] = Field(
        default_factory=list, description="Qualifications awarded (e.g., BMOQ, QL3)"
    )

    # Prerequisites (CONTEXT.md)
    prerequisite_courses: list[str] = Field(
        default_factory=list, description="Required prerequisite courses"
    )
    minimum_rank: str | None = Field(
        default=None, description="Minimum rank required (e.g., Private, Captain)"
    )

    # Civilian equivalency (CONTEXT.md)
    civilian_credential_level: str | None = Field(
        default=None,
        description="Standardized: 'certificate', 'diploma', 'degree', 'professional'",
    )
    civilian_equivalency_text: str | None = Field(
        default=None, description="Original civilian equivalency description"
    )

    # Recurring requirements (CONTEXT.md)
    recertification_required: bool = Field(
        default=False, description="Whether periodic recertification is needed"
    )
    recertification_frequency: str | None = Field(
        default=None, description="e.g., 'annually', 'every 5 years'"
    )

    # Provenance
    source_url: str | None = Field(
        default=None, description="Source URL for this training record"
    )
    extracted_at: str | None = Field(
        default=None, description="When training info was extracted"
    )


# Canonical training locations per RESEARCH.md Pitfall 3
CANONICAL_LOCATIONS = {
    "saint-jean": {
        "id": "cflrs-saint-jean-sur-richelieu",
        "name": "CFLRS Saint-Jean-sur-Richelieu",
        "province": "QC",
        "country": "Canada",
        "base_type": "cflrs",
    },
    "borden": {
        "id": "cfb-borden",
        "name": "CFB Borden",
        "province": "ON",
        "country": "Canada",
        "base_type": "cfb",
    },
    "gagetown": {
        "id": "cfb-gagetown",
        "name": "CFB Gagetown",
        "province": "NB",
        "country": "Canada",
        "base_type": "cfb",
    },
    "esquimalt": {
        "id": "cfb-esquimalt",
        "name": "CFB Esquimalt",
        "province": "BC",
        "country": "Canada",
        "base_type": "cfb",
    },
    "kingston": {
        "id": "cfb-kingston",
        "name": "CFB Kingston",
        "province": "ON",
        "country": "Canada",
        "base_type": "cfb",
    },
    "trenton": {
        "id": "cfb-trenton",
        "name": "CFB Trenton",
        "province": "ON",
        "country": "Canada",
        "base_type": "cfb",
    },
    "halifax": {
        "id": "cfb-halifax",
        "name": "CFB Halifax",
        "province": "NS",
        "country": "Canada",
        "base_type": "cfb",
    },
    "petawawa": {
        "id": "cfb-petawawa",
        "name": "CFB Petawawa",
        "province": "ON",
        "country": "Canada",
        "base_type": "cfb",
    },
    "edmonton": {
        "id": "cfb-edmonton",
        "name": "CFB Edmonton",
        "province": "AB",
        "country": "Canada",
        "base_type": "cfb",
    },
    "cold lake": {
        "id": "cfb-cold-lake",
        "name": "CFB Cold Lake",
        "province": "AB",
        "country": "Canada",
        "base_type": "cfb",
    },
    "comox": {
        "id": "cfb-comox",
        "name": "CFB Comox",
        "province": "BC",
        "country": "Canada",
        "base_type": "cfb",
    },
    "winnipeg": {
        "id": "cfb-winnipeg",
        "name": "CFB Winnipeg",
        "province": "MB",
        "country": "Canada",
        "base_type": "cfb",
    },
    "moose jaw": {
        "id": "cfb-moose-jaw",
        "name": "CFB Moose Jaw",
        "province": "SK",
        "country": "Canada",
        "base_type": "cfb",
    },
    "shilo": {
        "id": "cfb-shilo",
        "name": "CFB Shilo",
        "province": "MB",
        "country": "Canada",
        "base_type": "cfb",
    },
    "valcartier": {
        "id": "cfb-valcartier",
        "name": "CFB Valcartier",
        "province": "QC",
        "country": "Canada",
        "base_type": "cfb",
    },
    "greenwood": {
        "id": "cfb-greenwood",
        "name": "CFB Greenwood",
        "province": "NS",
        "country": "Canada",
        "base_type": "cfb",
    },
    "suffield": {
        "id": "cfb-suffield",
        "name": "CFB Suffield",
        "province": "AB",
        "country": "Canada",
        "base_type": "cfb",
    },
    "wainwright": {
        "id": "cfb-wainwright",
        "name": "CFB Wainwright",
        "province": "AB",
        "country": "Canada",
        "base_type": "cfb",
    },
}

# Civilian credential level mappings (ordered by specificity - most specific first)
CREDENTIAL_LEVELS = [
    ("trade", ["trade certification", "red seal", "journeyperson"]),
    ("graduate", ["graduate degree", "masters", "phd", "doctorate"]),
    ("professional", ["professional designation", "licensed", "registered"]),
    ("degree", ["degree", "bachelor", "undergraduate", "university degree"]),
    ("diploma", ["diploma", "technician diploma", "technologist diploma"]),
    ("certificate", ["certificate", "certification", "certified"]),
]


def normalize_training_location(location_text: str | None) -> tuple[str | None, dict | None]:
    """Normalize training location using fuzzy matching.

    Uses rapidfuzz to match location text to canonical CAF training bases.
    Returns None if no match above 80% threshold.

    Args:
        location_text: Raw location text from training description.

    Returns:
        Tuple of (training_location_id, location_metadata) or (None, None).
    """
    if not location_text:
        return None, None

    location_lower = location_text.lower().strip()

    # First try exact substring match
    for key, loc_data in CANONICAL_LOCATIONS.items():
        if key in location_lower:
            logger.debug(
                "location_exact_match",
                input=location_text,
                matched=loc_data["name"],
            )
            return loc_data["id"], loc_data

    # Fuzzy fallback using rapidfuzz
    best_match = None
    best_score = 0

    for key, loc_data in CANONICAL_LOCATIONS.items():
        # Try matching against both key and full name
        score_key = fuzz.partial_ratio(location_lower, key)
        score_name = fuzz.partial_ratio(location_lower, loc_data["name"].lower())
        score = max(score_key, score_name)

        if score > best_score:
            best_score = score
            best_match = loc_data

    if best_score >= 80 and best_match:
        logger.debug(
            "location_fuzzy_match",
            input=location_text,
            matched=best_match["name"],
            score=best_score,
        )
        return best_match["id"], best_match

    # Unknown location: log warning
    logger.warning("unknown_training_location", location=location_text)
    return None, None


def parse_duration_to_weeks(text: str | None) -> tuple[float | None, str | None]:
    """Parse duration text to standardized weeks.

    Handles various formats:
    - "10 weeks" -> 10.0
    - "12 weeks" -> 12.0
    - "2.5 months" -> 10.83 (approximate: month = 4.33 weeks)
    - "6 months" -> 26.0
    - "two weeks" -> 2.0
    - "eight to 11 weeks" -> 9.5 (average)

    Args:
        text: Duration text to parse.

    Returns:
        Tuple of (weeks, original_text). Weeks is None if unparseable.
    """
    if not text:
        return None, None

    original_text = text.strip()
    text_lower = text.lower().strip()

    # Word to number mapping
    word_numbers = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
        "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
        "nineteen": 19, "twenty": 20,
    }

    # Replace word numbers with digits
    for word, num in word_numbers.items():
        text_lower = re.sub(rf"\b{word}\b", str(num), text_lower)

    # Pattern: range "X to Y weeks/months"
    range_pattern = r"(\d+(?:\.\d+)?)\s*(?:to|-)\s*(\d+(?:\.\d+)?)\s*(weeks?|months?)"
    range_match = re.search(range_pattern, text_lower)
    if range_match:
        low = float(range_match.group(1))
        high = float(range_match.group(2))
        unit = range_match.group(3)
        avg = (low + high) / 2
        if "month" in unit:
            avg *= 4.33  # Convert months to weeks
        return round(avg, 1), original_text

    # Pattern: single value "X weeks/months"
    single_pattern = r"(\d+(?:\.\d+)?)\s*(weeks?|months?|days?)"
    single_match = re.search(single_pattern, text_lower)
    if single_match:
        value = float(single_match.group(1))
        unit = single_match.group(2)
        if "month" in unit:
            value *= 4.33  # Convert months to weeks
        elif "day" in unit:
            value /= 7  # Convert days to weeks
        return round(value, 1), original_text

    # Pattern: "approximately X weeks"
    approx_pattern = r"(?:approximately|about|approx\.?|~)\s*(\d+(?:\.\d+)?)\s*(weeks?|months?)"
    approx_match = re.search(approx_pattern, text_lower)
    if approx_match:
        value = float(approx_match.group(1))
        unit = approx_match.group(2)
        if "month" in unit:
            value *= 4.33
        return round(value, 1), original_text

    logger.debug("duration_parse_failed", text=text[:100] if text else "")
    return None, original_text


def parse_civilian_credential_level(text: str | None) -> str | None:
    """Parse civilian credential equivalency level.

    Maps training descriptions to standardized credential levels.
    Checks more specific levels first (trade, professional) before generic ones (certificate).

    Args:
        text: Training or civilian equivalency text.

    Returns:
        Standardized credential level or None.
    """
    if not text:
        return None

    text_lower = text.lower()

    # Check each credential level (ordered by specificity)
    for level, keywords in CREDENTIAL_LEVELS:
        for keyword in keywords:
            if keyword in text_lower:
                return level

    return None


def extract_certifications(text: str | None) -> list[str]:
    """Extract certification mentions from training text.

    Args:
        text: Training text to search.

    Returns:
        List of certification names found.
    """
    if not text:
        return []

    certifications = []

    # Common CAF/military certification patterns
    cert_patterns = [
        r"(?:earn|receive|obtain|awarded?)\s+(?:a\s+)?([A-Z][a-zA-Z\s]+(?:certificate|certification|credential|license|qualification))",
        r"(?:certificate|certification)\s+in\s+([A-Z][a-zA-Z\s]+)",
        r"([A-Z][a-zA-Z\s]+(?:certificate|certification))",
        r"(first aid|Standard First Aid|Emergency First Aid)",
        r"(driver'?s?\s+license|Class\s+[A-Z0-9]+\s+license)",
    ]

    for pattern in cert_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            cert_name = match.strip()
            if cert_name and len(cert_name) > 3 and cert_name not in certifications:
                certifications.append(cert_name)

    # Check for CPR separately (short acronym)
    if re.search(r"\bCPR\b", text, re.IGNORECASE):
        if "CPR" not in certifications:
            certifications.append("CPR")

    return certifications[:10]  # Limit to 10


def extract_qualifications(text: str | None) -> list[str]:
    """Extract military qualification mentions from training text.

    Args:
        text: Training text to search.

    Returns:
        List of qualification codes/names found.
    """
    if not text:
        return []

    qualifications = []

    # CAF qualification patterns
    qual_patterns = [
        r"(BMOQ|BMQ|BMOQA|DP1|DP2|DP3|QL3|QL5|QL6[ABC]?)",
        r"Basic\s+(Military|Officer)\s+(?:Qualification|Training)",
        r"Occupational\s+(?:Training|Qualification)",
        r"(Phase\s+[IVX0-9]+\s+Training)",
    ]

    for pattern in qual_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            qual_name = match.strip()
            if qual_name and qual_name not in qualifications:
                qualifications.append(qual_name)

    return qualifications[:10]


def extract_recertification_info(text: str | None) -> tuple[bool, str | None]:
    """Extract recertification requirements from training text.

    Args:
        text: Training text to search.

    Returns:
        Tuple of (recertification_required, frequency_text).
    """
    if not text:
        return False, None

    text_lower = text.lower()

    # Recertification patterns
    recert_patterns = [
        r"(recertif(?:y|ied|ication)\s+(?:every|annually|yearly|biannually|every\s+\d+\s+years?))",
        r"(annual\s+recertification)",
        r"(renew(?:al)?\s+every\s+\d+\s+years?)",
        r"(currency\s+training)",
        r"(periodic\s+requalification)",
    ]

    for pattern in recert_patterns:
        match = re.search(pattern, text_lower)
        if match:
            return True, match.group(1).strip()

    # Also check for keywords without capturing frequency
    if any(kw in text_lower for kw in ["recertif", "requalif", "currency", "periodic training"]):
        return True, None

    return False, None


def parse_training_info(career_data: dict) -> list[CAFTraining]:
    """Parse training information from CAF career data.

    Extracts BMQ and occupation-specific training records from the
    training_en field of a CAF occupation.

    Args:
        career_data: Dict with CAF occupation data including training_en field.

    Returns:
        List of CAFTraining records. May be empty for sparse data.
    """
    training_records = []

    career_id = career_data.get("career_id", "")
    training_text = career_data.get("training_en", "")
    source_url = career_data.get("url_en", "")

    if not training_text:
        logger.debug("no_training_text", career_id=career_id)
        return []

    extracted_at = datetime.now(timezone.utc).isoformat()

    # Split training text into BMQ and occupation-specific sections
    bmq_section = None
    occupation_section = None

    # Common section headers
    bmq_headers = [
        "basic military officer qualification",
        "basic military qualification",
        "basic training",
        "bmoq",
        "bmq",
    ]

    occupation_headers = [
        "available professional training",
        "occupational training",
        "basic occupational qualification",
        "available specialty training",
        "specialist training",
        "occupation-specific training",
        "advanced training",
    ]

    text_lower = training_text.lower()

    # Find BMQ section
    for header in bmq_headers:
        if header in text_lower:
            start_idx = text_lower.find(header)
            # Find the end (next section or end of text)
            end_idx = len(training_text)
            for occ_header in occupation_headers:
                occ_idx = text_lower.find(occ_header, start_idx + len(header))
                if occ_idx > 0:
                    end_idx = min(end_idx, occ_idx)
                    break
            bmq_section = training_text[start_idx:end_idx].strip()
            break

    # Find occupation-specific section
    for header in occupation_headers:
        if header in text_lower:
            start_idx = text_lower.find(header)
            occupation_section = training_text[start_idx:].strip()
            break

    # Parse BMQ training
    if bmq_section:
        bmq_record = _parse_training_section(
            career_id=career_id,
            training_type="bmq",
            section_text=bmq_section,
            source_url=source_url,
            extracted_at=extracted_at,
        )
        if bmq_record:
            training_records.append(bmq_record)

    # Parse occupation-specific training
    if occupation_section:
        occ_record = _parse_training_section(
            career_id=career_id,
            training_type="occupation_specific",
            section_text=occupation_section,
            source_url=source_url,
            extracted_at=extracted_at,
        )
        if occ_record:
            training_records.append(occ_record)

    # If no sections found but training text exists, create a generic record
    if not training_records and training_text:
        generic_record = _parse_training_section(
            career_id=career_id,
            training_type="occupation_specific",
            section_text=training_text,
            source_url=source_url,
            extracted_at=extracted_at,
        )
        if generic_record:
            training_records.append(generic_record)

    logger.debug(
        "training_parsed",
        career_id=career_id,
        record_count=len(training_records),
    )

    return training_records


def _parse_training_section(
    career_id: str,
    training_type: str,
    section_text: str,
    source_url: str,
    extracted_at: str,
) -> Optional[CAFTraining]:
    """Parse a single training section into a CAFTraining record.

    Args:
        career_id: CAF occupation ID.
        training_type: 'bmq' or 'occupation_specific'.
        section_text: Text of the training section.
        source_url: Source URL.
        extracted_at: Extraction timestamp.

    Returns:
        CAFTraining record or None if parsing failed.
    """
    if not section_text or len(section_text) < 20:
        return None

    # Extract location
    location_id, location_meta = _extract_location_from_text(section_text)

    # Extract duration
    duration_weeks, duration_text = _extract_duration_from_text(section_text)

    # Extract certifications and qualifications
    certifications = extract_certifications(section_text)
    qualifications = extract_qualifications(section_text)

    # Extract civilian credential level
    civilian_level = parse_civilian_credential_level(section_text)
    civilian_text = _extract_civilian_equivalency_text(section_text)

    # Extract recertification info
    recert_required, recert_frequency = extract_recertification_info(section_text)

    return CAFTraining(
        caf_occupation_id=career_id,
        training_type=training_type,
        duration_weeks=duration_weeks,
        duration_text=duration_text,
        training_location_id=location_id,
        training_location_text=_extract_raw_location_text(section_text),
        certifications_awarded=certifications,
        qualifications_awarded=qualifications,
        prerequisite_courses=[],  # Not typically in forces.ca pages
        minimum_rank=None,  # Not typically in forces.ca pages
        civilian_credential_level=civilian_level,
        civilian_equivalency_text=civilian_text,
        recertification_required=recert_required,
        recertification_frequency=recert_frequency,
        source_url=source_url,
        extracted_at=extracted_at,
    )


def _extract_location_from_text(text: str) -> tuple[str | None, dict | None]:
    """Extract and normalize location from training text.

    Args:
        text: Training section text.

    Returns:
        Tuple of (location_id, location_metadata).
    """
    # Common location patterns in CAF training text
    location_patterns = [
        r"(?:at|in)\s+(?:the\s+)?([A-Za-z\s\-]+?(?:School|Centre|Center|College|Base))\s+(?:in|at)?\s*([A-Za-z\s\-]+(?:,\s*[A-Za-z\s]+)?)",
        r"(?:at|in)\s+(?:CFB|CFLRS|Canadian Forces)\s+([A-Za-z\s\-]+)",
        r"(?:at|in)\s+([A-Za-z\s\-]+),\s*(?:Ontario|Quebec|Alberta|British Columbia|Nova Scotia|New Brunswick|Manitoba|Saskatchewan)",
        r"(?:conducted|held|takes place)\s+(?:at|in)\s+([A-Za-z\s\-]+)",
    ]

    for pattern in location_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Get the location part (may be in different groups)
            location_text = match.group(1)
            if len(match.groups()) > 1 and match.group(2):
                location_text = f"{match.group(1)} {match.group(2)}"

            location_id, location_meta = normalize_training_location(location_text)
            if location_id:
                return location_id, location_meta

    return None, None


def _extract_raw_location_text(text: str) -> str | None:
    """Extract raw location text mention from training description.

    Args:
        text: Training section text.

    Returns:
        Raw location text or None.
    """
    # Try to find location mentions
    patterns = [
        r"(?:at|in)\s+(?:the\s+)?([^.]+?(?:School|Centre|Center|College|Base)[^.]*)",
        r"(?:at|in)\s+(CFB[^.]+|CFLRS[^.]+|Canadian Forces[^.]+)",
        r"(?:conducted|held)\s+(?:at|in)\s+([^.]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()[:200]  # Limit length

    return None


def _extract_duration_from_text(text: str) -> tuple[float | None, str | None]:
    """Extract duration information from training text.

    Args:
        text: Training section text.

    Returns:
        Tuple of (weeks, duration_text).
    """
    # Duration patterns
    duration_patterns = [
        r"(?:for|takes?|lasts?|approximately|about)\s+(\d+(?:\.\d+)?(?:\s*(?:to|-)\s*\d+(?:\.\d+)?)?)\s*(weeks?|months?|days?)",
        r"(\d+(?:\s*(?:to|-)\s*\d+)?)\s*(?:-)?week",
        r"(\d+(?:\.\d+)?)\s*months?",
        r"training\s+(?:takes?|lasts?)\s+(\d+(?:\.\d+)?(?:\s*(?:to|-)\s*\d+(?:\.\d+)?)?)\s*(weeks?|months?)",
    ]

    for pattern in duration_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            duration_text = match.group(0)
            weeks, _ = parse_duration_to_weeks(duration_text)
            if weeks:
                return weeks, duration_text.strip()

    return None, None


def _extract_civilian_equivalency_text(text: str) -> str | None:
    """Extract civilian equivalency text if present.

    Args:
        text: Training section text.

    Returns:
        Civilian equivalency text or None.
    """
    patterns = [
        r"((?:civilian|equivalent|transferable)[^.]*(?:certification|diploma|degree|credential)[^.]*\.)",
        r"((?:skills|training)\s+(?:are\s+)?transferable[^.]*\.)",
        r"(qualify\s+(?:for|as)\s+[^.]*(?:civilian|commercial)[^.]*\.)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return None


def get_all_canonical_locations() -> list[dict]:
    """Return all canonical training locations for dim_caf_training_location.

    Returns:
        List of location dicts with id, name, province, country, base_type.
    """
    return list(CANONICAL_LOCATIONS.values())
