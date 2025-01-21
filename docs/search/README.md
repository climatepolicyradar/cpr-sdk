# Developing on Search

The docs in this directory cover all things technical about search:

1. [How retrieval and ranking work when you use a search engine, and how this works in Vespa](./1_search_retrieval_and_ranking.md)
2. [What Vespa schemas do](./2_cpr_product_schemas.md)
3. [How our searches work](./3_cpr_searches.md)
4. [Search intention testing](./4_search_intention_tests.md)

## Prerequisites

To be able to develop on search, you'll want to be able to fire requests at our production Vespa instance from your machine. (We don't use staging here, as its data is not kept up-to-date with what's in production).

Instructions for creating a read-only certificate are in the [navigator infra repo here](https://github.com/climatepolicyradar/navigator-infra/tree/main/vespa#how-to-add-a-certificate-for-vespa-cloud-access).
