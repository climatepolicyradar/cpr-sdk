import pytest

from cpr_sdk.search_adaptors import VespaSearchAdapter
from cpr_sdk.models.search import SearchParameters, SearchResponse, Passage, Family

from cpr_sdk.search_intention_testing.models import (
    TestCase,
    TopFamiliesTestCase,
    FieldCharacteristicsTestCase,
    FamiliesInTopKTestCase,
    SearchComparisonTestCase,
    PassagesTestCase,
)


def get_search_response(
    test_case: TestCase,
    limit: int,
    instance_url: str,
    **kwargs,
) -> SearchResponse[Family]:
    """Get a response from a Vespa instance given a test case and a limit."""
    search_adapter = VespaSearchAdapter(instance_url)

    search_parameters = SearchParameters(
        query_string=test_case.search_terms,
        exact_match=test_case.exact_match,
        document_ids=[test_case.document_id] if test_case.document_id else None,
        filters=test_case.get_search_filters(),
        limit=limit,
        **kwargs,
    )

    return search_adapter.search(search_parameters)


def do_test_top_families(
    test_case: TopFamiliesTestCase,
    instance_url: str,
):
    search_response = get_search_response(test_case, 20, instance_url)

    top_family_slugs = [
        family.hits[0].family_slug
        for family in search_response.results[: len(test_case.expected_family_slugs)]
    ]

    if test_case.strict_order:
        assert top_family_slugs == test_case.expected_family_slugs
    else:
        assert set(top_family_slugs) == set(test_case.expected_family_slugs)


def do_test_families_in_top_k(
    test_case: FamiliesInTopKTestCase,
    instance_url: str,
):
    search_response = get_search_response(test_case, test_case.k, instance_url)

    family_slugs_in_response = [
        family.hits[0].family_slug for family in search_response.results
    ]

    expected_family_slugs_not_in_response = set(
        test_case.expected_family_slugs
    ).difference(set(family_slugs_in_response))

    assert (
        not expected_family_slugs_not_in_response
    ), f"Expected family slugs not found in top {test_case.k} results: {expected_family_slugs_not_in_response}"

    if test_case.forbidden_family_slugs is not None:
        forbidden_slugs_in_response = set(
            test_case.forbidden_family_slugs
        ).intersection(set(family_slugs_in_response))

        assert (
            not forbidden_slugs_in_response
        ), f"Forbidden family slugs found in top {test_case.k} results: {forbidden_slugs_in_response}"


def do_test_field_characteristics(
    test_case: FieldCharacteristicsTestCase,
    instance_url: str,
):
    search_response = get_search_response(test_case, test_case.k, instance_url)

    match test_case.test_field:
        case "family_name":
            field_values = [
                family.hits[0].family_name for family in search_response.results
            ]
        case "text_block_text":
            field_values = [
                hit.text_block
                for family in search_response.results
                for hit in family.hits
                if isinstance(hit, Passage)
            ]  # type: ignore
        case "geographies":
            field_values = [
                family.hits[0].family_geographies for family in search_response.results
            ]
        case _:
            raise ValueError(f"Unknown test field: {test_case.test_field}")

    failing_values = [
        value for value in field_values if not test_case.characteristics_test(value)
    ]

    match test_case.all_or_any:
        case "all":
            assert (
                not failing_values
            ), f"Values of {test_case.test_field} found failing test: {failing_values}"
        case "any":
            passing_values = [
                value for value in field_values if test_case.characteristics_test(value)
            ]
            assert (
                passing_values
            ), f"No values of {test_case.test_field} found passing test. Failing values: {failing_values}."


def do_test_search_comparison(
    test_case: SearchComparisonTestCase,
    instance_url: str,
):
    search_response_a = get_search_response(test_case, test_case.k, instance_url)

    test_case_b = test_case.model_copy(
        update={"search_terms": test_case.search_terms_to_compare}
    )
    search_response_b = get_search_response(test_case_b, test_case.k, instance_url)

    unit_of_comparison = None

    if test_case.document_id:
        results_a = [
            hit.text_block
            for family in search_response_a.results
            for hit in family.hits
            if isinstance(hit, Passage)
        ]
        results_b = [
            hit.text_block
            for family in search_response_b.results
            for hit in family.hits
            if isinstance(hit, Passage)
        ]
        unit_of_comparison = "text blocks"
    else:
        results_a = [family.hits[0].family_slug for family in search_response_a.results]
        results_b = [family.hits[0].family_slug for family in search_response_b.results]
        unit_of_comparison = "families"

    if test_case.strict_order:
        differences = [
            (idx, result_a, result_b)
            for idx, (result_a, result_b) in enumerate(zip(results_a, results_b))
            if result_a != result_b
        ]

        overlap_proportion = 1 - (
            len(differences) / max(len(results_a), len(results_b))
        )

        assert (
            overlap_proportion >= test_case.minimum_families_overlap
        ), f"Strict overlap between {unit_of_comparison} is less than expected ({overlap_proportion}). Differences: {differences}"
    else:
        if unit_of_comparison == "text blocks":
            # text blocks aren't unique, so we can't use set intersection
            overlap = len([block for block in results_a if block in results_b]) / max(
                len(results_a), len(results_b)
            )
            differences = [block for block in results_a if block not in results_b] + [
                block for block in results_b if block not in results_a
            ]

        else:
            overlap = len(set(results_a).intersection(set(results_b))) / test_case.k
            differences = set(results_a).symmetric_difference(set(results_b))

        assert (
            overlap >= test_case.minimum_families_overlap
        ), f"Overlap between {unit_of_comparison} is less than expected: {overlap} < {test_case.minimum_families_overlap}. Differences: {differences}"


def do_test_passage_thresholds(
    test_case: PassagesTestCase,
    instance_url: str,
):
    search_response = get_search_response(
        test_case=test_case,
        limit=100,
        max_hits_per_family=500,
        instance_url=instance_url,
    )

    if search_response.total_result_hits != 1:
        pytest.fail(
            f"Unexpected search response, documents: {search_response.total_result_hits}"
        )

    passages = [
        hit.text_block
        for family in search_response.results
        for hit in family.hits
        if isinstance(hit, Passage)
    ]

    missing_passages = []
    for passage in test_case.expected_passages:
        if passage not in passages:
            missing_passages.append(passage)

    forbidden_passages = []
    for passage in test_case.forbidden_passages:
        if passage in passages:
            forbidden_passages.append(passage)

    mismatch = len(missing_passages) + len(forbidden_passages)

    change = ""
    if missing_passages and forbidden_passages:
        change = "OVERLAP"
    if missing_passages:
        change = "RAISE"
    if forbidden_passages:
        change = "LOWER"

    missing_passages_str = "\n\t".join(missing_passages) if missing_passages else "/"
    forbidden_passages_str = (
        "\n\t".join(forbidden_passages) if forbidden_passages else "/"
    )
    assert not mismatch, (
        f"\nThreshold issue: {change}"
        f"\n{mismatch} passages don't match thresholds for {test_case.document_id}."
        f"\nPassages not found in search response: \n\t{missing_passages_str}"
        f"\nPassages that should not be found in search response: \n\t{forbidden_passages_str}."
    )
