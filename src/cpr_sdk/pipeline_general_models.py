from datetime import datetime
from typing import Any, Mapping, Optional, Sequence

from pydantic import BaseModel, field_validator

Json = dict[str, Any]

CONTENT_TYPE_HTML = "text/html"
CONTENT_TYPE_DOCX = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
CONTENT_TYPE_PDF = "application/pdf"


class BackendDocument(BaseModel):
    """
    A representation of all information expected to be provided for a document.

    This class comprises direct information describing a document, along
    with all metadata values that should be associated with that document.
    """

    name: str
    document_title: Optional[str] = None
    description: str
    import_id: str
    slug: str
    family_import_id: str
    family_slug: str
    publication_ts: datetime
    date: Optional[str] = None  # Deprecated
    source_url: Optional[str] = None
    download_url: Optional[str] = None
    corpus_import_id: Optional[str] = None
    corpus_type_name: Optional[str] = None
    collection_title: Optional[str] = None
    collection_summary: Optional[str] = None
    type: str
    source: str
    category: str
    geography: str
    geographies: Optional[list[str]] = None
    languages: Sequence[str]

    metadata: Json

    @field_validator("type", mode="before")
    @classmethod
    def none_to_empty_string(cls, value):
        """If the value is None, will convert to an empty string"""
        return "" if value is None else value

    def to_json(self) -> Mapping[str, Any]:
        """Provide a serialisable version of the model"""

        json_dict = self.model_dump()
        json_dict["publication_ts"] = (
            self.publication_ts.isoformat() if self.publication_ts is not None else None
        )
        return json_dict


class InputData(BaseModel):
    """Expected input data containing RDS state."""

    documents: Mapping[str, BackendDocument]
