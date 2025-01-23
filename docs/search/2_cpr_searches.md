# How CPR Product Searches Work

The overall mechanics of each product search are straightforward, but *not really in line with what the user sees on our apps*. They make use of the fact that we have two schemas: `family_document` (data about documents) and `document_passage` (data about passages withing documents), which both share a `family_import_id`.

When a user performs a search, one search is done on each schema:

- in the `family_document` schema, *documents* are retrieved and ranked by their family names and family descriptions;
- in the `document_passage` schema, *passages* are retrieved and ranked by their text.

The results are then combined and grouped by family import ID. Families are ordered by *the maximum score of any **hit** within them*, where a hit is what we call a document or passage in the SDK code.

You can see this ranking take place by using the [search CLI](../../src/cpr_sdk/cli/search.py).

<details>
<summary><b>The families are ranked, with a varying number of hits per family.</b></summary>

``` log
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                               Families                               ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━┳━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┓
┃ Family Name        ┃ Geography ┃ Score  ┃ Hits ┃ Slug                ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━╇━━━━━━╇━━━━━━━━━━━━━━━━━━━━━┩
│ Pilot Project for  │ BRA       │ 46.056 │ 10   │ pilot-project-for-… │
│ Methane Mitigation │           │        │      │                     │
│ and Recovery from  │           │        │      │                     │
│ Hydroelectric      │           │        │      │                     │
│ Power Reservoirs   │           │        │      │                     │
├────────────────────┼───────────┼────────┼──────┼─────────────────────┤
│ Industrial Heat    │ GBR       │ 21.03  │ 7    │ industrial-heat-re… │
│ Recovery Support   │           │        │      │                     │
│ programme          │           │        │      │                     │
├────────────────────┼───────────┼────────┼──────┼─────────────────────┤
│ Reduction of       │ JOR       │ 21.028 │ 3    │ reduction-of-metha… │
│ Methane Emissions  │           │        │      │                     │
│ and Utilization of │           │        │      │                     │
│ Municipal Waste    │           │        │      │                     │
│ for Energy in      │           │        │      │                     │
│ Amman              │           │        │      │                     │
├────────────────────┼───────────┼────────┼──────┼─────────────────────┤
│ Vanuatu Recovery   │ VUT       │ 20.897 │ 4    │ vanuatu-recovery-s… │
│ Strategy 2020-2023 │           │        │      │                     │
├────────────────────┼───────────┼────────┼──────┼─────────────────────┤
│ Somalia Recovery   │ SOM       │ 20.311 │ 1    │ somalia-recovery-a… │
│ and Resilience     │           │        │      │                     │
│ Framework          │           │        │      │                     │
├────────────────────┼───────────┼────────┼──────┼─────────────────────|
```
</details>

<details>
<summary><b>Within a family, the family itself (once per document) is ranked alongside each passage (aka text block).</b></summary>

``` log
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                               Results                                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
─ Family 1/20: 'Pilot Project for Methane Mitigation and Recovery fro… ─

            Total hits: 10
            Family: GEF.family.4144.0
            Family slug: 
pilot-project-for-methane-mitigation-and-recovery-from-hydroelectric-pow
er-reservoirs_755c
            Geography: BRA
            Relevance: 46.05639660121773
            
Description: The general objective of the project is to promote the 
adoption of Methane Gas (CH4) recovery technologies in
hydroelectric power reservoirs and facilities for electricity generation
and to promote Greenhouse Gas (GHG) mitigation and recovery.
This objective will be attained through the: (i) assessment of CH4 
concentration levels dissolved in water on the selected hydropower
plant3; (ii) testing of different technologies and devices for CH4 
mitigation and CH4 recovery from CH4-rich reservoir waters and identify
the most adequate one to be used in the selected hydropower; (iii) 
development of a pilot project for CH4 mitigation and recovery; and (iv)
conduct a technical and economical feasibility study for electricity 
generation using recovered CH44.

Hits:
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┓
┃ Text              ┃ Score  ┃ Type       ┃ TB ID ┃ Doc ID             ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━━━━┩
│ <see family       │ 46.056 │ Document   │ -     │ GEF.document.4144… │
│ description>      │        │            │       │                    │
├───────────────────┼────────┼────────────┼───────┼────────────────────┤
│ 1. Assessment of  │ 14.878 │ Text block │ 37    │ GEF.document.4144… │
│ methane (CH4)     │        │            │       │                    │
│ recovery from     │        │            │       │                    │
│ hydroelectric     │        │            │       │                    │
│ power tropical    │        │            │       │                    │
│ reservoirs.       │        │            │       │                    │
├───────────────────┼────────┼────────────┼───────┼────────────────────┤
│ 3. Testing and    │ 13.937 │ Text block │ 57    │ GEF.document.4144… │
│ selection of      │        │            │       │                    │
│ diverse CH4       │        │            │       │                    │
│ mitigation and    │        │            │       │                    │
│ recovery          │        │            │       │                    │
│ technologies and  │        │            │       │                    │
│ devices.          │        │            │       │                    │
├───────────────────┼────────┼────────────┼───────┼────────────────────┤
│ High-quality,     │ 13.932 │ Text block │ 50    │ GEF.document.4144… │
│ sound information │        │            │       │                    │
│ on CH4 recovery   │        │            │       │                    │
│ potential in the  │        │            │       │                    │
│ selected          │        │            │       │                    │
│ hydropower dam    │        │            │       │                    │
├───────────────────┼────────┼────────────┼───────┼────────────────────┤
│ Market risks -    │ 13.188 │ Text block │ 242   │ GEF.document.4144… │
│ Investments in RE │        │            │       │                    │
│ based on CH4      │        │            │       │                    │
│ recovery do not   │        │            │       │                    │
│ provide an        │        │            │       │                    │
│ attractive ROI    │        │            │       │                    │
├───────────────────┼────────┼────────────┼───────┼────────────────────|
```
</details>

Explainers of specific search types follow, from lowest to highest complexity.

> [!WARNING]
> In the following sections, example YQL queries and rank profiles are used to explain the mechanics of each search. **These will not necessarily be the same as are in product by the time you read this!** These are more meant as practical ways to explain relevant mechanics of Vespa and our searches.

## Exact search

The intention of this search is to return documents with the *exact phrase used* in their titles, descriptions or full text. Expert users tend to use this when they're searching for something very specific and often technical, or to count documents that mention a phrase. (Having said that, around 1% of users performed this search before we recently made it harder to find).

### Annotated YQL

```sql
-- RETRIEVAL PART
select * from sources family_document, document_passage where 
( 
    -- {stem: false} is an example of a query annotation, telling Vespa not to stem the query.
    -- It's important to ensure this term runs on a field that's *also not stemmed* – Vespa 
    -- doesn't do this automatically.
    -- Docs: https://docs.vespa.ai/en/reference/query-language-reference.html#stem
    (family_name_not_stemmed contains({stem: false}@query_string)) or 
    (family_description_not_stemmed contains({stem: false}@query_string)) or 
    (text_block_not_stemmed contains ({stem: false}@query_string)) 
) limit 0 | 
-- GROUPING PART
-- Here, the query groups by family import ID.
all( 
    group(family_import_id) 
    output(count()) -- Show the count of families
    max(20) -- Show maximum 20 families
    each( 
        output(count()) -- Show the count of hits within families
        max(10) 
        each( 
            output( 
                summary(search_summary) -- For each hit, show the fields defined by the 'search_summary' summary in the respective schema.
            ) 
        ) 
    ) 
)
```

### Relevant parts of schemas

#### `family_document` schema

Vespa stems fields by default. We define two fields with `_not_stemmed` suffixes which feed from the values of the raw index fields, but switch stemming off.

``` js
field family_name_not_stemmed type string {
    indexing: input family_name_index | index
    stemming: none
}

field family_description_not_stemmed type string {
    indexing: input family_description_index | index
    stemming: none
}
```

The default_family schema provides some input parameters which we want to be able to control all ranking on this schema with: weights of the parts of the calculations associated with names and descriptions.

``` js
rank-profile default_family inherits default {
    inputs {
        query(name_weight) double: 2.5
        query(description_weight) double: 2.0
    }
}
```

Each field's score uses a [Vespa-specific text ranking score called `fieldMatch`](https://docs.vespa.ai/en/reference/rank-features.html#field-match-features-normalized).

``` js
rank-profile exact_not_stemmed inherits default_family {
    function name_score() {
        expression: fieldMatch(family_name_not_stemmed)
    }
    function description_score() {
        expression: fieldMatch(family_description_not_stemmed)
    }
    // Scores per field are multiplied by their weight and summed
    first-phase {
        expression: query(name_weight) * name_score() + query(description_weight) * description_score()
    }
    // Scores are added to summary-features so that they can be inspected in Vespa's response
    summary-features: name_score() description_score() query(name_weight) query(description_weight)
}
```

#### `document_passage` schema

All the same applies to the document_passage schema, but on different fields.

``` js
field text_block_not_stemmed type string {
    indexing: input text_block | summary | index
    stemming: none
}

rank-profile default_passage inherits default {
    inputs {
        query(passage_weight) double: 1.0
    }
}

rank-profile exact_not_stemmed inherits default_passage {
    function text_score() {
        expression: fieldMatch(text_block_not_stemmed)
    }
    first-phase {
        expression: query(passage_weight) * text_score()
    }
    summary-features: query(passage_weight) text_score()
}
```

## Hybrid search

Hybrid search is the default search on our tool. It's implementation is similar to exact match search, but with a few extra parts to the query and schema. Here, just the differences will be highlighted.

### Annotated YQL

The group clause is exactly the same as before! But in the retrieval part, instead of using `contains` we use:

- [userInput](https://docs.vespa.ai/en/reference/query-language-reference.html#userinput): Vespa's way of turning a free text query into the lower-level query that it thinks is most suitable. Operates on the *default fieldset* defined in each schema.
- [nearestNeighbour](https://docs.vespa.ai/en/nearest-neighbor-search.html#querying-using-nearestneighbor-query-operator): performs approximate nearest neighbour search using an embedding of the query and the `text_embedding` field, which is the the vector-encoded version of each text block. This is what makes our search 'semantic'.

``` sql
select * from sources family_document, document_passage where ( 
    ---
    (userInput(@query_string)) 
    or ( 
        [{\"targetNumHits\": 1000}] nearestNeighbor(text_embedding,query_embedding) ) 
    ) 
    limit 0 
| all( 
    group(family_import_id) 
    output(count()) max(20) 
    each( output(count()) max(10) each( output( summary(search_summary) ) ) ) 
)
```

### Relevant parts of schemas

The ranking for each field is as follows:

- family names are ranked using BM25.
- family descriptions are ranked using a weighted sum of BM25 and vector similarity. The weight of the latter is set to 0 in the SDK, disabling vector search on descriptions.
- passages are ranked using a weighted sum of BM25 and vector similarity.

[BM25](https://en.wikipedia.org/wiki/Okapi_BM25) ranks according to the number of times a term in the query appears in each record, penalising occurrences (like 'climate') which appear in lots of records compared to those that are rarer.

> [!TIP]
> The `description_closeness_weight` has been set to 0 in the SDK code, rather than updating the default value in the schema. This method doesn't require a Vespa schema change thus redeploy, and changing values in code rather than the schema means SDK and backend unit tests can be run on the change.

``` js
// family_document hybrid rank profile
rank-profile hybrid inherits default_family {
    inputs {
        query(query_embedding) tensor<float>(x[768])
        query(description_bm25_weight) double: 1.0
        // NOTE: this is set to 0 in the SDK, disabling embedding search on descriptions
        query(description_closeness_weight) double: 1.0
    }
    function name_score() {
        expression: bm25(family_name_index)
    }
    function description_score() {
        expression: query(description_bm25_weight) * bm25(family_description_index) + query(description_closeness_weight) * closeness(family_description_embedding)
    }
    first-phase {
        expression: (query(name_weight) * name_score()) + (query(description_weight) * description_score())
    }
    summary-features: name_score() description_score() bm25(family_name_index) bm25(family_description_index) closeness(family_description_embedding)
}

// document_passage hybrid rank profile
rank-profile hybrid inherits default_passage {
    inputs {
        query(query_embedding) tensor<float>(x[768])
        query(passage_bm25_weight) double: 1.0
        query(passage_closeness_weight) double: 1.0
    }
    function text_score() {
        expression: query(passage_bm25_weight) * bm25(text_block) + query(passage_closeness_weight) * closeness(text_embedding)
    }
    first-phase {
        expression: query(passage_weight) * text_score()
    }
    summary-features: text_score() bm25(text_block) closeness(text_embedding) query(passage_weight)
}

```

### Disabling vector search for sensitive queries

The embedding model we use is trained on English Wikipedia and a dataset of out-of-copyright books then finetuned on thousands of Bing searches (a dataset called msmarco). As a result, there are some troublesome biases that we'd like to avoid our users seeing.

As such, there's an escape hatch for any queries that contain likely sensitive terms including protected characteristics, nationalities, and some miscellaneous terms ([full list here](../../src/cpr_sdk/resources/sensitive_query_terms.tsv)).

The mechanics of the sensitive query are identical to the hybrid search query, but with use of embeddings for both retrieval and ranking removed.
