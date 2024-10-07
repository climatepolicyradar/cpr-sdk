import json 

with open("/Users/markcottam/PycharmProjects/cpr-sdk/tests/local_vespa/test_documents/document_passage.json") as f:
    data = json.load(f)

data_new = [] 
for i, x in enumerate(data):
    concepts_new = []
    for concept in x['fields']['concepts']:
        # del concept["parent_names"] 
        # del concept["parent_ids"] 
        concept["parent_concepts"] = [
            {
                "id": i,
                "name": f"Q{i}"
            },
            {
                "id": i+1,
                "name": f"Q{i+1}"
            }
        ]
        concept["parent_concept_ids_flat"] = f"Q{i},Q{i+1},"
        concepts_new.append(concept)
    x['fields']['concepts'] = concepts_new
    data_new.append(x)

with open("/Users/markcottam/PycharmProjects/cpr-sdk/tests/local_vespa/test_documents/document_passage.json", "w") as f:
    json.dump(data_new, indent=2, fp=f)
