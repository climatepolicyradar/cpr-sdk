"""Adaptors for searching CPR data"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generic, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel
from vespa.application import Vespa

import cpr_sdk.models.search as models
from cpr_sdk.vespa import find_vespa_cert_paths


P = TypeVar("P", contravariant=True)  # Params
R = TypeVar("R", covariant=True)  # Result


@runtime_checkable
class Client(Protocol, Generic[P, R]):
    """Generic client protocol that all clients must satisfy for a service."""

    _client: Vespa

    def query(self, params: P) -> Sequence[R]:
        """Send a query to Vespa to get 0 or more documents."""
        ...

    def get(self, id: str) -> R:
        """Get a single document from Vespa."""
        ...


class Concept:
    """Concept client implementation."""

    def __init__(self, _client: Vespa):
        self._client = _client

    def query(self, params: Any) -> Sequence[models.Concept]:
        """Send a query to Vespa to get 0 or more concepts."""
        return NotImplemented

    def get(self, id: str) -> models.Concept:
        """Get a single concept from Vespa."""
        return NotImplemented


class AuthMethods:
    """Possible authentication methods for Vespa."""

    @dataclass
    class CloudToken:
        """Authentication using Vespa Cloud secret token."""

        token: str

    @dataclass
    class Certificate:
        """Authentication using certificates."""

        cert_directory: str

    @dataclass
    class AutoDiscoverCertificate:
        """Authentication using auto discovered certificates."""

    @dataclass
    class Local:
        """No authentication (for local/development instances)."""


Auth = (
    AuthMethods.CloudToken
    | AuthMethods.Certificate
    | AuthMethods.AutoDiscoverCertificate
    | AuthMethods.Local
)


class Session(BaseModel):
    """Session manages connection configuration and creates clients."""

    instance_url: str
    auth: Auth
    _client: Vespa | None = None

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

    def client(self, service: str) -> Concept:
        """Create a client instance."""
        if self._client is None:
            self._client = self._create_vespa_client()

        if service == "concept":
            return Concept(_client=self._client)
        else:
            raise ValueError(f"unknown service: {service}")


def session(
    instance_url: str,
    auth: Auth,
) -> Session:
    """Create a session with the specified authentication method."""
    return Session(
        instance_url=instance_url,
        auth=auth,
    )


def client(
    service: str,
    instance_url: str,
    auth: Auth,
) -> Concept:
    """Create a client for the service with the specified authentication method."""
    return Session(
        instance_url=instance_url,
        auth=auth,
    ).client(service)


def concept(
    instance_url: str,
    auth: Auth,
) -> Concept:
    return client(
        service="concept",
        instance_url=instance_url,
        auth=auth,
    )
