import pytest
from vespa.io import VespaQueryResponse


@pytest.mark.vespa
@pytest.mark.parametrize(
    "field,value",
    [
        ("name", "sectors"),
        ("id", "concept_137_137"),
        ("model", "environment_model"),
        ("timestamp", "2024-09-26T16:15:39.817896"),
    ],
)
def test_concepts(test_vespa, field, value) -> None:
    """Test that we can retrieve concepts from a document."""
    response: VespaQueryResponse = test_vespa.client.query(
        yql="select * from document_passage "
        "where concepts contains "
        f'sameElement({field} contains "{value}")'
    )

    assert response.is_successful()
    assert len(response.hits) > 0
    for hit in response.hits:
        assert value in [concept[field] for concept in hit["fields"]["concepts"]]
