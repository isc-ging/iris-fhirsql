import json
from typing import Dict, Any, Optional
from pathlib import Path

class TransformSpecBuilder:
    """Build transform specifications programmatically.

    Example:
        builder = TransformSpecBuilder("Patient Demographics")
        builder.set_analysis_id("analysis123")
        builder.add_resource_type("Patient")
        builder.add_field("Patient", "id", "string")
        builder.save("spec.json")
    """

    def __init__(self, name: str, spec_data: Optional[Dict] = None):
        self.spec = spec_data.copy() if spec_data else {"name": name, "resourceTypes": {}}
        self.name = name

    def set_analysis_id(self, analysis_id: str):
        self.spec["analysisID"] = analysis_id
        return self

    def add_resource_type(self, resource_type: str):
        if resource_type not in self.spec["resourceTypes"]:
            self.spec["resourceTypes"][resource_type] = {"fields": {}}
        return self

    def add_field(self, resource_type: str, field_path: str, field_type: str, **kwargs):
        if resource_type not in self.spec["resourceTypes"]:
            self.add_resource_type(resource_type)

        field_spec = {"type": field_type}
        field_spec.update(kwargs)
        self.spec["resourceTypes"][resource_type]["fields"][field_path] = field_spec
        return self

    def remove_field(self, resource_type: str, field_path: str):
        if resource_type in self.spec["resourceTypes"]:
            self.spec["resourceTypes"][resource_type]["fields"].pop(field_path, None)
        return self

    def to_dict(self) -> Dict[str, Any]:
        return self.spec.copy()

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.spec, indent=indent)

    def save(self, file_path: str):
        Path(file_path).write_text(json.dumps(self.spec, indent=2))

    @classmethod
    def load(cls, file_path: str):
        spec_data = json.loads(Path(file_path).read_text())
        return cls(name=spec_data.get("name", "Loaded Spec"), spec_data=spec_data)

    @classmethod
    def from_dict(cls, spec_data: Dict[str, Any]):
        return cls(name=spec_data.get("name", "Untitled"), spec_data=spec_data)
