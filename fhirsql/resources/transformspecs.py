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

    def create(self, name: str, scan_id: int, spec_data: Dict[str, Any] = None) -> TransformSpec:
        """
        Create a transformation specification defining FHIR-to-SQL field mappings.

        Transform specs use analysis results to map nested FHIR resources to flat
        SQL columns. Created specs are used by projections to generate actual tables.

        Workflow:
        1. Run Analysis and get analysis.id (scan_id)
        2. Create Transform Spec with name and scan_id
        3. Use TransformSpecBuilder or spec_data to define field mappings
        4. Use spec.id when creating Projection

        Args:
            name: Display name for the specification
            scan_id: Analysis ID (from Analysis.id) providing resource schema
            spec_data: Optional dict with 'resources' array containing mappings

        Returns:
            TransformSpec: Created specification object

        Example:
            spec = client.transform_specs.create(
                name="Patient Demographics",
                scan_id=analysis.id
            )
        """
        if not name:
            raise ValidationError("name required")
        if not scan_id:
            raise ValidationError("scan_id required")

        payload = {"name": name, "scanId": scan_id}
        if spec_data:
            payload.update(spec_data)

        data = self._make_request("POST", "/transformspec", json=payload)
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
