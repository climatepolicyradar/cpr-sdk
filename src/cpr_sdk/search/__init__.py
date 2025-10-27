"""CPR SDK search module - clients and resources for searching CPR data."""

from cpr_sdk.search.base import Auth, AuthMethods, AsyncResource, Resource
from cpr_sdk.search.clients import AsyncClient, Client
from cpr_sdk.search.concepts import (
    AsyncConceptResource,
    ConceptQueryParams,
    ConceptResource,
)
from cpr_sdk.search.families import (
    AsyncFamilyResource,
    FamilyQueryParams,
    FamilyResource,
)
from cpr_sdk.search.passages import (
    AsyncPassageResource,
    PassageQueryParams,
    PassageResource,
)

__all__ = [
    # Auth
    "Auth",
    "AuthMethods",
    # Clients
    "Client",
    "AsyncClient",
    # Protocols
    "Resource",
    "AsyncResource",
    # Concepts
    "ConceptResource",
    "AsyncConceptResource",
    "ConceptQueryParams",
    # Passages
    "PassageResource",
    "AsyncPassageResource",
    "PassageQueryParams",
    # Families
    "FamilyResource",
    "AsyncFamilyResource",
    "FamilyQueryParams",
]
