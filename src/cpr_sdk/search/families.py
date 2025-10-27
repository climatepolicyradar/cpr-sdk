"""Family (document) search resources."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from vespa.application import Vespa
from vespa.io import VespaQueryResponse, VespaResponse

import cpr_sdk.models.search as models


@dataclass
class FamilyQueryParams:
    """Parameters for family (document) queries."""

    query_string: str | None = None
    """Full text search query."""

    family_ids: Sequence[str] | None = None
    """Filter by specific family IDs."""

    family_geography: Sequence[str] | None = None
    """Filter by family geography."""

    family_category: Sequence[str] | None = None
    """Filter by family category."""

    family_source: Sequence[str] | None = None
    """Filter by family source."""

    limit: int = 100
    """Maximum number of results to return."""

    offset: int = 0
    """Number of results to skip (for pagination)."""

    def build_yql(self) -> str:
        """Build Vespa YQL query for families (documents)."""
        yql_parts = ["select * from family_document where"]
        conditions = []

        if self.query_string:
            conditions.append("userQuery()")

        if self.family_ids:
            id_conditions = " or ".join(
                [f'family_import_id contains "{fid}"' for fid in self.family_ids]
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

        if self.family_source:
            source_conditions = " or ".join(
                [f'family_source contains "{src}"' for src in self.family_source]
            )
            conditions.append(f"({source_conditions})")

        if not conditions:
            conditions.append("true")

        return f"{yql_parts[0]} {' and '.join(conditions)} limit {self.limit} offset {self.offset}"

    def build_vespa_body(self) -> dict[str, Any]:
        """Build Vespa request body for families."""
        body: dict[str, Any] = {"yql": self.build_yql()}

        if self.query_string:
            body["query"] = self.query_string

        return body


class FamilyResource:
    """Synchronous family (document) operations implementing Resource[FamilyQueryParams, models.Document]."""

    def __init__(self, client: Vespa):
        self._client = client

    def query(self, params: FamilyQueryParams) -> Sequence[models.Document]:
        """
        Query families (documents) from Vespa.

        Args:
            params: Query parameters including filters, pagination, etc.

        Returns:
            Sequence of Document objects matching the query.
        """
        response: VespaQueryResponse = self._client.query(body=params.build_vespa_body())

        documents: list[models.Document] = []
        if response.is_successful():
            for hit in response.hits:
                documents.append(models.Document.from_vespa_response(hit))

        return documents

    def get(self, id: str) -> models.Document | None:
        """
        Get a single family (document) from Vespa by ID.

        Args:
            id: The family/document ID to retrieve.

        Returns:
            Document object if found, None otherwise.
        """
        doc_id = f"id:doc_search:family_document::{id}"
        response: VespaResponse = self._client.get_data(
            schema="family_document", data_id=doc_id
        )

        if response.is_successful():
            return models.Document.from_vespa_response(response.json)
        return None


class AsyncFamilyResource:
    """Asynchronous family (document) operations implementing AsyncResource[FamilyQueryParams, models.Document]."""

    def __init__(self, client: Vespa):
        self._client = client

    async def query(self, params: FamilyQueryParams) -> Sequence[models.Document]:
        """
        Async query families (documents) from Vespa.

        Args:
            params: Query parameters including filters, pagination, etc.

        Returns:
            Sequence of Document objects matching the query.
        """
        response: VespaQueryResponse = await self._client.query_async(
            body=params.build_vespa_body()
        )

        documents: list[models.Document] = []
        if response.is_successful():
            for hit in response.hits:
                documents.append(models.Document.from_vespa_response(hit))

        return documents

    async def get(self, id: str) -> models.Document | None:
        """
        Async get a single family (document) from Vespa by ID.

        Args:
            id: The family/document ID to retrieve.

        Returns:
            Document object if found, None otherwise.
        """
        doc_id = f"id:doc_search:family_document::{id}"
        response: VespaResponse = await self._client.get_data_async(
            schema="family_document", data_id=doc_id
        )

        if response.is_successful():
            return models.Document.from_vespa_response(response.json)
        return None
