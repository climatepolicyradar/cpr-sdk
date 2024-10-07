import json
from random import choice, randint

with open(
    "/Users/markcottam/PycharmProjects/cpr-sdk/tests/local_vespa/test_documents/document_passage.json",
    "r",
) as f:
    data = json.load(f)

data_new = []

concepts = ["sectors", "environment", "just transition", "floods"]

for i, d_value in enumerate(data):
    concept = choice(concepts)
    concept_2 = choice(concepts)
    concepts_ = [
        {
            "name": concept,
            "id": f"concept_{i}_{i}",
            "parent_concepts": [{"id": i, "name": f"Q{i}"}],
            "parent_concept_ids_flat": f"Q{i},Q{i+1}",
            "start": randint(0, 10),
            "end": randint(11, 20),
            "model": f"{concept}_model",
            "timestamp": "2024-09-26T16:15:39.817896",
        },
        {
            "name": concept_2,
            "id": f"concept_{i}_{i}",
            "parent_concepts": [{"id": i+1, "name": f"Q{i+1}"}],
            "parent_concept_ids_flat": f"Q{i+1},Q{i+2}",
            "start": randint(11, 20),
            "end": randint(20, 40),
            "model": f"{concept_2}_model",
            "timestamp": "2024-09-26T16:15:39.817896",
        },
    ]
    d_value["fields"]["concepts"] = concepts_
    data_new.append(d_value)

with open(
    "/Users/markcottam/PycharmProjects/cpr-sdk/tests/local_vespa/test_documents/document_passage.json",
    "w",
) as f:
    json.dump(data_new, f, indent=2)
