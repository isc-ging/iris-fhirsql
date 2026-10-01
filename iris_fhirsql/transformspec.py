import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from iris_fhirsql.exceptions import ValidationError

class TransformSpecBuilder:
    """Build transform specifications programmatically.

    Produces the payload shape the FSB /transformspec endpoint expects:
    {"name", "scanId", "description", "resources": [{"resourceType", "columns": [...]}]}

    Example:
        builder = TransformSpecBuilder("Patient Demographics", scan_id=analysis.id)
        builder.add_field("Patient", "Patient.name.family", "String", name="FamilyName", length=50)
        builder.add_field("Patient", "Patient.gender", "String", name="Gender", length=10, index=True)
        spec = client.transform_specs.create_from_builder(builder)
    """

    def __init__(self, name: str, scan_id: int, description: str = ""):
        self.spec = {"name": name, "scanId": scan_id, "description": description, "resources": []}

    @property
    def name(self) -> str:
        return self.spec["name"]

    @property
    def scan_id(self) -> int:
        return self.spec["scanId"]

    @property
    def description(self) -> str:
        return self.spec["description"]

    @property
    def resources(self) -> List[Dict[str, Any]]:
        return self.spec["resources"]

    def _find_resource(self, resource_type: str) -> Optional[Dict[str, Any]]:
        # None means the resource type has not been added yet; callers branch on it
        for resource in self.spec["resources"]:
            if resource["resourceType"] == resource_type:
                return resource
        return None

    def add_resource_type(self, resource_type: str):
        if self._find_resource(resource_type) is None:
            self.spec["resources"].append({"resourceType": resource_type, "columns": []})
        return self

    def add_field(self, resource_type: str, path: str, field_type: str, name: str,
                  length: Optional[int] = None, index: bool = False, data_index: bool = False):
        """
        Add a column to a resource type's table.

        Args:
            resource_type: FHIR resource type (e.g. "Patient")
            path: Full FHIRPath starting with the resource type (e.g. "Patient.name.family")
            field_type: Column type as reported by analysis ("String", "Number", "Boolean").
                        "Number" maps to %Integer and ROUNDS decimals (39.696 -> 40); use
                        "%Numeric" to keep decimals.
            name: SQL column name
            length: Max length for String columns (omit for Number/Boolean)
            index: Create an index on this column
            data_index: Create a data index on this column
        """
        if not path.startswith(f"{resource_type}."):
            raise ValidationError(f"path '{path}' must start with '{resource_type}.'")
        self.add_resource_type(resource_type)
        columns = self._find_resource(resource_type)["columns"]
        if any(col["name"] == name for col in columns):
            raise ValidationError(f"column '{name}' already exists on {resource_type}")

        column = {"name": name, "type": field_type, "path": path,
                  "index": index, "dataIndex": data_index}
        if length is not None:
            column["length"] = length
        columns.append(column)
        return self

    def remove_field(self, resource_type: str, name: str):
        resource = self._find_resource(resource_type)
        if resource is None:
            raise ValidationError(f"resource type '{resource_type}' not in spec")
        remaining = [col for col in resource["columns"] if col["name"] != name]
        if len(remaining) == len(resource["columns"]):
            raise ValidationError(f"column '{name}' not found on {resource_type}")
        resource["columns"] = remaining
        return self

    def _all_table_names(self) -> List[str]:
        names = []
        for resource in self.spec["resources"]:
            names.append(resource["resourceType"])
            names.extend(sub["name"] for sub in resource.get("subTables", []))
        return names

    def _get_subtable(self, resource_type: str, subtable: str) -> Dict[str, Any]:
        resource = self._find_resource(resource_type)
        if resource is None:
            raise ValidationError(f"resource type '{resource_type}' not in spec")
        for sub in resource.get("subTables", []):
            if sub["name"] == subtable:
                return sub
        raise ValidationError(f"subtable '{subtable}' not found on {resource_type}")

    def add_subtable(self, resource_type: str, name: str, path: str):
        """
        Add a subtable: one SQL row per repetition of a repeating element.

        Args:
            resource_type: Parent FHIR resource type (e.g. "Patient"); added if missing
            name: SQL table name; must be unique across the whole spec (case-insensitive)
            path: Full FHIRPath of the repeating element (e.g. "Patient.address")
        """
        if not path.startswith(f"{resource_type}."):
            raise ValidationError(f"path '{path}' must start with '{resource_type}.'")
        if name.lower() in (existing.lower() for existing in self._all_table_names()):
            raise ValidationError(f"table name '{name}' already used in spec (names are case-insensitive)")
        self.add_resource_type(resource_type)
        self._find_resource(resource_type).setdefault("subTables", []).append(
            {"name": name, "path": path, "columns": []})
        return self

    def add_subtable_field(self, resource_type: str, subtable: str, path: str, field_type: str,
                           name: str, length: Optional[int] = None, index: bool = False,
                           data_index: bool = False):
        """
        Add a column to a subtable.

        Args:
            resource_type: Parent FHIR resource type
            subtable: Subtable name given to add_subtable
            path: FHIRPath RELATIVE to the subtable path (e.g. "city" for "Patient.address").
                  Full paths are accepted by the server but silently give all-NULL columns.
            field_type: Column type, as for add_field
            name: SQL column name
            length: Max length for String columns
            index: Create an index on this column
            data_index: Create a data index on this column
        """
        if path.startswith(f"{resource_type}."):
            raise ValidationError(
                f"subtable path '{path}' must be relative to the subtable path, not start with '{resource_type}.'")
        columns = self._get_subtable(resource_type, subtable)["columns"]
        if any(col["name"] == name for col in columns):
            raise ValidationError(f"column '{name}' already exists on subtable {subtable}")

        column = {"name": name, "type": field_type, "path": path,
                  "index": index, "dataIndex": data_index}
        if length is not None:
            column["length"] = length
        columns.append(column)
        return self

    def remove_subtable_field(self, resource_type: str, subtable: str, name: str):
        sub = self._get_subtable(resource_type, subtable)
        remaining = [col for col in sub["columns"] if col["name"] != name]
        if len(remaining) == len(sub["columns"]):
            raise ValidationError(f"column '{name}' not found on subtable {subtable}")
        sub["columns"] = remaining
        return self

    def to_dict(self) -> Dict[str, Any]:
        return json.loads(json.dumps(self.spec))

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.spec, indent=indent)

    def save(self, file_path: str):
        Path(file_path).write_text(self.to_json())

    @classmethod
    def load(cls, file_path: str):
        return cls.from_dict(json.loads(Path(file_path).read_text()))

    @classmethod
    def from_dict(cls, spec_data: Dict[str, Any]):
        builder = cls(spec_data["name"], spec_data["scanId"], spec_data["description"])
        builder.spec["resources"] = json.loads(json.dumps(spec_data["resources"]))
        return builder
