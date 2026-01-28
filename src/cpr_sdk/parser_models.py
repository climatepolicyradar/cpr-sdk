import json
import logging
import logging.config
from collections import Counter
from datetime import date
from enum import Enum
from typing import (
    Any,
    Final,
    Generic,
    List,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    Annotated,
)

from cpr_sdk.pipeline_general_models import (
    CONTENT_TYPE_HTML,
    BackendDocument,
    Json,
)
from cpr_sdk.utils import remove_key_if_all_nested_vals_none, unflatten_json
from langdetect import DetectorFactory, LangDetectException, detect
from pydantic import AnyHttpUrl, BaseModel, Field, model_validator

_LOGGER = logging.getLogger(__name__)

PARSER_METADATA_KEY: Final = "parser_metadata"
AZURE_API_VERSION_KEY: Final = "azure_api_version"
AZURE_MODEL_ID_KEY: Final = "azure_model_id"
PARSING_DATE_KEY: Final = "parsing_date"
PDF_PAGE_METADATA_KEY: Final = "pdf_data_page_metadata"
PDF_DATA_PASSAGE_LEVEL_EXPAND_FIELDS: Final = {"text_blocks", "page_metadata"}
HTML_DATA_PASSAGE_LEVEL_EXPAND_FIELDS: Final = {"text_blocks"}


class VerticalFlipError(Exception):
    """Exception for when a vertical flip fails."""

    pass


class BlockType(str, Enum):
    """
    List of possible block types from the PubLayNet model.

    https://layout-parser.readthedocs.io/en/latest/notes/modelzoo.html#model-label-map
    """

    TEXT = "Text"
    TITLE = "Title"
    LIST = "List"
    TABLE = "Table"
    TABLE_CELL = "TableCell"
    FIGURE = "Figure"
    INFERRED = "Inferred from gaps"
    # TODO: remove this when OCRProcessor._infer_block_type is implemented
    AMBIGUOUS = "Ambiguous"
    GOOGLE_BLOCK = "Google Text Block"
    PAGE_HEADER = "pageHeader"
    PAGE_FOOTER = "pageFooter"
    TITLE_LOWER_CASE = "title"
    SECTION_HEADING = "sectionHeading"
    PAGE_NUMBER = "pageNumber"
    DOCUMENT_HEADER = "Document Header"
    FOOT_NOTE = "footnote"


class _TextBlockProto(Protocol):
    """
    Protocol capturing the shared interface of text block types.

    All text blocks (TextBlock, TextBlockV2, HTMLTextBlock) share these
    attributes/methods from _TextBlockMixin.
    """

    language: Optional[str]

    def to_string(self) -> str: ...

    def model_dump_json(
        self, *, exclude: Union[set[str], dict[str, Any], None] = None
    ) -> str: ...


class _TextBlockMixin:
    """
    Shared fields for TextBlock* classes.

    Must be used with a class that inherits from Pydantic's BaseModel.
    """

    language: Optional[str] = (
        None  # TODO: validate this against a list of language ISO codes
    )
    type: BlockType
    type_confidence: float = Field(ge=0, le=1)


class TextBlock(_TextBlockMixin, BaseModel):
    """
    text block with text as a list (v1).

    :attribute text: list of text lines contained in the text block
    """

    text_block_id: str
    text: List[str]

    def to_string(self) -> str:
        """Returns lines in a text block separated by spaces as a string."""

        return " ".join([line.strip() for line in self.text])


class TextBlockV2(_TextBlockMixin, BaseModel):
    """
    text block with text as singular (v2).

    :attribute text: text lines in the text block
    """

    text: str

    def to_string(self) -> str:
        """
        Returns lines in a text block separated by spaces as a string.

        For backwards compatibility with v1.
        """

        return self.text


class HTMLTextBlock(TextBlock):
    """
    Text block parsed from an HTML document.

    Type is set to "Text" with a confidence of 1.0 by default, as we do not predict
    types for text blocks parsed from HTML.
    """


class PDFTextBlock(TextBlock):
    """
    Text block parsed from a PDF document.

    Stores the text and positional information for a single text block extracted from
    a document.

    :attribute coords: list of coordinates of the vertices defining the boundary of
    the text block. Each coordinate is a tuple in the format (x, y). (0, 0) is at the
    top left corner of the page, and the positive x- and y- directions are right and
    down. :attribute page_number: page number of the page containing the text block.
    """

    coords: List[Tuple[float, float]]
    page_number: int = Field(ge=0)

    def to_string(self) -> str:
        """Returns lines in a text block separated by spaces as a string."""

        return " ".join([line.strip() for line in self.text])


class Page(BaseModel):
    """Bounding boxes for a specific page."""

    class BoundingBox(BaseModel):
        """A bounding box defined by a specific number coordinate points."""

        class Coordinate(BaseModel):
            """A single (x, y) coordinate point."""

            x: Annotated[float, Field(ge=0, description="X dimension of point.")]
            y: Annotated[float, Field(ge=0, description="Y dimension of point.")]

        coordinates: Annotated[
            list[Coordinate],
            Field(
                min_length=4,
                max_length=4,
                description="A restricted number of coordinates to represent the bounding box.",
            ),
        ]

    number: Annotated[
        int,
        Field(ge=0, description="Page number this entry corresponds to."),
    ]

    bounding_boxes: Annotated[
        list[BoundingBox],
        Field(
            min_length=1,
            description="List of bounding boxes on this page.",
        ),
    ]


class PDFTextBlockV2(TextBlockV2):
    """V2 text block parsed from a PDF document with str text."""

    id: Annotated[
        str,
        Field(description="Global ID. Replaces `text_block_id`."),
    ]

    idx: Annotated[
        int,
        Field(
            strict=True,
            ge=0,
            description="Index of this text block within the range of all text blocks on the parent document",
        ),
    ]

    pages: Annotated[
        list[Page],
        Field(
            min_length=1,
            description="Page(s) within the document that this text block is found on.",
        ),
    ]

    heading_id: Optional[str] = None
    tokens: Optional[list[str]] = None
    serialised_text: Optional[str] = None

    def to_string(self) -> str:
        """
        Returns the text content as a string.

        For backwards compatibility with v1.
        """
        return self.text


class ParserInput(BaseModel):
    """Base class for input to a parser."""

    document_id: str
    document_name: str
    document_description: str
    document_source_url: Optional[AnyHttpUrl] = None
    document_cdn_object: Optional[str] = None
    document_content_type: Optional[str] = None
    document_md5_sum: Optional[str] = None
    document_slug: str
    document_metadata: BackendDocument

    pipeline_metadata: Json = {}  # note: defaulting to {} here is safe (pydantic)


class HTMLData(BaseModel):
    """Set of metadata specific to HTML documents."""

    detected_title: Optional[str] = None
    detected_date: Optional[date] = None
    has_valid_text: bool
    text_blocks: Sequence[HTMLTextBlock]


class PDFPageMetadata(BaseModel):
    """
    Set of metadata for a single page of a PDF document.

    :attribute dimensions: (width, height) of the page in pixels
    """

    page_number: int = Field(ge=0)
    dimensions: Tuple[float, float]


class PDFData(BaseModel):
    """
    Set of metadata unique to PDF documents.

    :attribute pages: List of pages contained in the document :attribute filename:
    Name of the PDF file, without extension :attribute md5sum: md5sum of PDF content
    :attribute language: list of 2-letter ISO language codes, optional. If null,
    the OCR processor didn't support language detection
    """

    page_metadata: Sequence[PDFPageMetadata]
    md5sum: str
    text_blocks: Sequence[PDFTextBlock]


class PDFDataV2(BaseModel):
    """
    Set of metadata unique to PDF documents.

    :attribute pages: List of pages contained in the document :attribute filename:
    Name of the PDF file, without extension :attribute md5sum: md5sum of PDF content
    :attribute language: list of 2-letter ISO language codes, optional. If null,
    the OCR processor didn't support language detection
    """

    page_metadata: Sequence[PDFPageMetadata]
    md5sum: str
    text_blocks: Sequence[PDFTextBlockV2]


_PO = TypeVar("_PO", bound="_BaseParserOutputFieldsMixin")

PDFDataT = TypeVar("PDFDataT", PDFData, PDFDataV2)
PDFTextBlockT = TypeVar("PDFTextBlockT", PDFTextBlock, PDFTextBlockV2)


class _BaseParserOutputFieldsMixin(BaseModel, Generic[PDFDataT, PDFTextBlockT]):
    """Shared fields and methods for BaseParserOutput* classes."""

    document_id: str
    document_metadata: dict
    document_name: str
    document_description: str
    document_source_url: Optional[AnyHttpUrl] = None
    document_cdn_object: Optional[str] = None
    document_content_type: Optional[str] = None
    document_md5_sum: Optional[str] = None
    document_slug: str

    languages: Optional[Sequence[str]] = None
    translated: bool = False
    html_data: Optional[HTMLData] = None
    pdf_data: Optional[PDFDataT] = None

    pipeline_metadata: Json = {}  # note: defaulting to {} here is safe (pydantic)

    @property
    def text_blocks(self) -> Sequence[_TextBlockProto]:
        """
        Return the text blocks in the document.

        These could differ in format depending on the content type.
        """

        if self.html_data is not None:
            return self.html_data.text_blocks
        elif self.pdf_data is not None:
            return self.pdf_data.text_blocks
        return []

    def get_text_blocks(
        self, including_invalid_html=False
    ) -> Sequence[_TextBlockProto]:
        """A method for getting text blocks with the option to include invalid html."""
        if self.document_content_type == CONTENT_TYPE_HTML and self.html_data:
            if not including_invalid_html and not self.html_data.has_valid_text:
                return []
        return self.text_blocks

    def to_string(self) -> str:
        """Return the text blocks in the parser output as a string"""

        return " ".join(
            [text_block.to_string().strip() for text_block in self.text_blocks]
        )

    @model_validator(mode="after")
    def check_html_pdf_metadata(self):
        """
        Validate the relationship between content-type and the data that is set.

        Check that if the content-type is not HTML or PDF, then html_data and pdf_data
        are both null.
        """

        document_has_data = self.html_data is not None or self.pdf_data is not None

        if not self.document_content_type and document_has_data:
            raise ValueError(
                "html_data or pdf_data must be null for documents with no content type."
            )

        return self

    def detect_and_set_languages(self: _PO) -> _PO:
        """
        Detect language of the text and set the language attribute.

        Return an instance of ParserOutput with the language attribute set. Assumes
        that a document only has one language.
        """

        if self.document_content_type != CONTENT_TYPE_HTML:
            _LOGGER.warning(
                "Language detection should not be required for non-HTML documents, "
                "but it has been run on one. This will overwrite any document "
                "languages detected via other means, e.g. OCR. "
            )

        # language detection is not deterministic, so we need to set a seed
        DetectorFactory.seed = 0

        if len(self.text_blocks) > 0:
            try:
                detected_language = detect(self.to_string())
            except LangDetectException:
                _LOGGER.warning(
                    "Language detection failed for document with id %s",
                    self.document_id,
                )
                detected_language = None
            self.languages = [detected_language] if detected_language else []
            for text_block in self.text_blocks:
                text_block.language = detected_language

        return self

    def set_document_languages_from_text_blocks(
        self: _PO, min_language_proportion: float = 0.4
    ) -> _PO:
        """
        Store the document languages attribute as part of the object.

        Done by getting all languages with proportion above `min_language_proportion`.

        :attribute min_language_proportion: Minimum proportion of text blocks in a
        language for it to be considered a language of the document.
        """

        all_text_block_languages = [
            text_block.language for text_block in self.text_blocks
        ]

        if all([lang is None for lang in all_text_block_languages]):
            self.languages = None

        else:
            lang_counter = Counter(
                [lang for lang in all_text_block_languages if lang is not None]
            )
            self.languages = [
                lang
                for lang, count in lang_counter.items()
                if count / len(all_text_block_languages) > min_language_proportion
            ]

        return self


class BaseParserOutput(_BaseParserOutputFieldsMixin[PDFData, PDFTextBlock]):
    """Base class for an output to a parser (v1)."""

    def vertically_flip_text_block_coords(self: _PO) -> _PO:
        """
        Flips the coordinates of all PDF text blocks vertically.

        Acts in-place on the coordinates in the ParserOutput object.

        Should the document fail to flip, a VerticalFlipError is raised. This is most
        commonly due to a page number being referenced in a text block that doesn't
        exist in the page_metadata mapping.
        """

        if self.pdf_data is None:
            return self

        page_height_map = {
            page.page_number: page.dimensions[1] for page in self.pdf_data.page_metadata
        }

        try:
            for text_block in self.pdf_data.text_blocks:
                if text_block.coords is not None and text_block.page_number is not None:
                    text_block.coords = [
                        (x, page_height_map[text_block.page_number] - y)
                        for x, y in text_block.coords
                    ]

                    # flip top and bottom so y values are still increasing as you go
                    # through the coordinates list
                    text_block.coords = [
                        text_block.coords[3],
                        text_block.coords[2],
                        text_block.coords[1],
                        text_block.coords[0],
                    ]
        except Exception as e:
            _LOGGER.exception(
                "Error flipping text block coordinates.",
                extra={"props": {"document_id": self.document_id}},
            )
            raise VerticalFlipError(
                f"Failed to flip text blocks for {self.document_id}"
            ) from e

        return self


class BaseParserOutputV2(_BaseParserOutputFieldsMixin[PDFDataV2, PDFTextBlockV2]):
    """Base class for an output from a parser (v2)."""


class _ParserOutputMethodsMixin(BaseModel):
    """
    Shared methods for ParserOutput classes.

    This mixin provides methods that work with both BaseParserOutput and BaseParserOutputV2.
    Expected to be used with classes that inherit from _BaseParserOutputFieldsMixin.
    """

    @classmethod
    def from_flat_json(cls, data: dict):
        """Instantiate a parser output object from flat json."""
        unflattened = unflatten_json(data)

        # We remove optional fields that have complex nested structures.
        # E.g. if html_data had a value of None for has_valid_text, we need to remove
        # it as this would throw a validation error.
        unflattened = remove_key_if_all_nested_vals_none(unflattened, "html_data")
        unflattened = remove_key_if_all_nested_vals_none(unflattened, "pdf_data")

        return cls.model_validate(unflattened)

    @staticmethod
    def _rename_text_block_keys(
        keys: Union[list[str], dict[str, Any]],
    ) -> Union[list[str], dict[str, Any]]:
        """Prepend text_block. to the keys in the dictionary or list."""

        if isinstance(keys, list):
            return [f"text_block.{key}" for key in keys]

        if isinstance(keys, dict):
            return {f"text_block.{key}": value for key, value in keys.items()}

        raise ValueError("keys must be a list or a dictionary")

    def get_page_metadata_by_page_number(self, page_number: int) -> Optional[dict]:
        """
        Retrieve the first element of PDF page metadata where the page number matches the given page number.

        The reason we convert from the pydantic BaseModel to a string using the
        model_dump_json method and then reloading with json.load is as objects like
        Enums and child pydantic objects persist when using the model_dump method.
        We don't want these when we push to huggingface.

        :param pdf_data: PDFData object containing the metadata.
        :param page_number: The page number to match.
        :return: The first matching PDFPageMetadata object, or None if no match is found.
        """
        if self.pdf_data and self.pdf_data.page_metadata:  # type: ignore[attr-defined]
            for metadata in self.pdf_data.page_metadata:  # type: ignore[attr-defined]
                if metadata.page_number == page_number:
                    return json.loads(metadata.model_dump_json())
        return None


class ParserOutput(_ParserOutputMethodsMixin, BaseParserOutput):
    """Output to a parser with the metadata format used by the CPR backend."""

    document_metadata: BackendDocument  # type: ignore[override]

    def to_passage_level_json(self, include_empty: bool = True) -> list[dict[str, Any]]:
        """
        Convert the parser output to a passage-level JSON format.

        In passage-level format we have a row for every text block in the document. This
        is as for natural language processing tasks we often want to work with text at
        the passage level.

        HTML data won't contain PDF fields and vice versa, thus we must fill this in.
        We could rely on the hugging face dataset transformation to fill in the missing
        fields, but this is more explicit and provides default values.

        The reason we convert from the pydantic BaseModel to a string using the
        model_dump_json method and then reloading with json.load is as objects like
        Enums and child pydantic objects persist when using the model_dump method.
        We don't want these when we push to huggingface.

        :param include_empty: Whether to output the document metadata if there are no
        text blocks in the ParserOutput. If True, outputs a single dict with None values
        for each text block related field. If False, returns an empty list.
        """

        if not self.text_blocks and not include_empty:
            return []

        fixed_fields_dict = json.loads(
            self.model_dump_json(
                exclude={
                    "pdf_data": PDF_DATA_PASSAGE_LEVEL_EXPAND_FIELDS,
                    "html_data": HTML_DATA_PASSAGE_LEVEL_EXPAND_FIELDS,
                }
            )
        )

        # For v1, we use HTMLTextBlock and PDFTextBlock directly
        empty_html_text_block_keys = self._rename_text_block_keys(
            list(HTMLTextBlock.model_fields.keys())
        )
        empty_pdf_text_block_keys = self._rename_text_block_keys(
            list(PDFTextBlock.model_fields.keys())
        )

        if not self.text_blocks:
            passages_array_filled = [
                {key: None for key in empty_html_text_block_keys}
                | {key: None for key in empty_pdf_text_block_keys}
                | fixed_fields_dict
                | {"text_block.index": 0, PDF_PAGE_METADATA_KEY: None}
            ]

            return passages_array_filled

        passages_array = [
            fixed_fields_dict
            | self._rename_text_block_keys(
                json.loads(block.model_dump_json(exclude={"text"}))
            )
            | {"text_block.text": block.to_string(), "text_block.index": idx}
            for idx, block in enumerate(self.text_blocks)
        ]

        # TODO: do we need this code?
        for passage in passages_array:
            page_number = passage.get("text_block.page_number", None)
            passage[PDF_PAGE_METADATA_KEY] = (
                self.get_page_metadata_by_page_number(page_number)
                if page_number is not None
                else None
            )

        passages_array_filled = []
        for passage in passages_array:
            for key in empty_html_text_block_keys:
                if key not in passage:
                    passage[key] = None
            for key in empty_pdf_text_block_keys:
                if key not in passage:
                    passage[key] = None
            passages_array_filled.append(passage)

        return passages_array_filled


class ParserOutputV2(_ParserOutputMethodsMixin, BaseParserOutputV2):
    """Output to a parser with the metadata format used by the CPR backend."""

    document_metadata: BackendDocument  # type: ignore[override]

    def to_passage_level_json(self, include_empty: bool = True) -> list[dict[str, Any]]:
        """
        Convert the parser output to a passage-level JSON format.

        In passage-level format we have a row for every text block in the document. This
        is as for natural language processing tasks we often want to work with text at
        the passage level.

        HTML data won't contain PDF fields and vice versa, thus we must fill this in.
        We could rely on the hugging face dataset transformation to fill in the missing
        fields, but this is more explicit and provides default values.

        The reason we convert from the pydantic BaseModel to a string using the
        model_dump_json method and then reloading with json.load is as objects like
        Enums and child pydantic objects persist when using the model_dump method.
        We don't want these when we push to huggingface.

        :param include_empty: Whether to output the document metadata if there are no
        text blocks in the ParserOutput. If True, outputs a single dict with None values
        for each text block related field. If False, returns an empty list.
        """

        if not self.text_blocks and not include_empty:
            return []

        fixed_fields_dict = json.loads(
            self.model_dump_json(
                exclude={
                    "pdf_data": PDF_DATA_PASSAGE_LEVEL_EXPAND_FIELDS,
                    "html_data": HTML_DATA_PASSAGE_LEVEL_EXPAND_FIELDS,
                }
            )
        )

        # For v2, we use HTMLTextBlock and PDFTextBlockV2 directly
        empty_html_text_block_keys = self._rename_text_block_keys(
            list(HTMLTextBlock.model_fields.keys())
        )
        empty_pdf_text_block_keys = self._rename_text_block_keys(
            list(PDFTextBlockV2.model_fields.keys())
        )

        if not self.text_blocks:
            passages_array_filled = [
                {key: None for key in empty_html_text_block_keys}
                | {key: None for key in empty_pdf_text_block_keys}
                | fixed_fields_dict
                | {"text_block.index": 0, PDF_PAGE_METADATA_KEY: None}
            ]

            return passages_array_filled

        passages_array = [
            fixed_fields_dict
            | self._rename_text_block_keys(
                json.loads(block.model_dump_json(exclude={"text"}))
            )
            | {"text_block.text": block.to_string(), "text_block.index": idx}
            for idx, block in enumerate(self.text_blocks)
        ]

        # TODO: do we need this code?
        for passage in passages_array:
            page_number = passage.get("text_block.page_number", None)
            passage[PDF_PAGE_METADATA_KEY] = (
                self.get_page_metadata_by_page_number(page_number)
                if page_number is not None
                else None
            )

        passages_array_filled = []
        for passage in passages_array:
            for key in empty_html_text_block_keys:
                if key not in passage:
                    passage[key] = None
            for key in empty_pdf_text_block_keys:
                if key not in passage:
                    passage[key] = None
            passages_array_filled.append(passage)

        return passages_array_filled
