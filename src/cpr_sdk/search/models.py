import re
from datetime import datetime
from enum import Enum
from functools import total_ordering
from typing import Any, List, Literal, NewType, Optional, Sequence

from cpr_sdk.result import Result, Error, Ok, Err, is_err, unwrap_err
from cpr_sdk.utils import dig
from pydantic import (
    AliasChoices,
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    PositiveInt,
    computed_field,
    field_validator,
    model_validator,
)


@total_ordering
class WikibaseId(BaseModel):
    """A Wikibase ID, which is a string that starts with a 'Q' followed by a number."""

    numeric: PositiveInt

    @field_validator("numeric", mode="before")
    @classmethod
    def parse_wikibase_id(cls, value):
        """Parse Wikibase ID from string or return numeric value"""
        if isinstance(value, str):
            if not re.match(r"^Q[1-9]\d*$", value):
                raise ValueError(f"{value} is not a valid Wikibase ID")
            return int(value[1:])

        return value

    def __lt__(self, other) -> bool:
        """Compare two Wikibase IDs numerically"""
        if not isinstance(other, WikibaseId):
            return NotImplemented

        return self.numeric < other.numeric

    def __eq__(self, other) -> bool:
        """Check if two Wikibase IDs are equal"""

        if not isinstance(other, WikibaseId):
            return NotImplemented

        return self.numeric == other.numeric

    def __hash__(self) -> int:
        """Hash a Wikibase ID consistently with string representation"""
        return hash(str(self))

    def __str__(self) -> str:
        """Return string representation"""
        return f"Q{self.numeric}"

    def __repr__(self) -> str:
        """Return string representation"""
        return f"Q{self.numeric}"


JsonDict = NewType("JsonDict", dict[str, Any])

SCHEMA_NAME_FIELD_NAME = "sddocname"


# Example:
#
# {
#   "id": "id:doc_search:concept::w2m7ymf7",
#   "relevance": 0.0,
#   "source": "family-document-passage",
#   "fields": {
#     "sddocname": "concept",
#     "documentid": "id:doc_search:concept::w2m7ymf7",
#     "id": "w2m7ymf7",
#     "wikibase_id": "Q290",
#     "wikibase_url": "https://wikibase.example.org/wiki/Item:Q290",
#     "preferred_label": "pollution",
#     "subconcept_of": [
#       "hzaw3hdg"
#     ],
#     "recursive_has_subconcept": false
#   }
# }
def _extract_schema_name(response_hit: JsonDict) -> Result[str, Error]:
    """Extract schema name from the Vespa response."""
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
            case [_, schema_name, *_]:
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
    id: str
    wikibase_id: WikibaseId
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
    recursive_concept_of: Sequence[str] | None = Field(
        default=None,
        description="List of all parent concept IDs, recursively up the hierarchy",
    )
    recursive_has_subconcept: Sequence[str] | None = Field(
        default=None,
        description="List of all sub-concept IDs, recursively down the hierarchy",
    )

    response_raw: JsonDict = Field(exclude=True)  # Don't include in serialisation

    @field_validator("wikibase_id", mode="before")
    @classmethod
    def convert_wikibase_id(cls, v):
        """Convert string to Wikibase ID, if needed.

        Pydantic can be odd, and expect either a dict or an actual
        class instance."""
        if isinstance(v, str):
            return WikibaseId(numeric=v)
        return v

    @classmethod
    def from_vespa_response(cls, response_hit: JsonDict) -> "Concept":
        schema_name = _extract_schema_name(response_hit)

        match schema_name:
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
