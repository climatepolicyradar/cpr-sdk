"""Base classes and protocols for search resources."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar, runtime_checkable

from vespa.application import Vespa


@dataclass
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

P = TypeVar("P", contravariant=True)  # Params
R = TypeVar("R", covariant=True)  # Result


@runtime_checkable
class Resource(Protocol, Generic[P, R]):
    """Generic synchronous resource protocol that all sync resources must satisfy."""

    _client: Vespa

    def query(self, params: P) -> Sequence[R]:
        """Send a query to Vespa to get 0 or more documents."""
        ...

    def get(self, id: str) -> R | None:
        """Get a single document from Vespa."""
        ...


@runtime_checkable
class AsyncResource(Protocol, Generic[P, R]):
    """Generic asynchronous resource protocol that all async resources must satisfy."""

    _client: Vespa

    async def query(self, params: P) -> Sequence[R]:
        """Send an async query to Vespa to get 0 or more documents."""
        ...

    async def get(self, id: str) -> R | None:
        """Get a single document from Vespa asynchronously."""
        ...
