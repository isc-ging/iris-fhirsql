"""Fixtures for tests against a live IRIS container (see docker-compose.ci.yml).

Connection settings come from env vars, with no defaults, so a misconfigured run fails
immediately with a KeyError rather than testing the wrong instance:
    FHIRSQL_HOST, FHIRSQL_PORT (mapped web port), FHIRSQL_SUPERSERVER_PORT (mapped),
    IRISUSERNAME, IRISPASSWORD

The full FSB workflow (credentials -> repository -> analysis -> spec -> projection) is slow,
so it runs once per session in the `workflow` fixture and individual tests inspect the result.
"""
import logging
import os
import time
import uuid
from contextlib import ExitStack

import iris
import pytest
import requests

from fhirsql import FHIRSQLClient, TransformSpecBuilder

log = logging.getLogger(__name__)

NAMESPACE = "FHIRSERVER"
FHIR_URL = "/fhir/r4"
INTERNAL_WEB_PORT = 52773  # web port as seen from inside the container
ANALYSIS_TIMEOUT_S = 600
ANALYSIS_POLL_S = 5


@pytest.fixture(scope="session")
def host():
    return os.environ["FHIRSQL_HOST"]


@pytest.fixture(scope="session")
def web_port():
    return int(os.environ["FHIRSQL_PORT"])


@pytest.fixture(scope="session")
def superserver_port():
    return int(os.environ["FHIRSQL_SUPERSERVER_PORT"])


@pytest.fixture(scope="session")
def client(host, web_port, superserver_port):
    return FHIRSQLClient(hostname=host, port=web_port, superserver_port=superserver_port,
                         username=os.environ["IRISUSERNAME"], password=os.environ["IRISPASSWORD"])


@pytest.fixture(scope="session")
def fhir_server_ready(client, host, web_port):
    """Fail early and clearly if the container has no FHIR server with sample patients."""
    log.info("checking FHIR endpoint %s has Patient data", FHIR_URL)
    response = requests.get(f"http://{host}:{web_port}{FHIR_URL}/Patient", params={"_summary": "count"},
                            auth=client.session.auth)
    response.raise_for_status()
    total = response.json()["total"]
    assert total > 0, f"FHIR server at {FHIR_URL} has no Patient resources (sample data not loaded?)"
    log.info("FHIR endpoint has %d patients", total)
    return total


@pytest.fixture(scope="session")
def db(host, superserver_port, client):
    """DB API connection to the FHIRSERVER namespace for querying projected tables."""
    username, password = client.session.auth
    conn = iris.connect(host, superserver_port, NAMESPACE, username, password)
    yield conn
    conn.close()


def query(db, sql):
    cursor = db.cursor()
    cursor.execute(sql)
    return cursor.fetchall()


@pytest.fixture(scope="session")
def workflow(client, fhir_server_ready):
    """Run the whole FSB workflow once; delete everything created on teardown."""
    run = uuid.uuid4().hex[:8]
    package = f"ci{run}"
    start = time.time()

    def step(message):
        log.info("[workflow %6.1fs] %s", time.time() - start, message)

    with ExitStack() as cleanup:
        step("credentials")
        cred = client.credentials.create(system_name=f"CICreds{run}")
        cleanup.callback(client.credentials.delete, cred.id)

        step("repository")
        repo = client.repositories.create(
            name=f"CIRepo{run}", host="localhost", fhir_url=FHIR_URL,
            internal_port=INTERNAL_WEB_PORT, credentials_name=cred.system_name)
        cleanup.callback(client.repositories.delete, repo.id)

        step("analysis")
        analysis = client.analysis.create(repository_id=repo.id, max_distinct=1000, selectivity_percentage=100)
        cleanup.callback(client.analysis.delete, analysis.id)
        while analysis.status != "completed":
            if time.time() - start > ANALYSIS_TIMEOUT_S:
                raise TimeoutError(f"analysis {analysis.id} still '{analysis.status}' after {ANALYSIS_TIMEOUT_S}s")
            time.sleep(ANALYSIS_POLL_S)
            analysis = client.analysis.get(analysis.id)
            step(f"analysis status: {analysis.status}")

        step("transform spec")
        builder = TransformSpecBuilder(f"CISpec{run}", scan_id=analysis.id)
        builder.add_field("Patient", "Patient.name.family", "String", name="FamilyName", length=50)
        builder.add_field("Patient", "Patient.gender", "String", name="Gender", length=10)
        builder.add_subtable("Patient", "PatientAddress", path="Patient.address")
        builder.add_subtable_field("Patient", "PatientAddress", "city", "String", name="City", length=50)
        builder.add_subtable_field("Patient", "PatientAddress", "state", "String", name="State", length=50)
        spec = client.transform_specs.create_from_builder(builder)
        cleanup.callback(client.transform_specs.delete, spec.id)

        step("projection")
        projection = client.projections.create(
            repository_id=repo.id, spec_id=spec.id, package_name=package,
            users=["_SYSTEM", "SuperUser"], name=f"CIProjection{run}")
        cleanup.callback(client.projections.delete, projection.id)
        projection = client.projections.poll_until_complete(projection.id)
        step(f"projection status: {projection.status}")

        yield {"package": package, "credential": cred, "repository": repo, "analysis": analysis,
               "spec": spec, "projection": projection}

        step("cleanup")
