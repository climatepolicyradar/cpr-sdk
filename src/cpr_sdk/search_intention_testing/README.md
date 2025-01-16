# search-tests

Tests on product search. Adapted from [wellcomecollection/rank](https://github.com/wellcomecollection/rank).

*Note for the public:* we made this repo open source as it's a nice way of testing search we wanted to share. But, you're unlikely to use this code as-is as it's heavily tied to our backend search schemas and use of the Vespa database.

## Getting started

* make sure you have Vespa credentials set up for the instance you want to test: [see instructions here](https://github.com/climatepolicyradar/navigator-infra/tree/main/vespa#how-to-add-a-certificate-for-vespa-cloud-access)
* fill in required environment variables, including the Vespa URL, in `.env`
* run `make test_search_intentions` to run the tests. Optionally open the HTML report at `./search_test_report.html`

## A note on unconventional testing

This code uses `pytest` in a slightly inconventional way, because we want to keep tests in this repo that fail (we won't always fix search tests immediately, but might want to come back and fix them another time – or acknowledge that they will fail for the foreseeable future).

Each [test model](/src/search_testing/models.py) has a `known_failure: bool` property. When marked as True, it'll be logged as a failure but won't fail tests.

## How to use these tests

1. Examine the tests with `known_failure = True` in the *src/search_testing/tests* directory. These are the ones that need fixing.
2. Set `known_faliure` to `False` for each of the tests you want to fix.
3. Go and fix them! If you're using the CPR SDK, you'll probably want to run `poetry add --editable ~/my-local-path-to-cpr-sdk`
4. Once they're fixed, you should be able to open a PR with `known_failure=False` for those tests.
5. 🎉
