from typing import List
from fhirsql.resources.base import BaseResource
from fhirsql.models import Projection
from fhirsql.exceptions import ValidationError

class ProjectionResource(BaseResource):
    def list(self) -> List[Projection]:
        data = self._make_request("GET", "/projection/")
        return [Projection.from_dict(item) for item in (data if isinstance(data, list) else [])]

    def get(self, projection_id: str) -> Projection:
        data = self._make_request("GET", "/projection", params={"ID": projection_id})
        return Projection.from_dict(data)

    def create(self, spec_id: str) -> Projection:
        if not spec_id:
            raise ValidationError("spec_id required")
        data = self._make_request("POST", "/projection", json={"specID": spec_id})
        return Projection.from_dict(data)

    def update(self, projection_id: str, spec_id: str) -> Projection:
        if not all([projection_id, spec_id]):
            raise ValidationError("projection_id and spec_id required")
        data = self._make_request("PUT", "/projection",
                                 json={"id": projection_id, "specID": spec_id})
        return Projection.from_dict(data)

    def delete(self, projection_id: str) -> bool:
        self._make_request("DELETE", "/projection", params={"ID": projection_id})
        return True
