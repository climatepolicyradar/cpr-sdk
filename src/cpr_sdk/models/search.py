import re
from datetime import datetime
from enum import Enum
from typing import Any, List, Literal, Optional, Sequence

from pydantic import (
    AliasChoices,
    BaseModel,
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
        if self.name == "parent_concept_ids_flat" and self.value[-1] != ",":
            self.value = self.value + ","
        return self


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
    parent_concepts: List[dict[str, str]]
    parent_concept_ids_flat: str
    model: str
    end: int
    start: int
    timestamp: datetime

    model_config = ConfigDict(
        use_enum_values=True,
        json_encoders={datetime: lambda dt: dt.isoformat()},
    )

    @model_validator(mode="after")
    def validate_parent_concept_ids_flat(self) -> "Concept":
        """
        Validate parent_concept_ids_flat field.

        This field should hold the same ids as concepts in the parent_concepts field.
        """
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


class SearchParameters(BaseModel):
    """Parameters for a search request"""

    query_string: Optional[str] = ""
    """
    A string representation of the search to be performed.
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

    replace_acronyms: bool = False
    """
    Whether to perform acronym replacement based on the 'acronyms' ruleset.
    See docs: https://docs.vespa.ai/en/query-rewriting.html#rule-bases
    """

    @model_validator(mode="after")
    def validate(self):
        """Validate against mutually exclusive fields"""
        if self.exact_match and self.all_results:
            raise ValueError("`exact_match` and `all_results` are mutually exclusive")
        if self.documents_only and not self.all_results:
            raise ValueError(
                "`documents_only` requires `all_results`, other queries are not supported"
            )
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

    @model_validator(mode="after")
    def query_string_must_not_be_empty(self):
        """Validate that the query string is not empty."""
        if not self.query_string:
            self.all_results = True
        return self

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
    corpus_type_name: Optional[str] = None
    corpus_import_id: Optional[str] = None
    metadata: Optional[Sequence[dict[str, str]]] = None
    concepts: Optional[Sequence[Concept]] = None
    relevance: Optional[float] = None
    rank_features: Optional[dict[str, float]] = None
    concept_counts: Optional[dict[str, int]] = None

    @classmethod
    def from_vespa_response(cls, response_hit: dict) -> "Hit":
        """
        Create a Hit from a Vespa response hit.

        :param dict response_hit: part of a json response from Vespa
        :raises ValueError: if the response type is unknown
        :return Hit: an individual document or passage hit
        """
        # vespa structures its response differently depending on the api endpoint
        # for searches, the response should contain a sddocname field
        response_type = response_hit.get("fields", {}).get("sddocname")
        if response_type is None:
            # for get_by_id, the response should contain an id field
            response_type = response_hit["id"].split(":")[2]

        if response_type == "family_document":
            hit = Document.from_vespa_response(response_hit=response_hit)
        elif response_type == "document_passage":
            hit = Passage.from_vespa_response(response_hit=response_hit)
        else:
            raise ValueError(f"Unknown response type: {response_type}")
        return hit

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
            corpus_type_name=fields.get("corpus_type_name"),
            corpus_import_id=fields.get("corpus_import_id"),
            metadata=fields.get("metadata"),
            concepts=fields.get("concepts"),
            relevance=response_hit.get("relevance"),
            rank_features=fields.get("summaryfeatures"),
            concept_counts=fields.get("concept_counts"),
        )


class Passage(Hit):
    """A passage search result hit."""

    text_block: str
    text_block_id: str
    text_block_type: str
    text_block_page: Optional[int] = None
    text_block_coords: Optional[Sequence[tuple[float, float]]] = None

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


class SearchResponse(BaseModel):
    """Relevant results, and search response metadata"""

    total_hits: int
    total_family_hits: int = 0
    query_time_ms: Optional[int] = None
    total_time_ms: Optional[int] = None
    families: Sequence[Family]
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
