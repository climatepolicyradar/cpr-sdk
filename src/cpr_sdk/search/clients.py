"""Main client classes for CPR SDK."""

from pathlib import Path

from vespa.application import Vespa

from cpr_sdk.search.base import Auth, AuthMethods
from cpr_sdk.search.concepts import AsyncConceptResource, ConceptResource
from cpr_sdk.search.families import AsyncFamilyResource, FamilyResource
from cpr_sdk.search.passages import AsyncPassageResource, PassageResource
from cpr_sdk.vespa import find_vespa_cert_paths


class BaseClient:
    """Base client with shared implementation for sync and async clients."""

    def __init__(
        self,
        instance_url: str,
        auth: Auth,
        vespa_client: Vespa | None = None,
    ):
        """
        Initialize a base CPR SDK client.

        Args:
            instance_url: The Vespa instance URL.
            auth: Authentication method (CloudToken, Certificate, AutoDiscoverCertificate, or Local).
            vespa_client: Optional Vespa client for dependency injection (useful for testing).
        """
        self.instance_url = instance_url
        self.auth = auth
        self._vespa_client = vespa_client

    def _get_vespa_client(self) -> Vespa:
        """Get or create the Vespa client."""
        if self._vespa_client is None:
            self._vespa_client = self._create_vespa_client()
        return self._vespa_client

    def _create_vespa_client(self) -> Vespa:
        """Create Vespa client based on authentication method."""
        match self.auth:
            case AuthMethods.CloudToken(token):
                return Vespa(url=self.instance_url, vespa_cloud_secret_token=token)
            case AuthMethods.Certificate(cert_directory):
                cert_path = (Path(cert_directory) / "cert.pem").__str__()
                key_path = (Path(cert_directory) / "key.pem").__str__()

                return Vespa(url=self.instance_url, cert=cert_path, key=key_path)
            case AuthMethods.AutoDiscoverCertificate():
                cert_path, key_path = find_vespa_cert_paths()

                return Vespa(url=self.instance_url, cert=cert_path, key=key_path)
            case AuthMethods.Local():
                return Vespa(url=self.instance_url)


class Client(BaseClient):
    """Synchronous CPR SDK client."""

    def __init__(
        self,
        instance_url: str,
        auth: Auth,
        vespa_client: Vespa | None = None,
    ):
        """
        Initialize a CPR SDK client.

        Args:
            instance_url: The Vespa instance URL.
            auth: Authentication method (CloudToken, Certificate, AutoDiscoverCertificate, or Local).
            vespa_client: Optional Vespa client for dependency injection (useful for testing).
        """
        super().__init__(instance_url, auth, vespa_client)
        self._concepts_resource: ConceptResource | None = None
        self._passages_resource: PassageResource | None = None
        self._families_resource: FamilyResource | None = None

    @property
    def concepts(self) -> ConceptResource:
        """Access concept operations."""
        if self._concepts_resource is None:
            self._concepts_resource = ConceptResource(self._get_vespa_client())
        return self._concepts_resource

    @property
    def passages(self) -> PassageResource:
        """Access passage operations."""
        if self._passages_resource is None:
            self._passages_resource = PassageResource(self._get_vespa_client())
        return self._passages_resource

    @property
    def families(self) -> FamilyResource:
        """Access family (document) operations."""
        if self._families_resource is None:
            self._families_resource = FamilyResource(self._get_vespa_client())
        return self._families_resource


class AsyncClient(BaseClient):
    """Asynchronous CPR SDK client."""

    def __init__(
        self,
        instance_url: str,
        auth: Auth,
        vespa_client: Vespa | None = None,
    ):
        """
        Initialize an async CPR SDK client.

        Args:
            instance_url: The Vespa instance URL.
            auth: Authentication method (CloudToken, Certificate, AutoDiscoverCertificate, or Local).
            vespa_client: Optional Vespa client for dependency injection (useful for testing).
        """
        super().__init__(instance_url, auth, vespa_client)
        self._concepts_resource: AsyncConceptResource | None = None
        self._passages_resource: AsyncPassageResource | None = None
        self._families_resource: AsyncFamilyResource | None = None

    @property
    def concepts(self) -> AsyncConceptResource:
        """Access async concept operations."""
        if self._concepts_resource is None:
            self._concepts_resource = AsyncConceptResource(self._get_vespa_client())
        return self._concepts_resource

    @property
    def passages(self) -> AsyncPassageResource:
        """Access async passage operations."""
        if self._passages_resource is None:
            self._passages_resource = AsyncPassageResource(self._get_vespa_client())
        return self._passages_resource

    @property
    def families(self) -> AsyncFamilyResource:
        """Access async family (document) operations."""
        if self._families_resource is None:
            self._families_resource = AsyncFamilyResource(self._get_vespa_client())
        return self._families_resource
