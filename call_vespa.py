from cpr_sdk.search_adaptors import SearchParameters, VespaSearchAdapter

search_adatper = VespaSearchAdapter(
    instance_url="https://db530e3a.e242b833.z.vespa-app.cloud/",
    cert_directory="/Users/markcottam/PycharmProjects/navigator-data-pipeline/certs/",
)

response = search_adatper.search(
    parameters=SearchParameters(query_string="Michal", limit=1, exact_match=True)
)

print("Staging instance!")
print(f"Geographies: {response.families[0].hits[0].family_geographies}")
print(f"Geography: {response.families[0].hits[0].family_geography}")

# search_adatper = VespaSearchAdapter(
#     instance_url="http://0.0.0.0:19071",
# )

# response = search_adatper.search(
#     parameters=SearchParameters(query_string="the", limit=1, exact_match=True)
# )

# print("Local instance!")
# print(f"Geographies: {response.families[0].hits[0].family_geographies}")
# print(f"Geography: {response.families[0].hits[0].family_geography}")


# breakpoint()

# No exact_match = True led to the following error
# vespa.exceptions.VespaError: [{'code': 3, 'summary': 'Illegal query', 'message': "Could not set 'ranking.features.query(query_embedding)' to 'embed(msmarco-distilbert-dot-v5, @query_string)': Can't find embedder 'msmarco-distilbert-dot-v5'. Available embedder ids are 'com.yahoo.language.provider.DefaultEmbedderProvider'."}]

# Confirmed we are getting no geographies when performing a search with the following:
# SearchParameters(query_string="the", limit=1, exact_match=True)
