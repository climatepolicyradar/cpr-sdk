"""Passage search resources."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from vespa.application import Vespa
from vespa.io import VespaQueryResponse, VespaResponse

import cpr_sdk.models.search as models


@dataclass
class PassageQueryParams:
    """Parameters for passage queries."""

    query_string: str | None = None
    """Full text search query."""

    family_ids: Sequence[str] | None = None
    """Filter by specific family IDs."""

    document_ids: Sequence[str] | None = None
    """Filter by specific document IDs."""

    family_geography: Sequence[str] | None = None
    """Filter by family geography."""

    family_category: Sequence[str] | None = None
    """Filter by family category."""

    limit: int = 100
    """Maximum number of results to return."""

    offset: int = 0
    """Number of results to skip (for pagination)."""

    def build_yql(self) -> str:
        """Build Vespa YQL query for passages."""
        yql_parts = ["select * from document_passage where"]
        conditions = []

        if self.query_string:
            conditions.append("userQuery()")

        if self.family_ids:
            id_conditions = " or ".join(
                [f'family_import_id contains "{fid}"' for fid in self.family_ids]
            )
            conditions.append(f"({id_conditions})")

        if self.document_ids:
            id_conditions = " or ".join(
                [f'document_import_id contains "{did}"' for did in self.document_ids]
            )
            conditions.append(f"({id_conditions})")

        if self.family_geography:
            geo_conditions = " or ".join(
                [f'family_geography contains "{geo}"' for geo in self.family_geography]
            )
            conditions.append(f"({geo_conditions})")

        if self.family_category:
            cat_conditions = " or ".join(
                [f'family_category contains "{cat}"' for cat in self.family_category]
            )
            conditions.append(f"({cat_conditions})")

        if not conditions:
            conditions.append("true")

        return f"{yql_parts[0]} {' and '.join(conditions)} limit {self.limit} offset {self.offset}"

    def build_vespa_body(self) -> dict[str, Any]:
        """Build Vespa request body for passages."""
        body: dict[str, Any] = {"yql": self.build_yql()}

        if self.query_string:
            body["query"] = self.query_string

        return body


class PassageResource:
    """Synchronous passage operations implementing Resource[PassageQueryParams, models.Passage]."""

    def __init__(self, client: Vespa):
        self._client = client

    def query(self, params: PassageQueryParams) -> Sequence[models.Passage]:
        """
        Query passages from Vespa.

        Args:
            params: Query parameters including filters, pagination, etc.

        Returns:
            Sequence of Passage objects matching the query.
        """
        response: VespaQueryResponse = self._client.query(body=params.build_vespa_body())

        passages: list[models.Passage] = []
        if response.is_successful():
            for hit in response.hits:
                passages.append(models.Passage.from_vespa_response(hit))

        return passages

    def get(self, id: str) -> models.Passage | None:
        """
        Get a single passage from Vespa by ID.

        Args:
            id: The passage ID to retrieve.

        Returns:
            Passage object if found, None otherwise.
        """
        doc_id = f"id:doc_search:document_passage::{id}"
        response: VespaResponse = self._client.get_data(
            schema="document_passage", data_id=doc_id
        )

        if response.is_successful():
            return models.Passage.from_vespa_response(response.json)
        return None


class AsyncPassageResource:
    """Asynchronous passage operations implementing AsyncResource[PassageQueryParams, models.Passage]."""

    def __init__(self, client: Vespa):
        self._client = client

    async def query(self, params: PassageQueryParams) -> Sequence[models.Passage]:
        """
        Async query passages from Vespa.

        Args:
            params: Query parameters including filters, pagination, etc.

        Returns:
            Sequence of Passage objects matching the query.
        """
        response: VespaQueryResponse = await self._client.query_async(
            body=params.build_vespa_body()
        )

        passages: list[models.Passage] = []
        if response.is_successful():
            for hit in response.hits:
                passages.append(models.Passage.from_vespa_response(hit))

        return passages

    async def get(self, id: str) -> models.Passage | None:
        """
        Async get a single passage from Vespa by ID.

        Args:
            id: The passage ID to retrieve.

        Returns:
            Passage object if found, None otherwise.
        """
        doc_id = f"id:doc_search:document_passage::{id}"
        response: VespaResponse = await self._client.get_data_async(
            schema="document_passage", data_id=doc_id
        )

        if response.is_successful():
            return models.Passage.from_vespa_response(response.json)
        return None
