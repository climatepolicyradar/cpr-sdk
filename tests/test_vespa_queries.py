import pytest
from vespa.io import VespaQueryResponse


@pytest.mark.vespa
def test_concepts(test_vespa) -> None:
    """Test that we can retrieve concepts from a document."""
    response: VespaQueryResponse = test_vespa.client.query(
        yql="select * from document_passage "
        "where concepts contains "
        'sameElement(name contains "sectors")'
    )

    assert response.is_successful()
    assert len(response.hits) > 0
    for hit in response.hits:
        assert "sectors" in [concept["name"] for concept in hit["fields"]["concepts"]]

    response: VespaQueryResponse = test_vespa.client.query(
        yql="select * from document_passage "
        "where concepts contains "
        'sameElement(name contains "sectors", parent_ids contains "concept_0")'
    )

    assert response.is_successful()
    assert len(response.hits) > 0
