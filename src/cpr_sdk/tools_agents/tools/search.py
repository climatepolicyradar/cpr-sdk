from typing import Optional

from cpr_sdk.config import VESPA_URL
from cpr_sdk.models.search import (
    Family,
    SearchParameters,
    SearchResponse,
    Passage,
    Filters,
)
from cpr_sdk.search_adaptors import VespaSearchAdapter


def _get_search_adapter() -> VespaSearchAdapter:
    if VESPA_URL is None:
        raise ValueError("Set VESPA_URL in your environment to use this tool")

    return VespaSearchAdapter(VESPA_URL)


def search_database(
    query: str,
    limit: int = 20,
    max_hits_per_family: int = 10,
    filters: Optional[Filters] = None,
    exact_match: bool = False,
) -> list[Family]:
    """
    Search whole database.

    Args:
        query: The query to search for.
        limit: The maximum number of results to return.
        max_hits_per_family: The maximum number of hits to return per family.
        filters: The filters to apply to the search.
        exact_match: Whether to use exact matching.

    Returns:
        A list of families containing the search results. Each of these contains a mix of
        documents and passages.
    """

    search_adapter = _get_search_adapter()
    search_parameters = SearchParameters(
        query_string=query,
        limit=limit,
        max_hits_per_family=max_hits_per_family,
        filters=filters,
        exact_match=exact_match,
    )

    response: SearchResponse = search_adapter.search(search_parameters)
    return list(response.families)


def search_within_document(
    document_id: str,
    query: str,
    limit: int = 20,
    filters: Optional[Filters] = None,
    exact_match: bool = False,
) -> list[Passage]:
    """Search for passages within a document based on a query."""

    search_adapter = _get_search_adapter()
    search_parameters = SearchParameters(
        query_string=query,
        limit=limit,
        document_ids=[document_id],
        filters=filters,
        exact_match=exact_match,
    )

    response: SearchResponse = search_adapter.search(search_parameters)

    hits: list[Passage] = [
        _hit for _hit in response.families[0].hits if isinstance(_hit, Passage)
    ]
    return hits
