import pytest

from src.config import VESPA_URL
from src.search_testing.models import TopFamiliesTestCase
from src.search_testing.executors import do_test_top_families

test_cases = [
    TopFamiliesTestCase(
        search_terms="Directive (EU) 2022/2464 of the European Parliament and of the Council of 14 December 2022 amending Regulation (EU) No 537/2014, Directive 2004/109/EC, Directive 2006/43/EC and Directive 2013/34/EU, as regards corporate sustainability reporting (Corporate Sustainability Reporting Directive or CSRD)",
        expected_family_slugs=[
            "directive-eu-2022-2464-of-the-european-parliament-and-of-the-council-of-14-december-2022-amending-regulation-eu-no-537-2014-directive-2004-109-ec-directive-2006-43-ec-and-directive-2013-34-eu-as-regards-corporate-sustainability-reporting-corporate-sustainability-reporting-directive-or-csrd_1ee9"
        ],
        description="Searching for a family title should return the correct family, where the title has brackets.",
        known_failure=False,
    ),
    TopFamiliesTestCase(
        search_terms="obligation to provide renewable fuels 2005",
        expected_family_slugs=[
            "act-2005-1248-on-the-obligation-to-provide-renewable-fuels_8e02"
        ],
        description="Searching for a family title where the words are in a different order.",
        known_failure=False,
    ),
    TopFamiliesTestCase(
        search_terms="UK Climate Change Act",
        expected_family_slugs=["climate-change-act-2008_47b4"],
        description="Searching for title + geography should return the correct family if geography is not in the family title. In this instance the family title is 'Climate Change Act 2008'",
        known_failure=True,
    ),
    TopFamiliesTestCase(
        search_terms="egypt national climate change strategy",
        expected_family_slugs=["egypt-national-climate-change-strategy-nccs-2050_d3b1"],
        description="Searching for the family title should return the correct family.",
    ),
    TopFamiliesTestCase(
        search_terms="fca rules of tcfd",
        exact_match=True,
        filters={"geographies": ["GBR"]},
        expected_family_slugs=["financial-conduct-authority-rules-on-tcfd_ae89"],
        description="Acronyms in family titles",
        known_failure=True,
    ),
    TopFamiliesTestCase(
        search_terms="power up britain",
        expected_family_slugs=["powering-up-britain-overview_241c"],
        filters={"geographies": ["GBR"]},
        description="Stemmed words in family titles",
    ),
]


@pytest.mark.parametrize("test_case", [test_case.param for test_case in test_cases])
def test_top_families(test_case: TopFamiliesTestCase):
    return do_test_top_families(test_case, VESPA_URL)
