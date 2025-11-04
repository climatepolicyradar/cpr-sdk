import re
from pydantic_core import CoreSchema, core_schema
from typing import Any, Callable, Generic, TypeVar
from datetime import datetime
from enum import Enum
from typing import Annotated, List, Literal, Optional, Sequence, TypeAlias
from functools import total_ordering

from cpr_sdk.result import Result, Error, Ok, Err
from typing_extensions import assert_never
from cpr_sdk.utils import dig
from pydantic import (
    AliasChoices,
    AnyHttpUrl,
    BaseModel,
    NonNegativeInt,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

# Value Lookup Tables
sort_orders = {
    "asc": "+",
    "desc": "-",
    "ascending": "+",
    "descending": "-",
}

sort_fields = {
    "date": "family_publication_ts",
    "title": "family_name",
    "name": "family_name",
    "concept_counts": "concept_counts.value",
}

filter_fields = {
    "geography": "family_geography",
    "geographies": "family_geographies",
    "category": "family_category",
    "language": "document_languages",
    "source": "family_source",
}

_ID_ELEMENT = r"[a-zA-Z0-9]+([-_]?[a-zA-Z0-9]+)*"
ID_PATTERN = re.compile(rf"{_ID_ELEMENT}\.{_ID_ELEMENT}\.{_ID_ELEMENT}\.{_ID_ELEMENT}")

SCHEMA_NAME_FIELD_NAME = "sddocname"

JsonDict: TypeAlias = dict[str, Any]


@total_ordering
class WikibaseId(str):
    """
    A Wikibase ID, which is a string that starts with a 'Q' followed by a number.

    Originally from the Knowledge Graph repository.
    """

    regex = r"^Q[1-9][0-9]*$"

    def __new__(cls, value):
        """Validate the Wikibase ID string and create a new instance."""
        cls._validate(value)
        return str.__new__(cls, value)

    @property
    def numeric(self) -> int:
        """The numeric value of the Wikibase ID"""
        return int(self[1:])

    def __lt__(self, other) -> bool:
        """Compare two Wikibase IDs numerically"""
        if isinstance(other, str):
            other = WikibaseId(other)
        if not isinstance(other, WikibaseId):
            return NotImplemented
        return self.numeric < other.numeric

    def __eq__(self, other) -> bool:
        """Check if two Wikibase IDs are equal"""
        if isinstance(other, str):
            other = WikibaseId(other)
        if not isinstance(other, WikibaseId):
            return NotImplemented
        return self.numeric == other.numeric

    def __hash__(self) -> int:
        """Hash a Wikibase ID consistently with string representation"""
        return hash(str(self))

    @classmethod
    def _validate(cls, __input_value: Any) -> str:
        """Validate that the Wikibase ID is in the correct format."""
        if not isinstance(__input_value, str):
            raise ValueError(f"Wikibase ID must be a string, got {type(__input_value)}")
        if not re.match(cls.regex, __input_value):
            raise ValueError(f"'{__input_value}' is not a valid Wikibase ID")
        return __input_value

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,
        handler: Callable[[Any], CoreSchema],  # type: ignore
    ) -> CoreSchema:
        """Returns a pydantic_core.CoreSchema object for Pydantic V2 compatibility."""
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.no_info_plain_validator_function(cls._validate),
        )


class OperandTypeEnum(Enum):
    """Enumeration of possible operands for yql queries"""

    GREATER_THAN = ">"
    GREATER_THAN_OR_EQUAL = ">="
    LESS_THAN = "<"
    LESS_THAN_OR_EQUAL = "<="
    EQUALS = "="


class MetadataFilter(BaseModel):
    """A filter for metadata fields"""

    name: str
    value: str


class ConceptFilter(BaseModel):
    """A filter for concept fields"""

    name: Literal["name", "id", "model", "timestamp", "parent_concept_ids_flat"]
    value: str

    @model_validator(mode="after")
    def validate_parent_concept_ids_flat(self) -> "ConceptFilter":
        """
        Validate parent_concept_ids_flat field.

        In the schema we comma separate values in the parent_concept_ids_flat field.
        This means we must ensure that the last character is a comma to avoid the
        situation below:

        E.g. querying parent_concept_ids_flat on "Q1" should only return "Q1" but you
        will also return "Q12, Q123" which is invalid.

        To get around this we query on "Q1," instead using the comma suffix to separate
        values.
        """
        if (
            self.name == "parent_concept_ids_flat"
            and self.value
            and self.value[-1] != ","
        ):
            self.value = self.value + ","
        return self


class Filters(BaseModel):
    """Filterable fields in a search request"""

    family_geography: Sequence[str] = []
    family_geographies: Sequence[str] = []
    family_category: Sequence[str] = []
    document_languages: Sequence[str] = []
    family_source: Sequence[str] = []

    model_config: ConfigDict = {
        "extra": "forbid",
    }

    @field_validator(
        "family_geographies",
        "family_geography",
        "family_category",
        "document_languages",
        "family_source",
    )
    def sanitise_filter_inputs(cls, field):
        """Remove problematic characters from filter values"""
        clean_values = []
        for keyword in field:
            keyword = keyword.replace('"', "")
            keyword = keyword.replace("\\", " ")
            keyword = " ".join(keyword.split())
            clean_values.append(keyword)
        return clean_values


class ConceptCountFilter(BaseModel):
    """
    A filter for a concept count.

    Can combine filters for concept ID and concept count to achieve logic like:
    - Documents with greater than 10 matches of concept Q123.
    - Documents with greater than 1000 matches of any concept.

    These ConceptCountFilters can be combined with an 'and' operator to create more
    complex queries like:
    - Documents with more than 10 matches for concept Q123 and more than 5 matches for
        concept Q456.

    param concept_id: If provided this is the ID of the concept to filter on. If it
        left blank then all concepts that match the query will be counted.
    param count: The number of matches to filter on.
    param operand: The operand to use for the filter.
        E.g. we want to filter for documents with more than 10 matches of concept Q123.
    param negate: Whether to negate the filter.
        E.g. we want to filter for documents that do NOT have a match for a concept.
    """

    concept_id: Optional[str] = None
    count: int
    operand: OperandTypeEnum
    negate: bool = False


class ConceptV2PassageFilter(BaseModel):
    """
    A filter for v2 concept data in passage spans.

    Examples:
    - Find passages with Wikibase ID Q10: ConceptV2PassageFilter(concept_wikibase_id="Q10")
    - Find passages with concept ID "nhhzwfva": ConceptV2PassageFilter(concept_id="nhhzwfva")
    - Find passages with classifier ID "chrtt0a7": ConceptV2PassageFilter(classifier_id="chrtt0a7")
    """

    concept_id: str | None = None
    """If provided this is the concept ID to filter on. If left blank then all concepts that match will be counted."""

    concept_wikibase_id: str | None = None
    """If provided this is the Wikibase ID (e.g. Q374) to filter on. If left blank then all concepts that match will be counted."""

    classifier_id: str | None = None
    """If provided this is the classifier ID to filter on. If left blank then all classifiers that match will be counted."""

    negate: bool = False
    """Whether to negate the filter. E.g. we want to filter for documents that do NOT have a match for a concept."""

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "ConceptV2PassageFilter":
        """Ensure at least one filter field is provided."""
        if not any([self.concept_id, self.concept_wikibase_id, self.classifier_id]):
            raise ValueError("At least one constraint must be provided")
        return self


class ConceptV2DocumentFilter(BaseModel):
    """
    A filter for v2 concept counts in documents.

    Can combine filters for concept ID, Wikibase ID, classifier ID,
    and concept count to achieve logic like:
    - Documents with greater than 10 matches of concept "nhhzwfva".
    - Documents with greater than 5 matches of concept Q374.
    - Documents with greater than 1000 matches of any concept from classifier "chrtt0a7".

    These ConceptV2DocumentFilters can be combined with an 'and' operator to create more
    complex queries like:
    - Documents with more than 10 matches for concept "nhhzwfva" and more than 5 matches for
      concept Q374.
    """

    concept_id: str | None = None
    """If provided this is the concept ID to filter on. If left blank then all concepts that match will be counted."""

    concept_wikibase_id: str | None = None
    """If provided this is the Wikibase ID (e.g. Q374) to filter on. If left blank then all concepts that match will be counted."""

    classifier_id: str | None = None
    """If provided this is the classifier ID to filter on. If left blank then all classifiers that match will be counted."""

    count: int | None = None
    """The number of matches to filter on."""

    operand: OperandTypeEnum | None = None
    """The operand to use for the filter. E.g. we want to filter for documents with more than 10 matches of concept "nhhzwfva"."""

    negate: bool = False
    """Whether to negate the filter. E.g. we want to filter for documents that do NOT have a match for a concept."""

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "ConceptV2DocumentFilter":
        """Ensure at least one filter field is provided."""
        if not any(
            [
                self.concept_id,
                self.concept_wikibase_id,
                self.classifier_id,
                all([self.count, self.operand]),
            ],
        ):
            raise ValueError("At least one constraint must be provided")
        return self


class SearchParameters(BaseModel):
    """Parameters for a search request"""

    query_string: Optional[str] = None
    """
    A string representation of the search to be performed. Omitting
    this will set all results to true.

    For example: 'Adaptation strategy'"
    """

    exact_match: bool = False
    """
    Indicate if the `query_string` should be treated as an exact match when
    the search is performed.
    """

    all_results: bool = False
    """
    Return all results rather than searching or ranking

    Filters can still be applied
    """

    documents_only: bool = False
    """Ignores passages in search when true."""

    limit: int = Field(ge=0, default=100, le=500)
    """
    Refers to the maximum number of results to return from the "
    query result.
    """

    max_hits_per_family: int = Field(
        validation_alias=AliasChoices("max_passages_per_doc", "max_hits_per_family"),
        default=10,
        ge=0,
        le=500,
    )
    """
    The maximum number of matched passages to be returned for a "
    single document.
    """

    family_ids: Optional[Sequence[str]] = None
    """Optionally limit a search to a specific set of family ids."""

    document_ids: Optional[Sequence[str]] = None
    """Optionally limit a search to a specific set of document ids."""

    filters: Optional[Filters] = None
    """Filter results to matching filter items."""

    year_range: Optional[tuple[Optional[int], Optional[int]]] = None
    """
    The years to search between. Containing exactly two values,
    which can be null or an integer representing the years to
    search between. These are inclusive and can be null. Example:
    [null, 2010] will return all documents return in or before 2010.
    """

    sort_by: Optional[str] = Field(
        validation_alias=AliasChoices("sort_field", "sort_by"), default=None
    )
    """The field to sort by can be chosen from `date` or `title`."""

    sort_order: str = "descending"
    """
    The order of the results according to the `sort_field`, can be chosen from
    ascending (use “asc”) or descending (use “desc”).
    """

    continuation_tokens: Optional[Sequence[str]] = None
    """
    Use to return the next page of results from a specific search, the next token
    can be found on the response object. It's also possible to get the next page
    of passages by including the family level continuation token first in the
    array followed by the passage level one.
    """

    corpus_type_names: Optional[Sequence[str]] = None
    """
    The name of the corpus that a document belongs to.
    """

    corpus_import_ids: Optional[Sequence[str]] = None
    """
    The import id of the corpus that a document belongs to.
    """

    metadata: Optional[Sequence[MetadataFilter]] = None
    """
    A field and item mapping to search in the metadata field of the documents.

    E.g. [{"name": "family.sector", "value": "Price"}]
    """

    concept_filters: Optional[Sequence[ConceptFilter]] = None
    """
    A field and item mapping to search in the concepts field of the document passages.
    """

    custom_vespa_request_body: Optional[dict[str, Any]] = None
    """
    Extra fields to be added to the vespa request body. Overrides any existing fields,
    so can also be used to override YQL or ranking profiles.
    """

    concept_count_filters: Optional[Sequence[ConceptCountFilter]] = None
    """
    A list of concept count filters to apply to the search.
    """

    concept_v2_passage_filters: Sequence[ConceptV2PassageFilter] | None = None
    """
    A list of v2 concept filters to apply to passages' spans.
    """

    concept_v2_document_filters: Sequence[ConceptV2DocumentFilter] | None = None
    """
    A list of v2 concept count filters to apply to documents.
    """

    replace_acronyms: bool = False
    """
    Whether to perform acronym replacement based on the 'acronyms' ruleset.
    See docs: https://docs.vespa.ai/en/query-rewriting.html#rule-bases
    """

    distance_threshold: Optional[float] = 0.24
    """
    Optional threshold for the nearest neighbor search distance. Results with a
    distance score below this threshold will be excluded. Based on the 'innerproduct'
    distance metric, lower scores are less relevant.
    """

    by_document_title: bool = False
    """
    Whether to search by document title rather than family title.
    """

    @model_validator(mode="after")
    def validate(self):
        """Validate against mutually exclusive fields"""
        if self.exact_match and self.all_results:
            raise ValueError("`exact_match` and `all_results` are mutually exclusive")
        if not self.query_string:
            self.all_results = True
        return self

    @model_validator(mode="after")
    def concept_filters_not_set_if_documents_only(self) -> "SearchParameters":
        """Ensure concept_filters are not set if browse mode (documents_only) is set."""
        if self.concept_filters is not None and self.documents_only is True:
            raise ValueError(
                "Cannot set concept_filters when only searching documents. This is as concept_filters are only applicable to passages."
            )
        return self

    @field_validator("continuation_tokens")
    def continuation_tokens_must_be_upper_strings(cls, continuation_tokens):
        """Validate continuation_tokens match the expected format"""
        if not continuation_tokens:
            return continuation_tokens

        for token in continuation_tokens:
            if token == "":
                continue
            if not token.isalpha():
                raise ValueError(f"Expected continuation tokens to be letters: {token}")
            if not token.isupper():
                raise ValueError(
                    f"Expected continuation tokens to be uppercase: {token}"
                )
        return continuation_tokens

    @field_validator("family_ids", "document_ids")
    def ids_must_fit_pattern(cls, ids):
        """
        Validate that the family and document ids are ids.

        Example ids:
            CCLW.document.i00000004.n0000
            CCLW.family.i00000003.n0000
            CCLW.executive.10014.4470
            CCLW.family.10014.0
        """
        if ids:
            for _id in ids:
                if not re.fullmatch(ID_PATTERN, _id):
                    raise ValueError(f"id seems invalid: {_id}")
        return ids

    @field_validator("year_range")
    def year_range_must_be_valid(cls, year_range):
        """Validate that the year range is valid."""
        if year_range is not None:
            if year_range[0] is not None and year_range[1] is not None:
                if year_range[0] > year_range[1]:
                    raise ValueError(
                        "The first supplied year must be less than or equal to the "
                        f"second supplied year. Received: {year_range}"
                    )
        return year_range

    @field_validator("sort_by")
    def sort_by_must_be_valid(cls, sort_by):
        """Validate that the sort field is valid."""
        if sort_by is not None:
            if sort_by not in sort_fields:
                raise ValueError(
                    f"Invalid sort field: {sort_by}. sort_by must be one of: "
                    f"{list(sort_fields.keys())}"
                )
        return sort_by

    @field_validator("sort_order")
    def sort_order_must_be_valid(cls, sort_order):
        """Validate that the sort order is valid."""
        if sort_order not in sort_orders:
            raise ValueError(
                f"Invalid sort order: {sort_order}. sort_order must be one of: "
                f"{sort_orders}"
            )
        return sort_order

    @computed_field
    def vespa_sort_by(self) -> Optional[str]:
        """Translates sort by into the format acceptable by vespa"""
        if self.sort_by:
            return sort_fields.get(self.sort_by)
        else:
            return None

    @computed_field
    def vespa_sort_order(self) -> Optional[str]:
        """Translates sort order into the format acceptable by vespa"""
        return sort_orders.get(self.sort_order)


class SearchConceptParameters(BaseModel):
    """Parameters for a concept search request"""

    id: Optional[str] = None
    """
    The ID to search for in concepts.
    For example: 'y28e4s6n'
    """

    wikibase_id: Optional[str] = None
    """
    The Wikibase ID to search for in concepts.
    For example: 'Q880'
    """

    wikibase_revision: Optional[int] = None
    """
    The Wikibase revision to search for in concepts.
    For example: 2200
    """

    preferred_label: Optional[str] = None
    """
    The preferred label to search for in concepts.
    For example: 'climate change' or 'renewable energy'
    """

    limit: int = Field(ge=0, default=100, le=500)
    """
    Refers to the maximum number of results to return from the
    query result.
    """

    continuation_tokens: Optional[Sequence[str]] = None
    """
    Use to return the next page of results from a specific search, the next token
    can be found on the response object.
    """


class SearchClassifiersProfileParameters(BaseModel):
    """Parameters for a classifiers profile search request"""

    id: Optional[str] = None
    """
    The ID to search for in classifiers profiles.
    For example: 'j2ssznnr'
    """

    name: Optional[str] = None
    """
    The name to search for in classifiers profiles.
    For example: 'primary', 'experimental', 'retired'
    """

    limit: int = Field(ge=0, default=100, le=500)
    """
    Refers to the maximum number of results to return from the
    query result.
    """

    continuation_tokens: Optional[Sequence[str]] = None
    """
    Use to return the next page of results from a specific search, the next token
    can be found on the response object.
    """

    @field_validator("continuation_tokens")
    def continuation_tokens_must_be_upper_strings(cls, continuation_tokens):
        """Validate continuation_tokens match the expected format"""
        if not continuation_tokens:
            return continuation_tokens

        for token in continuation_tokens:
            if token == "":
                continue
            if not token.isalpha():
                raise ValueError(f"Expected continuation tokens to be letters: {token}")
            if not token.isupper():
                raise ValueError(
                    f"Expected continuation tokens to be uppercase: {token}"
                )
        return continuation_tokens


class Hit(BaseModel):
    """Common model for all search result hits."""

    family_name: Optional[str] = None
    family_description: Optional[str] = None
    family_source: Optional[str] = None
    family_import_id: Optional[str] = None
    family_slug: Optional[str] = None
    family_category: Optional[str] = None
    family_publication_ts: Optional[datetime] = None
    family_geography: Optional[str] = None
    family_geographies: Optional[List[str]] = None
    document_import_id: Optional[str] = None
    document_slug: Optional[str] = None
    document_languages: Optional[List[str]] = None
    document_content_type: Optional[str] = None
    document_cdn_object: Optional[str] = None
    document_source_url: Optional[str] = None
    document_title: Optional[str] = None
    corpus_type_name: Optional[str] = None
    corpus_import_id: Optional[str] = None
    metadata: Optional[Sequence[dict[str, str]]] = None
    concepts: Optional[Sequence["Passage.Concept"]] = None
    relevance: Optional[float] = None
    rank_features: Optional[dict[str, float]] = None
    concept_counts: Optional[dict[str, int]] = None

    @classmethod
    def from_vespa_response(cls, response_hit: JsonDict) -> "Hit":
        """
        Create a Hit from a Vespa response hit.

        :param dict response_hit: part of a json response from Vespa
        :raises ValueError: if the response type is unknown
        :return Hit: an individual document or passage hit
        """
        # vespa structures its response differently depending on the api endpoint
        # for searches, the response should contain a sddocname field
        match extract_schema_name(response_hit):
            case Ok(schema_name):
                match schema_name:
                    case "family_document":
                        return Document.from_vespa_response(response_hit=response_hit)
                    case "document_passage":
                        return Passage.from_vespa_response(response_hit=response_hit)
                    case _:
                        raise ValueError(
                            f"response hit wasn't a concept, it had schema name `{schema_name}`"
                        )
            case Err(error):
                raise ValueError(error.msg)
            case _ as unreachable:
                assert_never(unreachable)

    def __eq__(self, other):
        """
        Check if two hits are equal.

        Ignores relevance and rank_features as these are dependent on non-deterministic query routing.
        """
        if not isinstance(other, self.__class__):
            return False

        fields_to_compare = [
            f for f in self.__dict__.keys() if f not in ("relevance", "rank_features")
        ]

        return all(getattr(self, f) == getattr(other, f) for f in fields_to_compare)


class Document(Hit):
    """A document search result hit."""

    class ConceptV2(BaseModel):
        """Concepts (v2) instances in the document."""

        concept_id: Annotated[
            str,
            Field(
                description="A unique ID for the concept",
                examples=["5d4xcy5g"],
            ),
        ]
        concept_wikibase_id: Annotated[
            Optional[str],
            Field(
                description="The Wikibase (Concept Store) ID",
                examples=["Q100"],
            ),
        ] = None
        classifier_id: Annotated[
            str,
            Field(
                description="A unique ID for the classifier",
                examples=["zv3r45ae"],
            ),
        ]
        count: Annotated[
            NonNegativeInt,
            Field(description="Number of instances of this concept in this document"),
        ]

    concept_counts: Optional[dict[str, int]] = None
    concepts_v2: Annotated[
        Optional[Sequence[ConceptV2]],
        Field(description="Concepts identified in this document", default=None),
    ]

    @classmethod
    def from_vespa_response(cls, response_hit: dict) -> "Document":
        """
        Create a Document from a Vespa response hit.

        :param dict response_hit: part of a json response from Vespa
        :return Document: a populated document
        """
        fields = response_hit["fields"]
        family_publication_ts = fields.get("family_publication_ts", None)
        family_publication_ts = (
            datetime.fromisoformat(family_publication_ts)
            if family_publication_ts
            else None
        )
        return cls(
            family_name=fields.get("family_name"),
            family_description=fields.get("family_description"),
            family_source=fields.get("family_source"),
            family_import_id=fields.get("family_import_id"),
            family_slug=fields.get("family_slug"),
            family_category=fields.get("family_category"),
            family_publication_ts=family_publication_ts,
            family_geography=fields.get("family_geography"),
            family_geographies=fields.get("family_geographies", []),
            document_import_id=fields.get("document_import_id"),
            document_slug=fields.get("document_slug"),
            document_languages=fields.get("document_languages", []),
            document_content_type=fields.get("document_content_type"),
            document_cdn_object=fields.get("document_cdn_object"),
            document_source_url=fields.get("document_source_url"),
            document_title=fields.get("document_title"),
            corpus_type_name=fields.get("corpus_type_name"),
            corpus_import_id=fields.get("corpus_import_id"),
            metadata=fields.get("metadata"),
            concepts=fields.get("concepts"),
            relevance=response_hit.get("relevance"),
            rank_features=fields.get("summaryfeatures"),
            concept_counts=fields.get("concept_counts"),
            concepts_v2=fields.get("concepts_v2", []),
        )


class Passage(Hit):
    """A passage search result hit."""

    class Span(BaseModel):
        """Spans in the passage."""

        class ConceptV2(BaseModel):
            """Concepts (v2) instances in the passage."""

            concept_id: Annotated[
                str,
                Field(
                    description="Unique ID for the concept",
                    examples=["5d4xcy5g"],
                ),
            ]
            concept_wikibase_id: Annotated[
                str,
                Field(
                    description="Wikibase (Concept Store) ID",
                    examples=["Q100"],
                ),
            ]
            classifier_id: Annotated[
                str,
                Field(
                    description="Unique ID for the classifier",
                    examples=["zv3r45ae"],
                ),
            ]

        start: Annotated[
            NonNegativeInt,
            Field(description="Index start position character"),
        ]
        end: Annotated[
            NonNegativeInt,
            Field(description="Index start position character"),
        ]
        concepts_v2: Annotated[
            Sequence[ConceptV2],
            Field(
                description="Concepts identified in this span",
            ),
        ]

    class Concept(BaseModel):
        """
        A concept extracted from a passage of text.

        This refers to a span of text within passage that holds a concept.
        E.g. "Adaptation strategy" is a concept within a passage starting at index 0 and
        ending at index 17, classified by model "environment_model_1" on the 12th Jan at
        12:00.
        """

        id: str
        name: str
        parent_concepts: Optional[List[dict[str, str]]] = None
        parent_concept_ids_flat: Optional[str] = None
        model: str
        end: int
        start: int
        timestamp: datetime

        model_config = ConfigDict(
            use_enum_values=True,
            json_encoders={datetime: lambda dt: dt.isoformat()},
        )

        @model_validator(mode="after")
        def validate_parent_concept_ids_flat(self) -> "Passage.Concept":
            """
            Validate parent_concept_ids_flat field.

            This field should hold the same ids as concepts in the parent_concepts field.
            """
            # Skip validation if either field is missing
            if self.parent_concepts is None or self.parent_concept_ids_flat is None:
                return self

            parent_concept_ids_flattened = ",".join(
                [parent_concept["id"] for parent_concept in self.parent_concepts]
            )

            if not (
                self.parent_concept_ids_flat == parent_concept_ids_flattened
                or self.parent_concept_ids_flat == parent_concept_ids_flattened + ","
            ):
                raise ValueError(
                    "parent_concept_ids_flat must be a comma separated list of parent "
                    "concept ids held in the parent concepts field. "
                    f"Received parent_concept_ids_flat: {self.parent_concept_ids_flat}\n"
                    "Received ids in the parent_concept objects: "
                    f"{parent_concept_ids_flattened}"
                )
            return self

    text_block: str
    text_block_id: str
    text_block_type: str
    text_block_page: Optional[int] = None
    text_block_coords: Optional[Sequence[tuple[float, float]]] = None
    concepts: Optional[Sequence[Concept]] = None
    spans: Annotated[
        Optional[Sequence[Span]],
        Field(
            description="Spans within the passage",
            default=None,
        ),
    ]

    @classmethod
    def from_vespa_response(cls, response_hit: dict) -> "Passage":
        """
        Create a Passage from a Vespa response hit.

        :param dict response_hit: part of a json response from Vespa
        :return Passage: a populated passage
        """
        fields = response_hit["fields"]
        family_publication_ts = fields.get("family_publication_ts")
        family_publication_ts = (
            datetime.fromisoformat(family_publication_ts)
            if family_publication_ts
            else None
        )

        return cls(
            family_name=fields.get("family_name"),
            family_description=fields.get("family_description"),
            family_source=fields.get("family_source"),
            family_import_id=fields.get("family_import_id"),
            family_slug=fields.get("family_slug"),
            family_category=fields.get("family_category"),
            family_publication_ts=family_publication_ts,
            family_geography=fields.get("family_geography"),
            family_geographies=fields.get("family_geographies", []),
            document_import_id=fields.get("document_import_id"),
            document_slug=fields.get("document_slug"),
            document_languages=fields.get("document_languages", []),
            document_content_type=fields.get("document_content_type"),
            document_cdn_object=fields.get("document_cdn_object"),
            document_source_url=fields.get("document_source_url"),
            corpus_type_name=fields.get("corpus_type_name"),
            corpus_import_id=fields.get("corpus_import_id"),
            text_block=fields["text_block"],
            text_block_id=fields["text_block_id"],
            text_block_type=fields["text_block_type"],
            text_block_page=fields.get("text_block_page"),
            text_block_coords=fields.get("text_block_coords"),
            metadata=fields.get("metadata"),
            concepts=fields.get("concepts"),
            spans=fields.get("spans", []),
            relevance=response_hit.get("relevance"),
            rank_features=fields.get("summaryfeatures"),
        )


class Family(BaseModel):
    """A family containing relevant documents and passages."""

    id: str
    hits: Sequence[Hit]
    total_passage_hits: int = 0
    continuation_token: Optional[str] = None
    prev_continuation_token: Optional[str] = None
    relevance: Optional[float] = None

    def __eq__(self, other):
        """
        Check if two Families are equal.

        Ignores relevance as it's dependent on non-deterministic query routing.
        """

        if not isinstance(other, self.__class__):
            return False

        fields_to_compare = [f for f in self.__dict__.keys() if f not in ("relevance")]

        return all(getattr(self, f) == getattr(other, f) for f in fields_to_compare)


R = TypeVar("R")  # Result


class SearchResponse(BaseModel, Generic[R]):
    """Relevant results, and search response metadata"""

    total_hits: int
    total_result_hits: int = 0
    query_time_ms: Optional[int] = None
    total_time_ms: Optional[int] = None
    results: Sequence[R]
    continuation_token: Optional[str] = None
    this_continuation_token: Optional[str] = None
    prev_continuation_token: Optional[str] = None

    def __eq__(self, other):
        """
        Check if two hits are equal.

        Ignores query time fields as they are non-deterministic.
        """

        if not isinstance(other, self.__class__):
            return False

        fields_to_compare = [
            f
            for f in self.__dict__.keys()
            if f not in ("query_time_ms", "total_time_ms")
        ]

        return all(getattr(self, f) == getattr(other, f) for f in fields_to_compare)


def extract_schema_name(response_hit: JsonDict) -> Result[str, Error]:
    """
    Extract schema name from a Vespa response.

    Example:
    ```
    {
      "id": "id:doc_search:concept::Q290.w2m7ymf7",
      "relevance": 0.0,
      "source": "family-document-passage",
      "fields": {
        "sddocname": "concept",
        "documentid": "id:doc_search:concept::w2m7ymf7",
        "wikibase_id": "Q290",
        ..
        "subconcept_of": [
          "hzaw3hdg"
        ],
        "recursive_has_subconcept": false
      }
    }
    ```

    This will try first to to get the schema field name, and from it,
    return `concept`. If that wasn't present, it would extract
    `concept` from the top-level `"id"` field.
    """
    schema_name: str | None = dig(response_hit, "fields", SCHEMA_NAME_FIELD_NAME)

    if schema_name is not None:
        return Ok(schema_name)

    # For `get_by_id()`, extract from ID field
    if id := response_hit.get("id"):
        if not isinstance(id, str):
            return Err(
                Error(
                    msg=f"Expected string ID, got {type(id).__name__}: {id}",
                    metadata=None,
                ),
            )

        match id.split(":"):
            case [_, _, schema_name, *_]:
                return Ok(schema_name)
            case _:
                return Err(
                    Error(
                        msg=f"Could not parse response type from ID: {id}",
                        metadata={},
                    ),
                )
    else:
        return Err(
            Error(
                msg=f"Response had neither {SCHEMA_NAME_FIELD_NAME} nor ID field",
                metadata={},
            ),
        )


class Concept(BaseModel):
    """As from our Concept Store via Vespa."""

    id: str  # A canonical ID
    wikibase_id: WikibaseId
    wikibase_revision: int
    wikibase_url: AnyHttpUrl
    preferred_label: str = Field(
        ...,
        description="The preferred label for the concept",
        min_length=1,
    )
    description: str | None = Field(
        default=None,
        description=(
            "A short description of the concept which should be sufficient to "
            "disambiguate it from other concepts with similar labels"
        ),
        min_length=1,
    )
    definition: str | None = Field(
        default=None,
        description=(
            "A more exhaustive definition of the concept, which should be enough for a "
            "human labeller to identify instances of the concept in a given text. "
        ),
    )
    alternative_labels: Sequence[str] = Field(
        default_factory=list,
        description="List of alternative labels for the concept",
    )
    negative_labels: Sequence[str] = Field(
        default_factory=list,
        description=(
            "Labels which should not be matched instances of the concept. "
            "Negative labels should be unique, and cannot overlap with positive labels."
        ),
    )
    subconcept_of: Sequence[str] = Field(
        default_factory=list,
        description="List of parent concept IDs",
    )
    has_subconcept: Sequence[str] = Field(
        default_factory=list, description="List of sub-concept IDs"
    )
    related_concepts: Sequence[str] = Field(
        default_factory=list, description="List of related concept IDs"
    )
    recursive_subconcept_of: Sequence[str] | None = Field(
        default=None,
        description="List of all parent concept IDs, recursively up the hierarchy",
    )
    recursive_has_subconcept: Sequence[str] | None = Field(
        default=None,
        description="List of all sub-concept IDs, recursively down the hierarchy",
    )

    response_raw: JsonDict = Field(exclude=True)  # Don't include in serialisation

    @classmethod
    def from_vespa_response(cls, response_hit: JsonDict) -> "Concept":
        """
        Create a Concept from a Vespa response hit.

        :param dict response_hit: part of a json response from Vespa
        :return Concept: a populated Concept
        """
        match extract_schema_name(response_hit):
            case Ok(schema_name):
                if schema_name != "concept":
                    raise ValueError(
                        f"response hit wasn't a concept, it had schema name `{schema_name}`"
                    )
            case Err(error):
                raise ValueError(error.msg)

        if fields := dig(response_hit, "fields"):
            return cls(**fields, response_raw=response_hit)
        else:
            raise ValueError("response hit was missing `fields`")


class ClassifiersProfile(BaseModel):
    """A mapping over classifers to the versions to be used."""

    class Mapping(BaseModel):
        """A mapping between a concept and the classifier to use for it."""

        concept_id: Annotated[
            str,
            Field(
                description="Canonical ID of the concept being mapped",
                examples=["r3dkctge"],
            ),
        ]
        concept_wikibase_id: Annotated[
            WikibaseId,
            Field(
                description="Wikibase ID of the concept being mapped",
                examples=[WikibaseId("Q789")],
            ),
        ]
        classifier_id: Annotated[
            str,
            Field(
                description="Canonical ID of the classifier to use for this concept",
                examples=["kx7m3p9w"],
            ),
        ]

    id: Annotated[
        str,
        Field(
            description="Document ID as in Vespa",
            examples=["primary.p34ehv2x"],
        ),
    ]
    name: Annotated[
        str,
        Field(
            description="Semantic, human readable name",
            examples=["primary", "experimental", "retired"],
        ),
    ]
    mappings: Annotated[
        list[Mapping],
        Field(
            description="List of mappings between concepts and classifiers for this profile",
            examples=[
                [
                    Mapping(
                        concept_id="r3dkctge",
                        concept_wikibase_id=WikibaseId("Q125"),
                        classifier_id="kx7m3p9w",
                    )
                ]
            ],
        ),
    ]
    multi: Annotated[
        bool,
        Field(
            description="Whether this classifiers profile can have multiple mappings per Wikibase ID",
            examples=[False],
        ),
    ]

    response_raw: JsonDict = Field(exclude=True)  # Don't include in serialisation

    @classmethod
    def from_vespa_response(cls, response_hit: JsonDict) -> "ClassifiersProfile":
        """
        Create a ClassifiersProfile from a Vespa response hit.

        :param dict response_hit: part of a json response from Vespa
        :return ClassifiersProfile: a populated ClassifiersProfile
        """
        match extract_schema_name(response_hit):
            case Ok(schema_name):
                if schema_name != "classifiers_profile":
                    raise ValueError(
                        f"response hit wasn't a classifiers_profile, it had schema name `{schema_name}`"
                    )
            case Err(error):
                raise ValueError(error.msg)

        if fields := dig(response_hit, "fields"):
            return cls(**fields, response_raw=response_hit)
        else:
            raise ValueError("response hit was missing `fields`")


class ClassifiersProfiles(BaseModel):
    """A singleton mapping over unique classifiers profiles to their version."""

    id: Annotated[
        str,
        Field(
            description="Document ID as in Vespa",
            examples=["default"],
        ),
    ]
    mappings: Annotated[
        dict[str, str],
        Field(
            description="Pairs of classifiers profile name to a version of it",
            examples=[
                {
                    "primary": "primary.j2ssznnr",
                    "experimental": "experimental.ger8qyfc",
                    "retired": "retired.39vikj2a",
                }
            ],
        ),
    ]

    response_raw: JsonDict = Field(exclude=True)  # Don't include in serialisation

    @classmethod
    def from_vespa_response(cls, response_hit: JsonDict) -> "ClassifiersProfiles":
        """
        Create a ClassifiersProfiles from a Vespa response hit.

        :param dict response_hit: part of a json response from Vespa
        :return ClassifiersProfiles: a populated ClassifiersProfiles
        """
        match extract_schema_name(response_hit):
            case Ok(schema_name):
                if schema_name != "classifiers_profiles":
                    raise ValueError(
                        f"response hit wasn't a classifiers_profiles, it had schema name `{schema_name}`"
                    )
            case Err(error):
                raise ValueError(error.msg)

        if fields := dig(response_hit, "fields"):
            # Extract the ID from the document ID since it's not in the fields
            # Document ID format: "id:doc_search:classifiers_profiles::default"
            doc_id = response_hit.get("id", "")
            extracted_id = doc_id.split("::")[-1] if "::" in doc_id else "default"
            return cls(id=extracted_id, **fields, response_raw=response_hit)
        else:
            raise ValueError("response hit was missing `fields`")
