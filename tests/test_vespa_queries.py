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
        ("parent_concept_ids_flat", "Q1,", "matches"),
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
        all_concepts_field_values = [
            concept[field] for concept in hit["fields"]["concepts"]
        ]
        if field == "parent_concept_ids_flat":
            parent_concept_ids: list[list[str]] = [
                parent_concept_ids_flat.split(",")
                for parent_concept_ids_flat in all_concepts_field_values
            ]
            assert any(
                [
                    value.replace(",", "") in parent_concept_id
                    for parent_concept_id in parent_concept_ids
                ]
            )
        else:
            assert value in all_concepts_field_values
