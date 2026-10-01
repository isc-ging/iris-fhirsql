---
name: using-iris-fhirsql
description: Use when projecting FHIR resources as SQL tables with InterSystems IRIS FHIR SQL Builder (FSB) from Python, writing code against the iris_fhirsql package, or debugging FSB projections that return NULL columns, wrong ports, or 500 errors.
---

# Using iris_fhirsql

## Overview

`iris_fhirsql.FHIRSQLClient` wraps the FSB REST API (`/csp/fhirsql/api/ui`). Workflow is a fixed chain, each step needs the previous step's output:

| Step | Call | Produces | Next step needs |
|---|---|---|---|
| 1. Credentials | `client.credentials.create(...)` | `Credential` | `cred.system_name` |
| 2. Repository | `client.repositories.create(...)` | `Repository` | `repo.id` |
| 3. Analysis | `client.analysis.create(...)` | `Analysis` (async) | `analysis.id` once `status == "completed"` |
| 4. Transform spec | `TransformSpecBuilder` + `client.transform_specs.create_from_builder(b)` | `TransformSpec` | `spec.id` |
| 5. Projection | `client.projections.create(...)` | SQL tables `<package_name>.<Table>` | - |

## Workflow

```python
import time
from iris_fhirsql import FHIRSQLClient, TransformSpecBuilder

# port = web server port the CLIENT connects to (mapped host port for containers)
# username/password fall back to IRISUSERNAME / IRISPASSWORD env vars; raises if neither
client = FHIRSQLClient(hostname="localhost", port=32783)

cred = client.credentials.create(system_name="SQLBuilderCreds")   # username/password default to client login
repo = client.repositories.create(
    name="Repo",
    host="localhost",                  # hostname as seen FROM the FSB instance
    fhir_url="/fhir/r4",               # FHIR endpoint path (CSP url)
    credentials_name=cred.system_name, # system_name, NOT cred.id
    internal_port=52773,               # see "Ports" below
)

analysis = client.analysis.create(repository_id=repo.id, selectivity_percentage=100)
while analysis.status != "completed":           # "running" -> "completed"
    time.sleep(5)
    analysis = client.analysis.get(analysis.id)

b = TransformSpecBuilder("MySpec", scan_id=analysis.id, description="")
b.add_field("Patient", "Patient.name.family", "String", name="LastName", length=50)
b.add_field("Patient", "Patient.gender", "String", name="Gender", length=10, index=True)
b.add_subtable("Patient", "PatientAddress", path="Patient.address")
b.add_subtable_field("Patient", "PatientAddress", "city", "String", name="City", length=50)
spec = client.transform_specs.create_from_builder(b)

proj = client.projections.create(repository_id=repo.id, spec_id=spec.id,
                                 package_name="patientdata", users=["_SYSTEM", "SuperUser"])
proj = client.projections.poll_until_complete(proj.id)   # status goes straight to "Active"
```

Query: `SELECT p.LastName, a.City FROM patientdata.PatientAddress a JOIN patientdata.Patient p ON a.Patient = p.ID`

Runnable versions: `examples/complete_workflow.py`, `examples/subtable_workflow.py`. Real request bodies: `payload-examples/*.body`.

## Defining columns: `add_field`

```python
b.add_field(resource_type, path, field_type, name, length=None, index=False, data_index=False)
```

One call = one column on table `<package>.<resource_type>` (one row per FHIR resource). Resource type is added to the spec on first use.

| Param | Meaning |
|---|---|
| `resource_type` | FHIR resource type, e.g. `"Patient"`, `"Observation"`. Becomes table name. |
| `path` | **Full FHIRPath starting with the resource type**: `"Patient.name.family"`, `"Observation.valueQuantity.value"`, `"Observation.subject.reference"`. Builder raises `ValidationError` if it does not start with `"<resource_type>."`. |
| `field_type` | `"String"`, `"Number"`/`"Integer"`, `"Boolean"`, `"Reference"` (case-insensitive), or any IRIS type passed through, e.g. `"%Numeric"`. See Types. |
| `name` | SQL column name. Unique per table (builder raises on duplicate). |
| `length` | Max length for string columns. Optional, server default 250. Omit for numbers/booleans. |
| `index` | Create a standard index on the column. |
| `data_index` | Create a data index on the column. |

Server does NOT validate `path` or `type`: a typo in the path projects fine and gives an all-NULL column. Check `COUNT(col)` after projecting.

Types (`$$$DataType` macro): `string`/`reference` -> `%String`; `number`/`integer` -> `%Integer` (ROUNDS decimals: 39.696 -> 40); `boolean` -> `%Boolean`. For decimal values (lab results, vitals) use `"%Numeric"`.

Other builder calls: `remove_field(resource_type, name)`, `save(path)` / `TransformSpecBuilder.load(path)` (JSON file), `to_dict()`. Spec with zero resources fails server-side: 500 `<INVALID OREF>ValidateStructure`.

## Subtables (repeating elements)

FHIR elements that repeat (arrays: `Patient.address`, `Patient.telecom`, `Patient.identifier`, `Observation.component`) need a subtable: separate SQL table with **one row per array element**, linked back to parent row.

```python
b.add_subtable(resource_type, name, path)
b.add_subtable_field(resource_type, subtable, path, field_type, name, length=None, index=False, data_index=False)
```

- `add_subtable("Patient", "PatientAddress", path="Patient.address")`: `path` is FULL path to the repeating element. `name` becomes table `<package>.PatientAddress`; must be unique across the WHOLE spec including resource table names, case-insensitive (so `"patient"` clashes with `Patient`).
- `add_subtable_field("Patient", "PatientAddress", "city", ...)`: `subtable` is the `name` from `add_subtable`. `path` is **RELATIVE to the subtable path** (`"city"`, not `"Patient.address.city"`). Builder raises if it starts with `"Patient."`; the raw API accepts full paths but silently projects all-NULL. Other params same as `add_field`.
- In JSON, subtables nest inside the parent resource (`resources[i].subTables`), not as separate `resources` entries.

Generated subtable columns: `Patient` (parent row `ID`, so `a.Patient->LastName` implicit join works), `ID` (`<parentID>||<n>`), `<name>Number`, plus your columns.

Resource tables get `ID`, `Key` (`Patient/<id>`, same form as `Observation.subject.reference`) and `RowNum`. So a column added with `add_field("Observation", "Observation.subject.reference", "Reference", name="SubjectRef")` joins directly: `o.SubjectRef = p.Key`.

## Ports and hosts (containers)

FSB calls the FHIR server itself, from inside IRIS. Two different ports:

- `FHIRSQLClient(port=...)`: port YOUR Python process uses to reach FSB REST API. For container = mapped host port (e.g. `32783`).
- `repositories.create(internal_port=...)` (or `port=`): stored as the `"port"` field of the repository record (`POST /fhirrepository` body: `{"hostname", "port", "repositoryURL", ...}`). FSB builds `http://<hostname>:<port><repositoryURL>` from it, so it must be the web port as seen from INSIDE the FSB instance (e.g. `52773`). Same for `host`: `"localhost"` when the FHIR server lives on the same IRIS instance.
- Precedence: `internal_port` > `port` > client's port. Omitting both behind a port map stores `32783`, and analysis fails to reach the FHIR server.

## Discovering and registering FHIR servers

Use when FHIR endpoint paths are unknown. Requires `pip install intersystems-irispython` (else `ImportError`) and the superserver port on the client (else `ValidationError`):

```python
client = FHIRSQLClient(hostname="localhost", port=32783, superserver_port=32782)
servers = client.repositories.find_fhir_servers()            # all namespaces
servers = client.repositories.find_fhir_servers(namespace="FHIRSERVER", include_disabled=True)
```

- Connects via DB API (not REST), reads internal web port from `^%SYS("WebServer","Port")`, queries `HS_FHIRServer.RepoInstance` in each namespace. Decommissioned endpoints always excluded; disabled excluded unless `include_disabled=True`.
- Returns `List[FHIRServer]`: `namespace`, `csp_url` (e.g. `/fhir/r4`), `fhir_version`, `web_port` (INTERNAL port, already correct for repository), `is_enabled`, `name` (often `None`). Empty list = none found.

Register as FSB repositories:

```python
repos = client.repositories.add_fhir_servers(servers, credentials_name=cred.system_name, host="localhost")
repo = client.repositories.create_from_fhir_server(server, credentials_name=cred.system_name,
                                                   name=None, host="localhost", ssl_config=None)
```

- `create_from_fhir_server`: one repository, `fhir_url=server.csp_url`, `internal_port=server.web_port`. Name defaults to `server.name` or `"<namespace><csp_url>"`.
- `add_fhir_servers`: calls `create_from_fhir_server` for each, skipping servers whose `(host, port, csp_url)` already exists as a repository. Returns only newly created ones.

## Other gotchas

- `create()` POSTs return the full entity list; resource methods pick the new one by name. Use unique names.
- `analysis.create`: pass `selectivity_percentage` (0-100) OR `max_distinct`, not both; default `selectivity_percentage=100`.
- List/get/delete on every manager: `client.<credentials|repositories|analysis|transform_specs|projections>.list()/get(id)/delete(id)`. GET/DELETE by id use `ID` query param; analysis update uses `TASKID` (unverified).

## Writing new code in this package

Existing code uses `.get()` and fallbacks when parsing responses. Do not copy. Fail loudly on missing expected fields (`d["key"]`).
