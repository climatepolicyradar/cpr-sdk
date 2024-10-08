from typing import Optional

import pytest
from pydantic_core import ValidationError

from cpr_sdk.models.search import SearchParameters


@pytest.mark.parametrize(
    "params,expect_error,error_message",
    [
        (
            {"query_string": "the", "exact_match": False, "all_results": True},
            False,
            None,
        ),
        ({"query_string": "", "exact_match": False, "all_results": True}, False, None),
        (
            {
                "query_string": "",
                "exact_match": False,
                "all_results": True,
                "concept_filters": [{"name": "name", "value": "environment"}],
            },
            True,
            "Cannot set concept_filters when browse_mode is set.",
        ),
    ],
)
@pytest.mark.vespa
def test_vespa_search_parameters(
    params: dict, expect_error: bool, error_message: Optional[str]
) -> None:
    """Test that we can correctly instantiate the SearchParameters object."""
    if expect_error:
        with pytest.raises(
            ValidationError,
            match=error_message,
        ):
            SearchParameters.model_validate(params)
    else:
        SearchParameters.model_validate(params)
