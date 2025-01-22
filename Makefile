include ./Makefile-vespa.defs

.PHONY: install test test_not_vespa test_search_intentions

install:
	poetry install --all-extras --with dev

test:
	poetry run pytest -vvv -m "not search_intention"

test_not_vespa:
	poetry run pytest -vvv -m "not vespa and not search_intention"

test_search_intentions:
	poetry run pytest -vvv -m "search_intention" --html=search_test_report.html --self-contained-html
