"""End-to-end FSB workflow against the CI container. See conftest.py for the workflow fixture."""
from tests.integration.conftest import FHIR_URL, INTERNAL_WEB_PORT, NAMESPACE, query


def ids(items):
    return [str(item.id) for item in items]


def test_credential_listed(client, workflow):
    assert workflow["credential"].system_name in [c.system_name for c in client.credentials.list()]


def test_repository_listed(client, workflow):
    repo = workflow["repository"]
    assert str(repo.id) in ids(client.repositories.list())
    assert repo.repository_url == FHIR_URL
    assert str(repo.port) == str(INTERNAL_WEB_PORT)


def test_analysis_completed(client, workflow):
    assert client.analysis.get(workflow["analysis"].id).status == "completed"


def test_spec_listed(client, workflow):
    assert str(workflow["spec"].id) in ids(client.transform_specs.list())


def test_projection_active(client, workflow):
    assert client.projections.get(workflow["projection"].id).status == "Active"


def test_patient_table_has_standard_columns_and_rows(db, workflow, fhir_server_ready):
    pkg = workflow["package"]
    (count,), = query(db, f"SELECT COUNT(*) FROM {pkg}.Patient")
    assert count == fhir_server_ready
    # Key has the same form as subject.reference, so tables join on it directly
    (bad_keys,), = query(db, f"SELECT COUNT(*) FROM {pkg}.Patient WHERE \"Key\" NOT LIKE 'Patient/%'")
    assert bad_keys == 0
    (rownum_nulls,), = query(db, f"SELECT COUNT(*) FROM {pkg}.Patient WHERE RowNum IS NULL")
    assert rownum_nulls == 0


def test_patient_columns_populated(db, workflow):
    pkg = workflow["package"]
    (total, family, gender), = query(db, f"SELECT COUNT(*), COUNT(FamilyName), COUNT(Gender) FROM {pkg}.Patient")
    assert family > 0
    assert gender > 0
    assert total >= family


def test_subtable_rows_link_to_parent(db, workflow):
    pkg = workflow["package"]
    (count,), = query(db, f"SELECT COUNT(*) FROM {pkg}.PatientAddress")
    assert count > 0
    (orphans,), = query(db, f"SELECT COUNT(*) FROM {pkg}.PatientAddress a "
                            f"LEFT JOIN {pkg}.Patient p ON a.Patient = p.ID WHERE p.ID IS NULL")
    assert orphans == 0
    (bad_ids,), = query(db, f"SELECT COUNT(*) FROM {pkg}.PatientAddress WHERE ID NOT LIKE '%||%'")
    assert bad_ids == 0


def test_subtable_relative_paths_not_all_null(db, workflow):
    """Regression guard: full-path subtable columns silently give all-NULL columns."""
    pkg = workflow["package"]
    (rows, cities, states), = query(db, f"SELECT COUNT(*), COUNT(City), COUNT(State) FROM {pkg}.PatientAddress")
    assert cities > 0
    assert states > 0
    assert rows >= cities


def test_arrow_join_from_subtable_to_parent(db, workflow):
    pkg = workflow["package"]
    rows = query(db, f"SELECT TOP 5 a.Patient->FamilyName, a.City FROM {pkg}.PatientAddress a")
    assert rows
    assert any(family is not None for family, _ in rows)


def test_find_fhir_servers_discovers_container_endpoint(client):
    servers = client.repositories.find_fhir_servers(namespace=NAMESPACE)
    matches = [s for s in servers if s.csp_url == FHIR_URL]
    assert len(matches) == 1, f"expected one server at {FHIR_URL}, found {[s.csp_url for s in servers]}"
    assert matches[0].web_port == INTERNAL_WEB_PORT
