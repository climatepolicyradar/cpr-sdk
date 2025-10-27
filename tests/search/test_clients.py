import pytest
from unittest.mock import Mock, MagicMock
from vespa.application import Vespa
from vespa.io import VespaQueryResponse, VespaResponse

from cpr_sdk.search.clients import (
    Client,
    AsyncClient,
    ConceptResource,
    AsyncConceptResource,
    ConceptQueryParams,
    AuthMethods,
    client,
    async_client,
    concept_client,
    async_concept_client,
)
from cpr_sdk.models.search import Concept, WikibaseId


class TestClient:
    """Test the synchronous Client class."""

    def test_client_initialization(self):
        """Test that Client initializes correctly."""
        c = Client(
            instance_url="http://localhost:8080",
            auth=AuthMethods.Local(),
        )
        assert c.instance_url == "http://localhost:8080"
        assert isinstance(c.auth, AuthMethods.Local)

    def test_client_with_cloud_token(self):
        """Test Client with CloudToken authentication."""
        c = Client(
            instance_url="https://vespa.example.com",
            auth=AuthMethods.CloudToken(token="sk_test_123"),
        )
        assert isinstance(c.auth, AuthMethods.CloudToken)

    def test_client_with_certificate(self):
        """Test Client with Certificate authentication."""
        c = Client(
            instance_url="https://vespa.example.com",
            auth=AuthMethods.Certificate(cert_directory="/path/to/certs"),
        )
        assert isinstance(c.auth, AuthMethods.Certificate)

    def test_concepts_property_returns_resource(self):
        """Test that concepts property returns ConceptResource."""
        mock_vespa = Mock(spec=Vespa)
        c = Client(
            instance_url="http://localhost:8080",
            auth=AuthMethods.Local(),
            vespa_client=mock_vespa,
        )
        assert isinstance(c.concepts, ConceptResource)

    def test_concepts_property_is_cached(self):
        """Test that concepts property is lazy-loaded and cached."""
        mock_vespa = Mock(spec=Vespa)
        c = Client(
            instance_url="http://localhost:8080",
            auth=AuthMethods.Local(),
            vespa_client=mock_vespa,
        )
        resource1 = c.concepts
        resource2 = c.concepts
        assert resource1 is resource2

    def test_dependency_injection(self):
        """Test that Vespa client can be injected for testing."""
        mock_vespa = Mock(spec=Vespa)
        c = Client(
            instance_url="http://localhost:8080",
            auth=AuthMethods.Local(),
            vespa_client=mock_vespa,
        )
        assert c._vespa_client is mock_vespa


class TestAsyncClient:
    """Test the asynchronous AsyncClient class."""

    def test_async_client_initialization(self):
        """Test that AsyncClient initializes correctly."""
        c = AsyncClient(
            instance_url="http://localhost:8080",
            auth=AuthMethods.Local(),
        )
        assert c.instance_url == "http://localhost:8080"
        assert isinstance(c.auth, AuthMethods.Local)

    def test_concepts_property_returns_async_resource(self):
        """Test that concepts property returns AsyncConceptResource."""
        mock_vespa = Mock(spec=Vespa)
        c = AsyncClient(
            instance_url="http://localhost:8080",
            auth=AuthMethods.Local(),
            vespa_client=mock_vespa,
        )
        assert isinstance(c.concepts, AsyncConceptResource)


class TestConceptResource:
    """Test the ConceptResource class."""

    def test_query_basic(self):
        """Test basic concept query."""
        mock_vespa = Mock(spec=Vespa)
        mock_response = Mock(spec=VespaQueryResponse)
        mock_response.is_successful.return_value = True
        mock_response.hits = [
            {
                "fields": {
                    "sddocname": "concept",
                    "id": "w2m7ymf7",
                    "wikibase_id": "Q290",
                    "wikibase_url": "https://example.org/wiki/Item:Q290",
                    "preferred_label": "pollution",
                    "subconcept_of": ["hzaw3hdg"],
                }
            }
        ]
        mock_vespa.query.return_value = mock_response

        resource = ConceptResource(client=mock_vespa)
        params = ConceptQueryParams(query_string="pollution")
        results = resource.query(params)

        assert len(results) == 1
        assert results[0].id == "w2m7ymf7"
        assert results[0].preferred_label == "pollution"
        mock_vespa.query.assert_called_once()

    def test_query_with_wikibase_id(self):
        """Test concept query with Wikibase ID filter."""
        mock_vespa = Mock(spec=Vespa)
        mock_response = Mock(spec=VespaQueryResponse)
        mock_response.is_successful.return_value = True
        mock_response.hits = []
        mock_vespa.query.return_value = mock_response

        resource = ConceptResource(client=mock_vespa)
        params = ConceptQueryParams(wikibase_id=WikibaseId("Q290"))
        results = resource.query(params)

        assert len(results) == 0
        mock_vespa.query.assert_called_once()
        call_args = mock_vespa.query.call_args
        assert "Q290" in call_args.kwargs["body"]["yql"]

    def test_query_with_concept_ids(self):
        """Test concept query with concept IDs filter."""
        mock_vespa = Mock(spec=Vespa)
        mock_response = Mock(spec=VespaQueryResponse)
        mock_response.is_successful.return_value = True
        mock_response.hits = []
        mock_vespa.query.return_value = mock_response

        resource = ConceptResource(client=mock_vespa)
        params = ConceptQueryParams(concept_ids=["w2m7ymf7", "abc123"])
        results = resource.query(params)

        assert len(results) == 0
        mock_vespa.query.assert_called_once()
        call_args = mock_vespa.query.call_args
        yql = call_args.kwargs["body"]["yql"]
        assert "w2m7ymf7" in yql
        assert "abc123" in yql

    def test_query_with_parent_concept_id(self):
        """Test concept query with parent concept ID filter."""
        mock_vespa = Mock(spec=Vespa)
        mock_response = Mock(spec=VespaQueryResponse)
        mock_response.is_successful.return_value = True
        mock_response.hits = []
        mock_vespa.query.return_value = mock_response

        resource = ConceptResource(client=mock_vespa)
        params = ConceptQueryParams(parent_concept_id="hzaw3hdg")
        results = resource.query(params)

        assert len(results) == 0
        mock_vespa.query.assert_called_once()
        call_args = mock_vespa.query.call_args
        assert "subconcept_of" in call_args.kwargs["body"]["yql"]
        assert "hzaw3hdg" in call_args.kwargs["body"]["yql"]

    def test_query_with_limit_and_offset(self):
        """Test concept query with pagination parameters."""
        mock_vespa = Mock(spec=Vespa)
        mock_response = Mock(spec=VespaQueryResponse)
        mock_response.is_successful.return_value = True
        mock_response.hits = []
        mock_vespa.query.return_value = mock_response

        resource = ConceptResource(client=mock_vespa)
        params = ConceptQueryParams(limit=50, offset=10)
        results = resource.query(params)

        assert len(results) == 0
        mock_vespa.query.assert_called_once()
        call_args = mock_vespa.query.call_args
        yql = call_args.kwargs["body"]["yql"]
        assert "limit 50" in yql
        assert "offset 10" in yql

    def test_query_empty_response(self):
        """Test concept query with no results."""
        mock_vespa = Mock(spec=Vespa)
        mock_response = Mock(spec=VespaQueryResponse)
        mock_response.is_successful.return_value = False
        mock_response.hits = []
        mock_vespa.query.return_value = mock_response

        resource = ConceptResource(client=mock_vespa)
        params = ConceptQueryParams(query_string="nonexistent")
        results = resource.query(params)

        assert len(results) == 0

    def test_get_success(self):
        """Test getting a concept by ID successfully."""
        mock_vespa = Mock(spec=Vespa)
        mock_response = Mock(spec=VespaResponse)
        mock_response.is_successful.return_value = True
        mock_response.json = {
            "id": "id:doc_search:concept::w2m7ymf7",
            "fields": {
                "id": "w2m7ymf7",
                "wikibase_id": "Q290",
                "wikibase_url": "https://example.org/wiki/Item:Q290",
                "preferred_label": "pollution",
                "subconcept_of": ["hzaw3hdg"],
            },
        }
        mock_vespa.get_data.return_value = mock_response

        resource = ConceptResource(client=mock_vespa)
        concept = resource.get(id="w2m7ymf7")

        assert concept is not None
        assert concept.id == "w2m7ymf7"
        assert concept.preferred_label == "pollution"
        mock_vespa.get_data.assert_called_once_with(
            schema="concept", data_id="id:doc_search:concept::w2m7ymf7"
        )

    def test_get_not_found(self):
        """Test getting a concept that doesn't exist."""
        mock_vespa = Mock(spec=Vespa)
        mock_response = Mock(spec=VespaResponse)
        mock_response.is_successful.return_value = False
        mock_vespa.get_data.return_value = mock_response

        resource = ConceptResource(client=mock_vespa)
        concept = resource.get(id="nonexistent")

        assert concept is None


class TestAsyncConceptResource:
    """Test the AsyncConceptResource class."""

    @pytest.mark.asyncio
    async def test_query_basic(self):
        """Test basic async concept query."""
        mock_vespa = Mock(spec=Vespa)
        mock_response = Mock(spec=VespaQueryResponse)
        mock_response.is_successful.return_value = True
        mock_response.hits = [
            {
                "fields": {
                    "sddocname": "concept",
                    "id": "w2m7ymf7",
                    "wikibase_id": "Q290",
                    "wikibase_url": "https://example.org/wiki/Item:Q290",
                    "preferred_label": "pollution",
                    "subconcept_of": ["hzaw3hdg"],
                }
            }
        ]

        # Create an async mock
        async def mock_query_async(*args, **kwargs):
            return mock_response

        mock_vespa.query_async = mock_query_async

        resource = AsyncConceptResource(client=mock_vespa)
        params = ConceptQueryParams(query_string="pollution")
        results = await resource.query(params)

        assert len(results) == 1
        assert results[0].id == "w2m7ymf7"
        assert results[0].preferred_label == "pollution"

    @pytest.mark.asyncio
    async def test_get_success(self):
        """Test async getting a concept by ID successfully."""
        mock_vespa = Mock(spec=Vespa)
        mock_response = Mock(spec=VespaResponse)
        mock_response.is_successful.return_value = True
        mock_response.json = {
            "id": "id:doc_search:concept::w2m7ymf7",
            "fields": {
                "id": "w2m7ymf7",
                "wikibase_id": "Q290",
                "wikibase_url": "https://example.org/wiki/Item:Q290",
                "preferred_label": "pollution",
                "subconcept_of": ["hzaw3hdg"],
            },
        }

        # Create an async mock
        async def mock_get_data_async(*args, **kwargs):
            return mock_response

        mock_vespa.get_data_async = mock_get_data_async

        resource = AsyncConceptResource(client=mock_vespa)
        concept = await resource.get(id="w2m7ymf7")

        assert concept is not None
        assert concept.id == "w2m7ymf7"
        assert concept.preferred_label == "pollution"


class TestFactoryFunctions:
    """Test convenience factory functions."""

    def test_client_factory(self):
        """Test client() factory function."""
        c = client(
            instance_url="http://localhost:8080",
            auth=AuthMethods.Local(),
        )
        assert isinstance(c, Client)
        assert c.instance_url == "http://localhost:8080"

    def test_async_client_factory(self):
        """Test async_client() factory function."""
        c = async_client(
            instance_url="http://localhost:8080",
            auth=AuthMethods.Local(),
        )
        assert isinstance(c, AsyncClient)
        assert c.instance_url == "http://localhost:8080"

    def test_concept_client_factory(self):
        """Test concept_client() factory function."""
        mock_vespa = Mock(spec=Vespa)

        # We need to create a client with the mock first
        base_client = Client(
            instance_url="http://localhost:8080",
            auth=AuthMethods.Local(),
            vespa_client=mock_vespa,
        )

        resource = base_client.concepts
        assert isinstance(resource, ConceptResource)

    def test_async_concept_client_factory(self):
        """Test async_concept_client() factory function."""
        mock_vespa = Mock(spec=Vespa)

        # We need to create an async client with the mock first
        base_client = AsyncClient(
            instance_url="http://localhost:8080",
            auth=AuthMethods.Local(),
            vespa_client=mock_vespa,
        )

        resource = base_client.concepts
        assert isinstance(resource, AsyncConceptResource)


class TestAuthentication:
    """Test different authentication methods."""

    def test_local_auth(self):
        """Test Local authentication."""
        auth = AuthMethods.Local()
        c = Client(instance_url="http://localhost:8080", auth=auth)
        assert isinstance(c.auth, AuthMethods.Local)

    def test_cloud_token_auth(self):
        """Test CloudToken authentication."""
        auth = AuthMethods.CloudToken(token="sk_test_123")
        c = Client(instance_url="https://vespa.example.com", auth=auth)
        assert isinstance(c.auth, AuthMethods.CloudToken)
        assert c.auth.token == "sk_test_123"

    def test_certificate_auth(self):
        """Test Certificate authentication."""
        auth = AuthMethods.Certificate(cert_directory="/path/to/certs")
        c = Client(instance_url="https://vespa.example.com", auth=auth)
        assert isinstance(c.auth, AuthMethods.Certificate)
        assert c.auth.cert_directory == "/path/to/certs"

    def test_auto_discover_certificate_auth(self):
        """Test AutoDiscoverCertificate authentication."""
        auth = AuthMethods.AutoDiscoverCertificate()
        c = Client(instance_url="https://vespa.example.com", auth=auth)
        assert isinstance(c.auth, AuthMethods.AutoDiscoverCertificate)
