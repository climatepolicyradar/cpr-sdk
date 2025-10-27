"""Concept search resources."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from vespa.application import Vespa
from vespa.io import VespaQueryResponse, VespaResponse

import cpr_sdk.models.search as models


@dataclass
class ConceptQueryParams:
    """Parameters for concept queries."""

    query_string: str | None = None
    """Search term for concept labels (preferred, alternative, negative)."""

    wikibase_id: models.WikibaseId | None = None
    """Filter by specific Wikibase ID."""

    concept_ids: Sequence[str] | None = None
    """Filter by specific concept IDs."""

    parent_concept_id: str | None = None
    """Filter concepts by parent concept ID."""

    limit: int = 100
    """Maximum number of results to return."""

    offset: int = 0
    """Number of results to skip (for pagination)."""

    def build_yql(self) -> str:
        """Build Vespa YQL query from parameters."""
        yql_parts = ["select * from concept where"]
        conditions = []

        if self.query_string:
            conditions.append(
                f'(userQuery() or default contains "{self.query_string}")'
            )

        if self.wikibase_id:
            conditions.append(f'wikibase_id contains "{self.wikibase_id}"')

        if self.concept_ids:
            id_conditions = " or ".join(
                [f'id contains "{cid}"' for cid in self.concept_ids]
            )
            conditions.append(f"({id_conditions})")

        if self.parent_concept_id:
            conditions.append(f'subconcept_of contains "{self.parent_concept_id}"')

        if not conditions:
            conditions.append("true")

        return f"{yql_parts[0]} {' and '.join(conditions)} limit {self.limit} offset {self.offset}"

    def build_vespa_body(self) -> dict[str, Any]:
        """Build Vespa request body from parameters."""
        body: dict[str, Any] = {"yql": self.build_yql()}

        if self.query_string:
            body["query"] = self.query_string

        return body


class ConceptResource:
    """Synchronous concept operations implementing Resource[ConceptQueryParams, models.Concept]."""

    def __init__(self, client: Vespa):
        self._client = client

    def query(self, params: ConceptQueryParams) -> Sequence[models.Concept]:
        """
        Query concepts from Vespa.

        Args:
            params: Query parameters including filters, pagination, etc.

        Returns:
            Sequence of Concept objects matching the query.
        """
        response: VespaQueryResponse = self._client.query(
            body=params.build_vespa_body()
        )

        concepts: list[models.Concept] = []
        if response.is_successful():
            for hit in response.hits:
                concepts.append(models.Concept.from_vespa_response(hit))

        return concepts

    def get(self, id: str) -> models.Concept | None:
        """
        Get a single concept from Vespa by ID.

        Args:
            id: The concept ID to retrieve.

        Returns:
            Concept object if found, None otherwise.
        """
        doc_id = f"id:doc_search:concept::{id}"
        response: VespaResponse = self._client.get_data(
            schema="concept", data_id=doc_id
        )

        if response.is_successful():
            return models.Concept.from_vespa_response(response.json)
        return None


class AsyncConceptResource:
    """Asynchronous concept operations implementing AsyncResource[ConceptQueryParams, models.Concept]."""

    def __init__(self, client: Vespa):
        self._client = client

    async def query(self, params: ConceptQueryParams) -> Sequence[models.Concept]:
        """
        Async query concepts from Vespa.

        Args:
            params: Query parameters including filters, pagination, etc.

        Returns:
            Sequence of Concept objects matching the query.
        """
        response: VespaQueryResponse = await self._client.query_async(
            body=params.build_vespa_body()
        )

        concepts: list[models.Concept] = []
        if response.is_successful():
            for hit in response.hits:
                concepts.append(models.Concept.from_vespa_response(hit))

        return concepts

    async def get(self, id: str) -> models.Concept | None:
        """
        Async get a single concept from Vespa by ID.

        Args:
            id: The concept ID to retrieve.

        Returns:
            Concept object if found, None otherwise.
        """
        doc_id = f"id:doc_search:concept::{id}"
        response: VespaResponse = await self._client.get_data_async(
            schema="concept", data_id=doc_id
        )

        if response.is_successful():
            return models.Concept.from_vespa_response(response.json)
        return None
