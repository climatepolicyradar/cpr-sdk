import pytest
import re

from cpr_sdk.config import VESPA_URL
from cpr_sdk.search_intention_testing.executors import do_test_field_characteristics
from cpr_sdk.search_intention_testing.models import FieldCharacteristicsTestCase


def all_words_in_string(include_words: list[str], string: str) -> bool:
    """Case-insensitive check for if all words are in a string, ignoring punctuation."""
    words = re.findall(r"\b\w+\b", string.lower())

    return all(word.lower() in words for word in include_words)


def any_words_in_string(include_words: list[str], string: str) -> bool:
    """Case-insensitive check for if any words are in a string."""
    words = re.findall(r"\b\w+\b", string.lower())

    return any(word.lower() in words for word in include_words)


test_cases = [
    FieldCharacteristicsTestCase(
        search_terms="adaptation strategy",
        test_field="family_name",
        characteristics_test=lambda x: all_words_in_string(
            ["adaptation", "strategy"], x
        ),
        description="Search for 'Adaptation Strategy' should contain at least 20 adaptation strategies first.",
        k=20,
        known_failure=False,
    ),
    FieldCharacteristicsTestCase(
        search_terms="national communication",
        test_field="family_name",
        characteristics_test=lambda x: all_words_in_string(
            ["national", "communication"], x.lower()
        ),
        description="Search for 'National Communication' should contain at least 20 national communications first.",
        k=20,
        known_failure=False,
    ),
    FieldCharacteristicsTestCase(
        search_terms="$100",
        exact_match=True,
        test_field="text_block_text",
        characteristics_test=lambda x: "$100" in x,
        description="Exact match search for $100 should always return $100.",
        k=20,
        known_failure=True,
    ),
    FieldCharacteristicsTestCase(
        search_terms="$100",
        exact_match=True,
        test_field="text_block_text",
        characteristics_test=lambda x: "$1000" not in x,
        description="Exact match search for $100 should not return $1000.",
        k=20,
        known_failure=False,
    ),
    FieldCharacteristicsTestCase(
        search_terms="nationally determined contribution",
        test_field="text_block_text",
        characteristics_test=lambda x: "NDC" in x
        and not all_words_in_string(["nationally", "determined", "contribution"], x),
        description="Acronyms: search for nationally determined contribution should return NDC.",
        k=100,
        all_or_any="any",
        known_failure=False,
    ),
    FieldCharacteristicsTestCase(
        search_terms="enviornment",
        document_id="CCLW.executive.1317.2153",
        test_field="text_block_text",
        characteristics_test=lambda x: all_words_in_string(["environment"], x),
        description="Search for mispelled text in single document (enviornment).",
        k=20,
        all_or_any="any",
        known_failure=True,
    ),
    FieldCharacteristicsTestCase(
        search_terms="fiji climate change",
        test_field="geographies",
        characteristics_test=lambda x: x in [["FJI"], ["XAA"]],
        description="Search for country name should return documents from country.",
        k=10,
        all_or_any="all",
        known_failure=False,
    ),
    FieldCharacteristicsTestCase(
        search_terms='"national strategy for climate change 2050"',
        test_field="text_block_text",
        characteristics_test=lambda x: "national strategy for climate change 2050"
        in x.lower(),
        description="Search in quotes should perform an exact match search.",
        k=100,
        all_or_any="all",
        known_failure=True,
    ),
    FieldCharacteristicsTestCase(
        search_terms="reactors feasibility",
        test_field="text_block_text",
        exact_match=True,
        characteristics_test=(
            lambda x: not (
                "reactors. Feasibility" in x and "reactors feasibility" not in x.lower()
            )
        ),
        description="Exact match search should not ignore full stops.",
        document_id="UNFCCC.non-party.1196.0",
        k=100,
        all_or_any="all",
        known_failure=True,
    ),
    FieldCharacteristicsTestCase(
        search_terms="adaptation options",
        test_field="text_block_text",
        exact_match=True,
        characteristics_test=(
            lambda x: not (
                "adaptation option" in x.lower()
                and "adaptation options" not in x.lower()
            )
        ),
        description="Exact match search should not perform stemming.",
        document_id="UNFCCC.non-party.1196.0",
        k=100,
        all_or_any="all",
        known_failure=False,
    ),
]


@pytest.mark.search_intention
@pytest.mark.parametrize("test_case", [test_case.param for test_case in test_cases])
def test_top_families(test_case: FieldCharacteristicsTestCase):
    return do_test_field_characteristics(test_case, VESPA_URL)
