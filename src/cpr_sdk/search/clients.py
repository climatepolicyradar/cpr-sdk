"""Adaptors for searching CPR data"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import Enum
import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Generic, TypeVar, Union

from pydantic import BaseModel
from typing_extensions import override

from requests.exceptions import HTTPError
from vespa.application import Vespa
from vespa.exceptions import VespaError

from cpr_sdk.exceptions import DocumentNotFoundError, FetchError, QueryError
import cpr_sdk.search.models as models
from cpr_sdk.vespa import (
    VespaErrorDetails,
    build_vespa_request_body,
    find_vespa_cert_paths,
    parse_vespa_response,
    split_document_id,
)


class Client(ABC):
    _client: Vespa

    def __init__(self, _client: Vespa):
        self._client = _client

    @abstractmethod
    def query(self, params: Any) -> Sequence[Any]:
        """Search with type-specific parameters"""
        ...

    @abstractmethod
    def get(self, id: Any) -> Any:
        """Get by type-specific ID"""
        ...


class Concept(Client):
    @override
    def query(self, params: models.Concept) -> Sequence[models.Concept]:
        return NotImplemented

    @override
    def get(self, id: str) -> models.Concept:
        return NotImplemented


class AuthnMethods:
    @dataclass
    class CloudToken:
        """Authentication using Vespa Cloud secret token"""

        token: str

    @dataclass
    class Certificate:
        """Authentication using certificates"""

        cert_directory: str | None = None  # None means auto-discover certs

    @dataclass
    class Local:
        """No authentication (for local/development instances)"""

        pass


# This is the ADT - a union of the possible authentication methods
Authn = AuthnMethods.CloudToken | AuthnMethods.Certificate | AuthnMethods.Local


class Session(BaseModel):
    """Session manages connection configuration and creates clients."""

    instance_url: str
    authn: Authn
    _client: Vespa | None = None

    def _create_vespa_client(self) -> Vespa:
        """Create Vespa client based on authentication method."""
        match self.authn:
            case AuthnMethods.CloudToken(token):
                return Vespa(url=self.instance_url, vespa_cloud_secret_token=token)
            case AuthnMethods.Certificate(cert_directory):
                if cert_directory is None:
                    cert_path, key_path = find_vespa_cert_paths()
                else:
                    cert_path = (Path(cert_directory) / "cert.pem").__str__()
                    key_path = (Path(cert_directory) / "key.pem").__str__()
                return Vespa(url=self.instance_url, cert=cert_path, key=key_path)
            case AuthnMethods.Local():
                return Vespa(url=self.instance_url)

    def client(self, service: str) -> Client:
        if self._client is None:
            self._client = self._create_vespa_client()

        if service == "concept":
            return Concept(_client=self._client)
        else:
            raise ValueError(f"unknown service: {service}")


def session(
    instance_url: str,
    authn: Authn,
) -> Session:
    """Create a session with the specified authentication method."""
    return Session(
        instance_url=instance_url,
        authn=authn,
    )


def client(
    service: str,
    instance_url: str,
    authn: Authn,
) -> Client:
    """Create a client with the specified authentication method."""
    return Session(
        instance_url=instance_url,
        authn=authn,
    ).client(service)
