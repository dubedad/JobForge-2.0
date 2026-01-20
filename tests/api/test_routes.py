"""Tests for FastAPI routes."""

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from jobforge.api.routes import create_api_app
from jobforge.pipeline.config import PipelineConfig


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_api_app(PipelineConfig())
        return TestClient(app)

    def test_health_returns_ok(self, client):
        """Test health endpoint returns ok status."""
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestTablesEndpoint:
    """Tests for tables listing endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_api_app(PipelineConfig())
        return TestClient(app)

    def test_list_tables(self, client):
        """Test tables endpoint lists gold tables."""
        response = client.get("/api/tables")
        assert response.status_code == 200
        data = response.json()
        assert "tables" in data
        assert "count" in data
        assert data["count"] >= 20  # Should have at least 20 gold tables
        assert "dim_noc" in data["tables"]


class TestMetadataQueryEndpoint:
    """Tests for metadata query endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_api_app(PipelineConfig())
        return TestClient(app)

    def test_query_metadata_table_count(self, client):
        """Test metadata query for table count."""
        response = client.post(
            "/api/query/metadata", json={"question": "how many gold tables?"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "question" in data
        assert "answer" in data
        assert "tables" in data["answer"].lower()

    def test_query_metadata_lineage(self, client):
        """Test metadata query for lineage."""
        response = client.post(
            "/api/query/metadata",
            json={"question": "where does dim_noc come from?"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["answer"]) > 0

    def test_query_metadata_missing_question(self, client):
        """Test metadata query with missing question field."""
        response = client.post("/api/query/metadata", json={})
        assert response.status_code == 422  # Validation error


class TestDataQueryEndpoint:
    """Tests for data query endpoint (mocked Claude)."""

    @pytest.fixture
    def mock_anthropic_response(self):
        """Create a mock Anthropic response."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps(
                    {
                        "sql": "SELECT COUNT(*) as cnt FROM dim_noc",
                        "explanation": "Count rows in dim_noc",
                        "tables_used": ["dim_noc"],
                    }
                )
            )
        ]
        return mock_response

    def test_query_data_success(self, mock_anthropic_response):
        """Test data query with mocked Claude."""
        with patch("jobforge.api.data_query.anthropic.Anthropic") as mock_cls:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_anthropic_response
            mock_cls.return_value = mock_client

            app = create_api_app(PipelineConfig())
            client = TestClient(app)

            response = client.post(
                "/api/query/data",
                json={"question": "How many rows in dim_noc?"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["sql"] == "SELECT COUNT(*) as cnt FROM dim_noc"
            assert data["row_count"] > 0

    def test_query_data_error(self):
        """Test data query handles errors."""
        with patch("jobforge.api.data_query.anthropic.Anthropic") as mock_cls:
            mock_client = MagicMock()
            mock_client.messages.create.side_effect = Exception("API Error")
            mock_cls.return_value = mock_client

            app = create_api_app(PipelineConfig())
            client = TestClient(app)

            response = client.post(
                "/api/query/data",
                json={"question": "Bad query"},
            )

            assert response.status_code == 400
            assert "API Error" in response.json()["detail"]


class TestComplianceEndpoint:
    """Tests for compliance endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_api_app(PipelineConfig())
        return TestClient(app)

    def test_compliance_unknown_framework(self, client):
        """Test compliance endpoint with unknown framework."""
        response = client.get("/api/compliance/unknown")
        # Either 404 (unknown) or 501 (module not available)
        assert response.status_code in [404, 501]

    def test_compliance_dadm_success(self, client):
        """Test compliance endpoint returns DADM compliance log."""
        response = client.get("/api/compliance/dadm")
        assert response.status_code == 200
        data = response.json()
        assert "framework_name" in data
        assert "entries" in data
        assert "DADM" in data["framework_name"] or "Directive" in data["framework_name"]

    def test_compliance_dama_success(self, client):
        """Test compliance endpoint returns DAMA compliance log."""
        response = client.get("/api/compliance/dama")
        assert response.status_code == 200
        data = response.json()
        assert "framework_name" in data
        assert "DAMA" in data["framework_name"]

    def test_compliance_classification_success(self, client):
        """Test compliance endpoint returns classification compliance log."""
        response = client.get("/api/compliance/classification")
        assert response.status_code == 200
        data = response.json()
        assert "framework_name" in data
        assert "entries" in data


class TestOpenAPIDocs:
    """Tests for OpenAPI documentation."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_api_app(PipelineConfig())
        return TestClient(app)

    def test_docs_available(self, client):
        """Test OpenAPI docs are available."""
        response = client.get("/docs")
        # Should return HTML
        assert response.status_code == 200
        assert "html" in response.headers.get("content-type", "").lower()

    def test_openapi_json(self, client):
        """Test OpenAPI JSON schema available."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert data["info"]["title"] == "JobForge Query API"
        assert "/api/query/data" in data["paths"]
        assert "/api/query/metadata" in data["paths"]
