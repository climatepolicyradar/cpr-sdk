"""Adaptors for searching CPR data"""

from cpr_sdk.exceptions import DocumentNotFoundError, FetchError, QueryError
from cpr_sdk.models.search import (
    ClassifiersProfile,
    ClassifiersProfiles,
    Concept,
    Family,
    Hit,
    SearchClassifiersProfileParameters,
    SearchConceptParameters,
    SearchParameters,
    SearchResponse,
)
from cpr_sdk.vespa import (
    VespaErrorDetails,
    build_vespa_request_body,
    find_vespa_cert_paths,
    parse_vespa_response,
    split_document_id,
)
from cpr_sdk.utils import dig


import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path


from cpr_sdk.yql_builder import ClassifiersProfileYQLBuilder, ConceptYQLBuilder
from typing_extensions import override

from requests.exceptions import HTTPError
from vespa.application import Vespa
from vespa.exceptions import VespaError
from vespa.io import VespaQueryResponse


LOGGER = logging.getLogger(__name__)


class SearchAdapter(ABC):
    """Base class for all search adapters."""

    @abstractmethod
    def search(self, parameters: SearchParameters) -> SearchResponse[Family]:
        """
        Search a dataset

        :param SearchParameters parameters: a search request object
        :return SearchResponse[Family]: a list of parent families, each containing relevant
            child documents and passages
        """
        raise NotImplementedError

    @abstractmethod
    async def async_search(
        self, parameters: SearchParameters
    ) -> SearchResponse[Family]:
        """
        Search a dataset asynchronously

        :param SearchParameters parameters: a search request object
        :return SearchResponse[Family]: a list of parent families, each containing relevant
            child documents and passages
        """
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, document_id: str) -> Hit:
        """
        Get a single document by its ID

        :param str document_id: document ID
        :return Hit: a single document or passage
        """
        raise NotImplementedError

    @abstractmethod
    def get_concept(self, concept_id: str) -> Concept:
        """
        Get a single concept by its ID

        :param str concept_id: concept ID
        :return Concept: a single concept
        """
        raise NotImplementedError

    @abstractmethod
    async def async_get_concept(self, concept_id: str) -> Concept:
        """
        Get a single concept by its ID asynchronously

        :param str concept_id: concept ID
        :return Concept: a single concept
        """
        raise NotImplementedError

    @abstractmethod
    def search_concepts(
        self, parameters: SearchConceptParameters
    ) -> SearchResponse[Concept]:
        """
        Query concepts

        :param SearchConceptParameters parameters: search parameters
        :return SearchResponse[Concept]: search response with concepts
        """
        raise NotImplementedError

    @abstractmethod
    async def async_search_concepts(
        self, parameters: SearchConceptParameters
    ) -> SearchResponse[Concept]:
        """
        Query concepts asynchronously

        :param SearchConceptParameters parameters: search parameters
        :return SearchResponse[Concept]: search response with concepts
        """
        raise NotImplementedError

    @abstractmethod
    def get_classifiers_profile(self, profile_id: str) -> "ClassifiersProfile":
        """
        Get a single classifiers profile by its ID

        :param str profile_id: classifiers profile ID
        :return ClassifiersProfile: a single classifiers profile
        """
        raise NotImplementedError

    @abstractmethod
    async def async_get_classifiers_profile(
        self, profile_id: str
    ) -> "ClassifiersProfile":
        """
        Get a single classifiers profile by its ID asynchronously

        :param str profile_id: classifiers profile ID
        :return ClassifiersProfile: a single classifiers profile
        """
        raise NotImplementedError

    @abstractmethod
    def search_classifiers_profiles(
        self, parameters: "SearchClassifiersProfileParameters"
    ) -> "SearchResponse[ClassifiersProfile]":
        """
        Query classifiers profiles

        :param SearchClassifiersProfileParameters parameters: search parameters
        :return SearchResponse[ClassifiersProfile]: search response with classifiers profiles
        """
        raise NotImplementedError

    @abstractmethod
    async def async_search_classifiers_profiles(
        self, parameters: "SearchClassifiersProfileParameters"
    ) -> "SearchResponse[ClassifiersProfile]":
        """
        Query classifiers profiles asynchronously

        :param SearchClassifiersProfileParameters parameters: search parameters
        :return SearchResponse[ClassifiersProfile]: search response with classifiers profiles
        """
        raise NotImplementedError

    @abstractmethod
    def get_classifiers_profiles(self) -> "ClassifiersProfiles":
        """
        Get the singleton classifiers profiles registry

        :return ClassifiersProfiles: the classifiers profiles registry
        """
        raise NotImplementedError

    @abstractmethod
    async def async_get_classifiers_profiles(self) -> "ClassifiersProfiles":
        """
        Get the singleton classifiers profiles registry asynchronously

        :return ClassifiersProfiles: the classifiers profiles registry
        """
        raise NotImplementedError


class VespaSearchAdapter(SearchAdapter):
    """Search within a Vespa instance."""

    instance_url: str
    client: Vespa

    def __init__(
        self,
        instance_url: str,
        cert_directory: str | None = None,
        skip_cert_usage: bool = False,
        vespa_cloud_secret_token: str | None = None,
    ):
        """
        Initialise the Vespa search adapter.

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

    @override
    def search(self, parameters: SearchParameters) -> SearchResponse[Family]:
        """
        Search a vespa instance

        :param SearchParameters parameters: a search request object
        :return SearchResponse[Family]: a list of families, with response metadata
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

        response = parse_vespa_response(vespa_response=vespa_response)  # type: ignore[arg-type]

        response.query_time_ms = int((query_time_end - query_time_start) * 1000)
        response.total_time_ms = int((time.time() - total_time_start) * 1000)

        return response

    @override
    async def async_search(
        self, parameters: SearchParameters
    ) -> SearchResponse[Family]:
        """
        Search a vespa instance asynchronously

        :param SearchParameters parameters: a search request object
        :return SearchResponse[Family]: a list of families, with response metadata
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

        response = parse_vespa_response(vespa_response=vespa_response)  # type: ignore[arg-type]

        response.query_time_ms = int((query_time_end - query_time_start) * 1000)
        response.total_time_ms = int((time.time() - total_time_start) * 1000)

        return response

    @override
    def get_by_id(self, document_id: str) -> Hit:
        """
        Get a single document by its ID

        :param str document_id: IDs should look something like
            "id:doc_search:family_document::CCLW.family.11171.0"
            or
            "id:doc_search:document_passage::UNFCCC.party.1060.0.3743"
        :return Hit: a single document or passage
        """
        document_id_parts = split_document_id(document_id)
        try:
            vespa_response = self.client.get_data(
                namespace=document_id_parts.namespace,
                schema=document_id_parts.schema,
                data_id=document_id_parts.data_id,
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

    @override
    def get_concept(self, concept_id: str) -> Concept:
        """
        Get a single concept by its ID

        :param str concept_id: concept ID
        :return Concept: a single concept
        """
        document_id_parts = split_document_id(concept_id)
        try:
            vespa_response = self.client.get_data(
                namespace=document_id_parts.namespace,
                schema=document_id_parts.schema,
                data_id=document_id_parts.data_id,
            )
        except HTTPError as e:
            if e.response is not None:
                status_code = e.response.status_code
            else:
                status_code = "Unknown"
            if status_code == 404:
                raise DocumentNotFoundError(concept_id) from e
            else:
                raise FetchError(
                    f"Received status code {status_code} when fetching "
                    f"concept {concept_id}",
                    status_code=status_code,
                ) from e

        if not vespa_response.is_successful():
            if vespa_response.status_code == 404:
                raise DocumentNotFoundError(concept_id)

            raise ValueError(
                f"failed when getting document {concept_id}. status code: {vespa_response.status_code}, JSON: {vespa_response.get_json()}"
            )

        return Concept.from_vespa_response(vespa_response.json)

    @override
    async def async_get_concept(self, concept_id: str) -> Concept:
        """
        Get a single concept by its ID asynchronously

        :param str concept_id: concept ID
        :return Concept: a single concept
        """
        document_id_parts = split_document_id(concept_id)
        try:
            async with self.client.asyncio() as session:
                vespa_response = await session.get_data(
                    namespace=document_id_parts.namespace,
                    schema=document_id_parts.schema,
                    data_id=document_id_parts.data_id,
                )
        except HTTPError as e:
            if e.response is not None:
                status_code = e.response.status_code
            else:
                status_code = "Unknown"
            if status_code == 404:
                raise DocumentNotFoundError(concept_id) from e
            else:
                raise FetchError(
                    f"Received status code {status_code} when fetching "
                    f"concept {concept_id}",
                    status_code=status_code,
                ) from e

        if not vespa_response.is_successful():
            if vespa_response.status_code == 404:
                raise DocumentNotFoundError(concept_id)

            raise ValueError(
                f"failed when getting document {concept_id}. status code: {vespa_response.status_code}, JSON: {vespa_response.get_json()}"
            )

        return Concept.from_vespa_response(vespa_response.json)

    @override
    def search_concepts(
        self, parameters: SearchConceptParameters
    ) -> SearchResponse[Concept]:
        """
        Query concepts

        :param SearchConceptParameters parameters: search parameters
        :return SearchResponse[Concept]: search response with concepts
        """
        q = ConceptYQLBuilder().build(parameters)

        try:
            vespa_response: VespaQueryResponse = self.client.query(yql=q)  # type: ignore[assignment]
        except VespaError as e:
            err_details = VespaErrorDetails(e)
            if err_details.is_invalid_query_parameter:
                LOGGER.error(err_details.message)
                raise QueryError(err_details.summary)
            else:
                raise e

        # Parse the response
        root = vespa_response.json.get("root", {})
        hits = root.get("children", [])
        concepts = []
        for hit in hits:
            if "fields" in hit:
                concepts.append(Concept.from_vespa_response(hit))

        # Extract continuation tokens
        next_continuation = dig(root, "continuation", "next")
        prev_continuation = dig(root, "continuation", "prev")
        this_continuation = dig(root, "continuation", "this")

        # Create SearchResponse with concepts as results
        total_hits = len(concepts)
        return SearchResponse[Concept](
            total_hits=total_hits,
            total_result_hits=1,  # One "concept result set"
            results=concepts,  # The concepts themselves
            continuation_token=next_continuation,
            this_continuation_token=this_continuation,
            prev_continuation_token=prev_continuation,
        )

    @override
    async def async_search_concepts(
        self, parameters: SearchConceptParameters
    ) -> SearchResponse[Concept]:
        """
        Query concepts asynchronously

        :param SearchConceptParameters parameters: search parameters
        :return SearchResponse[Concept]: search response with concepts
        """
        q = ConceptYQLBuilder().build(parameters)

        try:
            async with self.client.asyncio() as session:
                vespa_response = await session.query(yql=q)
        except VespaError as e:
            err_details = VespaErrorDetails(e)
            if err_details.is_invalid_query_parameter:
                LOGGER.error(err_details.message)
                raise QueryError(err_details.summary)
            else:
                raise e

        # Parse the response
        root = vespa_response.json.get("root", {})
        hits = root.get("children", [])
        concepts: list[Concept] = []
        for hit in hits:
            if "fields" in hit:
                concepts.append(Concept.from_vespa_response(hit))

        # Extract continuation tokens
        next_continuation = dig(root, "continuation", "next")
        prev_continuation = dig(root, "continuation", "prev")
        this_continuation = dig(root, "continuation", "this")

        # Create SearchResponse with concepts as results
        total_hits = len(concepts)
        return SearchResponse[Concept](
            total_hits=total_hits,
            # One "concept result set". This is from the SearchResponse originally being for a family.
            total_result_hits=1,
            results=concepts,  # The concepts themselves
            continuation_token=next_continuation,
            this_continuation_token=this_continuation,
            prev_continuation_token=prev_continuation,
        )

    @override
    def get_classifiers_profile(self, profile_id: str) -> ClassifiersProfile:
        """
        Get a single classifiers profile by its ID

        :param str profile_id: classifiers profile ID
        :return ClassifiersProfile: a single classifiers profile
        """
        document_id_parts = split_document_id(profile_id)
        try:
            vespa_response = self.client.get_data(
                namespace=document_id_parts.namespace,
                schema=document_id_parts.schema,
                data_id=document_id_parts.data_id,
            )
        except HTTPError as e:
            if e.response is not None:
                status_code = e.response.status_code
            else:
                status_code = "Unknown"
            if status_code == 404:
                raise DocumentNotFoundError(profile_id) from e
            else:
                raise FetchError(
                    f"Received status code {status_code} when fetching "
                    f"classifiers profile {profile_id}",
                    status_code=status_code,
                ) from e

        if not vespa_response.is_successful():
            if vespa_response.status_code == 404:
                raise DocumentNotFoundError(profile_id)

            raise ValueError(
                f"failed when getting document {profile_id}. status code: {vespa_response.status_code}, JSON: {vespa_response.get_json()}"
            )

        return ClassifiersProfile.from_vespa_response(vespa_response.json)

    @override
    async def async_get_classifiers_profile(
        self, profile_id: str
    ) -> ClassifiersProfile:
        """
        Get a single classifiers profile by its ID asynchronously

        :param str profile_id: classifiers profile ID
        :return ClassifiersProfile: a single classifiers profile
        """
        document_id_parts = split_document_id(profile_id)
        try:
            async with self.client.asyncio() as session:
                vespa_response = await session.get_data(
                    namespace=document_id_parts.namespace,
                    schema=document_id_parts.schema,
                    data_id=document_id_parts.data_id,
                )
        except HTTPError as e:
            if e.response is not None:
                status_code = e.response.status_code
            else:
                status_code = "Unknown"
            if status_code == 404:
                raise DocumentNotFoundError(profile_id) from e
            else:
                raise FetchError(
                    f"Received status code {status_code} when fetching "
                    f"classifiers profile {profile_id}",
                    status_code=status_code,
                ) from e

        if not vespa_response.is_successful():
            if vespa_response.status_code == 404:
                raise DocumentNotFoundError(profile_id)

            raise ValueError(
                f"failed when getting document {profile_id}. status code: {vespa_response.status_code}, JSON: {vespa_response.get_json()}"
            )

        return ClassifiersProfile.from_vespa_response(vespa_response.json)

    @override
    def search_classifiers_profiles(
        self, parameters: SearchClassifiersProfileParameters
    ) -> SearchResponse[ClassifiersProfile]:
        """
        Query classifiers profiles

        :param SearchClassifiersProfileParameters parameters: search parameters
        :return SearchResponse[ClassifiersProfile]: search response with classifiers profiles
        """
        q = ClassifiersProfileYQLBuilder().build(parameters)

        try:
            vespa_response: VespaQueryResponse = self.client.query(yql=q)  # type: ignore[assignment]
        except VespaError as e:
            err_details = VespaErrorDetails(e)
            if err_details.is_invalid_query_parameter:
                LOGGER.error(err_details.message)
                raise QueryError(err_details.summary)
            else:
                raise e

        # Parse the response
        root = vespa_response.json.get("root", {})
        hits = root.get("children", [])
        profiles = []
        for hit in hits:
            if "fields" in hit:
                profiles.append(ClassifiersProfile.from_vespa_response(hit))

        # Create SearchResponse with classifiers profiles as results
        total_hits = len(profiles)
        return SearchResponse[ClassifiersProfile](
            total_hits=total_hits,
            total_result_hits=1,  # One "classifiers profile result set"
            results=profiles,  # The classifiers profiles themselves
        )

    @override
    async def async_search_classifiers_profiles(
        self, parameters: SearchClassifiersProfileParameters
    ) -> SearchResponse[ClassifiersProfile]:
        """
        Query classifiers profiles asynchronously

        :param SearchClassifiersProfileParameters parameters: search parameters
        :return SearchResponse[ClassifiersProfile]: search response with classifiers profiles
        """
        q = ClassifiersProfileYQLBuilder().build(parameters)

        try:
            async with self.client.asyncio() as session:
                vespa_response = await session.query(yql=q)
        except VespaError as e:
            err_details = VespaErrorDetails(e)
            if err_details.is_invalid_query_parameter:
                LOGGER.error(err_details.message)
                raise QueryError(err_details.summary)
            else:
                raise e

        # Parse the response
        root = vespa_response.json.get("root", {})
        hits = root.get("children", [])
        profiles: list[ClassifiersProfile] = []
        for hit in hits:
            if "fields" in hit:
                profiles.append(ClassifiersProfile.from_vespa_response(hit))

        # Create SearchResponse with classifiers profiles as results
        total_hits = len(profiles)
        return SearchResponse[ClassifiersProfile](
            total_hits=total_hits,
            # One "classifiers profile result set". This is from the SearchResponse originally being for a family.
            total_result_hits=1,
            results=profiles,  # The classifiers profiles themselves
        )

    @override
    def get_classifiers_profiles(self) -> ClassifiersProfiles:
        """
        Get the singleton classifiers profiles registry

        :return ClassifiersProfiles: the classifiers profiles registry
        """
        # The document ID for the singleton is always the same
        name = "default"
        document_id = f"id:doc_search:classifiers_profiles::{name}"
        document_id_parts = split_document_id(document_id)
        try:
            vespa_response = self.client.get_data(
                namespace=document_id_parts.namespace,
                schema=document_id_parts.schema,
                data_id=document_id_parts.data_id,
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
                    f"classifiers profiles registry",
                    status_code=status_code,
                ) from e

        if not dig(vespa_response.json, "fields"):
            raise DocumentNotFoundError(document_id)

        if not vespa_response.is_successful():
            raise ValueError(
                f"failed when getting document {document_id}. status code: {vespa_response.status_code}, JSON: {vespa_response.get_json()}"
            )

        return ClassifiersProfiles.from_vespa_response(vespa_response.json)

    @override
    async def async_get_classifiers_profiles(self) -> ClassifiersProfiles:
        """
        Get the singleton classifiers profiles registry asynchronously

        :return ClassifiersProfiles: the classifiers profiles registry
        """
        # The document ID for the singleton is always the same
        name = "default"
        document_id = f"id:doc_search:classifiers_profiles::{name}"
        document_id_parts = split_document_id(document_id)
        try:
            async with self.client.asyncio() as session:
                vespa_response = await session.get_data(
                    namespace=document_id_parts.namespace,
                    schema=document_id_parts.schema,
                    data_id=document_id_parts.data_id,
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
                    f"classifiers profiles registry",
                    status_code=status_code,
                ) from e

        if not dig(vespa_response.json, "fields"):
            raise DocumentNotFoundError(document_id)

        if not vespa_response.is_successful():
            raise ValueError(
                f"failed when getting document {document_id}. status code: {vespa_response.status_code}, JSON: {vespa_response.get_json()}"
            )

        return ClassifiersProfiles.from_vespa_response(vespa_response.json)
