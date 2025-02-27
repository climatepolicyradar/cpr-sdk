# Search Intention Testing

The command `make test_search_intentions` runs a set of pytest tests that run queries against our production search index and test for certain results, or characteristics of results.

These were adapted from [wellcomecollection/rank](https://github.com/wellcomecollection/rank).

> [!WARNING]
> Results from directly querying Vespa won't always be the same as those in the user-facing apps. This is because the apps only show documents that have been published and not deleted. Vespa has no field storing published status, and the pipeline that populates it is write-only.
>
> What this means in practice is that some failing tests could pass in our tools, or vice-versa. There's currently no way of handing this in the tests themselves, so use your best judgement as to how to adapt the test to exclude documents that are in Vespa but not in our tools.

## What are these tests for?

In an ideal world, we'll maintain a collection of search queries we know about and the kinds of results they should return. These could be from users, analytics or dogfooding our own apps. We should also collect a list of search intentions for each new data corpus or custom app.

If we maintain them in code here, it's easy to see how many search intentions we can address at a given time.

## How to use these

This code uses `pytest` in a slightly unconventional way, because we want to keep tests in this repo that fail (we won't always fix search tests immediately, but might want to come back and fix them another time – or acknowledge that they will fail for the foreseeable future).

Each [test model](../../src/cpr_sdk/search_intention_testing/models.py) has a `known_failure: bool` property. When marked as True, it'll be logged as a failure but won't fail tests.

1. Examine the tests with `known_failure = True` in the *src/search_testing/tests* directory. These are the ones that need fixing.
2. Set `known_failure` to `False` for each of the tests you want to fix.
3. Go and fix them! If you're using the CPR SDK, you'll probably want to run `poetry add --editable ~/my-local-path-to-cpr-sdk`
4. Once they're fixed, you should be able to open a PR with `known_failure=False` for those tests.
5. 🎉
