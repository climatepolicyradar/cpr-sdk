"""Adaptors for searching CPR data"""

import logging
import time
from abc import ABC
from pathlib import Path
from typing import Optional

from requests.exceptions import HTTPError
from vespa.application import Vespa
from vespa.exceptions import VespaError

from cpr_sdk.exceptions import DocumentNotFoundError, FetchError, QueryError
from cpr_sdk.models.search import Hit, SearchParameters, SearchResponse
from cpr_sdk.vespa import (
    VespaErrorDetails,
    build_vespa_request_body,
    find_vespa_cert_paths,
    parse_vespa_response,
    split_document_id,
)

LOGGER = logging.getLogger(__name__)


class SearchAdapter(ABC):
    """Base class for all search adapters."""

    def search(self, parameters: SearchParameters) -> SearchResponse:
        """
        Search a dataset

        :param SearchParameters parameters: a search request object
        :return SearchResponse: a list of parent families, each containing relevant
            child documents and passages
        """
        raise NotImplementedError

    async def async_search(self, parameters: SearchParameters) -> SearchResponse:
        """
        Search a dataset asynchronously

        :param SearchParameters parameters: a search request object
        :return SearchResponse: a list of parent families, each containing relevant
            child documents and passages
        """
        raise NotImplementedError

    def get_by_id(self, document_id: str) -> SearchResponse:
        """
        Get a single document by its id

        :param str document_id: document id
        :return Hit: a single document or passage
        """
        raise NotImplementedError


class VespaSearchAdapter(SearchAdapter):
    """Search within a Vespa instance."""

    instance_url: str
    client: Vespa

    def __init__(
        self,
        instance_url: str,
        cert_directory: Optional[str] = None,
        skip_cert_usage: bool = False,
        vespa_cloud_secret_token=None,
    ):
        """
        Initialize the Vespa search adapter.

        :param instance_url: URL of the Vespa instance to connect to
        :param cert_directory: Optional directory containing cert.pem and key.pem files.
            If None, will attempt to find certs automatically.
        :param skip_cert_usage: If True, will not use certs, this is useful for
            running against local instances that aren't secured.
        :param vespa_cloud_secret_token: If present, will use to authenticate to vespa
            cloud
        """
        self.instance_url = instance_url
        if vespa_cloud_secret_token:
            self.client = Vespa(
                url=instance_url, vespa_cloud_secret_token=vespa_cloud_secret_token
            )
        elif skip_cert_usage:
            cert_path = None
            key_path = None
            self.client = Vespa(url=instance_url)
        elif cert_directory is None:
            cert_path, key_path = find_vespa_cert_paths()
            self.client = Vespa(url=instance_url, cert=cert_path, key=key_path)
        else:
            cert_path = (Path(cert_directory) / "cert.pem").__str__()
            key_path = (Path(cert_directory) / "key.pem").__str__()
            self.client = Vespa(url=instance_url, cert=cert_path, key=key_path)

    def search(self, parameters: SearchParameters) -> SearchResponse:
        """
        Search a vespa instance

        :param SearchParameters parameters: a search request object
        :return SearchResponse: a list of families, with response metadata
        """
        total_time_start = time.time()
        vespa_request_body = build_vespa_request_body(parameters)
        query_time_start = time.time()
        try:
            vespa_response = self.client.query(body=vespa_request_body)
        except VespaError as e:
            err_details = VespaErrorDetails(e)
            if err_details.is_invalid_query_parameter:
                LOGGER.error(err_details.message)
                raise QueryError(err_details.summary)
            else:
                raise e
        query_time_end = time.time()

        response = parse_vespa_response(vespa_response=vespa_response)

        response.query_time_ms = int((query_time_end - query_time_start) * 1000)
        response.total_time_ms = int((time.time() - total_time_start) * 1000)

        return response

    async def async_search(self, parameters: SearchParameters) -> SearchResponse:
        """
        Search a vespa instance asynchronously

        :param SearchParameters parameters: a search request object
        :return SearchResponse: a list of families, with response metadata
        """
        total_time_start = time.time()
        vespa_request_body = build_vespa_request_body(parameters)
        query_time_start = time.time()

        try:
            async with self.client.asyncio() as session:
                vespa_response = await session.query(body=vespa_request_body)
        except VespaError as e:
            err_details = VespaErrorDetails(e)
            if err_details.is_invalid_query_parameter:
                LOGGER.error(err_details.message)
                raise QueryError(err_details.summary)
            else:
                raise e
        query_time_end = time.time()

        response = parse_vespa_response(vespa_response=vespa_response)

        response.query_time_ms = int((query_time_end - query_time_start) * 1000)
        response.total_time_ms = int((time.time() - total_time_start) * 1000)

        return response

    def get_by_id(self, document_id: str) -> Hit:
        """
        Get a single document by its id

        :param str document_id: IDs should look something like
            "id:doc_search:family_document::CCLW.family.11171.0"
            or
            "id:doc_search:document_passage::UNFCCC.party.1060.0.3743"
        :return Hit: a single document or passage
        """
        namespace, schema, data_id = split_document_id(document_id)
        try:
            vespa_response = self.client.get_data(
                namespace=namespace, schema=schema, data_id=data_id
            )
        except HTTPError as e:
            if e.response is not None:
                status_code = e.response.status_code
            else:
                status_code = "Unknown"
            if status_code == 404:
                raise DocumentNotFoundError(document_id) from e
            else:
                raise FetchError(
                    f"Received status code {status_code} when fetching "
                    f"document {document_id}",
                    status_code=status_code,
                ) from e

        return Hit.from_vespa_response(vespa_response.json)
