import pydantic
import pytest
from cpr_sdk.parser_models import (
    HTML_DATA_PASSAGE_LEVEL_EXPAND_FIELDS,
    PDF_DATA_PASSAGE_LEVEL_EXPAND_FIELDS,
    HTMLData,
    HTMLTextBlock,
    ParserInput,
    ParserOutput,
    ParserOutputV2,
    PDFData,
    PDFDataV2,
    PDFTextBlock,
    PDFTextBlockV2,
    TextBlock,
    VerticalFlipError,
    PDF_PAGE_METADATA_KEY,
)
from cpr_sdk.pipeline_general_models import (
    CONTENT_TYPE_HTML,
    CONTENT_TYPE_PDF,
    BackendDocument,
)


def test_parser_input_object(parser_output_json_pdf) -> None:
    """
    Test that we can correctly instantiate the parser input object.

    Also test the methods on the parser input object.
    """
    # Instantiate the parser input object
    ParserInput.model_validate(parser_output_json_pdf)


def test_parser_output_object(
    parser_output_json_pdf: dict,
    parser_output_json_html: dict,
    parser_output_json_flat: dict,
) -> None:
    """
    Test that we correctly instantiate the parser output object.

    Also test the methods on the parser output object.
    """

    # Instantiate the parser output object
    ParserOutput.model_validate(parser_output_json_pdf)

    # Test the optional fields
    parser_output_empty_fields = parser_output_json_pdf.copy()
    parser_output_empty_fields["document_cdn_object"] = None
    parser_output_empty_fields["document_md5_sum"] = None

    ParserOutput.model_validate(parser_output_empty_fields)

    # Test the check html pdf metadata method
    parser_output_no_pdf_data = parser_output_json_pdf.copy()
    parser_output_no_pdf_data["pdf_data"] = None
    parser_output_no_pdf_data["document_content_type"] = CONTENT_TYPE_PDF

    parser_output_no_html_data = parser_output_json_pdf.copy()
    parser_output_no_html_data["html_data"] = None
    parser_output_no_html_data["document_content_type"] = CONTENT_TYPE_HTML

    # PDF data is set as the default
    parser_output_no_content_type = parser_output_json_pdf.copy()
    parser_output_no_content_type["document_content_type"] = None

    with pytest.raises(pydantic.ValidationError) as context:
        ParserOutput.model_validate(parser_output_no_content_type)
    assert (
        "html_data or pdf_data must be null for documents with no content type."
    ) in str(context.value)

    # PDF data is set as the default
    parser_output_not_known_content_type = parser_output_json_pdf.copy()
    parser_output_not_known_content_type["document_content_type"] = "application/msword"

    ParserOutput.model_validate(parser_output_not_known_content_type)

    # Test the text blocks property
    assert ParserOutput.model_validate(parser_output_json_pdf).text_blocks != []
    parser_output_no_data = parser_output_json_pdf.copy()
    parser_output_no_data["pdf_data"] = None
    parser_output_no_data["document_content_type"] = None
    assert ParserOutput.model_validate(parser_output_no_data).text_blocks == []

    # Test the to string method
    assert ParserOutput.model_validate(parser_output_json_pdf).to_string() != ""
    assert ParserOutput.model_validate(parser_output_no_data).to_string() == ""

    # Test the flip coords method
    parser_output = ParserOutput.model_validate(parser_output_json_pdf)
    original_text_blocks = parser_output.text_blocks
    assert parser_output.vertically_flip_text_block_coords() != original_text_blocks

    parser_output = ParserOutput.model_validate(parser_output_json_pdf)
    # Set as page number that doesn't exist in the page_metadata field to throw exception
    assert isinstance(parser_output.text_blocks[0], PDFTextBlock)
    parser_output.text_blocks[0].page_number = 123456  # type: ignore

    with pytest.raises(VerticalFlipError) as context:
        parser_output.vertically_flip_text_block_coords()
    assert str(context.value) == (
        f"Failed to flip text blocks for {parser_output.document_id}"
    )

    # Test the get_text_blocks method
    # The test html document has invalid html data so the text blocks should be empty
    parser_output = ParserOutput.model_validate(parser_output_json_html)
    assert parser_output.get_text_blocks() == []
    assert (
        parser_output.get_text_blocks(including_invalid_html=True)
        == parser_output.text_blocks
    )

    # Test that the get_text_blocks method works on pdfs. This test pdf has data so we
    # should get text blocks.
    parser_output = ParserOutput.model_validate(parser_output_json_pdf)
    text_blocks_raw = parser_output.get_text_blocks()
    assert text_blocks_raw
    text_blocks_include_invalid = parser_output.get_text_blocks(
        including_invalid_html=True
    )
    assert text_blocks_include_invalid
    text_blocks_not_include_invalid = parser_output.get_text_blocks(
        including_invalid_html=False
    )
    assert text_blocks_not_include_invalid
    assert (
        text_blocks_raw
        == text_blocks_include_invalid
        == text_blocks_not_include_invalid
    )

    # Test that the correct validation error is thrown during instantiation
    parser_output_json_bad_text_block = parser_output_json_pdf.copy()
    parser_output_json_bad_text_block["pdf_data"]["text_blocks"][0][
        "type"
    ] = "ThisBlockTypeDoesNotExist"
    with pytest.raises(pydantic.ValidationError) as context:
        ParserOutput.model_validate(parser_output_json_bad_text_block)
    assert ("1 validation error for ParserOutput\npdf_data.text_blocks.0.type") in str(
        context.value
    )

    # Test that we can correctly instantiate the parser output object from flat json.
    with pytest.raises(pydantic.ValidationError) as context:
        ParserOutput.model_validate(parser_output_json_flat)
    parser_output = ParserOutput.from_flat_json(parser_output_json_flat)


@pytest.mark.parametrize("null_text_blocks", [True, False])
@pytest.mark.parametrize("include_empty_text_blocks", [True, False])
def test_to_passage_level_json_method(
    parser_output_json_pdf: dict,
    parser_output_json_html: dict,
    null_text_blocks: bool,
    include_empty_text_blocks: bool,
) -> None:
    """
    Test that we can successfully create a passage level array from the text blocks.

    :param null_text_blocks: Whether to set the text blocks to None in the parser output
    :param include_empty_text_blocks: The setting for the `include_empty_text_blocks`
    kwarg in the `to_passage_level_json` method
    """
    expected_top_level_fields = set(
        [f"text_block.{k}" for k in list(TextBlock.model_fields.keys())]
        + [f"text_block.{k}" for k in list(HTMLTextBlock.model_fields.keys())]
        + [f"text_block.{k}" for k in list(PDFTextBlock.model_fields.keys())]
        + list(ParserOutput.model_fields.keys())
        + ["text_block.index", PDF_PAGE_METADATA_KEY]
    )

    expected_document_metadata_fields = set(BackendDocument.model_fields.keys())

    expected_html_data_fields = set(HTMLData.model_fields.keys())
    for field in HTML_DATA_PASSAGE_LEVEL_EXPAND_FIELDS:
        expected_html_data_fields.remove(field)

    expected_pdf_data_fields = set(PDFData.model_fields.keys())
    for field in PDF_DATA_PASSAGE_LEVEL_EXPAND_FIELDS:
        expected_pdf_data_fields.remove(field)

    parser_output_pdf = ParserOutput.model_validate(parser_output_json_pdf)
    assert parser_output_pdf.pdf_data is not None
    parser_output_html = ParserOutput.model_validate(parser_output_json_html)
    assert parser_output_html.html_data is not None

    if null_text_blocks:
        parser_output_pdf.pdf_data.text_blocks = []
        parser_output_html.html_data.text_blocks = []

    passage_level_array_pdf = parser_output_pdf.to_passage_level_json(
        include_empty=include_empty_text_blocks
    )
    passage_level_array_html = parser_output_html.to_passage_level_json(
        include_empty=include_empty_text_blocks
    )

    if null_text_blocks:
        if include_empty_text_blocks:
            assert len(passage_level_array_pdf) == 1
            assert len(passage_level_array_html) == 1
        else:
            assert len(passage_level_array_pdf) == 0
            assert len(passage_level_array_html) == 0

            # the resulting output is [] so we can stop the test here
            return
    else:
        assert len(passage_level_array_pdf) == len(parser_output_pdf.text_blocks)
        assert len(passage_level_array_html) == len(parser_output_html.text_blocks)

    for passage_level_array in [passage_level_array_pdf, passage_level_array_html]:
        first_doc_keys = set(passage_level_array[0].keys())
        for passage in passage_level_array:
            assert isinstance(passage, dict)
            assert set(passage.keys()) == first_doc_keys
            assert set(passage.keys()) == expected_top_level_fields
            assert (
                set(passage["document_metadata"].keys())
                == expected_document_metadata_fields
            )

            if passage["document_content_type"] == CONTENT_TYPE_PDF:
                if not (null_text_blocks and include_empty_text_blocks):
                    assert passage[PDF_PAGE_METADATA_KEY] is not None
                assert set(passage["pdf_data"].keys()) == expected_pdf_data_fields
            elif passage["document_content_type"] == CONTENT_TYPE_HTML:
                assert set(passage["html_data"].keys()) == expected_html_data_fields
            else:
                raise ValueError("Document content type must be either PDF or HTML")

    passage_level_array_pdf_first_doc = passage_level_array_pdf[0]
    passage_level_array_html_first_doc = passage_level_array_html[0]

    assert (
        passage_level_array_pdf_first_doc.keys()
        == passage_level_array_html_first_doc.keys()
    )


def test_rename_text_block_keys_static_method() -> None:
    """Test the _rename_text_block_keys static method of _ParserOutputMethodsMixin."""
    # Test with list input
    keys_list = ["text", "language", "type"]
    result_list = ParserOutput._rename_text_block_keys(keys_list)
    assert result_list == ["text_block.text", "text_block.language", "text_block.type"]

    # Test with dict input
    keys_dict = {"text": "foo", "language": "en"}
    result_dict = ParserOutput._rename_text_block_keys(keys_dict)
    assert result_dict == {"text_block.text": "foo", "text_block.language": "en"}

    # Test with invalid input raises ValueError
    with pytest.raises(ValueError):
        ParserOutput._rename_text_block_keys("invalid")  # type: ignore


def test_from_flat_json_classmethod(
    parser_output_json_flat: dict,
) -> None:
    """Test the from_flat_json classmethod of _ParserOutputMethodsMixin."""
    # from_flat_json should succeed where model_validate fails on flat data
    with pytest.raises(pydantic.ValidationError):
        ParserOutput.model_validate(parser_output_json_flat)

    # from_flat_json should handle flat JSON correctly
    parser_output = ParserOutput.from_flat_json(parser_output_json_flat)
    assert parser_output.document_id == parser_output_json_flat["document_id"]
    assert parser_output.text_blocks is not None
    assert len(parser_output.text_blocks) > 0


def test_get_page_metadata_by_page_number(
    parser_output_json_pdf: dict,
) -> None:
    """Test the get_page_metadata_by_page_number method of _ParserOutputMethodsMixin."""
    parser_output = ParserOutput.model_validate(parser_output_json_pdf)
    assert parser_output.pdf_data is not None

    # Get page 1 metadata (should exist)
    page_1_metadata = parser_output.get_page_metadata_by_page_number(1)
    assert page_1_metadata is not None
    assert page_1_metadata["page_number"] == 1

    # Get page 999 metadata (should not exist)
    page_999_metadata = parser_output.get_page_metadata_by_page_number(999)
    assert page_999_metadata is None

    # Test with HTML document (no PDF data)
    with open("tests/test_data/valid/test_html.json") as f:
        html_data = __import__("json").load(f)

    parser_output_html = ParserOutput.model_validate(html_data)
    page_metadata = parser_output_html.get_page_metadata_by_page_number(1)
    assert page_metadata is None


def test_rename_text_block_keys_v2_static_method() -> None:
    """Test the _rename_text_block_keys static method works for V2."""
    # Test with list input
    keys_list = ["text", "language", "type"]
    result_list = ParserOutputV2._rename_text_block_keys(keys_list)
    assert result_list == ["text_block.text", "text_block.language", "text_block.type"]

    # Test with dict input
    keys_dict = {"text": "foo", "language": "en"}
    result_dict = ParserOutputV2._rename_text_block_keys(keys_dict)
    assert result_dict == {"text_block.text": "foo", "text_block.language": "en"}


def test_get_page_metadata_by_page_number_v2(
    parser_output_json_pdf_v2: dict,
) -> None:
    """Test the get_page_metadata_by_page_number method of _ParserOutputMethodsMixin with V2."""
    parser_output = ParserOutputV2.model_validate(parser_output_json_pdf_v2)
    assert parser_output.pdf_data is not None
    assert isinstance(parser_output.pdf_data, PDFDataV2)

    # Get page 1 metadata (should exist)
    page_1_metadata = parser_output.get_page_metadata_by_page_number(1)
    assert page_1_metadata is not None
    assert page_1_metadata["page_number"] == 1

    # Get page 999 metadata (should not exist)
    page_999_metadata = parser_output.get_page_metadata_by_page_number(999)
    assert page_999_metadata is None


def test_parser_output_v2_object(
    parser_output_json_pdf_v2: dict,
) -> None:
    """Test that we correctly instantiate the ParserOutputV2 object."""
    # Instantiate the parser output object
    parser_output = ParserOutputV2.model_validate(parser_output_json_pdf_v2)
    assert parser_output.document_id == parser_output_json_pdf_v2["document_id"]
    assert parser_output.pdf_data is not None
    assert isinstance(parser_output.pdf_data, PDFDataV2)

    # Test text blocks are V2 type with string text
    assert len(parser_output.text_blocks) > 0
    assert isinstance(parser_output.text_blocks[0], PDFTextBlockV2)
    assert isinstance(parser_output.text_blocks[0].text, str)
    assert isinstance(parser_output.text_blocks[0].id, str)
    assert isinstance(parser_output.text_blocks[0].idx, int)
    assert isinstance(parser_output.text_blocks[0].pages, list)

    # Test to_string method works
    assert parser_output.to_string() != ""
    assert isinstance(parser_output.to_string(), str)
