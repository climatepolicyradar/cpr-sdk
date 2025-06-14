import pytest
from vespa.exceptions import VespaError

from cpr_sdk.models.search import (
    ConceptCountFilter,
    Filters,
    OperandTypeEnum,
    SearchParameters,
    sort_fields,
    sort_orders,
)
from cpr_sdk.vespa import VespaErrorDetails
from cpr_sdk.yql_builder import YQLBuilder


def test_whether_document_only_search_ignores_passages_in_yql():
    params = SearchParameters(
        all_results=True,
        documents_only=True,
    )
    yql = YQLBuilder(params).to_str()
    assert "family_document" in yql
    assert "document_passage" not in yql


def test_whether_single_filter_values_and_lists_of_filter_values_appear_in_yql():
    filters = {
        "family_geographies": ["SWE", "USA"],
        "family_geography": ["SWE"],
        "family_category": ["Executive"],
        "document_languages": ["English", "Swedish"],
        "family_source": ["CCLW"],
    }
    params = SearchParameters(
        query_string="test",
        filters=Filters(**filters),
    )
    yql = YQLBuilder(params).to_str()
    assert isinstance(params.filters, Filters)

    for key, values in filters.items():
        for value in values:
            assert key in yql
            assert value in yql


@pytest.mark.parametrize(
    "year_range, expected_include, expected_exclude",
    [
        ((2000, 2020), [">= 2000", "<= 2020"], []),
        ((2000, None), [">= 2000"], ["<="]),
        ((None, 2020), ["<= 2020"], [">="]),
    ],
)
def test_whether_year_ranges_appear_in_yql(
    year_range, expected_include, expected_exclude
):
    params = SearchParameters(query_string="test", year_range=year_range)
    yql = YQLBuilder(params).to_str()
    for include in expected_include:
        assert include in yql
    for exclude in expected_exclude:
        assert exclude not in yql


@pytest.mark.parametrize("sort_by", sort_fields.keys())
@pytest.mark.parametrize("sort_order", sort_orders.keys())
def test_sorting_appears_in_yql(sort_by, sort_order):
    params = SearchParameters(
        query_string="test", sort_by=sort_by, sort_order=sort_order
    )
    assert "order" in YQLBuilder(params).to_str()


def test_sorting_does_not_appear_in_yql():
    params = SearchParameters(query_string="test", sort_order="ascending")
    assert "order" not in YQLBuilder(params).to_str()
    params = SearchParameters(query_string="test")
    assert "order" not in YQLBuilder(params).to_str()


def test_vespa_error_details():
    # With invalid query parameter code
    err_object = [
        {
            "code": 4,
            "summary": "test_summary",
            "message": "test_message",
            "stackTrace": None,
        }
    ]
    err = VespaError(err_object)
    details = VespaErrorDetails(err)

    assert details.code == err_object[0]["code"]
    assert details.summary == err_object[0]["summary"]
    assert details.message == err_object[0]["message"]
    assert details.is_invalid_query_parameter

    # With other code
    err_object = [{"code": 1}]
    err = VespaError(err_object)
    details = VespaErrorDetails(err)
    assert not details.is_invalid_query_parameter


def test_filter_profiles_return_different_queries():
    exact_yql = YQLBuilder(
        params=SearchParameters(
            query_string="test", year_range=(2000, 2023), exact_match=True
        ),
        sensitive=False,
    ).to_str()
    assert "stem: false" in exact_yql
    assert "nearestNeighbor" not in exact_yql

    hybrid_yql = YQLBuilder(
        params=SearchParameters(
            query_string="test", year_range=(2000, 2023), exact_match=False
        ),
        sensitive=False,
    ).to_str()
    assert "nearestNeighbor" in hybrid_yql

    sensitive_yql = YQLBuilder(
        params=SearchParameters(
            query_string="test", year_range=(2000, 2023), exact_match=False
        ),
        sensitive=True,
    ).to_str()
    assert "nearestNeighbor" not in sensitive_yql

    all_yql = YQLBuilder(
        params=SearchParameters(
            query_string="test query string", year_range=(2000, 2024), all_results=True
        )
    ).to_str()
    assert "true" in all_yql
    assert "2024" in all_yql
    assert "test query string" not in all_yql

    queries = [exact_yql, hybrid_yql, sensitive_yql, all_yql]
    assert len(queries) == len(set(queries))


def test_yql_builder_build_where_clause():
    query_string = "climate"
    params = SearchParameters(query_string=query_string)
    where_clause = YQLBuilder(params).build_where_clause()
    # raw user input should NOT be in the where clause
    # We send this in the body so its cleaned by vespa
    assert query_string not in where_clause

    params = SearchParameters(
        query_string="climate", filters={"family_geography": ["SWE"]}
    )
    where_clause = YQLBuilder(params).build_where_clause()
    assert "SWE" in where_clause
    assert "family_geography" in where_clause

    params = SearchParameters(
        query_string="test",
        family_ids=("CCLW.family.i00000003.n0000", "CCLW.family.10014.0"),
    )
    where_clause = YQLBuilder(params).build_where_clause()
    assert "CCLW.family.i00000003.n0000" in where_clause
    assert "CCLW.family.10014.0" in where_clause

    params = SearchParameters(
        query_string="test",
        document_ids=("CCLW.document.i00000004.n0000", "CCLW.executive.10014.4470"),
    )
    where_clause = YQLBuilder(params).build_where_clause()
    assert "CCLW.document.i00000004.n0000" in where_clause
    assert "CCLW.executive.10014.4470" in where_clause

    params = SearchParameters(query_string="climate", year_range=(2000, None))
    where_clause = YQLBuilder(params).build_where_clause()
    assert "2000" in where_clause
    assert "family_publication_year" in where_clause

    params = SearchParameters(query_string="climate", year_range=(None, 2020))
    where_clause = YQLBuilder(params).build_where_clause()
    assert "2020" in where_clause
    assert "family_publication_year" in where_clause


def test_yql_builder_build_concept_count_filter() -> None:
    """Test that the concept count filter is built correctly"""

    concept_count_filter_clause = YQLBuilder(
        SearchParameters()
    ).build_concept_count_filter()

    assert not concept_count_filter_clause

    search_parameters = SearchParameters(
        concept_count_filters=[
            ConceptCountFilter(
                concept_id="concept_1_1", count=101, operand=OperandTypeEnum("=")
            )
        ]
    )
    concept_count_filter_clause = YQLBuilder(
        search_parameters
    ).build_concept_count_filter()
    assert concept_count_filter_clause
    assert concept_count_filter_clause.replace("  ", "").replace("\n", "") == (
        '((concept_counts contains sameElement(key contains "concept_1_1", value = 101)))'
    )


def test_distance_threshold_appears_in_yql():
    """Test whether the distance_threshold clause appears in the YQL when specified."""
    # Test with distance_threshold set
    threshold = 0.7
    params_with_threshold = SearchParameters(
        query_string="test", distance_threshold=threshold
    )
    yql_with_threshold = YQLBuilder(params_with_threshold).to_str()
    expected_substring = f'"distanceThreshold": {threshold}'
    assert expected_substring in yql_with_threshold

    # Test with distance_threshold (default is a Float)
    params_without_threshold = SearchParameters(query_string="test")
    yql_without_threshold = YQLBuilder(params_without_threshold).to_str()
    assert "distanceThreshold" in yql_without_threshold


def test_by_document_title_appears_in_yql():
    """Test whether the searchable document title field appears in the YQL when specified."""
    params = SearchParameters(query_string="test", by_document_title=True)
    yql = YQLBuilder(params).to_str()
    assert "document_title_index" in yql
