import pydantic
import pytest
from cpr_sdk.parser_models import (
    HTMLData,
    HTMLTextBlock,
    ParserInput,
    ParserOutput,
    PDFData,
    PDFTextBlock,
    TextBlock,
    VerticalFlipError,
    PDF_PAGE_METADATA_KEY
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

    with pytest.raises(pydantic.ValidationError) as context:
        ParserOutput.model_validate(parser_output_no_pdf_data)
    assert "pdf_data must be set for PDF documents" in str(context.value)

    parser_output_no_html_data = parser_output_json_pdf.copy()
    parser_output_no_html_data["html_data"] = None
    parser_output_no_html_data["document_content_type"] = CONTENT_TYPE_HTML

    with pytest.raises(pydantic.ValidationError) as context:
        ParserOutput.model_validate(parser_output_no_html_data)
    assert "html_data must be set for HTML documents" in str(context.value)

    parser_output_no_content_type = parser_output_json_pdf.copy()
    # PDF data is set as the default
    parser_output_no_content_type["document_content_type"] = None

    with pytest.raises(pydantic.ValidationError) as context:
        ParserOutput.model_validate(parser_output_no_content_type)
    assert (
        "html_data and pdf_data must be null for documents with no content type."
    ) in str(context.value)

    parser_output_not_known_content_type = parser_output_json_pdf.copy()
    # PDF data is set as the default
    parser_output_not_known_content_type["document_content_type"] = "not_known"

    with pytest.raises(pydantic.ValidationError) as context:
        ParserOutput.model_validate(parser_output_not_known_content_type)
    assert (
        "html_data and pdf_data must be null for documents with no content type."
    ) in str(context.value)

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


def test_to_passage_level_json_method(
    parser_output_json_pdf: dict,
    parser_output_json_html: dict,
) -> None:
    """Test that we can successfully create a passage level array from the text blocks."""
    expected_top_level_fields = set(
        list(TextBlock.model_fields.keys())
        + list(HTMLTextBlock.model_fields.keys())
        + list(PDFTextBlock.model_fields.keys())
        + list(ParserOutput.model_fields.keys())
        + ["block_index", PDF_PAGE_METADATA_KEY]
    )
    expected_document_metadata_fields = set(list(BackendDocument.model_fields.keys()))
    expected_html_data_fields = set(list(HTMLData.model_fields.keys()))
    expected_html_data_fields.remove("text_blocks")
    expected_pdf_data_fields = set(list(PDFData.model_fields.keys()))
    expected_pdf_data_fields.remove("text_blocks")
    expected_pdf_data_fields.remove("page_metadata")

    parser_output_pdf = ParserOutput.model_validate(parser_output_json_pdf)
    passage_level_array_pdf = parser_output_pdf.to_passage_level_json()

    parser_output_html = ParserOutput.model_validate(parser_output_json_html)
    passage_level_array_html = parser_output_html.to_passage_level_json()

    assert len(passage_level_array_pdf) == len(parser_output_pdf.text_blocks)
    assert len(passage_level_array_html) == len(parser_output_html.text_blocks)

    for passage_level_array in [passage_level_array_pdf, passage_level_array_html]:
        first_doc_keys = set(passage_level_array[0].keys())
        for passage in passage_level_array:
            assert set(passage.keys()) == first_doc_keys
            assert isinstance(passage, dict)
            assert set(passage.keys()) == expected_top_level_fields
            assert (
                set(passage["document_metadata"].keys())
                == expected_document_metadata_fields
            )

            if passage["document_content_type"] == CONTENT_TYPE_PDF:
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
