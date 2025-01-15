from timeit import timeit
from typing import Mapping, Union
from unittest.mock import patch

import pytest

from cpr_sdk.models.search import (
    Concept,
    ConceptCountFilter,
    ConceptFilter,
    Document,
    Filters,
    Hit,
    MetadataFilter,
    OperandTypeEnum,
    Passage,
    SearchParameters,
    SearchResponse,
    sort_fields,
)
from cpr_sdk.search_adaptors import VespaSearchAdapter
from cpr_sdk.utils import dig
from cpr_sdk.vespa import build_vespa_request_body


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


def is_sorted(arr: list[int]) -> tuple[bool, bool]:
    """
    Check if the array is sorted in ascending or descending order.

    :param arr: List of values to check.
    :return: Tuple of two booleans (is_ascending, is_descending).
    """
    is_ascending = all(arr[i] <= arr[i + 1] for i in range(len(arr) - 1))
    is_descending = all(arr[i] >= arr[i + 1] for i in range(len(arr) - 1))
    return is_ascending, is_descending


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


@pytest.mark.vespa
def test_vespa_search_adaptor_relevance_scoring(test_vespa):
    request = SearchParameters(query_string="the")
    response = vespa_search(test_vespa, request)

    for family in response.families:
        assert isinstance(family.relevance, float)
        for hit in family.hits:
            assert isinstance(hit.relevance, float)


@pytest.mark.vespa
def test_vespa_search_adaptor_rank_features(test_vespa):
    request = SearchParameters(query_string="the")
    response = vespa_search(test_vespa, request)

    for family in response.families:
        for hit in family.hits:
            assert isinstance(hit.rank_features, dict)


@pytest.mark.vespa
def test_vespa_search_adaptor__exact_search(test_vespa):
    """Test that exact search works"""

    request = SearchParameters(query_string="biodiversity", exact_match=True)
    response = vespa_search(test_vespa, request)

    assert response.total_hits > 0
    for family in response.families:
        for hit in family.hits:
            if isinstance(hit, Passage):
                assert "biodiversity" in hit.text_block.lower()


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
        raise AssertionError(f"failed with: {e}")


@pytest.mark.vespa
def test_vespa_search_adaptor__hybrid(test_vespa):
    family_name = "Nationally Determined Contribution: Climate Change Adaptation and Low Emissions Growth Strategy by 2035"
    request = SearchParameters(query_string=family_name)
    response = vespa_search(test_vespa, request)

    # Was the family searched for in the results.
    # Note that this is a fairly loose test
    got_family_names = []
    for fam in response.families:
        got_family_names.append(fam.hits[0].family_name)
    assert family_name in got_family_names


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
    initial_passages = [
        h.text_block_id
        for h in initial_response.families[0].hits
        if isinstance(h, Passage)
    ]

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
    new_passages = sorted(
        [h.text_block_id for h in response.families[0].hits if isinstance(h, Passage)]
    )
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
    prev_passages = sorted(
        [h.text_block_id for h in response.families[0].hits if isinstance(h, Passage)]
    )
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
        sorted(
            [
                h.text_block_id
                for h in response_one.families[0].hits
                if isinstance(h, Passage)
            ]
        )
        != sorted(
            [
                h.text_block_id
                for h in response_two.families[0].hits
                if isinstance(h, Passage)
            ]
        )
        != sorted(
            [
                h.text_block_id
                for h in response_three.families[0].hits
                if isinstance(h, Passage)
            ]
        )
        != sorted(
            [
                h.text_block_id
                for h in response_four.families[0].hits
                if isinstance(h, Passage)
            ]
        )
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
        assert len(family.hits) > 0
        for hit in family.hits:
            assert hit.corpus_type_name not in [None, []]
            assert hit.corpus_type_name in corpus_type_names


@pytest.mark.vespa
@pytest.mark.parametrize(
    "query_string, concept_filters",
    [
        (
            "the",
            [{"name": "name", "value": "environment"}],
        ),
        (
            "the",
            [
                {"name": "model", "value": "sectors_model"},
                {"name": "id", "value": "concept_0_0"},
            ],
        ),
        (
            "the",
            [
                {"name": "parent_concept_ids_flat", "value": "Q0"},
            ],
        ),
        (
            "the",
            [
                {"name": "parent_concept_ids_flat", "value": "Q0"},
                {"name": "parent_concept_ids_flat", "value": "Q1"},
            ],
        ),
        (
            "the",
            [
                {"name": "parent_concept_ids_flat", "value": "Q0,"},
                {"name": "id", "value": "concept_0_0"},
            ],
        ),
        (
            "",
            [
                {"name": "parent_concept_ids_flat", "value": "Q0,"},
                {"name": "id", "value": "concept_0_0"},
            ],
        ),
    ],
)
def test_vespa_search_adaptor__concept_filter(
    test_vespa, query_string: str, concept_filters: list[dict]
):
    """Test that the concept filter works"""
    request = SearchParameters(
        query_string=query_string,
        concept_filters=[
            ConceptFilter.model_validate(concept_filter)
            for concept_filter in concept_filters
        ],
        documents_only=False,
    )
    response = vespa_search(test_vespa, request)
    assert response.total_family_hits > 0
    for family in response.families:
        for hit in family.hits:
            assert hit.concepts and hit.concepts != []
            assert all(
                [isinstance(concept_hit, Concept) for concept_hit in hit.concepts]
            )

            for concept_filter in concept_filters:
                hit_concept_filter_vals = [
                    concept.__getattribute__(concept_filter["name"])
                    for concept in hit.concepts
                ]

                if concept_filter["name"] == "parent_concept_ids_flat":
                    assert any(
                        [
                            concept_filter["value"] in hit_concept_filter_val
                            for hit_concept_filter_val in hit_concept_filter_vals
                        ]
                    )
                else:
                    assert any(
                        [
                            hit_concept_filter_val == concept_filter["value"]
                            for hit_concept_filter_val in hit_concept_filter_vals
                        ]
                    )


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
        assert len(family.hits) > 0
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


@pytest.mark.vespa
@pytest.mark.parametrize("query_string", ["e"])
@pytest.mark.parametrize("exact_match", [True, False])
@pytest.mark.parametrize(
    "metadata_filters", [None, [{"name": "family.sector", "value": "Price"}]]
)
@pytest.mark.parametrize("geographies", [None, {"family_geographies": ["BIH"]}])
def test_vespa_search_response__geographies(
    test_vespa, query_string, exact_match, metadata_filters, geographies
) -> None:
    """Test that the search response includes geographies"""
    parameters = SearchParameters(
        query_string=query_string,
        exact_match=exact_match,
        filters=Filters.model_validate(geographies) if geographies else None,
        metadata=(
            [
                MetadataFilter.model_validate(metadata_filter)
                for metadata_filter in metadata_filters
            ]
            if metadata_filters
            else None
        ),
    )

    vespa_response = test_vespa.client.query(body=build_vespa_request_body(parameters))

    root = vespa_response.json["root"]
    response_families = dig(root, "children", 0, "children", 0, "children", default=[])
    for family in response_families:
        for hit in dig(family, "children", 0, "children", default=[]):
            hit = Hit.from_vespa_response(response_hit=hit)
            assert hit.family_geography not in [None, []]
            assert hit.family_geographies not in [None, []]


@pytest.mark.vespa
def test_vespa_search_hybrid_no_closeness_profile(test_vespa):
    query_string = "the"

    request_no_closeness = SearchParameters(
        query_string=query_string,
        custom_vespa_request_body={"ranking.profile": "hybrid_no_closeness"},
    )
    response_no_closeness = vespa_search(test_vespa, request_no_closeness)

    request_null_closeness_weights = SearchParameters(
        query_string=query_string,
        custom_vespa_request_body={
            "input.query(description_closeness_weight)": 0,
            "input.query(passage_closeness_weight)": 0,
        },
    )
    response_null_closeness_weights = vespa_search(
        test_vespa, request_null_closeness_weights
    )

    assert response_no_closeness == response_null_closeness_weights


@pytest.mark.vespa
@pytest.mark.parametrize(
    "concept_count_filters,expected_response_families,sort_by,sort_order",
    [
        # More than or equal to one count of concept_0_0.
        (
            [
                ConceptCountFilter(
                    concept_id="concept_0_0", count=1, operand=OperandTypeEnum(">=")
                )
            ],
            {"CCLW.family.i00000003.n0000"},
            None,
            None,
        ),
        # More than or equal to a count of 1000 for any concept.
        (
            [ConceptCountFilter(count=1000, operand=OperandTypeEnum(">="))],
            {"CCLW.family.10014.0"},
            None,
            None,
        ),
        # Exactly 101 counts of concept_1_1.
        (
            [
                ConceptCountFilter(
                    concept_id="concept_1_1", count=101, operand=OperandTypeEnum("=")
                )
            ],
            {"CCLW.family.10014.0"},
            None,
            None,
        ),
        # Exactly 101 counts of concept_1_1 and more than 1000 counts for any concept.
        (
            [
                ConceptCountFilter(
                    concept_id="concept_1_1", count=101, operand=OperandTypeEnum("=")
                ),
                ConceptCountFilter(count=1000, operand=OperandTypeEnum(">")),
            ],
            {"CCLW.family.10014.0"},
            None,
            None,
        ),
        # Any matches for concept_1_1.
        (
            [
                ConceptCountFilter(
                    concept_id="concept_1_1", count=0, operand=OperandTypeEnum(">")
                )
            ],
            {"CCLW.family.10014.0"},
            None,
            None,
        ),
        # Any documents with less than three matches for any concept.
        (
            [ConceptCountFilter(count=3, operand=OperandTypeEnum("<"))],
            {"CCLW.family.i00000003.n0000"},
            None,
            None,
        ),
        # Any documents with less than three matches for any concept,
        # sorted by concept count in descending order.
        (
            [ConceptCountFilter(count=1, operand=OperandTypeEnum(">"))],
            {"CCLW.family.i00000003.n0000", "CCLW.family.10014.0"},
            "concept_counts",
            "descending",
        ),
        # Any documents with less than three matches for any concept,
        # sorted by concept count in ascending order.
        (
            [ConceptCountFilter(count=1, operand=OperandTypeEnum(">"))],
            {"CCLW.family.i00000003.n0000", "CCLW.family.10014.0"},
            "concept_counts",
            "ascending",
        ),
        # Any documents that don't have concept_0_0 present.
        (
            [
                ConceptCountFilter(
                    concept_id="concept_0_0",
                    count=0,
                    operand=OperandTypeEnum(">"),
                    negate=True,
                )
            ],
            {"CCLW.family.4934.0", "CCLW.family.10014.0"},
            "concept_counts",
            "ascending",
        ),
    ],
)
def test_vespa_search_adaptor__concept_counts(
    test_vespa,
    concept_count_filters: list[ConceptCountFilter],
    expected_response_families: set[str],
    sort_by: Union[str, None],
    sort_order: Union[str, None],
) -> None:
    """Test that filtering for concept counts works"""
    request = SearchParameters(
        concept_count_filters=concept_count_filters,
        sort_by=sort_by,
    )
    if sort_order:
        request.sort_order = sort_order
    response = vespa_search(test_vespa, request)
    assert response.total_family_hits == len(expected_response_families)
    assert (
        set([family.id for family in response.families]) == expected_response_families
    )

    counts = []
    for family in response.families:
        for hit in family.hits:
            if hit.concept_counts:
                counts.append(max(hit.concept_counts))

    if sort_order is not None:
        if sort_order == "ascending":
            assert is_sorted(counts)[0]
        if sort_order == "descending":
            assert is_sorted(counts)[1]


def test_is_sorted() -> None:
    """Test that the is_sorted function works"""

    assert is_sorted([1, 2, 3]) == (True, False)  # Ascending
    assert is_sorted([3, 2, 1]) == (False, True)  # Descending


@pytest.mark.vespa
def test_acronym_replacement(test_vespa):
    ndc_response = vespa_search(
        test_vespa,
        SearchParameters(
            query_string="ndc",
            replace_acronyms=True,
        ),
    )

    ndc_response_no_replacement = vespa_search(
        test_vespa,
        SearchParameters(
            query_string="ndc",
            replace_acronyms=False,
        ),
    )

    assert "Nationally Determined Contribution" in str(
        ndc_response.families[0].hits[0].family_name
    )
    assert "Nationally Determined Contribution" not in str(
        ndc_response_no_replacement.families[0].hits[0].family_name
    )

    methane_ch4_response = vespa_search(
        test_vespa,
        SearchParameters(
            query_string="ch4",
            replace_acronyms=True,
        ),
    )
    methane_ch4_response_no_replacement = vespa_search(
        test_vespa,
        SearchParameters(
            query_string="ch4",
            replace_acronyms=False,
        ),
    )

    assert isinstance(methane_ch4_response.families[0].hits[0], Passage)
    assert "methane" in methane_ch4_response.families[0].hits[0].text_block.lower()

    assert (
        not (
            isinstance(methane_ch4_response_no_replacement.families[0].hits[0], Passage)
        )
        or "methane"
        not in methane_ch4_response_no_replacement.families[0]
        .hits[0]
        .text_block.lower()
    )


@pytest.mark.vespa
def test_acronym_replacement_exact_match_search(test_vespa, caplog):
    """Acronym replacement should not run on exact match searches"""

    # There are no exact matches for the query "ndc" in the test data
    ndc_response = vespa_search(
        test_vespa,
        SearchParameters(
            query_string="ndc",
            exact_match=True,
            replace_acronyms=True,
        ),
    )

    assert "Exact match and replace_acronyms are incompatible." in caplog.text
    assert len(ndc_response.families) == 0
