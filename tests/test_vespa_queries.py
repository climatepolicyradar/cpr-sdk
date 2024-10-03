import pytest
from vespa.io import VespaQueryResponse


@pytest.mark.vespa
@pytest.mark.parametrize(
    "field,value,search_term",
    [
        ("name", "sectors", "contains"),
        ("id", "concept_137_137", "contains"),
        ("model", "environment_model", "contains"),
        ("timestamp", "2024-09-26T16:15:39.817896", "contains"),
        ("parent_concept_ids_flat", "Q1", "matches"),
    ],
)
def test_concepts(test_vespa, field, search_term, value) -> None:
    """Test that we can retrieve concepts from a document."""
    response: VespaQueryResponse = test_vespa.client.query(
        yql="select * from document_passage "
        "where concepts contains "
        f'sameElement({field} {search_term} "{value}")'
    )

    assert response.is_successful()
    assert len(response.hits) > 0
    for hit in response.hits:
        assert value in [concept[field] for concept in hit["fields"]["concepts"]]
