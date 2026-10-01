from typing import List, Dict, Any
from fhirsql.resources.base import BaseResource
from fhirsql.models import TransformSpec
from fhirsql.exceptions import ValidationError

class TransformSpecResource(BaseResource):
    def list(self) -> List[TransformSpec]:
        data = self._make_request("GET", "/transformspec/")
        return [TransformSpec.from_dict(item) for item in (data if isinstance(data, list) else [])]

    def get(self, spec_id: str) -> TransformSpec:
        data = self._make_request("GET", "/transformspec", params={"ID": spec_id})
        return TransformSpec.from_dict(data)

    def create(self, name: str, scan_id: int, resources: List[Dict[str, Any]],
               description: str = "") -> TransformSpec:
        """
        Create a transformation specification defining FHIR-to-SQL field mappings.

        Transform specs use analysis results to map nested FHIR resources to flat
        SQL columns. Created specs are used by projections to generate actual tables.
        Usually called via create_from_builder() with a TransformSpecBuilder.

        Args:
            name: Display name for the specification
            scan_id: Analysis ID (from Analysis.id) providing resource schema
            resources: List of {"resourceType": ..., "columns": [...]} mappings.
                       Must be non-empty: the server rejects specs without resources.
            description: Optional description

        Returns:
            TransformSpec: Created specification object

        Example:
            builder = TransformSpecBuilder("Patient Demographics", scan_id=analysis.id)
            builder.add_field("Patient", "Patient.gender", "String", name="Gender", length=10)
            spec = client.transform_specs.create_from_builder(builder)
        """
        if not name:
            raise ValidationError("name required")
        if not scan_id:
            raise ValidationError("scan_id required")
        if not resources:
            raise ValidationError("resources required: add at least one field to the spec")
        for resource in resources:
            has_subtable_columns = any(sub["columns"] for sub in resource.get("subTables", []))
            if not resource["columns"] and not has_subtable_columns:
                raise ValidationError(
                    f"resource '{resource['resourceType']}' has no columns or subtable columns")

        payload = {"name": name, "scanId": scan_id, "description": description,
                   "resources": resources}
        data = self._make_request("POST", "/transformspec", json=payload)

        # API returns every spec; names are not guaranteed unique, so take the newest match
        matches = [item for item in data if item["name"] == name]
        if not matches:
            raise ValueError(f"created transform spec '{name}' not found in POST /transformspec response")
        return TransformSpec.from_dict(max(matches, key=lambda item: item["id"]))

    def create_from_builder(self, builder) -> TransformSpec:
        return self.create(builder.name, builder.scan_id, builder.to_dict()["resources"],
                           builder.description)

    def update(self, spec: TransformSpec) -> TransformSpec:
        if not spec.id:
            raise ValidationError("Transform spec ID required for update")
        data = self._make_request("PUT", "/transformspec", json=spec.to_dict())
        return TransformSpec.from_dict(data)

    def delete(self, spec_id: str) -> bool:
        self._make_request("DELETE", "/transformspec", params={"ID": spec_id})
        return True
