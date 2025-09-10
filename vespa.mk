# Setup dev instance of Vespa for test and local development

# The Vespa CLI is required, this checks if its installed
# See: https://docs.vespa.ai/en/vespa-cli.html
vespa_confirm_cli_installed:
	@if [ ! $$(which vespa) ]; then \
		echo 'ERROR: The vespa cli is not installed, please install and try again:' ; \
		echo 'https://docs.vespa.ai/en/vespa-cli.html'; \
		exit 1; \
	fi

# Starts a detached instance of Vespa ready
vespa_dev_start:
	docker compose -f tests/local_vespa/docker-compose.dev.yml up --detach --wait vespadaltest

# Confirms the local Vespa instance has been spun up and is healthy
vespa_healthy:
	@if [ ! $$(curl -f -s 'http://localhost:19071/status.html') ]; then \
		echo 'ERROR: Bad response from local vespa cluster, is it running?'; \
		exit 1; \
	fi

# Deploys app to local Vespa instance
.ONESHELL:
vespa_deploy_app:
	vespa config set target local
	@vespa deploy tests/local_vespa/test_app --wait 300

# Loads some test data into local Vespa instance
.ONESHELL:
vespa_load_data:
	vespa feed --target local --wait 60 tests/local_vespa/test_documents/*.json

# Deletes all test data from local Vespa instance
.ONESHELL:
vespa_delete_data:
	curl -X DELETE "http://localhost:8080/document/v1/doc_search/family_document/docid?selection=true&cluster=family-document-passage"
	curl -X DELETE "http://localhost:8080/document/v1/doc_search/document_passage/docid?selection=true&cluster=family-document-passage"
	curl -X DELETE "http://localhost:8080/document/v1/doc_search/search_weights/docid?selection=true&cluster=family-document-passage"
	curl -X DELETE "http://localhost:8080/document/v1/doc_search/concept/docid?selection=true&cluster=family-document-passage"
	curl -X DELETE "http://localhost:8080/document/v1/doc_search/classifiers_profile/docid?selection=true&cluster=family-document-passage"

# Set up a local instance of Vespa
vespa_dev_setup: vespa_confirm_cli_installed vespa_dev_start vespa_healthy vespa_deploy_app vespa_load_data

# Stop and remove the Vespa container
vespa_dev_down:
	docker compose -f tests/local_vespa/docker-compose.dev.yml down vespadaltest
