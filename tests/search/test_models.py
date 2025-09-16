from cpr_sdk.search.models import Concept, JsonDict, WikibaseId


def test_concept_from_response_hit():
    response_hit: JsonDict = JsonDict(
        {
            "id": "id:doc_search:concept::w2m7ymf7",
            "relevance": 0.0,
            "source": "family-document-passage",
            "fields": {
                "sddocname": "concept",
                "documentid": "id:doc_search:concept::w2m7ymf7",
                "id": "w2m7ymf7",
                "wikibase_id": "Q290",
                "wikibase_url": "https://wikibase.example.org/wiki/Item:Q290",
                "preferred_label": "pollution",
                "subconcept_of": ["hzaw3hdg"],
                "recursive_has_subconcept": [],
            },
        }
    )

    assert Concept(
        id="w2m7ymf7",
        wikibase_id=WikibaseId(numeric=290),
        wikibase_url=AnyHttpUrl("https://wikibase.example.org/wiki/Item:Q290"),
        preferred_label="pollution",
        description=None,
        definition=None,
        alternative_labels=[],
        negative_labels=[],
        subconcept_of=["hzaw3hdg"],
        has_subconcept=[],
        related_concepts=[],
        recursive_concept_of=None,
        recursive_has_subconcept=[],
        response_raw=JsonDict(
            {
                "id": "id:doc_search:concept::w2m7ymf7",
                "relevance": 0.0,
                "source": "family-document-passage",
                "fields": {
                    "sddocname": "concept",
                    "documentid": "id:doc_search:concept::w2m7ymf7",
                    "id": "w2m7ymf7",
                    "wikibase_id": "Q290",
                    "wikibase_url": "https://wikibase.example.org/wiki/Item:Q290",
                    "preferred_label": "pollution",
                    "subconcept_of": ["hzaw3hdg"],
                    "recursive_has_subconcept": [],
                },
            }
        ),
    ) == Concept.from_vespa_response(response_hit)
