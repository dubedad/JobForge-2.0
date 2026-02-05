"""Enhanced qualification text parser for TBS Qualification Standards.

This module extracts CONTEXT.md structured fields from qualification text:
- Education level (standardized enum + original text)
- Experience years (numeric + original text)
- Essential vs Asset qualifications
- Bilingual requirements (reading, writing, oral levels)
- Security clearance levels
- Conditions of employment (travel, shift work, physical demands)
- Operational requirements (overtime, on-call, deployments)
- Equivalency statements

The parser uses permissive regex patterns with fallbacks (per RESEARCH.md Pitfall 1)
and always preserves original text alongside parsed values.
"""

import re
from typing import Optional

from pydantic import BaseModel, Field
import structlog

logger = structlog.get_logger(__name__)

# Maximum character limits
MAX_FIELD_LENGTH = 10000
MAX_FULL_TEXT_LENGTH = 50000


class EnhancedQualification(BaseModel):
    """Pydantic model for enhanced qualification data with CONTEXT.md fields.

    Contains structured fields extracted from TBS qualification text plus
    original text preserved for full-text search and audit.
    """

    # Education: structured + original
    education_level: Optional[str] = Field(
        default=None,
        description="Standardized education level: high_school, certificate, diploma, bachelors, masters, phd, professional_degree",
    )
    education_requirement_text: str = Field(
        default="",
        description="Original education requirement text extracted from source",
    )

    # Experience: numeric + original
    min_years_experience: Optional[int] = Field(
        default=None,
        description="Minimum years of experience required (numeric for filtering)",
    )
    experience_requirement_text: str = Field(
        default="",
        description="Original experience requirement text extracted from source",
    )

    # Essential vs Asset qualifications (CONTEXT.md requirement)
    essential_qualification_text: Optional[str] = Field(
        default=None,
        description="Essential/mandatory qualification requirements",
    )
    asset_qualification_text: Optional[str] = Field(
        default=None,
        description="Asset/preferred qualification requirements",
    )

    # Equivalency
    has_equivalency: bool = Field(
        default=False,
        description="Whether equivalency clause exists",
    )
    equivalency_statement: Optional[str] = Field(
        default=None,
        description="Full text of equivalency statement if present",
    )

    # Bilingual requirements: structured levels
    bilingual_reading_level: Optional[str] = Field(
        default=None,
        description="Official language reading proficiency level (A, B, C, P, E, X)",
    )
    bilingual_writing_level: Optional[str] = Field(
        default=None,
        description="Official language writing proficiency level (A, B, C, P, E, X)",
    )
    bilingual_oral_level: Optional[str] = Field(
        default=None,
        description="Official language oral proficiency level (A, B, C, P, E, X)",
    )

    # Security clearance: structured enum
    security_clearance: Optional[str] = Field(
        default=None,
        description="Required security clearance level: Reliability, Secret, Top Secret",
    )

    # Conditions of employment (CONTEXT.md)
    requires_travel: bool = Field(
        default=False,
        description="Position requires travel",
    )
    shift_work: bool = Field(
        default=False,
        description="Position requires shift work",
    )
    physical_demands: bool = Field(
        default=False,
        description="Position has physical demands",
    )

    # Operational requirements (CONTEXT.md)
    overtime_required: bool = Field(
        default=False,
        description="Position may require overtime",
    )
    on_call_required: bool = Field(
        default=False,
        description="Position requires on-call availability",
    )
    deployments_required: bool = Field(
        default=False,
        description="Position may require deployments",
    )

    # Certification (preserve existing)
    certification_requirement: Optional[str] = Field(
        default=None,
        description="Professional/occupational certification requirements",
    )

    # Full text for search
    full_text: str = Field(
        default="",
        description="Complete qualification standard text for full-text search",
    )


def _detect_education_level(text_to_check: str) -> Optional[str]:
    """Detect education level from text content.

    Args:
        text_to_check: Text to scan for education level keywords.

    Returns:
        Standardized education level or None.
    """
    text_lower = text_to_check.lower()

    # Check from highest to lowest specificity
    if any(term in text_lower for term in ["phd", "ph.d", "doctorate", "doctoral"]):
        return "phd"
    if any(
        term in text_lower
        for term in ["master's", "masters", "master degree", "graduate degree"]
    ):
        return "masters"
    if any(
        term in text_lower
        for term in [
            "professional engineer",
            "professional certification",
            "professional licence",
            "professional license",
            "bar admission",
            "law degree",
            "medical degree",
        ]
    ):
        return "professional_degree"
    if any(
        term in text_lower
        for term in [
            "bachelor",
            "degree from a recognized",
            "graduation with a degree",
            "university degree",
            "baccalaureate",
        ]
    ):
        return "bachelors"
    if any(
        term in text_lower
        for term in [
            "diploma from a recognized",
            "college diploma",
            "post-secondary diploma",
            "two-year diploma",
        ]
    ):
        return "diploma"
    if any(
        term in text_lower
        for term in [
            "certificate",
            "certification program",
            "training program",
        ]
    ):
        return "certificate"
    if any(
        term in text_lower
        for term in [
            "secondary school",
            "high school",
            "grade 12",
            "grade twelve",
        ]
    ):
        return "high_school"

    return None


def extract_education_level(text: str) -> tuple[Optional[str], str]:
    """Extract standardized education level from qualification text.

    Args:
        text: Full qualification text.

    Returns:
        Tuple of (standardized_level, original_text).
        standardized_level is one of:
        'high_school', 'certificate', 'diploma', 'bachelors', 'masters', 'phd', 'professional_degree'
        or None if not detected.
    """
    original_text = ""

    # Patterns for education sections
    education_patterns = [
        r"(?:The minimum standard(?:s)?[:\s]+(?:is|are)[:\s]*)(.+?)(?=The minimum standard|Experience|Certification|Occupational Certification|Professional Certification|Language|Security|Note[:\s]|$)",
        r"(?:Education|EDUCATION)[:\s]+(.+?)(?=Experience|EXPERIENCE|Certification|Language|Security|$)",
        r"(?:The minimum standard for positions)[:\s]*(.+?)(?=The minimum standard|Experience|Certification|$)",
    ]

    for pattern in education_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            extracted = match.group(1).strip()
            if len(extracted) > 30:  # Meaningful content
                original_text = extracted[:MAX_FIELD_LENGTH]
                break

    # Determine standardized level from extracted section first
    level = None
    if original_text:
        level = _detect_education_level(original_text)

    # If no level found in section, fall back to full text search
    # This handles cases where section extraction missed the education content
    if level is None:
        level = _detect_education_level(text)

    return (level, original_text)


def extract_experience_years(text: str) -> tuple[Optional[int], str]:
    """Extract minimum years of experience from qualification text.

    Args:
        text: Full qualification text.

    Returns:
        Tuple of (min_years, original_text).
        min_years is an integer or None if not detected.
    """
    original_text = ""

    # Patterns for experience sections
    experience_patterns = [
        r"(?:Experience|EXPERIENCE)[:\s]+(.+?)(?=Education|Certification|Language|Security|The minimum|$)",
        r"(?:experience\s+(?:is|are)\s+(?:required|needed|necessary))[:\s]*(.+?)(?=Certification|Language|Security|$)",
    ]

    for pattern in experience_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            extracted = match.group(1).strip()
            if len(extracted) > 20:
                original_text = extracted[:MAX_FIELD_LENGTH]
                break

    # Extract years number
    years = None
    search_text = original_text if original_text else text

    # Patterns for years extraction
    year_patterns = [
        r"(?:minimum of|at least|a minimum of)\s*(\d+)\s*(?:year|yr)",
        r"(\d+)\+?\s*(?:year|yr)s?\s*(?:of|'s|in|relevant|experience)",
        r"(\d+)\s*(?:to|-)\s*\d+\s*(?:year|yr)s?",  # Range like "2-3 years" - take lower
        r"(?:one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:year|yr)",
    ]

    for pattern in year_patterns:
        match = re.search(pattern, search_text, re.IGNORECASE)
        if match:
            captured = match.group(1) if match.lastindex and match.lastindex >= 1 else None
            if captured and captured.isdigit():
                years = int(captured)
                break

    # Handle word numbers
    if years is None:
        word_to_num = {
            "one": 1,
            "two": 2,
            "three": 3,
            "four": 4,
            "five": 5,
            "six": 6,
            "seven": 7,
            "eight": 8,
            "nine": 9,
            "ten": 10,
        }
        for word, num in word_to_num.items():
            if re.search(rf"{word}\s+(?:year|yr)", search_text, re.IGNORECASE):
                years = num
                break

    return (years, original_text)


def extract_bilingual_levels(text: str) -> dict[str, Optional[str]]:
    """Extract bilingual proficiency levels from qualification text.

    Args:
        text: Full qualification text.

    Returns:
        Dict with keys: reading, writing, oral.
        Values are proficiency levels (A, B, C, P, E, X) or None.
    """
    result = {"reading": None, "writing": None, "oral": None}

    # Common TBS language profile patterns
    # Format: BBB means B-B-B (reading-writing-oral)
    # Format: CBC means C-B-C
    # Can also appear as: "CBC/CBC" or "bilingual BBB"

    # Pattern for 3-letter profile like BBB, CBC, CCC, etc.
    profile_pattern = r"\b([ABCPEX])([ABCPEX])([ABCPEX])\b"
    match = re.search(profile_pattern, text)
    if match:
        result["reading"] = match.group(1)
        result["writing"] = match.group(2)
        result["oral"] = match.group(3)
        return result

    # Pattern for explicit format: "reading B, writing B, oral C"
    explicit_patterns = [
        (r"reading[:\s]+([ABCPEX])", "reading"),
        (r"writing[:\s]+([ABCPEX])", "writing"),
        (r"oral[:\s]+([ABCPEX])", "oral"),
        (r"comprehension[:\s]+([ABCPEX])", "reading"),
        (r"written expression[:\s]+([ABCPEX])", "writing"),
        (r"oral interaction[:\s]+([ABCPEX])", "oral"),
    ]

    for pattern, key in explicit_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result[key] = match.group(1).upper()

    return result


def extract_security_clearance(text: str) -> Optional[str]:
    """Extract security clearance level from qualification text.

    Args:
        text: Full qualification text.

    Returns:
        Security clearance level: 'Reliability', 'Secret', 'Top Secret', or None.
    """
    text_lower = text.lower()

    # Check from highest to lowest
    if any(
        term in text_lower
        for term in ["top secret", "level iii", "level 3", "ts clearance"]
    ):
        return "Top Secret"
    if any(
        term in text_lower
        for term in [
            "secret clearance",
            "secret security",
            "level ii",
            "level 2",
            "security level secret",
        ]
    ):
        return "Secret"
    if any(
        term in text_lower
        for term in [
            "reliability",
            "reliability status",
            "reliability clearance",
            "enhanced reliability",
            "level i",
            "level 1",
        ]
    ):
        return "Reliability"

    return None


def extract_equivalency(text: str) -> tuple[bool, Optional[str]]:
    """Extract equivalency information from qualification text.

    Args:
        text: Full qualification text.

    Returns:
        Tuple of (has_equivalency, statement).
    """
    equivalency_patterns = [
        r"((?:equivalent|equivalency|equivalences|acceptable combination)[^.]*\.[^.]*\.?)",
        r"((?:deemed to meet|accepted as having met)[^.]*\.)",
        r"((?:may be considered|will be accepted)[^.]*equivalent[^.]*\.)",
    ]

    for pattern in equivalency_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            statement = match.group(1).strip()[:MAX_FIELD_LENGTH]
            return (True, statement)

    return (False, None)


def extract_certification(text: str) -> Optional[str]:
    """Extract certification requirements from qualification text.

    Args:
        text: Full qualification text.

    Returns:
        Certification requirement text or None.
    """
    certification_patterns = [
        r"(?:Occupational Certification|Professional Certification|Certification)[:\s]+(.+?)(?=Education|Experience|Language|Security|The minimum|$)",
        r"(?:Eligibility for|Possession of)\s+([^.]+(?:certification|licence|license|membership)[^.]+\.?)",
        r"(?:certification|licence|Licence)\s+(?:is|are)\s+(?:required|needed)[:\s]*(.+?)(?=Education|Experience|Language|Security|$)",
        # Pattern for standalone licence possession statements
        r"(Possession of (?:a valid|an? )?\w+[^.]*(?:Licence|License|Certificate)[^.]*\.?)",
    ]

    for pattern in certification_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            extracted = match.group(1).strip()
            if len(extracted) > 15:  # Lower threshold for licence statements
                return extracted[:MAX_FIELD_LENGTH]

    return None


def extract_conditions_of_employment(text: str) -> dict[str, bool]:
    """Extract conditions of employment flags from qualification text.

    Args:
        text: Full qualification text.

    Returns:
        Dict with keys: requires_travel, shift_work, physical_demands.
    """
    text_lower = text.lower()

    return {
        "requires_travel": any(
            term in text_lower
            for term in [
                "travel required",
                "travel is required",
                "willingness to travel",
                "must be willing to travel",
                "frequent travel",
            ]
        ),
        "shift_work": any(
            term in text_lower
            for term in [
                "shift work",
                "rotating shifts",
                "night shift",
                "evening shift",
                "work shifts",
            ]
        ),
        "physical_demands": any(
            term in text_lower
            for term in [
                "physical demands",
                "physically demanding",
                "physical requirements",
                "ability to lift",
                "physical fitness",
            ]
        ),
    }


def extract_operational_requirements(text: str) -> dict[str, bool]:
    """Extract operational requirement flags from qualification text.

    Args:
        text: Full qualification text.

    Returns:
        Dict with keys: overtime_required, on_call_required, deployments_required.
    """
    text_lower = text.lower()

    return {
        "overtime_required": any(
            term in text_lower
            for term in [
                "overtime",
                "work overtime",
                "overtime work",
                "extended hours",
            ]
        ),
        "on_call_required": any(
            term in text_lower
            for term in [
                "on-call",
                "on call",
                "standby",
                "stand-by",
                "callback",
            ]
        ),
        "deployments_required": any(
            term in text_lower
            for term in [
                "deployment",
                "deployments",
                "deployed",
                "secondment",
            ]
        ),
    }


def extract_essential_asset_qualifications(
    text: str,
) -> tuple[Optional[str], Optional[str]]:
    """Extract essential and asset qualification sections.

    Args:
        text: Full qualification text.

    Returns:
        Tuple of (essential_text, asset_text).
    """
    essential_text = None
    asset_text = None

    # Essential qualifications patterns
    essential_patterns = [
        r"(?:essential\s+qualifications?|essential\s+requirements?|must\s+have)[:\s]+(.+?)(?=asset|preferred|desirable|nice to have|$)",
        r"(?:minimum\s+qualifications?|mandatory\s+requirements?)[:\s]+(.+?)(?=asset|preferred|desirable|$)",
    ]

    for pattern in essential_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            extracted = match.group(1).strip()
            if len(extracted) > 30:
                essential_text = extracted[:MAX_FIELD_LENGTH]
                break

    # Asset qualifications patterns
    asset_patterns = [
        r"(?:asset\s+qualifications?|assets?)[:\s]+(.+?)(?=essential|mandatory|conditions|operational|$)",
        r"(?:preferred\s+qualifications?|desirable|nice\s+to\s+have)[:\s]+(.+?)(?=essential|mandatory|conditions|$)",
    ]

    for pattern in asset_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            extracted = match.group(1).strip()
            if len(extracted) > 30:
                asset_text = extracted[:MAX_FIELD_LENGTH]
                break

    return (essential_text, asset_text)


def parse_enhanced_qualification(full_text: str) -> EnhancedQualification:
    """Parse TBS qualification text into structured EnhancedQualification model.

    This is the main entry point for qualification text parsing. It extracts
    all CONTEXT.md structured fields while preserving original text.

    Args:
        full_text: Complete qualification standard text.

    Returns:
        EnhancedQualification model with all extracted fields.
    """
    # Truncate if needed
    truncated_text = full_text[:MAX_FULL_TEXT_LENGTH]

    # Extract structured fields
    education_level, education_text = extract_education_level(truncated_text)
    min_years, experience_text = extract_experience_years(truncated_text)
    bilingual = extract_bilingual_levels(truncated_text)
    security = extract_security_clearance(truncated_text)
    has_equiv, equiv_statement = extract_equivalency(truncated_text)
    certification = extract_certification(truncated_text)
    conditions = extract_conditions_of_employment(truncated_text)
    operations = extract_operational_requirements(truncated_text)
    essential, asset = extract_essential_asset_qualifications(truncated_text)

    result = EnhancedQualification(
        education_level=education_level,
        education_requirement_text=education_text,
        min_years_experience=min_years,
        experience_requirement_text=experience_text,
        essential_qualification_text=essential,
        asset_qualification_text=asset,
        has_equivalency=has_equiv,
        equivalency_statement=equiv_statement,
        bilingual_reading_level=bilingual["reading"],
        bilingual_writing_level=bilingual["writing"],
        bilingual_oral_level=bilingual["oral"],
        security_clearance=security,
        requires_travel=conditions["requires_travel"],
        shift_work=conditions["shift_work"],
        physical_demands=conditions["physical_demands"],
        overtime_required=operations["overtime_required"],
        on_call_required=operations["on_call_required"],
        deployments_required=operations["deployments_required"],
        certification_requirement=certification,
        full_text=truncated_text,
    )

    # Log extraction summary
    extracted_fields = []
    if education_level:
        extracted_fields.append("education_level")
    if min_years is not None:
        extracted_fields.append("min_years_experience")
    if bilingual["reading"] or bilingual["writing"] or bilingual["oral"]:
        extracted_fields.append("bilingual_levels")
    if security:
        extracted_fields.append("security_clearance")
    if has_equiv:
        extracted_fields.append("equivalency")
    if certification:
        extracted_fields.append("certification")
    if essential:
        extracted_fields.append("essential_qualification")
    if asset:
        extracted_fields.append("asset_qualification")

    if extracted_fields:
        logger.debug(
            "qualification_parsed",
            extracted_fields=extracted_fields,
            text_length=len(truncated_text),
        )
    else:
        logger.debug(
            "no_structured_fields_extracted",
            text_length=len(truncated_text),
        )

    return result
