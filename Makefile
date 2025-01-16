include ./Makefile-vespa.defs

.PHONY: test

test:
	poetry run pytest -vvv -m "not search_test"

test_not_vespa:
	poetry run pytest -vvv -m "not vespa and not search_intention"

test_search_intentions:
	poetry run pytest -vvv -m "search_intention"