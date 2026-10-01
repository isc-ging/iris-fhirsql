"""Unit tests for the local TransformSpecBuilder and client construction. No IRIS needed."""
import pytest

from fhirsql import FHIRSQLClient, TransformSpecBuilder, ValidationError


def make_builder():
    return TransformSpecBuilder("Spec", scan_id=1, description="d")


def test_add_field_builds_column():
    builder = make_builder().add_field("Patient", "Patient.gender", "String", name="Gender", length=10, index=True)
    assert builder.to_dict()["resources"] == [{
        "resourceType": "Patient",
        "columns": [{"name": "Gender", "type": "String", "path": "Patient.gender",
                     "index": True, "dataIndex": False, "length": 10}],
    }]


def test_add_field_rejects_path_for_other_resource():
    with pytest.raises(ValidationError):
        make_builder().add_field("Patient", "Observation.code", "String", name="Code")


def test_add_field_rejects_duplicate_column_name():
    builder = make_builder().add_field("Patient", "Patient.gender", "String", name="Gender")
    with pytest.raises(ValidationError):
        builder.add_field("Patient", "Patient.birthDate", "String", name="Gender")


def test_remove_field_missing_raises():
    with pytest.raises(ValidationError):
        make_builder().remove_field("Patient", "Nope")


def test_subtable_column_paths_must_be_relative():
    builder = make_builder().add_subtable("Patient", "Addr", path="Patient.address")
    with pytest.raises(ValidationError):
        builder.add_subtable_field("Patient", "Addr", "Patient.address.city", "String", name="City")
    builder.add_subtable_field("Patient", "Addr", "city", "String", name="City", length=50)
    sub = builder.to_dict()["resources"][0]["subTables"][0]
    assert sub == {"name": "Addr", "path": "Patient.address",
                   "columns": [{"name": "City", "type": "String", "path": "city",
                                "index": False, "dataIndex": False, "length": 50}]}


def test_table_names_unique_case_insensitive():
    builder = make_builder().add_subtable("Patient", "Addr", path="Patient.address")
    with pytest.raises(ValidationError):
        builder.add_subtable("Patient", "ADDR", path="Patient.telecom")
    with pytest.raises(ValidationError):
        builder.add_subtable("Patient", "patient", path="Patient.telecom")


def test_save_load_roundtrip(tmp_path):
    builder = make_builder()
    builder.add_field("Patient", "Patient.gender", "String", name="Gender", length=10)
    builder.add_subtable("Patient", "Addr", path="Patient.address")
    builder.add_subtable_field("Patient", "Addr", "city", "String", name="City")
    path = tmp_path / "spec.json"
    builder.save(str(path))
    assert TransformSpecBuilder.load(str(path)).to_dict() == builder.to_dict()


def test_client_without_credentials_raises(monkeypatch):
    monkeypatch.delenv("IRISUSERNAME", raising=False)
    monkeypatch.delenv("IRISPASSWORD", raising=False)
    with pytest.raises(ValueError):
        FHIRSQLClient(hostname="localhost")
