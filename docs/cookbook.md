# Cookbook

Complete usage examples, from smallest to largest. Every recipe assumes:

```python
import time
from iris_fhirsql import FHIRSQLClient, TransformSpecBuilder

client = FHIRSQLClient(hostname="localhost", port=32783, superserver_port=32782)   # IRISUSERNAME/IRISPASSWORD set
```

and, where the spec needs one, an analysis (`analysis`) and repository (`repo`) created as shown in recipe 1.

Back to the [user guide](guide.md). Design details are in [Transform specs and subtables](transform-specs.md).

## Contents

1. [Flat projection, end to end](#1-flat-projection-end-to-end)
2. [Adding a subtable](#2-adding-a-subtable)
3. [Several subtables on one resource](#3-several-subtables-on-one-resource)
4. [Two resources joined by reference](#4-two-resources-joined-by-reference)
5. [Keeping decimals in measurements](#5-keeping-decimals-in-measurements)
6. [Save a spec, reload it, reuse it](#6-save-a-spec-reload-it-reuse-it)
7. [Discover FHIR servers instead of typing URLs](#7-discover-fhir-servers-instead-of-typing-urls)
8. [Run queries on the result from Python](#8-run-queries-on-the-result-from-python)
9. [Inspect and clean up](#9-inspect-and-clean-up)
10. [Handling errors](#10-handling-errors)

## 1. Flat projection, end to end

One resource, only single-valued columns. This is the smallest complete workflow.

```python
cred = client.credentials.create(system_name="CookbookCreds")

repo = client.repositories.create(
    name="CookbookRepo",
    host="localhost",
    fhir_url="/fhir/r4",
    internal_port=52773,               # container-internal web port
    credentials_name=cred.system_name,
)

analysis = client.analysis.create(repository_id=repo.id, selectivity_percentage=100)
while analysis.status != "completed":
    time.sleep(5)
    analysis = client.analysis.get(analysis.id)
    print("analysis:", analysis.status)

builder = TransformSpecBuilder("CookbookFlat", scan_id=analysis.id)
builder.add_field("Patient", "Patient.name.family", "String", name="LastName", length=50)
builder.add_field("Patient", "Patient.name.given",  "String", name="FirstName", length=50)
builder.add_field("Patient", "Patient.gender",      "String", name="Gender", length=10, index=True)
builder.add_field("Patient", "Patient.birthDate",   "String", name="BirthDate", length=10)
spec = client.transform_specs.create_from_builder(builder)

projection = client.projections.create(
    repository_id=repo.id, spec_id=spec.id,
    package_name="cookbookflat", users=["_SYSTEM", "SuperUser"],
)
projection = client.projections.poll_until_complete(projection.id)
print("status:", projection.status)   # Active
```

Result:

```sql
SELECT TOP 10 LastName, FirstName, Gender, BirthDate FROM cookbookflat.Patient
```

## 2. Adding a subtable

`Patient.name.family` flattens the repeating `name` element into one column, so a patient with several
addresses loses all but a flattened value. A subtable keeps every repetition as its own row.

```python
builder = TransformSpecBuilder("CookbookAddress", scan_id=analysis.id)

builder.add_field("Patient", "Patient.name.family", "String", name="LastName", length=50)

builder.add_subtable("Patient", "PatientAddress", path="Patient.address")
builder.add_subtable_field("Patient", "PatientAddress", "line",       "String", name="Line", length=100)
builder.add_subtable_field("Patient", "PatientAddress", "city",       "String", name="City", length=50)
builder.add_subtable_field("Patient", "PatientAddress", "state",      "String", name="State", length=50)
builder.add_subtable_field("Patient", "PatientAddress", "postalCode", "String", name="PostalCode", length=10)

print(builder.to_json())      # check the shape before sending
spec = client.transform_specs.create_from_builder(builder)
```

Project it as in recipe 1 with `package_name="cookbookaddress"`, then:

```sql
-- every address with its patient
SELECT p.LastName, a.City, a.State
FROM cookbookaddress.PatientAddress a
JOIN cookbookaddress.Patient p ON a.Patient = p.ID

-- patients with more than one address
SELECT p.LastName, COUNT(*) AS Addresses
FROM cookbookaddress.Patient p
JOIN cookbookaddress.PatientAddress a ON a.Patient = p.ID
GROUP BY p.LastName
HAVING COUNT(*) > 1

-- same join written with the reference arrow
SELECT a.Patient->LastName, a.City FROM cookbookaddress.PatientAddress a
```

Sanity check the paths worked. `COUNT(City)` counts non-NULL values, so it should be close to `COUNT(*)`:

```sql
SELECT COUNT(*) AS Rows, COUNT(City) AS WithCity FROM cookbookaddress.PatientAddress
```

If `WithCity` is 0, the column path is wrong. The classic cause is a full path such as
`Patient.address.city` instead of `city`, which the builder rejects for you.

## 3. Several subtables on one resource

Each repeating element gets its own subtable. Every table name in the spec must be unique
case-insensitively.

```python
builder = TransformSpecBuilder("CookbookContacts", scan_id=analysis.id)

builder.add_field("Patient", "Patient.gender", "String", name="Gender", length=10)
builder.add_field("Patient", "Patient.birthDate", "String", name="BirthDate", length=10)

builder.add_subtable("Patient", "PatientName", path="Patient.name")
builder.add_subtable_field("Patient", "PatientName", "use",    "String", name="NameUse", length=10)
builder.add_subtable_field("Patient", "PatientName", "family", "String", name="Family", length=50)
builder.add_subtable_field("Patient", "PatientName", "given",  "String", name="Given", length=50)

builder.add_subtable("Patient", "PatientAddress", path="Patient.address")
builder.add_subtable_field("Patient", "PatientAddress", "city",       "String", name="City", length=50)
builder.add_subtable_field("Patient", "PatientAddress", "postalCode", "String", name="PostalCode", length=10)

builder.add_subtable("Patient", "PatientTelecom", path="Patient.telecom")
builder.add_subtable_field("Patient", "PatientTelecom", "system", "String", name="System", length=10)
builder.add_subtable_field("Patient", "PatientTelecom", "value",  "String", name="Value", length=50, index=True)

spec = client.transform_specs.create_from_builder(builder)
```

Query the subtables together, for example each patient's email addresses and postcodes:

```sql
SELECT p.Gender, t.Value AS Email, a.PostalCode
FROM cookbookcontacts.Patient p
JOIN cookbookcontacts.PatientTelecom t ON t.Patient = p.ID AND t.System = 'email'
JOIN cookbookcontacts.PatientAddress a ON a.Patient = p.ID
```

Joining two subtables multiplies rows (emails x addresses per patient). That is expected SQL behaviour, not a
projection fault.

## 4. Two resources joined by reference

Project the referencing column as a real column, index it, and join on the other table's `Key`.

```python
builder = TransformSpecBuilder("CookbookClinical", scan_id=analysis.id)

builder.add_field("Patient", "Patient.name.family", "String", name="FamilyName", length=50)
builder.add_field("Patient", "Patient.birthDate",   "String", name="BirthDate", length=10)

builder.add_field("Observation", "Observation.status", "String", name="Status", length=10)
builder.add_field("Observation", "Observation.code.coding.code", "String", name="Code", length=20, index=True)
builder.add_field("Observation", "Observation.code.coding.display", "String", name="Description", length=250)
builder.add_field("Observation", "Observation.effectiveDateTime", "String", name="EffectiveDateTime", length=50)
builder.add_field("Observation", "Observation.valueQuantity.value", "%Numeric", name="Value")
builder.add_field("Observation", "Observation.valueQuantity.unit", "String", name="Unit", length=50)
builder.add_field("Observation", "Observation.subject.reference", "String", name="Patient", length=50, index=True)

spec = client.transform_specs.create_from_builder(builder)
```

```sql
SELECT p.FamilyName, o.Description, o.Value, o.Unit, o.EffectiveDateTime
FROM cookbookclinical.Patient p
JOIN cookbookclinical.Observation o ON o.Patient = p.Key    -- Key is 'Patient/<id>'
WHERE o.Code = '85354-9'
```

Combine with subtables freely: add `builder.add_subtable("Patient", "PatientAddress", "Patient.address")` and
so on to the same builder. Just make sure the subtable name does not equal `Patient` or `Observation`.

## 5. Keeping decimals in measurements

`Number` maps to `%Integer` and rounds. Use `%Numeric` for anything with a fractional part.

```python
builder = TransformSpecBuilder("CookbookNumbers", scan_id=analysis.id)
builder.add_field("Observation", "Observation.valueQuantity.value", "Number",   name="ValueRounded")
builder.add_field("Observation", "Observation.valueQuantity.value", "%Numeric", name="ValueExact")
```

For a stored value of `39.696`, `ValueRounded` is `40` and `ValueExact` is `39.696` (verified for
`%Numeric`; the rounding of `Number` is documented server behaviour). Projecting one path under two column
names has not been tested here; if the server objects, use two separate projections to compare.

## 6. Save a spec, reload it, reuse it

```python
builder.save("cookbook_contacts_spec.json")

# later, or on another machine
loaded = TransformSpecBuilder.load("cookbook_contacts_spec.json")
print(loaded.name, loaded.scan_id, [r["resourceType"] for r in loaded.resources])
```

Specs are tied to the analysis in `scanId`. To apply a saved spec to a different repository, analyse that
repository first and swap the id:

```python
import json
from pathlib import Path

data = json.loads(Path("cookbook_contacts_spec.json").read_text())
data["scanId"] = new_analysis.id
spec = client.transform_specs.create_from_builder(TransformSpecBuilder.from_dict(data))
```

Edit before reuse:

```python
loaded.remove_field("Patient", "BirthDate")
loaded.remove_subtable_field("Patient", "PatientTelecom", "System")
loaded.add_subtable_field("Patient", "PatientTelecom", "use", "String", name="Use", length=10)
```

## 7. Discover FHIR servers instead of typing URLs

Needs `superserver_port` on the client.

```python
cred = client.credentials.create(system_name="DiscoveryCreds")

servers = client.repositories.find_fhir_servers()
for s in servers:
    print(f"{s.namespace:12} {s.csp_url:20} {s.fhir_version}  internal port {s.web_port}")

created = client.repositories.add_fhir_servers(servers, credentials_name=cred.system_name)
print(f"registered {len(created)} new repositories")
```

Running it twice registers nothing the second time, because duplicates (same host, port and URL) are skipped.
Progress lines are printed per namespace and per server.

## 8. Run queries on the result from Python

Projected tables are ordinary SQL tables in the FSB namespace. Use the DB API on the superserver port:

```python
import iris

username, password = client.session.auth
conn = iris.connect("localhost", 32782, "FHIRSERVER", username, password)
cur = conn.cursor()

cur.execute("""
    SELECT p.FamilyName, a.City
    FROM cookbookaddress.PatientAddress a
    JOIN cookbookaddress.Patient p ON a.Patient = p.ID
""")
for family, city in cur.fetchall():
    print(family, city)

conn.close()
```

A full, runnable version with several queries and a NULL check is in
[`examples/subtable_workflow.py`](../examples/subtable_workflow.py).

## 9. Inspect and clean up

List what exists:

```python
for c in client.credentials.list():   print("credential", c.id, c.system_name)
for r in client.repositories.list():  print("repository", r.id, r.repository_url)
for a in client.analysis.list():      print("analysis  ", a.id, a.status)
for s in client.transform_specs.list(): print("spec      ", s.id, s.name)
for p in client.projections.list():   print("projection", p.id, p.package_name, p.status)
```

Delete in reverse dependency order (a projection uses the spec, the spec uses the analysis, and so on):

```python
client.projections.delete(projection.id)
client.transform_specs.delete(spec.id)
client.analysis.delete(analysis.id)
client.repositories.delete(repo.id)
client.credentials.delete(cred.id)
```

After deleting a projection, confirm in the Management Portal (System Explorer, SQL) that its package's tables
are gone if you need a clean namespace; this client does not check.

## 10. Handling errors

```python
from iris_fhirsql import ValidationError, APIError

# Caught by the builder, before any request
try:
    builder.add_subtable("Patient", "patientaddress", path="Patient.address")   # clashes with PatientAddress
except ValidationError as e:
    print("bad spec:", e)

try:
    builder.add_subtable_field("Patient", "Missing", "city", "String", name="City")
except ValidationError as e:
    print("bad spec:", e)      # subtable 'Missing' not found on Patient

# Caught by the client, before any request
try:
    client.transform_specs.create_from_builder(TransformSpecBuilder("Empty", scan_id=analysis.id))
except ValidationError as e:
    print("bad spec:", e)      # resources required

# Returned by the server
try:
    client.transform_specs.get("999999")
except APIError as e:
    print("server said", e.status_code, e)

# Projection outcomes
try:
    projection = client.projections.poll_until_complete(projection.id, interval=5, max_attempts=60)
except TimeoutError:
    print("still running after 5 minutes")
except RuntimeError as e:
    print("projection failed:", e)
```

Do not wrap these in a broad `except Exception`. Each failure above names what went wrong, and hiding it
tends to surface later as a table full of NULLs.
