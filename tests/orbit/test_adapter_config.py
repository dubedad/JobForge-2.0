"""Tests for Orbit adapter configuration validity.

Validates that the HTTP adapter and intent configurations are well-formed
and contain all required fields for Orbit integration.
"""

import re
from pathlib import Path

import pytest
import yaml


class TestJobForgeAdapterConfig:
    """Tests for orbit/config/adapters/jobforge.yaml validity."""

    @pytest.fixture
    def adapter_config(self):
        """Load adapter configuration."""
        config_path = Path("orbit/config/adapters/jobforge.yaml")
        assert config_path.exists(), "Adapter config not found at orbit/config/adapters/jobforge.yaml"
        with open(config_path) as f:
            return yaml.safe_load(f)

    def test_adapter_config_file_exists(self):
        """Test adapter config file exists."""
        config_path = Path("orbit/config/adapters/jobforge.yaml")
        assert config_path.exists(), "Adapter config not found"
        assert config_path.stat().st_size > 0, "Adapter config is empty"

    def test_adapter_has_required_fields(self, adapter_config):
        """Test adapter config has all required top-level fields."""
        required = ["name", "description", "enabled", "type", "http"]
        for field in required:
            assert field in adapter_config, f"Missing required field: {field}"

    def test_adapter_name_is_valid(self, adapter_config):
        """Test adapter name is properly formatted."""
        name = adapter_config["name"]
        assert isinstance(name, str)
        assert len(name) > 0
        # Name should be kebab-case or snake_case identifier
        assert re.match(r"^[a-z][a-z0-9_-]*$", name), f"Invalid adapter name format: {name}"

    def test_adapter_is_enabled(self, adapter_config):
        """Test adapter is enabled by default."""
        assert adapter_config["enabled"] is True

    def test_adapter_type_is_http(self, adapter_config):
        """Test adapter type is HTTP."""
        assert adapter_config["type"] == "http"

    def test_http_config_has_base_url(self, adapter_config):
        """Test HTTP config has base_url."""
        http = adapter_config["http"]
        assert "base_url" in http
        assert http["base_url"].startswith("http")

    def test_http_config_has_timeout(self, adapter_config):
        """Test HTTP config has reasonable timeout."""
        http = adapter_config["http"]
        assert "timeout" in http
        assert isinstance(http["timeout"], int)
        assert http["timeout"] > 0
        assert http["timeout"] <= 120  # Max 2 minutes

    def test_http_config_has_endpoints(self, adapter_config):
        """Test HTTP config defines all required endpoints."""
        http = adapter_config["http"]
        assert "endpoints" in http

        required_endpoints = ["data", "metadata", "compliance"]
        for endpoint in required_endpoints:
            assert endpoint in http["endpoints"], f"Missing endpoint: {endpoint}"

    def test_data_endpoint_config(self, adapter_config):
        """Test data endpoint is correctly configured."""
        data = adapter_config["http"]["endpoints"]["data"]
        assert data["path"] == "/api/query/data"
        assert data["method"] == "POST"
        assert "headers" in data
        assert data["headers"]["Content-Type"] == "application/json"
        assert "body" in data
        assert "question" in data["body"]

    def test_metadata_endpoint_config(self, adapter_config):
        """Test metadata endpoint is correctly configured."""
        metadata = adapter_config["http"]["endpoints"]["metadata"]
        assert metadata["path"] == "/api/query/metadata"
        assert metadata["method"] == "POST"
        assert "headers" in metadata
        assert metadata["headers"]["Content-Type"] == "application/json"

    def test_compliance_endpoint_config(self, adapter_config):
        """Test compliance endpoint is correctly configured."""
        compliance = adapter_config["http"]["endpoints"]["compliance"]
        assert compliance["path"].startswith("/api/compliance/")
        assert compliance["method"] == "GET"

    def test_intents_defined(self, adapter_config):
        """Test intent routing rules are defined."""
        assert "intents" in adapter_config
        intents = adapter_config["intents"]
        assert isinstance(intents, list)
        assert len(intents) >= 3, "Expected at least 3 intents"

        # Should have data, metadata, and compliance intents
        intent_names = {i["name"] for i in intents}
        assert "data_query" in intent_names, "Missing data_query intent"
        assert "metadata_query" in intent_names, "Missing metadata_query intent"
        assert "compliance_query" in intent_names, "Missing compliance_query intent"

    def test_intent_has_required_fields(self, adapter_config):
        """Test each intent has required fields."""
        required_fields = ["name", "description", "endpoint", "patterns"]
        for intent in adapter_config["intents"]:
            for field in required_fields:
                assert field in intent, f"Intent {intent.get('name', '?')} missing field: {field}"

    def test_intent_patterns_are_valid(self, adapter_config):
        """Test all intent patterns are valid non-empty strings."""
        for intent in adapter_config["intents"]:
            patterns = intent.get("patterns", [])
            assert len(patterns) > 0, f"Intent {intent['name']} has no patterns"
            for pattern in patterns:
                assert isinstance(pattern, str), f"Pattern {pattern} is not a string"
                assert len(pattern) > 0, f"Intent {intent['name']} has empty pattern"

    def test_intent_endpoints_are_valid(self, adapter_config):
        """Test intent endpoints reference valid HTTP endpoints."""
        valid_endpoints = set(adapter_config["http"]["endpoints"].keys())
        for intent in adapter_config["intents"]:
            assert intent["endpoint"] in valid_endpoints, (
                f"Intent {intent['name']} references invalid endpoint: {intent['endpoint']}"
            )

    def test_llm_config_defined(self, adapter_config):
        """Test LLM configuration is defined for fallback classification."""
        assert "llm" in adapter_config
        llm = adapter_config["llm"]
        assert "provider" in llm
        assert "model" in llm
        assert llm["provider"] in ["anthropic", "openai"]


class TestWiQIntentsConfig:
    """Tests for orbit/config/intents/wiq_intents.yaml validity."""

    @pytest.fixture
    def intents_config(self):
        """Load intents configuration."""
        config_path = Path("orbit/config/intents/wiq_intents.yaml")
        assert config_path.exists(), "Intents config not found"
        with open(config_path) as f:
            return yaml.safe_load(f)

    def test_intents_config_file_exists(self):
        """Test intents config file exists."""
        config_path = Path("orbit/config/intents/wiq_intents.yaml")
        assert config_path.exists(), "Intents config not found"
        assert config_path.stat().st_size > 0, "Intents config is empty"

    def test_intents_has_domain(self, intents_config):
        """Test intents config specifies domain."""
        assert "domain" in intents_config
        assert intents_config["domain"] == "workforce_intelligence"

    def test_intents_has_description(self, intents_config):
        """Test intents config has description."""
        assert "description" in intents_config
        assert len(intents_config["description"]) > 0

    def test_intents_has_version(self, intents_config):
        """Test intents config has version."""
        assert "version" in intents_config

    def test_entities_defined(self, intents_config):
        """Test domain entities are defined."""
        assert "entities" in intents_config
        entities = intents_config["entities"]

        required_entities = ["noc_code", "teer_level", "broad_category"]
        for entity in required_entities:
            assert entity in entities, f"Missing entity: {entity}"

    def test_entity_has_description(self, intents_config):
        """Test each entity has a description."""
        for entity_name, entity in intents_config["entities"].items():
            assert "description" in entity, f"Entity {entity_name} missing description"
            assert len(entity["description"]) > 0

    def test_entity_has_patterns(self, intents_config):
        """Test each entity has patterns for extraction."""
        for entity_name, entity in intents_config["entities"].items():
            assert "patterns" in entity, f"Entity {entity_name} missing patterns"
            assert len(entity["patterns"]) > 0

    def test_entity_patterns_are_valid_regex(self, intents_config):
        """Test entity patterns compile as valid regex."""
        for entity_name, entity in intents_config["entities"].items():
            for pattern in entity.get("patterns", []):
                try:
                    re.compile(pattern)
                except re.error as e:
                    pytest.fail(f"Invalid regex in {entity_name}: {pattern} - {e}")

    def test_entity_has_examples(self, intents_config):
        """Test each entity has examples."""
        for entity_name, entity in intents_config["entities"].items():
            assert "examples" in entity, f"Entity {entity_name} missing examples"
            assert len(entity["examples"]) > 0

    def test_intent_categories_defined(self, intents_config):
        """Test intent categories are defined."""
        assert "intent_categories" in intents_config
        categories = intents_config["intent_categories"]

        required = [
            "occupation_queries",
            "forecast_queries",
            "lineage_queries",
            "compliance_queries",
        ]
        for cat in required:
            assert cat in categories, f"Missing category: {cat}"

    def test_intent_category_has_required_fields(self, intents_config):
        """Test each intent category has required fields."""
        required_fields = ["description", "keywords", "sample_questions"]
        for cat_name, category in intents_config["intent_categories"].items():
            for field in required_fields:
                assert field in category, f"Category {cat_name} missing field: {field}"

    def test_intent_category_keywords_not_empty(self, intents_config):
        """Test intent categories have non-empty keywords."""
        for cat_name, category in intents_config["intent_categories"].items():
            assert len(category["keywords"]) > 0, f"Category {cat_name} has no keywords"

    def test_intent_category_has_sample_questions(self, intents_config):
        """Test intent categories have sample questions."""
        for cat_name, category in intents_config["intent_categories"].items():
            assert len(category["sample_questions"]) > 0, (
                f"Category {cat_name} has no sample questions"
            )

    def test_fallback_strategy_defined(self, intents_config):
        """Test fallback behavior is defined."""
        assert "fallback" in intents_config
        fallback = intents_config["fallback"]
        assert "strategy" in fallback
        assert fallback["strategy"] in ["metadata_first", "data_first", "ask"]

    def test_fallback_has_clarification_prompt(self, intents_config):
        """Test fallback has clarification prompt."""
        fallback = intents_config["fallback"]
        assert "clarification_prompt" in fallback
        assert len(fallback["clarification_prompt"]) > 0


class TestConfigConsistency:
    """Tests for consistency between adapter and intents configs."""

    @pytest.fixture
    def both_configs(self):
        """Load both configuration files."""
        adapter_path = Path("orbit/config/adapters/jobforge.yaml")
        intents_path = Path("orbit/config/intents/wiq_intents.yaml")

        with open(adapter_path) as f:
            adapter = yaml.safe_load(f)
        with open(intents_path) as f:
            intents = yaml.safe_load(f)

        return adapter, intents

    def test_adapter_intents_match_categories(self, both_configs):
        """Test adapter intents align with intent categories."""
        adapter, intents = both_configs

        # Get intent names from adapter
        adapter_intents = {i["name"] for i in adapter["intents"]}

        # Should have intents for main categories
        assert "data_query" in adapter_intents
        assert "metadata_query" in adapter_intents
        assert "compliance_query" in adapter_intents

    def test_llm_model_is_consistent(self, both_configs):
        """Test LLM model specification is valid."""
        adapter, _ = both_configs
        llm = adapter["llm"]

        # Should specify a valid Claude model
        if llm["provider"] == "anthropic":
            assert "claude" in llm["model"].lower() or "opus" in llm["model"].lower()
