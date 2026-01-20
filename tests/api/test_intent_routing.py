"""Intent classification validation tests.

Validates that user queries are classified into correct intent categories
(data, metadata, compliance, lineage) for routing to appropriate API endpoints.
"""

import re
from dataclasses import dataclass

import pytest


@dataclass
class IntentMatch:
    """Result of intent classification."""

    intent: str
    confidence: float
    matched_pattern: str | None = None


class IntentClassifier:
    """Test implementation of intent classification from adapter config.

    Mirrors the patterns defined in orbit/config/adapters/jobforge.yaml
    for validating that queries route correctly.
    """

    def __init__(self):
        """Initialize with patterns from adapter config."""
        # Patterns ordered by specificity (more specific patterns first)
        # Higher confidence = takes precedence
        # More specific patterns get higher confidence than generic ones
        self.patterns = [
            # Metadata patterns (high confidence) - check these first
            (re.compile(r"where does.*come from", re.I), "metadata", 0.95),
            (re.compile(r"lineage", re.I), "metadata", 0.95),
            (re.compile(r"what feeds", re.I), "metadata", 0.95),
            (re.compile(r"upstream", re.I), "metadata", 0.93),
            (re.compile(r"downstream", re.I), "metadata", 0.93),
            (re.compile(r"what columns", re.I), "metadata", 0.92),
            (re.compile(r"describe table", re.I), "metadata", 0.92),
            (re.compile(r"how many tables", re.I), "metadata", 0.91),  # More specific than "how many"
            (re.compile(r"list tables", re.I), "metadata", 0.91),
            (re.compile(r"source of", re.I), "metadata", 0.88),
            # Compliance patterns (high confidence)
            (re.compile(r"dadm compliance", re.I), "compliance", 0.95),
            (re.compile(r"dama complian", re.I), "compliance", 0.95),  # Matches "DAMA compliant" and "DAMA compliance"
            (re.compile(r"governance status", re.I), "compliance", 0.93),
            (re.compile(r"compliance report", re.I), "compliance", 0.93),
            (re.compile(r"classification compliance", re.I), "compliance", 0.93),
            # Data query patterns (lower confidence than specific patterns above)
            (re.compile(r"how many", re.I), "data", 0.90),
            (re.compile(r"count of", re.I), "data", 0.90),
            (re.compile(r"list all", re.I), "data", 0.85),
            (re.compile(r"show me", re.I), "data", 0.80),
            (re.compile(r"what is the", re.I), "data", 0.75),
            (re.compile(r"find", re.I), "data", 0.70),
            (re.compile(r"total", re.I), "data", 0.75),
            (re.compile(r"average", re.I), "data", 0.80),
            (re.compile(r"sum", re.I), "data", 0.75),
            (re.compile(r"group by", re.I), "data", 0.85),
        ]

    def classify(self, query: str) -> IntentMatch:
        """Classify query intent based on pattern matching.

        Args:
            query: Natural language query from user.

        Returns:
            IntentMatch with classified intent and confidence.
        """
        best = IntentMatch(intent="data", confidence=0.5)  # Default to data

        for pattern, intent, confidence in self.patterns:
            if pattern.search(query):
                if confidence > best.confidence:
                    best = IntentMatch(intent, confidence, pattern.pattern)

        return best


# Test data for data intent queries
DATA_QUERIES = [
    ("How many software developers are there?", "data"),
    ("Count of TEER 1 occupations", "data"),
    ("List all NOC unit groups", "data"),
    ("Show me occupations in category 2", "data"),
    ("What is the employment for 21232?", "data"),
    ("Find all occupations with TEER 0", "data"),
    ("Total employment in 2025", "data"),
    ("Average skill rating for developers", "data"),
    ("Group by TEER level", "data"),
]

# Test data for metadata intent queries
METADATA_QUERIES = [
    ("Where does dim_noc come from?", "metadata"),
    ("Show lineage for cops_employment", "metadata"),
    ("What columns are in element_labels?", "metadata"),
    ("Describe table dim_occupations", "metadata"),
    ("How many tables are there?", "metadata"),
    ("What feeds cops_employment?", "metadata"),
    ("Show upstream dependencies", "metadata"),
    ("What is downstream of dim_noc?", "metadata"),
    ("List tables in gold layer", "metadata"),
    ("What is the source of this data?", "metadata"),
]

# Test data for compliance intent queries
COMPLIANCE_QUERIES = [
    ("Show DADM compliance status", "compliance"),
    ("Is WiQ DAMA compliant?", "compliance"),
    ("Generate governance status report", "compliance"),
    ("Show compliance report for DADM", "compliance"),
    ("Classification compliance check", "compliance"),
]

# Test data for lineage queries (subset of metadata)
LINEAGE_QUERIES = [
    "Where does dim_noc come from?",
    "What feeds cops_employment?",
    "Show upstream dependencies of job_architecture",
    "What is the lineage for this table?",
]


class TestDataIntentClassification:
    """Tests for data query intent classification."""

    @pytest.mark.parametrize("query,expected_intent", DATA_QUERIES)
    def test_data_intent_classification(self, query: str, expected_intent: str):
        """Validate data queries are classified correctly."""
        classifier = IntentClassifier()
        result = classifier.classify(query)
        assert result.intent == expected_intent, (
            f"Query '{query}' classified as {result.intent}, expected {expected_intent}"
        )

    def test_data_intent_has_high_confidence(self):
        """Verify data queries get high confidence scores."""
        classifier = IntentClassifier()
        result = classifier.classify("How many rows in dim_noc?")
        assert result.confidence >= 0.7, f"Expected high confidence, got {result.confidence}"


class TestMetadataIntentClassification:
    """Tests for metadata query intent classification."""

    @pytest.mark.parametrize("query,expected_intent", METADATA_QUERIES)
    def test_metadata_intent_classification(self, query: str, expected_intent: str):
        """Validate metadata queries are classified correctly."""
        classifier = IntentClassifier()
        result = classifier.classify(query)
        assert result.intent == expected_intent, (
            f"Query '{query}' classified as {result.intent}, expected {expected_intent}"
        )

    def test_metadata_intent_has_high_confidence(self):
        """Verify metadata queries get high confidence scores."""
        classifier = IntentClassifier()
        result = classifier.classify("Where does dim_noc come from?")
        assert result.confidence >= 0.9, f"Expected high confidence, got {result.confidence}"


class TestComplianceIntentClassification:
    """Tests for compliance query intent classification."""

    @pytest.mark.parametrize("query,expected_intent", COMPLIANCE_QUERIES)
    def test_compliance_intent_classification(self, query: str, expected_intent: str):
        """Validate compliance queries are classified correctly."""
        classifier = IntentClassifier()
        result = classifier.classify(query)
        assert result.intent == expected_intent, (
            f"Query '{query}' classified as {result.intent}, expected {expected_intent}"
        )

    def test_compliance_intent_has_high_confidence(self):
        """Verify compliance queries get high confidence scores."""
        classifier = IntentClassifier()
        result = classifier.classify("Show DADM compliance status")
        assert result.confidence >= 0.9, f"Expected high confidence, got {result.confidence}"


class TestLineageIntentClassification:
    """Tests for lineage queries (routed to metadata)."""

    @pytest.mark.parametrize("query", LINEAGE_QUERIES)
    def test_lineage_classified_as_metadata(self, query: str):
        """Lineage queries should route to metadata endpoint."""
        classifier = IntentClassifier()
        result = classifier.classify(query)
        assert result.intent == "metadata", (
            f"Lineage query '{query}' should route to metadata, got {result.intent}"
        )


class TestAmbiguousQueries:
    """Tests for handling ambiguous or edge case queries."""

    def test_ambiguous_query_defaults_to_data(self):
        """Ambiguous queries should default to data intent."""
        classifier = IntentClassifier()
        result = classifier.classify("Tell me about occupations")
        # Low confidence, defaults to data
        assert result.intent == "data"
        assert result.confidence < 0.7, "Ambiguous query should have low confidence"

    def test_empty_query_defaults_to_data(self):
        """Empty query should default to data with low confidence."""
        classifier = IntentClassifier()
        result = classifier.classify("")
        assert result.intent == "data"
        assert result.confidence == 0.5

    def test_random_text_defaults_to_data(self):
        """Random text with no pattern should default to data."""
        classifier = IntentClassifier()
        result = classifier.classify("xyzzy plugh foobar")
        assert result.intent == "data"
        assert result.confidence == 0.5


class TestPatternPriority:
    """Tests for pattern priority when multiple patterns could match."""

    def test_tables_question_routes_to_metadata(self):
        """'How many tables' should route to metadata, not data."""
        classifier = IntentClassifier()
        result = classifier.classify("How many tables are in the gold layer?")
        # Should match 'how many tables' (metadata) not just 'how many' (data)
        assert result.intent == "metadata"

    def test_more_specific_pattern_wins(self):
        """More specific patterns should take precedence."""
        classifier = IntentClassifier()

        # "how many tables" is more specific than "how many"
        result = classifier.classify("How many tables exist?")
        assert result.intent == "metadata"

        # But plain "how many" without "tables" should be data
        result = classifier.classify("How many occupations are there?")
        assert result.intent == "data"

    def test_compliance_keywords_override_data(self):
        """Compliance-specific keywords should override generic data patterns."""
        classifier = IntentClassifier()
        result = classifier.classify("Show me the DADM compliance status")
        assert result.intent == "compliance"


class TestIntentMatchResult:
    """Tests for IntentMatch dataclass structure."""

    def test_intent_match_has_required_fields(self):
        """IntentMatch should have intent, confidence, and matched_pattern."""
        match = IntentMatch(intent="data", confidence=0.9, matched_pattern="how many")
        assert match.intent == "data"
        assert match.confidence == 0.9
        assert match.matched_pattern == "how many"

    def test_matched_pattern_is_optional(self):
        """IntentMatch matched_pattern defaults to None."""
        match = IntentMatch(intent="data", confidence=0.5)
        assert match.matched_pattern is None

    def test_classifier_sets_matched_pattern(self):
        """Classifier should set matched_pattern when pattern matches."""
        classifier = IntentClassifier()
        result = classifier.classify("How many rows?")
        assert result.matched_pattern is not None
        assert "how many" in result.matched_pattern
