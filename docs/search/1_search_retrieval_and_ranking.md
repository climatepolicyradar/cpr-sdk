# Retrieval and Ranking: aka How a Search Works

## Contents

- [How search engines work](#how-search-engines-work)
  - [Retrieval](#retrieval)
  - [Ranking](#ranking)
- [How Vespa implements retrieval and ranking](#how-vespa-implements-retrieval-and-ranking)

## How search engines work

### Retrieval

At its most basic level, a search involves getting records which match some query from a database. This could be text, or a combination of text and some filtering. **We can call this part retrieval**. To demonstrate using SQL:

``` sql
-- Retrieval: search string
SELECT * FROM table_name WHERE text LIKE '%climate change act%'

-- Retrieval: search string and two filters
SELECT * FROM table_name 
WHERE text LIKE '%climate change act%'
AND country = 'GBR' 
AND date_published > '2000-01-01'
```

### Ranking

Built-for-purpose search engines will also have a ranking step, which involves ordering the retrieved records to be displayed to the end user according.

A ranking step assigns scores (higher is better) according to some sense of the perceived relevance (or other signal of usefulness) to the query. These could be based on:

- the number of times terms in the query appear in each record, giving a lower weight to terms that appear in most records ('climate' in our case)
- a semantic similarity score calculated by looking at the closeness of a vector representing the query and a vector representing each document
- a heuristic which is likely to, on average, give people better results (e.g. users are far more likely to care about the *most recent NDC* than previous versions)

Common ranking algorithms you might have heard of include [PageRank](https://en.wikipedia.org/wiki/PageRank), [BM25](https://en.wikipedia.org/wiki/Okapi_BM25), and [vector cosine similarity](https://www.elastic.co/search-labs/blog/text-similarity-search-with-vectors-in-elasticsearch).

Adding a basic ranking step to our example SQL query from above already starts to make things a bit more complicated.

``` sql
-- This SQL is already much more complicated, and we haven't even thought about the fact that "climate" appears in every document here!
SELECT *,
  (REGEXP_COUNT(text, 'climate', 'i') + 
   REGEXP_COUNT(text, 'change', 'i') + 
   REGEXP_COUNT(text, 'act', 'i')) as total_word_count
FROM table_name 
WHERE text ILIKE '%climate change act%'
  AND country = 'GBR' 
  AND date_published > '2000-01-01'
ORDER BY total_word_count DESC
```

## How Vespa implements retrieval and ranking

Vespa separates the concerns of retrieval and ranking into separate mechanisms, which live in different places in our code:

- Retrieval is done in the query, written in a language called YQL. The query lives in [yql_builder.py:YQLBuilder](https://github.com/climatepolicyradar/cpr-sdk/blob/main/src/cpr_sdk/yql_builder.py#L8) in the SDK.
- Ranking is done in the schema, which lives in the *navigator-infra* repo. Different methods of ranking can be listed in the same schema, in data structures called *rank profiles*.

A call to the Vespa API specifies a query, and which rank profile to use for ranking the results returned by this query. This is convenient in principle, as it lets us change how we rank results by swapping out different rank profiles, whilst leaving the query constant.

### A note on deploying changes to queries and rank profiles

Ranking algorithms are specified in rank profiles in schemas. Schemas need Vespa redeploys to update, which make it hard -> impossible to quickly tweak the overall search algorithm.

There's a way around this, and an important part of building rank profiles: **to allow the parameters in the rank profile to be controlled in the query**. More on this in the next docs page.
