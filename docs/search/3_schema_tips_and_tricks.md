# Practical tips for working with our Vespa schemas

The Vespa schema is written in a proprietary language, and a lot of its more useful features (and potentially dangerous gotchas) don't jump straight out of the docs. This is a page for tips and tricks for working with Vespa schemas.

## Gotcha: searchable text fields are modified by default

Searchable (or string typed, [index](https://docs.vespa.ai/en/reference/schema-reference.html#index) fields) are subject to linguistic processing by default.

The processing that's done is:

- [tokenization](https://docs.vespa.ai/en/linguistics.html#tokenization): splitting into words (which also strips all punctuation)
- [normalization](https://docs.vespa.ai/en/linguistics.html#normalization): normalising accents (e.g. á -> a)
- [stemming](https://docs.vespa.ai/en/linguistics.html#stemming): translating words to their base form

As a result, there are two things to watch out for when designing queries:

- **Punctuation will always be ignored.** This is the default, unconfigurable behaviour of the Vespa tokenizer. There seems to be no obvious way to resolve this so that both the query and indexed text are subject to punctuation-aware tokenization, but the Vespa team are aware that we're having this issue.
- **If you apply any processing to the query, consider whether you need to apply it to the field you're searching on too.** E.g. using a `{stem: false}` annotation on the query will lead to unpredictable behaviour, unless you've also created a variant of the field you're searching with stemming disabled.

## Storing differently-analysed fields

Sometimes it's useful to have versions of the same field that have undergone slightly different processing, e.g. one that's been [stemmed](https://en.wikipedia.org/wiki/Stemming) and one that hasn't (for exact match search). In Vespa, you can use [indexing statements](https://docs.vespa.ai/en/reference/indexing-language-reference.html#indexing-statement) to create fields containing the results of different analyses of source fields. Computing these statements runs *on Vespa*, rather than requiring rewriting and rerunning our Python indexer.

**An important part of this is to try to use naming conventions where possible**: e.g. all non-stemmed versions of a field having the suffix `_not_stemmed` etc. This will make it easier to write queries and rank profiles in the long run.

E.g.

``` js
field family_name_not_stemmed type string {
    indexing: input family_name_index | index
    stemming: none
}
```

## Things to keep in mind when working on rank-profiles

If you're writing a new rank profile:

- see if you can use schema inheritance to save repeating parameters
- make sure it's in both the family_document and document_passage schemas+
- make sure it inherits from `default_family` or `default_passage`, directly or indirectly

+The way we search across multiple schemas is not intended by Vespa (our use of it was described by their support team as 'black belt stuff' 🥋). But with its weirdness comes power – *and some health warnings*.

## Using input parameters

All parameters should be exposed as `inputs` in rank profiles, for example:

``` js
rank-profile default_family inherits default {
    inputs {
        query(name_weight) double: 2.5
        query(description_weight) double: 2.0
    }
}
```

You can then tweak them via a Vespa query using the key `input.query(parameter_name)` in the request body. This prevents needing to change the schema and redeploy Vespa to make a weight change.
