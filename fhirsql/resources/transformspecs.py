from typing import List, Dict, Any
from fhirsql.resources.base import BaseResource
from fhirsql.models import TransformSpec
from fhirsql.exceptions import ValidationError

class TransformSpecResource(BaseResource):
    def list(self) -> List[TransformSpec]:
        data = self._make_request("GET", "/transformspec/")
        return [TransformSpec.from_dict(item) for item in (data if isinstance(data, list) else [])]

    def get(self, spec_id: str) -> TransformSpec:
        data = self._make_request("GET", "/transformspec", params={"SPECID": spec_id})
        return TransformSpec.from_dict(data)

    def create(self, spec_data: Dict[str, Any]) -> TransformSpec:
        if not spec_data.get("name"):
            raise ValidationError("name required")
        data = self._make_request("POST", "/transformspec", json=spec_data)
        return TransformSpec.from_dict(data)

    def create_from_builder(self, builder) -> TransformSpec:
        return self.create(builder.to_dict())

    def update(self, spec: TransformSpec) -> TransformSpec:
        if not spec.id:
            raise ValidationError("Transform spec ID required for update")
        data = self._make_request("PUT", "/transformspec", json=spec.to_dict())
        return TransformSpec.from_dict(data)

    def delete(self, spec_id: str) -> bool:
        self._make_request("DELETE", "/transformspec", params={"ID": spec_id})
        return True
