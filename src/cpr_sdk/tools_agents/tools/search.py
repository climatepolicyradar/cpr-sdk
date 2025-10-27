from typing import Literal, Optional

from cpr_sdk.config import VESPA_URL
from cpr_sdk.models.search import (
    SearchParameters,
    SearchResponse,
    Passage,
    Document,
    Filters,
    Hit,
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
    return_type: Literal["documents", "passages", "both"] = "documents",
    filters: Optional[Filters] = None,
    exact_match: bool = False,
) -> list[Hit]:
    """
    Search whole database.

    Args:
        query: The query to search for.
        limit: The maximum number of results to return.
        max_hits_per_family: The maximum number of hits to return per family.
        return_type: The type of results to return.
        filters: The filters to apply to the search.
        exact_match: Whether to use exact matching.

    Returns:
        A list of hits containing the search results.
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

    all_results = [hit for family in response.results for hit in family.hits]

    if return_type == "documents":
        return [hit for hit in all_results if isinstance(hit, Document)]
    elif return_type == "passages":
        return [hit for hit in all_results if isinstance(hit, Passage)]
    else:
        return all_results


def search_for_documents_by_title(
    query: str,
    limit: int = 20,
) -> list[Document]:
    """
    Search for documents by title.

    Args:
        query: The title to search for.
        limit: The maximum number of documents to return.

    Returns:
        A list of documents containing the search results.
    """
    search_parameters = SearchParameters(
        query_string=query,
        limit=limit,
        by_document_title=True,
        documents_only=True,
    )

    search_adapter = _get_search_adapter()
    response: SearchResponse = search_adapter.search(search_parameters)

    all_results = [hit for family in response.results for hit in family.hits]

    # We set the limit here as the limit in the query doesn't seem to work.
    # TODO: Investigate why the limit in the query doesn't work.
    return [hit for hit in all_results if isinstance(hit, Document)][:limit]


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

    if len(response.results) == 0:
        return []

    hits: list[Passage] = [
        _hit for _hit in response.results[0].hits if isinstance(_hit, Passage)
    ]
    return hits
