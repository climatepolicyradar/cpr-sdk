import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
import json

import pandas as pd
import pytest
from datasets import Dataset as HuggingFaceDataset
from pydantic import ValidationError

from cpr_sdk.models import (
    BaseDocument,
    BlockType,
    CPRDocument,
    CPRDocumentMetadata,
    Dataset,
    GSTDocument,
    KnowledgeBaseIDs,
    Span,
    TextBlock,
)
from cpr_sdk.models.search import Document, Passage, MetadataFilter


@pytest.fixture
def test_dataset() -> Dataset:
    """Create dataset load_from_local and use as a fixture."""
    dataset = (
        Dataset(document_model=BaseDocument)
        .load_from_local("tests/test_data/valid")
        .add_metadata(
            target_model=CPRDocument,
            metadata_csv_path=Path("tests/test_data/CPR_metadata.csv"),
        )
    )

    assert len(dataset) == 3
    return dataset


@pytest.fixture
def test_dataset_languages(test_dataset) -> Dataset:
    """Defines specific languages for filtering on test_dataset"""
    test_dataset.documents[0].languages = ["fr"]
    test_dataset.documents[1].languages = ["en", "fr"]
    test_dataset.documents[2].languages = ["en"]
    return test_dataset


@pytest.fixture
def test_dataset_gst() -> Dataset:
    dataset = (
        Dataset(document_model=BaseDocument)
        .load_from_local("tests/test_data/valid_gst")
        .add_metadata(
            target_model=GSTDocument,
            metadata_csv_path=Path("tests/test_data/GST_metadata.csv"),
        )
    )
    assert len(dataset) == 1
    return dataset


@pytest.fixture
def test_document(test_dataset) -> BaseDocument:
    """Test PDF document."""

    return [
        doc
        for doc in test_dataset.documents
        if doc.document_id == "CCLW.executive.1003.0"
    ][0]


@pytest.fixture
def test_huggingface_dataset_cpr() -> HuggingFaceDataset:
    """Test HuggingFace dataset."""

    return HuggingFaceDataset.from_parquet(
        "tests/test_data/CPR_huggingface_data_sample.parquet"
    )


@pytest.fixture
def test_huggingface_dataset_gst() -> HuggingFaceDataset:
    """Test HuggingFace dataset."""

    return HuggingFaceDataset.from_parquet(
        "tests/test_data/GST_huggingface_data_sample.parquet"
    )


@pytest.fixture
def test_huggingface_dataset_cpr_passage_level_flat() -> HuggingFaceDataset:
    """Test HuggingFace dataset with flattened passage level schema."""
    dataset_dir = "tests/test_data/huggingface/cpr_passage_level_flat"
    dataset_files = os.listdir(dataset_dir)

    dfs = []
    for f in [os.path.join(dataset_dir, f) for f in dataset_files]:
        df = pd.read_parquet(f)
        dfs.append(df)

    df_all = pd.concat(dfs)

    return HuggingFaceDataset.from_pandas(df_all)


def test_dataset_metadata_df(test_dataset):
    metadata_df = test_dataset.metadata_df

    assert isinstance(metadata_df, pd.DataFrame)
    assert len(metadata_df) == len(test_dataset)
    assert metadata_df.shape[1] > 0

    for col in ("text_blocks", "document_metadata"):
        assert col not in metadata_df.columns

    for col in ("num_text_blocks", "num_pages"):
        assert col in metadata_df.columns

    for key in CPRDocumentMetadata.model_fields.keys() | {"publication_year"}:
        assert key in metadata_df.columns


@pytest.fixture
def test_spans_valid(test_document) -> list[Span]:
    """Test spans."""
    return [
        Span(
            document_id=test_document.document_id,
            text_block_text_hash="0c8f98b268ce90f7bcd7d9bee09863fa__81e9c9f2b0fe330c612f8605b6d1df98ffa8f8df35e98c4e2b6749bda61b8b63",
            start_idx=12,
            end_idx=23,
            text="Agriculture",
            sentence="Contact: DG Agriculture and\nRural Development",
            id="test sentence 1",
            type="TEST",
            pred_probability=1,
            annotator="pytest",
        ),
        Span(
            document_id=test_document.document_id,
            text_block_text_hash="a12ff2b1979c932f07792d57aa6aacdc__ea4e549f185fd2237fdac7719cf0c6d88fc939fa4aa5a3b5574f3f7b4804ac26",
            start_idx=8,
            end_idx=11,
            text="CAP",
            sentence="The new CAP maintains the two pillars, but increases the links\nbetween them, thus offering a more holistic and integrated approach\nto policy support.",
            id="test sentence 2",
            type="TEST",
            pred_probability=0.99,
            annotator="pytest",
        ),
        Span(
            document_id=test_document.document_id,
            text_block_text_hash="a12ff2b1979c932f07792d57aa6aacdc__ea4e549f185fd2237fdac7719cf0c6d88fc939fa4aa5a3b5574f3f7b4804ac26",
            start_idx=4,
            end_idx=7,
            text="new",
            sentence="The new CAP maintains the two pillars, but increases the links\nbetween them, thus offering a more holistic and integrated approach\nto policy support.",
            id="test sentence 2",
            type="TEST",
            pred_probability=0.99,
            annotator="pytest",
            kb_ids=KnowledgeBaseIDs(
                wikidata_id="Q42",
                wikipedia_title="Douglas_Adams",
            ),
        ),
    ]


@pytest.fixture
def test_spans_invalid(test_document) -> list[Span]:
    """Test spans."""
    return [
        # invalid document id
        Span(
            document_id="abcd",
            text_block_text_hash="0c8f98b268ce90f7bcd7d9bee09863fa__81e9c9f2b0fe330c612f8605b6d1df98ffa8f8df35e98c4e2b6749bda61b8b63",
            start_idx=0,
            end_idx=5,
            text="test2",
            sentence="test2 second",
            id="test sentence 2",
            type="TEST",
            pred_probability=0.99,
            annotator="pytest",
        ),
        # invalid text block hash
        Span(
            document_id=test_document.document_id,
            text_block_text_hash="1234",
            start_idx=0,
            end_idx=5,
            text="test3",
            sentence="test3 second",
            id="test sentence 3",
            type="TEST",
            pred_probability=0.99,
            annotator="pytest",
        ),
    ]


def test_dataset_filter_by_language(test_dataset_languages):
    """Test Dataset.filter_by_language."""
    dataset = test_dataset_languages.filter_by_language("en")

    assert len(dataset) == 1, f"found {[d.languages for d in dataset]}"
    assert dataset.documents[0].languages == ["en"]


def test_dataset_filter_by_language__not_strict(test_dataset_languages):
    """Test Dataset.filter_by_language."""
    dataset_2 = test_dataset_languages.filter_by_language("en", strict_match=False)

    assert len(dataset_2) == 2, f"found {[d.languages for d in dataset_2]}"
    assert dataset_2.documents[0].languages == ["en", "fr"]
    assert dataset_2.documents[1].languages == ["en"]


def test_dataset_filter_by_language__strict(test_dataset_languages):
    """Test Dataset.filter_by_language."""
    dataset_3 = test_dataset_languages.filter_by_language("en", strict_match=True)

    assert len(dataset_3) == 1, f"found {[d.languages for d in dataset_3]}"
    assert dataset_3.documents[0].languages == ["en"]


def test_dataset_filter_by_corpus(test_dataset):
    """Test Dataset.filter_by_corpus"""
    dataset = test_dataset.filter_by_corpus("UNFCCC")

    assert len(dataset) == 0

    dataset = test_dataset.filter_by_corpus("CCLW")

    assert len(dataset) == 3


def test_dataset_get_all_text_blocks(test_dataset):
    text_blocks = test_dataset.get_all_text_blocks()
    num_text_blocks = sum(
        [
            len(doc.text_blocks) if doc.text_blocks is not None else 0
            for doc in test_dataset.documents
        ]
    )

    assert len(text_blocks) == num_text_blocks

    text_blocks_with_document_context = test_dataset.get_all_text_blocks(
        with_document_context=True
    )
    assert len(text_blocks_with_document_context) == num_text_blocks
    assert all([isinstance(i[1], dict) for i in text_blocks_with_document_context])
    assert all(["text_blocks" not in i[1] for i in text_blocks_with_document_context])


def test_dataset_sample_text_blocks(test_dataset):
    text_blocks = test_dataset.sample_text_blocks(2)
    num_text_blocks = sum(
        [
            len(doc.text_blocks) if doc.text_blocks is not None else 0
            for doc in test_dataset.documents
        ]
    )

    assert len(text_blocks) == 2
    assert len(text_blocks) < num_text_blocks


def test_text_block_add_valid_spans(test_document, test_spans_valid):
    block_1 = test_document.text_blocks[0]
    block_2 = test_document.text_blocks[1]

    block_1_span_added = block_1._add_spans([test_spans_valid[0]])
    block_2_span_added = block_2._add_spans([test_spans_valid[1], test_spans_valid[2]])

    assert len(block_1_span_added.spans) == 1
    assert len(block_2_span_added.spans) == 2


def test_text_block_add_invalid_spans(test_document, test_spans_invalid, caplog):
    text_block_with_spans = test_document.text_blocks[0]._add_spans(
        [test_spans_invalid[0]], raise_on_error=False
    )

    # This will add the text block and warn that the incorrect document ID was ignored
    assert len(text_block_with_spans.spans) == 1

    # This won't add the text block, as the text block hash is incorrect
    text_block_with_spans = test_document.text_blocks[1]._add_spans(
        [test_spans_invalid[1]], raise_on_error=False
    )
    assert len(text_block_with_spans.spans) == 0

    # This will raise as the second text block can't be added
    with pytest.raises(ValueError):
        test_document.add_spans(test_spans_invalid, raise_on_error=True)


@pytest.mark.parametrize("raise_on_error", [True, False])
def test_add_spans_empty_text_block(
    test_document, test_spans_valid, test_spans_invalid, raise_on_error
):
    text_block = test_document.text_blocks[0]
    text_block.text = ""

    all_spans = test_spans_valid + test_spans_invalid

    with pytest.raises(ValueError):
        text_block._add_spans(all_spans, raise_on_error=raise_on_error)


@pytest.mark.parametrize("raise_on_error", [True, False])
def test_document_add_valid_spans(test_document, test_spans_valid, raise_on_error):
    document_with_spans = test_document.add_spans(
        test_spans_valid, raise_on_error=raise_on_error
    )

    added_spans = [
        span
        for text_block in document_with_spans.text_blocks
        for span in text_block.spans
    ]

    assert len(added_spans) == len(test_spans_valid)
    # Check that all spans are unique
    assert len(set(added_spans)) == len(test_spans_valid)


def test_document_add_invalid_spans(test_document, test_spans_invalid):
    document_with_spans = test_document.add_spans(
        test_spans_invalid, raise_on_error=False
    )

    added_spans = [
        span
        for text_block in document_with_spans.text_blocks
        for span in text_block.spans
    ]
    assert len(added_spans) == 0

    with pytest.raises(ValueError):
        test_document.add_spans(test_spans_invalid, raise_on_error=True)


@pytest.mark.parametrize("raise_on_error", [True, False])
def test_add_spans_empty_document(
    test_document, test_spans_valid, test_spans_invalid, raise_on_error
):
    """Document.add_spans() should always raise if the document is empty."""
    empty_document = test_document.model_copy()
    empty_document.text_blocks = None

    # When the document is empty, no spans should be added
    all_spans = test_spans_valid + test_spans_invalid

    with pytest.raises(ValueError):
        empty_document.add_spans(all_spans, raise_on_error=raise_on_error)


@pytest.mark.parametrize("raise_on_error", [True, False])
def test_dataset_add_spans(test_dataset, test_spans_valid, raise_on_error):
    dataset_with_spans = test_dataset.add_spans(
        test_spans_valid, raise_on_error=raise_on_error
    )
    added_spans = [
        span
        for document in dataset_with_spans.documents
        if document.text_blocks is not None
        for text_block in document.text_blocks
        for span in text_block.spans
    ]

    assert len(added_spans) == len(test_spans_valid)
    # Check that all spans are unique
    assert len(set(added_spans)) == len(test_spans_valid)


def test_span_validation(test_spans_valid):
    """Test that spans produce uppercase span IDs and types."""
    for span in test_spans_valid:
        assert span.id.isupper()
        assert span.type.isupper()


def test_document_get_text_block_window(test_document):
    """Test Document.get_text_block_window() for success and failure cases."""
    text_block = test_document.text_blocks[3]
    window = test_document.get_text_block_window(text_block, (-2, 2))
    assert window == test_document.text_blocks[1:6]

    text_block = test_document.text_blocks[0]
    window = test_document.get_text_block_window(text_block, (-2, 2))
    assert window == test_document.text_blocks[:3]

    with pytest.raises(ValueError):
        test_document.get_text_block_window(text_block, (2, 2))

    with pytest.raises(ValueError):
        test_document.get_text_block_window(text_block, (2, -2))


def test_document_get_text_window(test_document):
    """Test Document.get_text_window()."""
    text_block = test_document.text_blocks[3]
    text_window = test_document.get_text_window(text_block, (-2, 2))
    assert isinstance(text_window, str)
    assert len(text_window) > len(text_block.to_string())


def test_dataset_to_huggingface(test_dataset, test_dataset_gst):
    """Test that the HuggingFace dataset can be created."""
    dataset_hf = test_dataset.to_huggingface()
    dataset_gst_hf = test_dataset_gst.to_huggingface()
    assert isinstance(dataset_hf, HuggingFaceDataset)
    assert isinstance(dataset_gst_hf, HuggingFaceDataset)
    assert len(dataset_hf) == sum(
        len(doc.text_blocks) for doc in test_dataset.documents if doc.text_blocks
    )
    assert len(dataset_gst_hf) == sum(
        len(doc.text_blocks) for doc in test_dataset_gst.documents if doc.text_blocks
    )


@pytest.mark.parametrize("limit", [None, 2])
def test_dataset_from_huggingface_cpr(test_huggingface_dataset_cpr, limit):
    """Test that a CPR dataset can be created from a HuggingFace dataset."""
    dataset = Dataset(document_model=CPRDocument)._from_huggingface_parquet(
        test_huggingface_dataset_cpr, limit=limit
    )

    assert isinstance(dataset, Dataset)
    assert all(isinstance(doc, CPRDocument) for doc in dataset.documents)

    if limit is None:
        limit = len({d["document_id"] for d in test_huggingface_dataset_cpr})

        # Check huggingface dataset has the same number of text blocks as the dataset
        assert sum(len(doc.text_blocks or []) for doc in dataset.documents) == len(
            test_huggingface_dataset_cpr
        )

    # Check huggingface dataset has the same number of documents as the dataset or the set limit
    assert len(dataset) == limit


def test_dataset_from_huggingface_gst(test_huggingface_dataset_gst):
    """Test that a dataset can be created from a HuggingFace dataset."""
    dataset = Dataset(document_model=GSTDocument)._from_huggingface_parquet(
        test_huggingface_dataset_gst
    )

    assert isinstance(dataset, Dataset)
    assert all(isinstance(doc, GSTDocument) for doc in dataset.documents)

    assert any(doc.languages is not None for doc in dataset.documents)

    # Check hugingface dataset has the same number of documents as the dataset
    assert len(dataset) == len({d["document_id"] for d in test_huggingface_dataset_gst})

    # Check huggingface dataset has the same number of text blocks as the dataset
    assert sum(len(doc.text_blocks or []) for doc in dataset.documents) == len(
        test_huggingface_dataset_gst
    )


def test_dataset_from_huggingface_cpr_passage_level_flat(
    test_huggingface_dataset_cpr_passage_level_flat,
):
    dataset = Dataset(
        document_model=BaseDocument
    )._from_huggingface_passage_level_flat_parquet(
        test_huggingface_dataset_cpr_passage_level_flat
    )

    assert isinstance(dataset, Dataset)
    assert len(dataset.documents) > 0
    assert all(isinstance(doc, BaseDocument) for doc in dataset.documents)

    dataset = Dataset(
        document_model=BaseDocument
    )._from_huggingface_passage_level_flat_parquet(
        huggingface_dataset=test_huggingface_dataset_cpr_passage_level_flat, limit=1
    )

    assert isinstance(dataset, Dataset)
    assert len(dataset.documents) > 0
    assert all(isinstance(doc, BaseDocument) for doc in dataset.documents)

    dataset_document_ids = {doc.document_id for doc in dataset.documents}
    assert len(dataset_document_ids) == 1


def test_dataset_indexable(test_dataset):
    """Tests that the dataset can be indexed to get documents"""
    assert isinstance(test_dataset[0], BaseDocument)


def test_dataset_iterable(test_dataset):
    """Tests that the dataset is an iterable"""
    assert isinstance(test_dataset, Iterable)
    for doc in test_dataset:
        assert isinstance(doc, BaseDocument)


def test_display_text_block(test_document, test_spans_valid):
    document_with_spans = test_document.add_spans(
        test_spans_valid, raise_on_error=False
    )

    block = [block for block in document_with_spans.text_blocks if block.spans][0]

    # TODO: test 'span' as well as 'ent' display style
    block_html = block.display("ent")

    assert isinstance(block_html, str)
    assert len(block_html) > 0
    assert block_html.startswith("<div")


def test_text_block_hashable(test_document):
    doc = test_document

    set(doc.text_blocks)

    first_block_hash = doc.text_blocks[0].__hash__()
    assert isinstance(first_block_hash, int)

    comparison_block = TextBlock(**doc.text_blocks[0].model_dump())

    assert comparison_block == doc.text_blocks[0]

    comparison_block.text_block_id = "0"

    assert comparison_block != doc.text_blocks[0]


def test_dataset_sample(test_dataset):
    dataset = test_dataset

    sample_1 = dataset.sample(1, random_state=20)
    sample_2 = dataset.sample(1, random_state=20)
    sample_3 = dataset.sample(1, random_state=40)

    assert len(sample_1) == 1
    assert sample_1.documents == sample_2.documents
    assert sample_1.documents != sample_3.documents

    sample_4 = dataset.sample(len(dataset) * 2, random_state=20)

    assert len(sample_4) == len(dataset)

    sample_5 = dataset.sample(1 / 3)

    assert len(sample_5) == len(dataset) / 3

    with pytest.raises(
        ValueError,
        match=r"n should be a float in \(0.0, 1.0\) or a positive integer. Provided value: -1",
    ):
        _ = dataset.sample(-1)


def test_dataset_dict(test_dataset):
    dataset = test_dataset

    d2 = Dataset(**dataset.dict())

    for k, v in dataset.__dict__.items():
        assert v == getattr(d2, k)

    d3_dict = dataset.dict(exclude=["documents", "document_model"])

    assert "documents" not in d3_dict.keys()
    assert "document_model" not in d3_dict.keys()

    d4_dict = dataset.dict(exclude="documents")

    assert "documents" not in d4_dict.keys()


def test_document_to_markdown(test_document):
    md = test_document.to_markdown(show_debug_elements=False)

    assert isinstance(md, str)
    assert len(md) > 0

    # Hide text elements - should be shorter
    md_debug = test_document.to_markdown(
        show_debug_elements=False, debug_only_types={BlockType.TEXT}
    )
    assert len(md_debug) < len(md)


def test_metadatafilters() -> None:
    """Validate that the metadata filters are correctly built."""
    MetadataFilter(name="test", value="test")

    with pytest.raises(ValidationError):
        MetadataFilter.model_validate({"name": "test"})

    with pytest.raises(ValidationError):
        MetadataFilter.model_validate({"value": "test"})


def test_vespa_concept_instantiation() -> None:
    """
    Test that the Vespa concept can be instantiated correctly.

    There is a relationship to enforce between the parent_concepts objects and the
    parent_concept_ids_flat fields.
    """
    Passage.Concept(
        name="test_concept_name_1",
        id="test_concept_id_1.1",
        parent_concepts=[
            {"id": "test_parent_concept_id_1", "name": "test_parent_concept_name_1"}
        ],
        parent_concept_ids_flat="test_parent_concept_id_1",
        start=1,
        end=10,
        model="test_model_1",
        timestamp=datetime.now(),
    )

    with pytest.raises(ValidationError):
        Passage.Concept(
            name="test_concept_name_2",
            id="test_concept_id_2.1",
            parent_concepts=[
                {"id": "test_parent_concept_id_2", "name": "test_parent_concept_name_2"}
            ],
            parent_concept_ids_flat="test_parent_concept_id_1",
            start=1,
            end=10,
            model="test_model_2",
            timestamp=datetime.now(),
        )


def test_vespa_concept_json_conversion() -> None:
    """Test that the Vespa concept can be converted to json correctly."""
    json.dumps(
        Passage.Concept(
            name="test_concept_name_1",
            id="test_concept_id_1.1",
            parent_concepts=[
                {"id": "test_parent_concept_id_1", "name": "test_parent_concept_name_1"}
            ],
            parent_concept_ids_flat="test_parent_concept_id_1",
            start=1,
            end=10,
            model="test_model_1",
            timestamp=datetime.now(),
        ).model_dump(mode="json")
    )


def test_vespa_passage_json() -> None:
    """Test that Vespa passage spans can be parsed and converted to JSON correctly."""
    # Load the test fixture
    with open(
        "tests/local_vespa/test_documents/document_passage.AF.document.009MHNWR.n0007.json"
    ) as f:
        passages_data = json.load(f)

    # Find a passage that has spans
    passage_with_spans = None
    for passage_data in passages_data:
        if passage_data.get("fields", {}).get("text_block_id") == "248":
            passage_with_spans = passage_data
            break

    assert passage_with_spans is not None, "No passage with spans found in test data"

    expected_passage = Passage(
        family_name=None,
        family_description=None,
        family_source=None,
        family_import_id=None,
        family_slug=None,
        family_category=None,
        family_publication_ts=None,
        family_geography=None,
        family_geographies=[],
        document_import_id=None,
        document_slug=None,
        document_languages=[],
        document_content_type=None,
        document_cdn_object=None,
        document_source_url=None,
        document_title=None,
        corpus_type_name=None,
        corpus_import_id=None,
        metadata=None,
        concepts=[
            Passage.Concept(
                id="Q704",
                name="women and minority genders",
                parent_concepts=[{"name": "", "id": "Q1170"}],
                parent_concept_ids_flat="Q1170,",
                model='KeywordClassifier("women and minority genders")',
                end=133,
                start=128,
                timestamp=datetime(2025, 6, 5, 14, 4, 52, 719991),
            )
        ],
        relevance=0.0017429193899782135,
        rank_features=None,
        concept_counts=None,
        text_block="5. While the project strengthened resilience to climate change at all levels and worked towards increasing the participation of women, it is still necessary to further enhance their active participation in actions linked to climate change adaptation and water resources management beyond what was observed in 2015 in pilots designed at the municipal level.",
        text_block_id="248",
        text_block_type="BlockType.TEXT",
        text_block_page=10,
        text_block_coords=[
            (88.3583984375, 268.81201171875),
            (540.8280029296875, 268.81201171875),
            (540.8280029296875, 348.5592041015625),
            (88.3583984375, 348.5592041015625),
        ],
        spans=[
            Passage.Span(
                start=128,
                end=133,
                concepts_v2=[
                    Passage.Span.ConceptV2(
                        concept_id="jr3s4jsa",
                        concept_wikibase_id="Q503",
                        classifier_id="5ul69f0j",
                    )
                ],
            )
        ],
    )

    # Parse it into a Passage object
    passage = Passage.from_vespa_response(passage_with_spans)
    assert passage == expected_passage

    # Dump it to JSON to ensure serialisation works
    passage_json = passage.model_dump(mode="json")

    # Load it back to verify round-trip
    assert Passage.model_validate(passage_json) == expected_passage


def test_vespa_document_json() -> None:
    """Test that Vespa document can be parsed and converted to JSON correctly."""
    with open(
        "tests/local_vespa/test_documents/family_document.AF.document.009MHNWR.n0007.json"
    ) as f:
        document_data = json.load(f)

    expected_document = Document(
        family_name="Addressing Climate Change Risks on Water Resources in Honduras: Increased Systemic Resilience and Reduced Vulnerability of the Urban Poor",
        family_description="The objective of the project is to increase resilience to climate change and water-related risks for the most vulnerable population in Honduras through pilot activities and an overarching intervention to mainstream climate change considerations into water sector policies. The specific project objectives included: Strengthen institutional structures to mainstream climate risks into water resources management, national planning; Assist in safeguarding water supplies of Tegucigalpa metro area against water scarcity and extreme climate events; Build capacity and outreach to enable all stakeholders to respond to long-term climate change impacts",
        family_source="AF",
        family_import_id="AF.family.009MHNWR.0",
        family_slug="addressing-climate-change-risks-on-water-resources-in-honduras-increased-systemic-resilience-and-reduced-vulnerability-of-the-urban-poor_df09",
        family_category="MCF",
        family_publication_ts=datetime(2010, 9, 17, 0, 0, tzinfo=timezone.utc),
        family_geography="HND",
        family_geographies=["HND"],
        document_import_id="AF.document.009MHNWR.n0007",
        document_slug="final-evaluation-report_8dec",
        document_languages=["English"],
        document_content_type="application/pdf",
        document_cdn_object="HND/2010/addressing-climate-change-risks-on-water-resources-in-honduras-increased-systemic-resilience-and-reduced-vulnerability-of-the-urban-poor_0996c52e8a82f6caf973962e8972797c.pdf",
        document_source_url="https://fifspubprd.azureedge.net/afdocuments/project/62/4399_AF_Honduras_Terminal%20eval%20report_May%2017.pdf",
        document_title="Final evaluation report",
        corpus_type_name="AF",
        corpus_import_id="MCF.corpus.AF.n0000",
        metadata=[
            {"name": "family.region", "value": "Latin America & Caribbean"},
            {"name": "family.sector", "value": "Water management"},
            {"name": "family.status", "value": "Project Completed"},
            {"name": "family.project_id", "value": "009MHNWR"},
            {
                "name": "family.project_url",
                "value": "https://www.adaptation-fund.org/project/addressing-climate-change-risks-on-water-resources-in-honduras-increased-systemic-resilience-and-reduced-vulnerability-of-the-urban-poor/",
            },
            {"name": "family.implementing_agency", "value": "UN Development Programme"},
            {"name": "family.project_value_fund_spend", "value": "5620300"},
            {"name": "family.project_value_co_financing", "value": "0"},
        ],
        concepts=None,
        relevance=None,
        rank_features=None,
        concept_counts={
            "Q1167:people with limited assets": 9,
            "Q1276:direct investment": 2,
            "Q1277:fees and charges": 1,
            "Q1281:codes and standards": 1,
            "Q1282:zoning and spatial planning": 11,
            "Q1286:early warning system": 3,
            "Q1343:climate finance": 21,
            "Q1362:climate fund": 21,
            "Q374:extreme weather": 19,
            "Q404:terrestrial risk": 14,
            "Q676:marginalized ethnicity": 1,
            "Q684:indigenous people": 1,
            "Q695:youth": 2,
            "Q701:people on the move": 1,
            "Q704:women and minority genders": 14,
            "Q715:tax": 2,
            "Q760:extractive sector": 6,
            "Q762:energy supply sector": 1,
            "Q763:environmental management sector": 5,
            "Q764:construction sector": 6,
            "Q765:trade sector": 2,
            "Q769:information communication technology sector": 3,
            "Q774:education sector": 3,
            "Q775:public sector": 23,
            "Q779:finance and insurance sector": 9,
            "Q786:agriculture sector": 9,
            "Q787:forestry sector": 4,
            "Q788:fishing sector": 1,
            "Q818:water management sector": 30,
            "Q856:healthcare sector": 4,
            "Q956:societal impact": 12,
            "Q973:slow onset event": 1,
            "Q986:geohazard": 4,
        },
        concepts_v2=[
            Document.ConceptV2(
                concept_id="b836x3e3",
                concept_wikibase_id="Q506",
                classifier_id="z664n8h8",
                count=9,
            ),
            Document.ConceptV2(
                concept_id="b836x3e3",
                concept_wikibase_id="Q506",
                classifier_id="3k993hvh",
                count=2,
            ),
            Document.ConceptV2(
                concept_id="mbu7hjcq",
                concept_wikibase_id="Q523",
                classifier_id="t9kpjjab",
                count=1,
            ),
            Document.ConceptV2(
                concept_id="3j4qadvf",
                concept_wikibase_id="Q528",
                classifier_id="zjmxvf2p",
                count=1,
            ),
            Document.ConceptV2(
                concept_id="2gvuuvnw",
                concept_wikibase_id="Q789",
                classifier_id="anfhdhxm",
                count=1,
            ),
            Document.ConceptV2(
                concept_id="mtg8hg7x",
                concept_wikibase_id="Q516",
                classifier_id="6vyhx47j",
                count=3,
            ),
            Document.ConceptV2(
                concept_id="rns7bps4",
                concept_wikibase_id="Q500",
                classifier_id="nd9bzgv5",
                count=1,
            ),
            Document.ConceptV2(
                concept_id="awgxsauj",
                concept_wikibase_id="Q501",
                classifier_id="gjx26rb3",
                count=1,
            ),
            Document.ConceptV2(
                concept_id="nhhzwfva",
                concept_wikibase_id="Q374",
                classifier_id="4xdbmh5t",
                count=9,
            ),
            Document.ConceptV2(
                concept_id="xaqt5dpj",
                concept_wikibase_id="Q502",
                classifier_id="28zh5bs4",
                count=4,
            ),
            Document.ConceptV2(
                concept_id="ca7awjjg",
                concept_wikibase_id="Q525",
                classifier_id="3snuveg6",
                count=1,
            ),
            Document.ConceptV2(
                concept_id="egnxgkd8",
                concept_wikibase_id="Q524",
                classifier_id="46rgzfnu",
                count=1,
            ),
            Document.ConceptV2(
                concept_id="bahk6avj",
                concept_wikibase_id="Q518",
                classifier_id="fqez4pu2",
                count=2,
            ),
            Document.ConceptV2(
                concept_id="9tskhyxb",
                concept_wikibase_id="Q527",
                classifier_id="3ehtcmgr",
                count=1,
            ),
            Document.ConceptV2(
                concept_id="jr3s4jsa",
                concept_wikibase_id="Q503",
                classifier_id="zqmpxwvx",
                count=4,
            ),
            Document.ConceptV2(
                concept_id="w7s2zf4v",
                concept_wikibase_id="Q517",
                classifier_id="f5597c7c",
                count=2,
            ),
            Document.ConceptV2(
                concept_id="zhj5vezx",
                concept_wikibase_id="Q508",
                classifier_id="hr5fnv8a",
                count=6,
            ),
            Document.ConceptV2(
                concept_id="ah84cx9r",
                concept_wikibase_id="Q526",
                classifier_id="b9htgybc",
                count=1,
            ),
            Document.ConceptV2(
                concept_id="3nj2mmps",
                concept_wikibase_id="Q510",
                classifier_id="aukd7tza",
                count=5,
            ),
            Document.ConceptV2(
                concept_id="3h6q3tmx",
                concept_wikibase_id="Q509",
                classifier_id="6anbektb",
                count=6,
            ),
            Document.ConceptV2(
                concept_id="9nzh8ngn",
                concept_wikibase_id="Q519",
                classifier_id="y8t4ztbx",
                count=2,
            ),
            Document.ConceptV2(
                concept_id="rfrb6hue",
                concept_wikibase_id="Q514",
                classifier_id="3dhbaxdc",
                count=3,
            ),
            Document.ConceptV2(
                concept_id="q5dt2x5y",
                concept_wikibase_id="Q515",
                classifier_id="jd5bafz5",
                count=3,
            ),
            Document.ConceptV2(
                concept_id="bqm9freh",
                concept_wikibase_id="Q123",
                classifier_id="arevhgbf",
                count=3,
            ),
            Document.ConceptV2(
                concept_id="8gpdnspp",
                concept_wikibase_id="Q507",
                classifier_id="cqt336zm",
                count=9,
            ),
            Document.ConceptV2(
                concept_id="kynzgerh",
                concept_wikibase_id="Q505",
                classifier_id="a2u6z83b",
                count=9,
            ),
            Document.ConceptV2(
                concept_id="tntx3gy5",
                concept_wikibase_id="Q512",
                classifier_id="ukwxdeh3",
                count=4,
            ),
            Document.ConceptV2(
                concept_id="xzknej96",
                concept_wikibase_id="Q521",
                classifier_id="z6txkdwk",
                count=1,
            ),
            Document.ConceptV2(
                concept_id="r7nmt2kg",
                concept_wikibase_id="Q456",
                classifier_id="ebvzbghd",
                count=0,
            ),
            Document.ConceptV2(
                concept_id="w3wrtq64",
                concept_wikibase_id="Q511",
                classifier_id="h5n4vrvw",
                count=4,
            ),
            Document.ConceptV2(
                concept_id="dw5brr9c",
                concept_wikibase_id="Q504",
                classifier_id="q2b4mq7k",
                count=2,
            ),
            Document.ConceptV2(
                concept_id="w9z6qa9t",
                concept_wikibase_id="Q522",
                classifier_id="d2gk7ksc",
                count=1,
            ),
            Document.ConceptV2(
                concept_id="gmerqh8z",
                concept_wikibase_id="Q513",
                classifier_id="fz3ejy99",
                count=4,
            ),
        ],
    )

    # Parse it into a Document object
    document = Document.from_vespa_response(document_data)
    assert document == expected_document

    # Dump it to JSON to ensure serialisation works
    document_json = document.model_dump(mode="json")

    # Load it back to verify round-trip
    assert Document.model_validate(document_json) == expected_document
