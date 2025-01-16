import pytest

from cpr_sdk.config import VESPA_URL
from search_testing.models import FamiliesInTopKTestCase
from search_testing.executors import do_test_families_in_top_k


test_cases = [
    # NOTE: this maybe isn't the best example of a test case, but it's still valid
    # and here to demonstrate how this test type might be useful.
    FamiliesInTopKTestCase(
        search_terms="just transition framework",
        k=10,
        expected_family_slugs=["just-transition-framework-for-south-africa_f7e1"],
        known_failure=False,
    )
]


@pytest.mark.parametrize("test_case", [test_case.param for test_case in test_cases])
def test_top_families(test_case: FamiliesInTopKTestCase):
    return do_test_families_in_top_k(test_case, VESPA_URL)
