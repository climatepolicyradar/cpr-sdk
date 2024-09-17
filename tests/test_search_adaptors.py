from timeit import timeit
from typing import Mapping
from unittest.mock import patch

import pytest

from cpr_sdk.models.search import (
    Document,
    Filters,
    MetadataFilter,
    Passage,
    SearchParameters,
    SearchResponse,
    sort_fields,
)
from cpr_sdk.search_adaptors import VespaSearchAdapter


def vespa_search(
    adaptor: VespaSearchAdapter, request: SearchParameters
) -> SearchResponse:
    try:
        response = adaptor.search(request)
    except Exception as e:
        pytest.fail(f"Vespa query failed. {e.__class__.__name__}: {e}")
    return response


def profile_search(
    test_vespa: VespaSearchAdapter, params: Mapping[str, str], n: int = 25
) -> float:
    t = timeit(
        lambda: vespa_search(test_vespa, SearchParameters(**params)),
        number=n,
    )
    avg_ms = (t / n) * 1000
    return avg_ms


@pytest.mark.parametrize(
    "search_adaptor_params",
    [
        {"instance_url": "http://localhost:8080", "cert_directory": "/tmp"},
        {"instance_url": "http://localhost:8080"},
    ],
)
@pytest.mark.vespa
def test_vespa_search_adaptor_instantiation(search_adaptor_params: dict) -> None:
    VespaSearchAdapter(**search_adaptor_params)


@pytest.mark.vespa
def test_vespa_search_adaptor__works(test_vespa):
    request = SearchParameters(query_string="the")
    response = vespa_search(test_vespa, request)

    assert len(response.families) == response.total_family_hits == 3
    assert response.query_time_ms < response.total_time_ms
    total_passage_count = sum([f.total_passage_hits for f in response.families])
    assert total_passage_count == response.total_hits


@pytest.mark.parametrize(
    "params",
    (
        {"query_string": "the"},
        {"query_string": "climate change"},
        {"query_string": "fuel", "exact_search": True},
        {"all_results": True, "documents_only": True},
        {"query_string": "fuel", "sort_by": "date", "sort_order": "asc"},
        {"query_string": "forest", "filter": {"family_category": "CCLW"}},
    ),
)
@pytest.mark.vespa
def test_vespa_search_adaptor__is_fast_enough(test_vespa, params):
    MAX_SPEED_MS = 850

    avg_ms = profile_search(test_vespa, params=params)
    assert avg_ms <= MAX_SPEED_MS


@pytest.mark.vespa
@pytest.mark.parametrize(
    "family_ids",
    [
        ["CCLW.family.i00000003.n0000"],
        ["CCLW.family.10014.0"],
        ["CCLW.family.i00000003.n0000", "CCLW.family.10014.0"],
        ["CCLW.family.4934.0"],
    ],
)
def test_vespa_search_adaptor__family_ids(test_vespa, family_ids):
    request = SearchParameters(query_string="the", family_ids=family_ids)
    response = vespa_search(test_vespa, request)
    got_family_ids = [f.id for f in response.families]
    assert sorted(got_family_ids) == sorted(family_ids)


@pytest.mark.vespa
@pytest.mark.parametrize(
    "document_ids",
    [
        ["CCLW.document.i00000004.n0000"],
        ["CCLW.executive.10014.4470"],
        ["CCLW.document.i00000004.n0000", "CCLW.executive.10014.4470"],
        ["CCLW.executive.4934.1571"],
    ],
)
def test_vespa_search_adaptor__document_ids(test_vespa, document_ids):
    request = SearchParameters(query_string="the", document_ids=document_ids)
    response = vespa_search(test_vespa, request)

    # As passages are returned we need to collect and deduplicate them to get id list
    got_document_ids = []
    for fam in response.families:
        for doc in fam.hits:
            got_document_ids.append(doc.document_import_id)
    got_document_ids = list(set(got_document_ids))

    assert sorted(got_document_ids) == sorted(document_ids)


@pytest.mark.vespa
def test_vespa_search_adaptor__bad_query_string_still_works(test_vespa):
    family_name = ' Bad " query/    '
    request = SearchParameters(query_string=family_name)
    try:
        vespa_search(test_vespa, request)
    except Exception as e:
        assert False, f"failed with: {e}"


@pytest.mark.vespa
def test_vespa_search_adaptor__hybrid(test_vespa):
    family_name = "Climate Change Adaptation and Low Emissions Growth Strategy by 2035"
    request = SearchParameters(query_string=family_name)
    response = vespa_search(test_vespa, request)

    # Was the family searched for in the results.
    # Note that this is a fairly loose test
    got_family_names = []
    for fam in response.families:
        for doc in fam.hits:
            got_family_names.append(doc.family_name)
    assert family_name in got_family_names


@pytest.mark.vespa
def test_vespa_search_adaptor__hybrid_encoding_on_vespa(test_vespa):
    family_name = "Climate Change Adaptation and Low Emissions Growth Strategy by 2035"
    requests = {
        "encode_in_sdk": SearchParameters(query_string=family_name),
        "encode_on_vespa": SearchParameters(
            query_string=family_name, experimental_encode_on_vespa=True
        ),
    }
    responses = dict()

    for request_name, request in requests.items():
        responses[request_name] = vespa_search(test_vespa, request)

        # Was the family searched for in the results.
        # Note that this is a fairly loose test
        got_family_names = []
        for fam in responses[request_name].families:
            for doc in fam.hits:
                got_family_names.append(doc.family_name)
        assert family_name in got_family_names

    assert (
        responses["encode_in_sdk"].total_hits == responses["encode_on_vespa"].total_hits
    )
    assert responses["encode_in_sdk"].families == responses["encode_on_vespa"].families


@pytest.mark.vespa
def test_vespa_search_adaptor__all(test_vespa):
    request = SearchParameters(query_string="", all_results=True)
    response = vespa_search(test_vespa, request)
    assert len(response.families) == response.total_family_hits

    # Filtering should still work
    family_id = "CCLW.family.i00000003.n0000"
    request = SearchParameters(
        query_string="", all_results=True, family_ids=[family_id]
    )
    response = vespa_search(test_vespa, request)
    assert len(response.families) == 1
    assert response.families[0].id == family_id


@pytest.mark.vespa
def test_vespa_search_adaptor__exact(test_vespa):
    query_string = "Environmental Strategy for 2014-2023"
    request = SearchParameters(query_string=query_string, exact_match=True)
    response = vespa_search(test_vespa, request)
    got_family_names = []
    for fam in response.families:
        for doc in fam.hits:
            got_family_names.append(doc.family_name)
    # For an exact query where this term only exists in the family name, we'd expect
    # it to be the only result so can be quite specific
    assert len(set(got_family_names)) == 1
    assert got_family_names[0] == query_string

    # Conversely we'd expect nothing if the query string isnt present
    query_string = "no such string as this can be found in the test documents"
    request = SearchParameters(query_string=query_string, exact_match=True)
    response = vespa_search(test_vespa, request)
    assert len(response.families) == 0


@pytest.mark.vespa
@patch("cpr_sdk.vespa.SENSITIVE_QUERY_TERMS", {"Government"})
def test_vespa_search_adaptor__sensitive(test_vespa):
    request = SearchParameters(query_string="Government")
    response = vespa_search(test_vespa, request)

    # Without being too prescriptive, we'd expect something back for this
    assert len(response.families) > 0


@pytest.mark.parametrize(
    "family_limit, max_hits_per_family",
    [
        (1, 1),
        (1, 100),
        (2, 1),
        (2, 5),
        (3, 500),
    ],
)
@pytest.mark.vespa
def test_vespa_search_adaptor__limits(test_vespa, family_limit, max_hits_per_family):
    request = SearchParameters(
        query_string="the",
        family_ids=[],
        limit=family_limit,
        max_hits_per_family=max_hits_per_family,
    )
    response = vespa_search(test_vespa, request)

    assert len(response.families) == family_limit
    for fam in response.families:
        assert len(fam.hits) <= max_hits_per_family


@pytest.mark.parametrize(
    "family_limit, max_hits_per_family",
    [
        (501, 5),
        (3, 501),
    ],
)
@pytest.mark.vespa
def test_vespa_search_adaptor__limits__errors(family_limit, max_hits_per_family):
    with pytest.raises(ValueError):
        SearchParameters(
            query_string="the",
            family_ids=[],
            limit=family_limit,
            max_hits_per_family=max_hits_per_family,
        )


@pytest.mark.vespa
def test_vespa_search_adaptor__continuation_tokens__families(test_vespa):
    query_string = "the"
    limit = 2
    max_hits_per_family = 3

    # Make an initial request to get continuation tokens and results
    request = SearchParameters(
        query_string=query_string,
        limit=limit,
        max_hits_per_family=max_hits_per_family,
    )
    response = vespa_search(test_vespa, request)
    first_family_ids = [f.id for f in response.families]
    family_continuation = response.continuation_token
    assert len(response.families) == 2
    assert response.total_family_hits == 3

    # Family increment
    request = SearchParameters(
        query_string=query_string,
        limit=limit,
        max_hits_per_family=max_hits_per_family,
        continuation_tokens=[family_continuation],
    )
    response = vespa_search(test_vespa, request)
    prev_family_continuation = response.prev_continuation_token
    assert len(response.families) == 1
    assert response.total_family_hits == 3

    # Family should have changed
    second_family_ids = [f.id for f in response.families]
    assert sorted(first_family_ids) != sorted(second_family_ids)
    # As this is the end of the results we also expect no more tokens
    assert response.continuation_token is None

    # Using prev_continuation_token give initial results
    request = SearchParameters(
        query_string=query_string,
        limit=limit,
        max_hits_per_family=max_hits_per_family,
        continuation_tokens=[prev_family_continuation],
    )
    response = vespa_search(test_vespa, request)
    prev_family_ids = [f.id for f in response.families]
    assert prev_family_ids == first_family_ids


@pytest.mark.vespa
def test_vespa_search_adaptor__continuation_tokens__passages(test_vespa):
    query_string = "the"
    limit = 1
    max_hits_per_family = 10

    # Make an initial request to get continuation tokens and results for comparison
    request = SearchParameters(
        query_string=query_string,
        limit=limit,
        max_hits_per_family=max_hits_per_family,
    )
    initial_response = vespa_search(test_vespa, request)

    # Collect family & hits for comparison later
    initial_family_id = initial_response.families[0].id
    initial_passages = [h.text_block_id for h in initial_response.families[0].hits]

    this_continuation = initial_response.this_continuation_token
    passage_continuation = initial_response.families[0].continuation_token

    # Passage Increment
    request = SearchParameters(
        query_string=query_string,
        limit=limit,
        max_hits_per_family=max_hits_per_family,
        continuation_tokens=[this_continuation, passage_continuation],
    )
    response = vespa_search(test_vespa, request)
    prev_passage_continuation = response.families[0].prev_continuation_token

    # Family should not have changed
    assert response.families[0].id == initial_family_id

    # But Passages SHOULD have changed
    new_passages = sorted([h.text_block_id for h in response.families[0].hits])
    assert sorted(new_passages) != sorted(initial_passages)

    # Previous passage continuation gives initial results
    request = SearchParameters(
        query_string=query_string,
        limit=limit,
        max_hits_per_family=max_hits_per_family,
        continuation_tokens=[this_continuation, prev_passage_continuation],
    )
    response = vespa_search(test_vespa, request)
    assert response.families[0].id == initial_family_id
    prev_passages = sorted([h.text_block_id for h in response.families[0].hits])
    assert sorted(prev_passages) != sorted(new_passages)
    assert sorted(prev_passages) == sorted(initial_passages)


@pytest.mark.vespa
def test_vespa_search_adaptor__continuation_tokens__families_and_passages(
    test_vespa,
):
    query_string = "the"
    limit = 1
    max_hits_per_family = 30

    # Make an initial request to get continuation tokens and results for comparison
    request_one = SearchParameters(
        query_string=query_string,
        limit=limit,
        max_hits_per_family=max_hits_per_family,
    )
    response_one = vespa_search(test_vespa, request_one)

    # Increment Families
    request_two = SearchParameters(
        query_string=query_string,
        limit=limit,
        max_hits_per_family=max_hits_per_family,
        continuation_tokens=[response_one.continuation_token],
    )
    response_two = vespa_search(test_vespa, request_two)

    # Then Increment Passages Twice

    request_three = SearchParameters(
        query_string=query_string,
        limit=limit,
        max_hits_per_family=max_hits_per_family,
        continuation_tokens=[
            response_two.this_continuation_token,
            response_two.families[0].continuation_token,
        ],
    )
    response_three = vespa_search(test_vespa, request_three)

    request_four = SearchParameters(
        query_string=query_string,
        limit=limit,
        max_hits_per_family=max_hits_per_family,
        continuation_tokens=[
            response_two.this_continuation_token,
            response_three.families[0].continuation_token,
        ],
    )
    response_four = vespa_search(test_vespa, request_four)

    # All of these should have different passages from each other
    assert (
        sorted([h.text_block_id for h in response_one.families[0].hits])
        != sorted([h.text_block_id for h in response_two.families[0].hits])
        != sorted([h.text_block_id for h in response_three.families[0].hits])
        != sorted([h.text_block_id for h in response_four.families[0].hits])
    )


@pytest.mark.parametrize("sort_by", sort_fields.keys())
@pytest.mark.vespa
def test_vespa_search_adapter_sorting(test_vespa, sort_by):
    ascend = vespa_search(
        test_vespa,
        SearchParameters(query_string="the", sort_by=sort_by, sort_order="ascending"),
    )
    descend = vespa_search(
        test_vespa,
        SearchParameters(query_string="the", sort_by=sort_by, sort_order="descending"),
    )

    assert ascend != descend


@pytest.mark.vespa
def test_vespa_search_no_passages_search(test_vespa):
    no_passages = vespa_search(
        test_vespa,
        SearchParameters(all_results=True, documents_only=True),
    )
    for family in no_passages.families:
        for hit in family.hits:
            assert isinstance(hit, Document)

    with_passages = vespa_search(
        test_vespa,
        SearchParameters(all_results=True),
    )
    found_a_passage = False
    for family in with_passages.families:
        for hit in family.hits:
            if isinstance(hit, Passage):
                found_a_passage = True
    assert found_a_passage


@pytest.mark.vespa
@pytest.mark.parametrize(
    "query_string, corpus_type_names",
    [
        (
            "the",
            ["UNFCCC Submissions"],
        ),
        (
            "the",
            ["UNFCCC Submissions", "Climate Change Laws of the World"],
        ),
    ],
)
def test_vespa_search_adaptor__corpus_type_name(
    test_vespa, query_string, corpus_type_names
):
    """Test that the corpus type name filter works"""
    request = SearchParameters(
        query_string=query_string,
        corpus_type_names=corpus_type_names,
    )
    response = vespa_search(test_vespa, request)
    assert response.total_family_hits > 0
    for family in response.families:
        for hit in family.hits:
            assert hit.corpus_type_name not in [None, []]
            assert hit.corpus_type_name in corpus_type_names


@pytest.mark.vespa
@pytest.mark.parametrize(
    "query_string, corpus_import_ids",
    [
        (
            "the",
            ["CCLW.corpus.i00000003.n0001"],
        ),
        (
            "the",
            ["CCLW.corpus.i00000003.n0001", "CCLW.corpus.i00000003.n0002"],
        ),
    ],
)
def test_vespa_search_adaptor__corpus_import_ids(
    test_vespa, query_string, corpus_import_ids
):
    """Test that the corpus import ids filter works"""
    request = SearchParameters(
        query_string=query_string,
        corpus_import_ids=corpus_import_ids,
    )
    response = vespa_search(test_vespa, request)
    assert response.total_family_hits > 0
    for family in response.families:
        for hit in family.hits:
            assert hit.corpus_import_id not in [None, []]
            assert hit.corpus_import_id in corpus_import_ids


@pytest.mark.vespa
@pytest.mark.parametrize(
    "query_string, metadata_filters",
    [
        (
            "the",
            [{"name": "family.sector", "value": "Price"}],
        ),
        (
            "the",
            [
                {"name": "family.sector", "value": "Price"},
                {"name": "family.topic", "value": "Mitigation"},
            ],
        ),
    ],
)
def test_vespa_search_adaptor__metadata(test_vespa, query_string, metadata_filters):
    """Test that the metadata filter works"""
    request = SearchParameters(
        query_string=query_string,
        metadata=[
            MetadataFilter.model_validate(metadata_filter)
            for metadata_filter in metadata_filters
        ],
    )
    response = vespa_search(test_vespa, request)
    assert response.total_family_hits > 0
    for family in response.families:
        for hit in family.hits:
            assert hit.metadata not in [None, []]
            for metadata_filter in metadata_filters:
                assert metadata_filter in hit.metadata


@pytest.mark.vespa
@pytest.mark.parametrize(
    "query_string, filters",
    [
        (
            "the",
            {"family_geographies": ["BIH"]},
        ),
        (
            "the",
            {"family_geographies": ["BIH", "NOR"]},
        ),
    ],
)
def test_vespa_search_adaptor__filters(test_vespa, query_string, filters):
    """Test that the search filters work"""
    request = SearchParameters(
        query_string=query_string,
        filters=Filters.model_validate(filters),
    )
    response = vespa_search(test_vespa, request)
    assert response.total_family_hits > 0
    for family in response.families:
        for hit in family.hits:
            for filter_name, filter_values in filters.items():
                attribute_value_from_hit = getattr(hit, filter_name)
                assert attribute_value_from_hit not in [None, []]
                assert all([val in attribute_value_from_hit for val in filter_values])
