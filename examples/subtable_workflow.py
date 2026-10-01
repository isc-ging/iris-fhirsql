"""
Subtable workflow: project Patient plus its repeating address and telecom elements.

Runs the full FSB workflow against the local iris-fhir container, queries the projected
tables over the DB API, then (optionally) deletes everything it created.

Requires IRISUSERNAME and IRISPASSWORD in the environment.

    python examples/subtable_workflow.py            # keep the projection
    python examples/subtable_workflow.py --cleanup  # delete everything afterwards
"""
import sys
import time

import iris

from iris_fhirsql import FHIRSQLClient, TransformSpecBuilder

WEB_PORT = 32783          # mapped host port for the web server
SUPERSERVER_PORT = 32782  # mapped host port for the superserver
INTERNAL_WEB_PORT = 52773 # web port as seen from inside the container
NAMESPACE = "FHIRSERVER"
PACKAGE = "subtabledemo"

start = time.time()


def log(message):
    print(f"[{time.time() - start:6.1f}s] {message}", flush=True)


client = FHIRSQLClient(hostname="localhost", port=WEB_PORT, superserver_port=SUPERSERVER_PORT)

log("1. credentials")
cred = client.credentials.create(system_name="SubtableDemoCreds")

log("2. repository")
repo = client.repositories.create(
    name="SubtableDemoRepo",
    host="localhost",
    fhir_url="/fhir/r4",
    internal_port=INTERNAL_WEB_PORT,
    credentials_name=cred.system_name,
)

log("3. analysis")
analysis = client.analysis.create(repository_id=repo.id, selectivity_percentage=100)
while analysis.status != "completed":
    time.sleep(5)
    analysis = client.analysis.get(analysis.id)
    log(f"   analysis status: {analysis.status}")

log("4. transform spec")
builder = TransformSpecBuilder("SubtableDemo", analysis_id=analysis.id)
builder.add_field("Patient", "Patient.name.family", "String", name="FamilyName", length=50)
builder.add_field("Patient", "Patient.gender", "String", name="Gender", length=10)

# One row per Patient.address. Column paths are RELATIVE to the subtable path.
builder.add_subtable("Patient", "PatientAddress", path="Patient.address")
builder.add_subtable_field("Patient", "PatientAddress", "city", "String", name="City", length=50)
builder.add_subtable_field("Patient", "PatientAddress", "state", "String", name="State", length=50)
builder.add_subtable_field("Patient", "PatientAddress", "postalCode", "String", name="PostalCode", length=10)

# One row per Patient.telecom
builder.add_subtable("Patient", "PatientTelecom", path="Patient.telecom")
builder.add_subtable_field("Patient", "PatientTelecom", "system", "String", name="System", length=10)
builder.add_subtable_field("Patient", "PatientTelecom", "value", "String", name="Value", length=50)

builder.save("subtable_demo_spec.json")
spec = client.transform_specs.create_from_builder(builder)
log(f"   spec id: {spec.id}")

log("5. projection")
projection = client.projections.create(
    repository_id=repo.id,
    spec_id=spec.id,
    package_name=PACKAGE,
    users=["_SYSTEM", "SuperUser"],
    name="SubtableDemoProjection",
)
projection = client.projections.poll_until_complete(projection.id)
log(f"   projection status: {projection.status}")

log("6. query")
username, password = client.session.auth
conn = iris.connect("localhost", SUPERSERVER_PORT, NAMESPACE, username, password)
cur = conn.cursor()

for label, sql in [
    ("row counts", f"SELECT (SELECT COUNT(*) FROM {PACKAGE}.Patient), "
                   f"(SELECT COUNT(*) FROM {PACKAGE}.PatientAddress), "
                   f"(SELECT COUNT(*) FROM {PACKAGE}.PatientTelecom)"),
    ("addresses joined to patients",
     f"SELECT TOP 5 p.FamilyName, a.City, a.State, a.PostalCode "
     f"FROM {PACKAGE}.PatientAddress a JOIN {PACKAGE}.Patient p ON a.Patient = p.ID"),
    ("phone numbers via -> join",
     f"SELECT TOP 5 t.Patient->FamilyName, t.System, t.Value FROM {PACKAGE}.PatientTelecom t"),
    ("null check on address city",
     f"SELECT COUNT(*), COUNT(City) FROM {PACKAGE}.PatientAddress"),
]:
    cur.execute(sql)
    log(f"   {label}:")
    for row in cur.fetchall():
        print("     ", row)
conn.close()

if "--cleanup" in sys.argv:
    log("7. cleanup")
    client.projections.delete(projection.id)
    client.transform_specs.delete(spec.id)
    client.analysis.delete(analysis.id)
    client.repositories.delete(repo.id)
    client.credentials.delete(cred.id)
    log("   deleted projection, spec, analysis, repository, credential")
else:
    log("7. skipping cleanup (pass --cleanup to delete created objects)")
