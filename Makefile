include ./Makefile-vespa.defs

.PHONY: test

test:
	poetry run pytest -vvv -m "not search_test"

test_not_vespa:
	poetry run pytest -vvv -m "not vespa and not search_test"

search_tests:
	poetry run pytest -vvv -m "search_test"