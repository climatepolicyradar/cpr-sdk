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

## Default text search

Default text search is the default search on our tool. It uses Vespa's `userInput` operator to turn a free text query into the most suitable lower-level query, ranked by BM25.

### Annotated YQL

In the retrieval part, [userInput](https://docs.vespa.ai/en/reference/query-language-reference.html#userinput) turns the query string into the lower-level query Vespa thinks is most suitable. It operates on the *default fieldset* defined in each schema.

``` sql
select * from sources family_document, document_passage where (
    (userInput(@query_string))
)
limit 0
| all(
    group(family_import_id)
    output(count()) max(20)
    each( output(count()) max(10) each( output( summary(search_summary) ) ) )
)
```

### Relevant schema parts for default search

No explicit rank profile is set for default text search, so Vespa uses its built-in `default` profile which applies BM25 ranking over the default fieldset for each schema.

[BM25](https://en.wikipedia.org/wiki/Okapi_BM25) ranks according to the number of times a term in the query appears in each record, penalising occurrences (like 'climate') which appear in lots of records compared to those that are rarer.

The default fieldsets are:

``` js
// family_document schema
fieldset default {
    fields: family_name_index, family_description_index
}

// document_passage schema
fieldset default {
    fields: text_block
}
```

## Exact search

The intention of this search is to return documents with the *exact phrase used* in their titles, descriptions or full text. Expert users tend to use this when they're searching for something very specific and often technical, or to count documents that mention a phrase. (Having said that, around 1% of users performed this search before we recently made it harder to find).

Like default text search, exact search uses the same grouping structure — the difference is in retrieval and ranking. Instead of `userInput`, it uses `contains` with stemming disabled, and selects the `exact_not_stemmed` rank profile.

### Annotated exact search YQL

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

### Relevant schema parts for exact search

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
