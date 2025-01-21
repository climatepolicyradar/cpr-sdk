# Practical tips for working with our Vespa schemas

The Vespa schema is written in a proprietary language, and a lot of its more useful features don't jump straight out of the docs. This is a page for tips and tricks for working with Vespa schemas.

## Field analysis

Sometimes it's useful to have versions of the same field that have undergone slightly different processing, e.g. one that's been [stemmed](https://en.wikipedia.org/wiki/Stemming) and one that hasn't (for exact match search). Instead of adding another field to the indexer and making this analysis change in Python, it's also possible to feed fields from others with different analysis settings in a Vespa schema.

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
