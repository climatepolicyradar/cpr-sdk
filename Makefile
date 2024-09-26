include ./Makefile-vespa.defs

.PHONY: test

test:
	poetry run pytest -vvv

test_not_vespa:
	poetry run pytest -vvv -m "not vespa"
