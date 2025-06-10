import pytest

from cpr_sdk.config import VESPA_URL
from cpr_sdk.search_intention_testing.models import PassagesTestCase
from cpr_sdk.search_intention_testing.executors import do_test_passage_thresholds

test_cases = [
    PassagesTestCase(
        document_id="CCLW.executive.8502.3203",
        search_terms="electric car",
        expected_passages=[
            "Shifting gear from Conventional Vehicles to Electric Vehicles",
            "Electricity Requirements for EV Fleet 43",
            "Types of No Pollution Electric Transport (No Emission Vehicles NEV)",
            "Battery Electric Vehicles (BEV/EV)",
            "Fuel Cell Electric Vehicles (FCEV)",
            "Types of Low Pollution Electric Transport (Low Emission Vehicles LEV)",
            "Hybrid Electric Vehicles (HEV)",
            "Plug-In Hybrid Vehicles (PHEV)",
            "Vehicle Categories.",
            "Cars",
        ],
        forbidden_passages=[
            "Scooters",
            "Vans and Trucks",
            "Buses",
        ],
        description="Passage threshold",
    ),
    PassagesTestCase(
        document_id="CCLW.document.i00003683.n0000",
        search_terms="Youth",
        expected_passages=[
            "Youth Volunteer for the Environment and Africa Youth Initiative for Change",
            "4.1 Involving Youth in Climate Change Adaptation",
        ],
        forbidden_passages=[
            "Forestry Commission, Ghana",
        ],
    ),
]


@pytest.mark.search_intention
@pytest.mark.parametrize("test_case", [test_case.param for test_case in test_cases])
def test_passage_thresholds(test_case: PassagesTestCase):
    return do_test_passage_thresholds(test_case, VESPA_URL)
