import logging
from abc import ABC
from typing import Dict, List, Optional
from pydantic import BaseModel

from requests.exceptions import HTTPError
from vespa.application import Vespa
from vespa.exceptions import VespaError

from cpr_sdk.exceptions import DocumentNotFoundError, FetchError, QueryError
from cpr_sdk.models.hit import BaseHit
from cpr_sdk.vespa import VespaErrorDetails, find_vespa_cert_paths

LOGGER = logging.getLogger(__name__)


class ConceptVersion(BaseModel):
    """Represents a concept version with its metadata."""
    concept_id: str
    wikibase_revision_id: str
    canonical_id: str


class ModelProfile(BaseHit):
    # E.g. "primaries", "experimentals"
    id: str
    # E.g. "primaries", "experimentals"
    name: Optional[str] = None
    # E.g. <Q990, ConceptVersion(concept_id="Q990", wikibase_revision_id="1610", canonical_id="n2nuerdn")>
    concepts_versions: Dict[str, ConceptVersion]

    @classmethod
    def from_vespa_response(cls, response_hit: dict) -> "ModelProfile":
        """
        Create a ModelProfile from a Vespa response hit.

        :param dict response_hit: part of a json response from Vespa
        :return ModelProfile: a populated model profile
        """
        fields = response_hit["fields"]
        profile_id = fields.get("id")
        
        # Parse concepts_versions from new struct format
        concepts_versions_raw = fields.get("concepts_versions", {})
        concepts_versions = {}
        
        for concept_id, version_data in concepts_versions_raw.items():
            if isinstance(version_data, dict):
                # New format: concept_version struct
                concepts_versions[concept_id] = ConceptVersion(
                    concept_id=version_data.get("concept_id", concept_id),
                    wikibase_revision_id=version_data.get("wikibase_revision_id", ""),
                    canonical_id=version_data.get("canonical_id", "")
                )
            else:
                # Legacy format: string (for backwards compatibility)
                concepts_versions[concept_id] = ConceptVersion(
                    concept_id=concept_id,
                    wikibase_revision_id="",
                    canonical_id=str(version_data)
                )
        
        return cls(
            id=profile_id,
            name=fields.get("name") or profile_id,  # Fallback to id if name is None
            concepts_versions=concepts_versions,
        )


class ModelProfileAdapter(ABC):
    """Base class for all model profile adapters."""

    def get_all_profiles(self) -> List[ModelProfile]:
        """
        Get all model profiles

        :return List[ModelProfile]: a list of all model profiles
        """
        raise NotImplementedError

    def get_profile_by_id(self, profile_id: str) -> Optional[ModelProfile]:
        """
        Get a specific model profile by ID

        :param str profile_id: the profile ID (e.g., 'primaries', 'experimentals')
        :return ModelProfile: the model profile if found, None otherwise
        """
        raise NotImplementedError


class VespaModelProfileAdapter(ModelProfileAdapter):
    """Vespa implementation of ModelProfileAdapter"""

    def __init__(
        self,
        instance_url: str,
        cert_directory: Optional[str] = None,
        skip_cert_usage: bool = False,
    ):
        """
        Create a VespaModelProfileAdapter

        :param str instance_url: Vespa instance URL
        :param str cert_directory: directory containing client certificates
        :param bool skip_cert_usage: skip using certificates
        """
        self.instance_url = instance_url
        self.skip_cert_usage = skip_cert_usage

        if not skip_cert_usage:
            self.cert_directory = cert_directory
            self.cert_paths = find_vespa_cert_paths(cert_directory)
            self.client = Vespa(
                url=instance_url,
                cert=self.cert_paths["cert"],
                key=self.cert_paths["key"],
            )
        else:
            self.client = Vespa(url=instance_url)

    def get_all_profiles(self) -> List[ModelProfile]:
        """
        Get all model profiles from Vespa

        :return List[ModelProfile]: a list of all model profiles
        """
        try:
            vespa_request_body = {
                "yql": "select * from models_profile where true",
                "hits": 100,  # Assuming we won't have more than 100 profiles
            }

            vespa_response = self.client.query(body=vespa_request_body)

            if "root" not in vespa_response.json:
                raise FetchError("Invalid response format from Vespa")

            root = vespa_response.json["root"]
            if "children" not in root:
                return []

            profiles = []
            for hit in root["children"]:
                profile = ModelProfile.from_vespa_response(hit)
                profiles.append(profile)

            return profiles

        except VespaError as e:
            err_details = VespaErrorDetails.from_vespa_error(e)
            raise QueryError(err_details.summary) from e
        except HTTPError as e:
            raise FetchError(f"HTTP error when fetching profiles: {e}") from e
        except Exception as e:
            raise FetchError(f"Unexpected error when fetching profiles: {e}") from e

    def get_profile_by_id(self, profile_id: str) -> Optional[ModelProfile]:
        """
        Get a specific model profile by ID

        :param str profile_id: the profile ID (e.g., 'primaries', 'experimentals')
        :return ModelProfile: the model profile if found, None otherwise
        """
        try:
            vespa_request_body = {
                "yql": f'select * from models_profile where id contains "{profile_id}"',
                "hits": 1,
            }

            vespa_response = self.client.query(body=vespa_request_body)

            if "root" not in vespa_response.json:
                raise FetchError("Invalid response format from Vespa")

            root = vespa_response.json["root"]
            if "children" not in root or len(root["children"]) == 0:
                return None

            # Return the first (and should be only) matching profile
            hit = root["children"][0]
            return ModelProfile.from_vespa_response(hit)

        except VespaError as e:
            err_details = VespaErrorDetails.from_vespa_error(e)
            raise QueryError(err_details.summary) from e
        except HTTPError as e:
            raise FetchError(
                f"HTTP error when fetching profile {profile_id}: {e}"
            ) from e
        except Exception as e:
            raise FetchError(
                f"Unexpected error when fetching profile {profile_id}: {e}"
            ) from e
