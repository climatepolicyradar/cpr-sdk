from typing import Optional, Any, Callable, Sequence, Literal

import pytest
from pydantic import BaseModel, Field, model_validator

from cpr_sdk.models.search import filter_fields, Filters


class TestCase(BaseModel):
    """A model to test the search functionality. Used by the `executors` module."""

    id: Optional[str] = Field(
        description="A unique identifier for the test case", default=None
    )
    search_terms: str = Field(description="The terms which will be searched for.")
    filters: Optional[dict[str, Sequence[str]]] = Field(
        description=("Filters to be applied to the search terms."), default=None
    )
    document_id: Optional[str] = Field(
        description=("An optional Document ID to filter the search on."), default=None
    )
    exact_match: bool = Field(
        description=("Whether to run an exact match search."),
        default=False,
    )
    description: Optional[str] = Field(
        description=(
            "An optional description of the test case. Can be used to explain "
            "what the test intention is, any assumptions made, links to "
            "discussions which motivated the test, etc."
        ),
        default=None,
    )
    known_failure: bool = Field(
        description=(
            "If True, the test is expected to fail. If False, the test is "
            "expected to pass. NOTE: this should be set to False for every test before starting to evaluate search. Setting this to True is a way of zooming in on failures to fix in a round of fixing. "
        ),
        default=False,
    )

    def __init__(self, **data):
        if "id" not in data or data["id"] is None:
            data["id"] = "__".join(
                [
                    str(self),
                    data.get("description", ""),
                    data["search_terms"],
                ]
            )
        super().__init__(**data)

    @property
    def param(self):
        """Return the test case as a pytest parameter"""
        return pytest.param(
            self,
            id=self.id,
            marks=[pytest.mark.xfail(strict=True)] if self.known_failure else [],
        )

    @model_validator(mode="after")
    def check_filter_fields(self):
        """Check that the filter fields are valid."""
        if self.filters is not None:
            supplied_filter_fields = set(self.filters.keys())
            if not supplied_filter_fields.issubset(set(filter_fields)):
                invalid_filter_fields = supplied_filter_fields - set(filter_fields)
                raise ValueError(
                    f"Filter fields {invalid_filter_fields} are not valid."
                )
        return self

    def get_search_filters(self) -> Optional[Filters]:
        """Return the search filters."""
        if self.filters is None:
            return None
        filters_mapped_names = {
            filter_fields[field]: values for field, values in self.filters.items()
        }
        return Filters.model_validate(filters_mapped_names)


class TopFamiliesTestCase(TestCase):
    """Dictates which should be the first (or top) families for a given search."""

    expected_family_slugs: list[str] = Field(
        description="The expected family slugs for the top results."
    )
    strict_order: bool = Field(
        description=(
            "Whether the expected family slugs should be in the exact order "
            "specified."
        ),
        default=False,
    )

    def __str__(self) -> str:  # noqa: D105
        return "TopFamiliesTestCase"

    @model_validator(mode="after")
    def check_expected_family_slugs_unique(self):
        """Check that the expected family slugs are unique."""
        if len(self.expected_family_slugs) != len(set(self.expected_family_slugs)):
            raise ValueError("expected_family_slugs must be unique")
        return self


class FieldCharacteristicsTestCase(TestCase):
    """Dictates the characteristics which any or all of the top k results should have for a given search."""

    test_field: Literal["family_name", "text_block_text", "geographies"] = Field(
        description="The field to test for the expected characteristics."
    )
    characteristics_test: Callable[[Any], bool] = Field(
        description="A function which returns True if the expected characteristics for the field value are met, and False otherwise."
    )
    k: int = Field(
        description="The number of families to check for the expected characteristics.",
    )
    all_or_any: Literal["all", "any"] = Field(
        description="Whether all or any of the words in the search terms should be in the field value.",
        default="all",
    )

    def __str__(self) -> str:  # noqa: D105
        return "CharacteristicsTestCase"


class FamiliesInTopKTestCase(TestCase):
    """Dictates families which should be anywhere within the top k results for a given search."""

    expected_family_slugs: list[str] = Field(
        description="Family slugs which should appear in the top k results."
    )
    forbidden_family_slugs: Optional[list[str]] = Field(
        description="Family slugs which should not appear in the top k results.",
        default=None,
    )
    k: int = Field(
        description="The number of results to check for the expected family slugs. Defaults to 20: the number of results shown on the first page of the CPR tools.",
        default=20,
    )

    @model_validator(mode="after")
    def check_expected_family_slugs_unique(self):
        """Check that the expected family slugs are unique."""
        if len(self.expected_family_slugs) != len(set(self.expected_family_slugs)):
            raise ValueError("expected_family_slugs must be unique")
        return self

    @model_validator(mode="after")
    def check_forbidden_family_slugs_unique(self):
        """Check that the forbidden family slugs are unique."""
        if self.forbidden_family_slugs is not None and len(
            self.forbidden_family_slugs
        ) != len(set(self.forbidden_family_slugs)):
            raise ValueError("expected_family_slugs must be unique")
        return self

    def __str__(self) -> str:  # noqa: D105
        return "TopCharacteristicsTestCase"


class SearchComparisonTestCase(TestCase):
    """
    Compare two searches to each other. Compares the top k results.

    For a whole-database search families are compared; for a single document search text of text blocks.
    """

    search_terms_to_compare: str = Field(
        description="The terms to compare the search_terms to."
    )

    k: int = Field(
        description="The number of results to compare for the expected family slugs. Defaults to 20: the number of results shown on the first page of the CPR tools.",
        default=20,
    )

    minimum_families_overlap: float = Field(
        description="The desired proportion of the top k results which have the same family slug.",
        strict=True,
        gt=0,
        le=1,
    )

    strict_order: bool = Field(
        description=(
            "Whether the expected family slugs should be in the exact order "
            "specified."
        ),
        default=False,
    )

    @model_validator(mode="after")
    def check_comparison_terms(self):
        """Check that the comparison terms are different from the search terms."""
        if self.search_terms == self.search_terms_to_compare:
            raise ValueError(
                "search_terms and search_terms_to_compare must be different"
            )
        return self

    def __str__(self) -> str:  # noqa: D105
        return "SearchComparisonTestCase"


class PassagesTestCase(TestCase):
    """Test the passages returned by the search."""

    expected_passages: list[str] = Field(
        description="The expected passages for the search."
    )
    forbidden_passages: list[str] = Field(
        description="The passages which should not be returned by the search.",
    )
