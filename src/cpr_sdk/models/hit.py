from typing_extensions import Self
from pydantic import BaseModel


class BaseHit(BaseModel):
    def from_vespa_response(self, response_hit: dict) -> Self:
        """
        Create a Hit from a Vespa response hit.

        :param dict response_hit: part of a json response from Vespa
        :raises ValueError: if the response type is unknown
        :return Hit: an individual document or passage hit
        """
        # vespa structures its response differently depending on the api endpoint
        # for searches, the response should contain a sddocname field
        response_type = response_hit.get("fields", {}).get("sddocname")
        if response_type is None:
            # for get_by_id, the response should contain an id field
            response_type = response_hit["id"].split(":")[2]

        if response_type == self.response_type:
            hit = self.from_vespa_response(response_hit=response_hit)
        else:
            raise ValueError(f"Unknown response type: {response_type}")
        return hit

    def __eq__(self, other):
        """
        Check if two hits are equal.

        Ignores relevance and rank_features as these are dependent on non-deterministic query routing.
        """
        if not isinstance(other, self.__class__):
            return False

        fields_to_compare = [
            f for f in self.__dict__.keys() if f not in ("relevance", "rank_features")
        ]

        return all(getattr(self, f) == getattr(other, f) for f in fields_to_compare)
