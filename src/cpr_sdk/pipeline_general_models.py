from datetime import datetime
from enum import Enum
from typing import Mapping, Any, List, Optional, Sequence, Union

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


class UpdateTypes(str, Enum):
    """Document types supported by the backend API."""

    NAME = "name"
    DESCRIPTION = "description"
    # IMPORT_ID = "import_id"
    SLUG = "slug"
    # PUBLICATION_TS = "publication_ts"
    SOURCE_URL = "source_url"
    # TYPE = "type"
    # SOURCE = "source"
    # CATEGORY = "category"
    # GEOGRAPHY = "geography"
    # LANGUAGES = "languages"
    # DOCUMENT_STATUS = "document_status"
    METADATA = "metadata"
    REPARSE = "reparse"


class Update(BaseModel):
    """Results of comparing db state data against the s3 data to identify updates."""

    s3_value: Optional[Union[str, datetime, dict]] = None
    db_value: Optional[Union[str, datetime, dict]] = None
    type: UpdateTypes


class PipelineUpdates(BaseModel):
    """
    Expected input data containing document updates and new documents.

    This is utilized by the ingest stage of the pipeline.
    """

    new_documents: List[BackendDocument]
    updated_documents: dict[str, List[Update]]


class ExecutionData(BaseModel):
    """Data unique to a step functions execution that is required at later stages."""

    input_dir_path: str
