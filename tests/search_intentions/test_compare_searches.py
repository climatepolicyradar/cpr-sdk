import pytest

from cpr_sdk.config import VESPA_URL
from cpr_sdk.search_intention_testing.models import SearchComparisonTestCase
from cpr_sdk.search_intention_testing.executors import do_test_search_comparison


test_cases = [
    SearchComparisonTestCase(
        search_terms="obligation to provide renewable fuels 2005",
        search_terms_to_compare="obligation to provide renewable fuel 2005",
        description="Searches for single vs duplicate terms in a relatively long query should return the same top few families",
        k=5,
        minimum_families_overlap=1.0,
        strict_order=False,
        known_failure=False,
    ),
    SearchComparisonTestCase(
        search_terms="solar power",
        search_terms_to_compare="solar powered",
        description="Compare single vs duplicated search terms in a single document.",
        # slug: hungary-s-recovery-and-resilience-plan_afb9
        document_id="CCLW.executive.10502.5402",
        k=20,
        minimum_families_overlap=0.8,
        strict_order=False,
        known_failure=False,
    ),
    SearchComparisonTestCase(
        search_terms="citizen assembly",
        search_terms_to_compare="citizens assembly",
        description="Compare single vs duplicated search terms in a single document.",
        # slug: hungary-s-recovery-and-resilience-plan_afb9
        document_id="CCLW.executive.10502.5402",
        k=20,
        minimum_families_overlap=0.8,
        strict_order=False,
        known_failure=False,
    ),
]


@pytest.mark.search_intention
@pytest.mark.parametrize("test_case", [test_case.param for test_case in test_cases])
def test_top_families(test_case: SearchComparisonTestCase):
    return do_test_search_comparison(test_case, VESPA_URL)
