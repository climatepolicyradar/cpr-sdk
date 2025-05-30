import re
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from cpr_sdk.models.search import Filters, SearchParameters, sort_fields, sort_orders
from cpr_sdk.vespa import build_vespa_request_body


@patch(
    "cpr_sdk.vespa.SENSITIVE_QUERY_TERMS",
    {re.compile(r"\b" + re.escape("sensitive") + r"\b")},
)
@pytest.mark.parametrize(
    "expected_rank_profile, params",
    [
        ("hybrid", SearchParameters(query_string="test")),
        ("exact_not_stemmed", SearchParameters(query_string="test", exact_match=True)),
        ("hybrid_no_closeness", SearchParameters(query_string="sensitive")),
        (
            "bm25_document_title",
            SearchParameters(query_string="test", by_document_title=True),
        ),
    ],
)
def test_build_vespa_request_body(expected_rank_profile, params):
    body = build_vespa_request_body(parameters=params)
    assert body["ranking.profile"] == expected_rank_profile
    for key, value in body.items():
        assert (
            not isinstance(value, str) or len(value) > 0
        ), f"Search parameters: {params} has an empty value for {key}: {value}"


def test_build_vespa_request_body__all():
    params = SearchParameters(query_string="", all_results=True)
    body = build_vespa_request_body(parameters=params)

    assert not body.get("ranking.profile")


def test_whether_an_empty_query_string_does_all_result_search():
    params = SearchParameters(query_string="")
    assert params.all_results

    # This rule does not apply to `all_result` requests:
    try:
        SearchParameters(query_string="", all_results=True)
    except Exception as e:
        pytest.fail(f"{e.__class__.__name__}: {e}")


def test_whether_combining_all_results_and_exact_match_raises_error():
    q = "Search"
    with pytest.raises(ValidationError) as excinfo:
        SearchParameters(query_string=q, exact_match=True, all_results=True)
    assert "`exact_match` and `all_results`" in str(excinfo.value)

    # They should be fine independently:
    try:
        SearchParameters(query_string=q, all_results=True)
        SearchParameters(query_string=q, exact_match=True)
    except Exception as e:
        pytest.fail(f"{e.__class__.__name__}: {e}")


def test_max_hit_aliases_work():
    max_hits_params = SearchParameters(max_hits_per_family=1)
    max_passages_params = SearchParameters(max_passages_per_doc=1)
    assert max_hits_params == max_passages_params


def test_sort_by_aliases_work():
    by_params = SearchParameters(sort_by="name")
    field_params = SearchParameters(sort_field="name")
    assert by_params == field_params


@pytest.mark.parametrize("year_range", [(2000, 2020), (2000, None), (None, 2020)])
def test_whether_valid_year_ranges_are_accepted(year_range):
    params = SearchParameters(query_string="test", year_range=year_range)
    assert isinstance(params, SearchParameters)


def test_whether_an_invalid_year_range_ranges_raises_a_validation_error():
    with pytest.raises(ValidationError) as excinfo:
        SearchParameters(query_string="test", year_range=(2023, 2000))
    assert (
        "The first supplied year must be less than or equal to the second supplied year"
        in str(excinfo.value)
    )


def test_whether_valid_family_ids_are_accepted():
    params = SearchParameters(
        query_string="test",
        family_ids=("CCLW.family.i00000003.n0000", "CCLW.family.10014.0"),
    )
    assert isinstance(params, SearchParameters)


@pytest.mark.parametrize(
    "bad_id",
    [
        "invalid_fam_id",
        "Not.Quite.It",
        "CCLW.family.i00000003.!!!!!!",
        "UNFCCC.family.i00000003",
        "UNFCCC.family.i00000003.n000.11",
    ],
)
def test_whether_an_invalid_family_id_raises_a_validation_error(bad_id):
    with pytest.raises(ValidationError) as excinfo:
        SearchParameters(
            query_string="test",
            family_ids=("CCLW.family.i00000003.n0000", bad_id),
        )
    assert f"id seems invalid: {bad_id}" in str(
        excinfo.value
    ), f"expected failure on {bad_id}"


def test_whether_valid_document_ids_are_accepted():
    params = SearchParameters(
        query_string="test",
        document_ids=("CCLW.document.i00000004.n0000", "CCLW.executive.10014.4470"),
    )
    assert isinstance(params, SearchParameters)


@pytest.mark.parametrize(
    "bad_id",
    [
        "invalid_fam_id",
        "Not.Quite.It",
        "CCLW.doc.i00000003.!!!!!!",
        "UNFCCC.doc.i00000003",
    ],
)
def test_whether_an_invalid_document_id_raises_a_validation_error(bad_id):
    with pytest.raises(ValidationError) as excinfo:
        SearchParameters(
            query_string="test",
            document_ids=(bad_id, "CCLW.document.i00000004.n0000"),
        )
    assert f"id seems invalid: {bad_id}" in str(
        excinfo.value
    ), f"expected failure on {bad_id}"


@pytest.mark.parametrize("field", sort_fields.keys())
def test_whether_valid_sort_fields_are_accepted(field):
    params = SearchParameters(query_string="test", sort_by=field)
    assert isinstance(params, SearchParameters)


def test_whether_an_invalid_sort_field_raises_a_validation_error():
    with pytest.raises(ValidationError) as excinfo:
        SearchParameters(query_string="test", sort_by="invalid_field")
    assert "sort_by must be one of" in str(excinfo.value)


@pytest.mark.parametrize("order", sort_orders.keys())
def test_whether_valid_sort_orders_are_accepted(order):
    params = SearchParameters(query_string="test", sort_order=order)
    assert isinstance(params, SearchParameters)


def test_whether_an_invalid_sort_order_raises_a_validation_error():
    with pytest.raises(ValidationError) as excinfo:
        SearchParameters(query_string="test", sort_order="invalid_order")
    assert "sort_order must be one of" in str(excinfo.value)


@pytest.mark.parametrize("sort_by", sort_fields.keys())
@pytest.mark.parametrize("sort_order", sort_orders.keys())
def test_computed_vespa_sort_fields(sort_by, sort_order):
    params = SearchParameters(
        query_string="test", sort_by=sort_by, sort_order=sort_order
    )
    assert params.vespa_sort_by and params.vespa_sort_order


@pytest.mark.parametrize(
    "field",
    [
        "family_geographies",
        "family_geography",
        "family_category",
        "document_languages",
        "family_source",
    ],
)
def test_whether_valid_filter_fields_are_accepted(field):
    filters = Filters(**{field: ["value"]})
    params = SearchParameters(query_string="test", filters=filters)
    assert isinstance(params, SearchParameters)


def test_whether_an_invalid_filter_fields_raises_a_valueerror():
    with pytest.raises(ValidationError) as excinfo:
        SearchParameters(
            query_string="test",
            filters=Filters(**{"invalid_field": ["value"]}),
        )
    assert "Extra inputs are not permitted" in str(excinfo.value)


@pytest.mark.parametrize(
    "input_filters,expected",
    (
        (['remove "double quotes"'], ["remove double quotes"]),
        (["keep 'single quotes'"], ["keep 'single quotes'"]),
        (["tab\t\tinput"], ["tab input"]),
        (["new \n \n \n lines"], ["new lines"]),
        (["back \\\\\\ slashes"], ["back slashes"]),
        (
            [' " or true or \t \n family_name contains " '],
            ["or true or family_name contains"],
        ),
    ),
)
def test_whether_an_invalid_filter_fields_value_fixes_it_silently(
    input_filters, expected
):
    params = SearchParameters(
        query_string="test",
        filters=Filters(**{"family_source": input_filters}),
    )
    assert params.filters.family_source == expected


@pytest.mark.parametrize(
    "tokens, error",
    (
        (["", None], ValidationError),
        ([123], ValidationError),
        (["123"], ValidationError),
        (["!@$"], ValidationError),
        (["lower"], ValidationError),
        (["", "lower"], ValidationError),
    ),
)
def test_continuation_tokens__bad(tokens, error):
    with pytest.raises(error):
        SearchParameters(query_string="test", continuation_tokens=tokens)


@pytest.mark.parametrize(
    "tokens",
    (
        None,
        ["ABCCCABCABCABC"],
        ["", "ABCCC"],
        ["", "ABCCC", "ABBBDDDC"],
        ["ABCC", "ABCCCCCC"],
        ["ABCC", "ABCCCCCC", "ABBBBBDDC"],
    ),
)
def test_continuation_tokens__good(tokens):
    try:
        SearchParameters(query_string="test", continuation_tokens=tokens)
    except Exception as e:
        pytest.fail(f"{e.__class__.__name__}: {e}")
