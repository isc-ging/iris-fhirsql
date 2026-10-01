---
name: using-iris-fhirsql
description: Use when projecting FHIR resources as SQL tables with InterSystems IRIS FHIR SQL Builder (FSB) from Python, or writing code against the iris_fhirsql package.
---

# Using iris_fhirsql

## Overview

`iris_fhirsql.FHIRSQLClient` wraps the FSB REST API (`/csp/fhirsql/api/ui`). Fixed chain, each step needs the previous step's output:

credentials (`system_name`) -> repository (`id`) -> analysis (`id`, once `completed`) -> transform spec (`id`) -> projection (SQL tables `<package_name>.<ResourceType>`)

## Workflow

```python
import time
from iris_fhirsql import FHIRSQLClient, TransformSpecBuilder

# port = web port the client connects to (mapped host port for containers)
# username/password fall back to IRISUSERNAME / IRISPASSWORD env vars; raises if neither
client = FHIRSQLClient(hostname="localhost", port=32783)

cred = client.credentials.create(system_name="SQLBuilderCreds")   # defaults to client login

# Registers an existing FHIR server endpoint with FSB; does not create a FHIR server
repo = client.repositories.create(
    name="Repo",
    host="localhost",                  # hostname as seen from the FSB instance
    fhir_url="/fhir/r4",               # FHIR endpoint path
    credentials_name=cred.system_name, # system_name, NOT cred.id
    internal_port=52773,               # see Ports
)

analysis = client.analysis.create(repository_id=repo.id, selectivity_percentage=100)
while analysis.status != "completed":           # "running" -> "completed"
    time.sleep(5)
    analysis = client.analysis.get(analysis.id)

b = TransformSpecBuilder("MySpec", scan_id=analysis.id)
b.add_field("Patient", "Patient.name.family", "String", name="LastName", length=50)
b.add_field("Patient", "Patient.gender", "String", name="Gender", length=10, index=True)
spec = client.transform_specs.create_from_builder(b)

proj = client.projections.create(repository_id=repo.id, spec_id=spec.id,
                                 package_name="patientdata", users=["_SYSTEM", "SuperUser"])
proj = client.projections.poll_until_complete(proj.id)   # status goes straight to "Active"
# SELECT LastName, Gender FROM patientdata.Patient
```

Runnable: `examples/complete_workflow.py`. Real request bodies: `payload-examples/*.body`.

## `add_field`

```python
b.add_field(resource_type, path, field_type, name, length=None, index=False, data_index=False)
```

One call = one column on table `<package>.<resource_type>` (one row per resource).

| Param | Meaning |
|---|---|
| `resource_type` | FHIR resource type (`"Patient"`). Becomes table name. |
| `path` | Full FHIRPath starting with resource type: `"Patient.name.family"`, `"Observation.valueQuantity.value"`. Builder raises otherwise. |
| `field_type` | `"String"`/`"Reference"` -> `%String`; `"Number"`/`"Integer"` -> `%Integer` (ROUNDS decimals: 39.696 -> 40); `"Boolean"` -> `%Boolean`. Other values pass through as IRIS types: use `"%Numeric"` for decimals. |
| `name` | SQL column name, unique per table. |
| `length` | Max string length. Optional, default 250. |
| `index` / `data_index` | Create index / data index on column. |

Server does not validate `path` or `type`: bad path = all-NULL column. Spec with no fields fails: 500 `<INVALID OREF>ValidateStructure`. Repeating elements (address, telecom) need subtables: see `examples/subtable_workflow.py`.

Projected tables also get `ID`, `RowNum` and `Key` (`Patient/<id>`, same form as `subject.reference`, so join reference columns on it directly).

## Ports

FSB fetches FHIR data itself, from inside IRIS, so the repository needs the port as seen from inside the instance:

- `FHIRSQLClient(port=32783)`: port your Python process uses (mapped host port).
- `repositories.create(internal_port=52773)`: stored as the repository's `"port"` field; FSB calls `http://<host>:<port><fhir_url>`. Precedence `internal_port` > `port` > client port, so omitting both behind a port map stores the wrong port.

## Discovering FHIR servers

Finds FHIR endpoints on the instance over the DB API. Needs `pip install intersystems-irispython` and the superserver port:

```python
client = FHIRSQLClient(hostname="localhost", port=32783, superserver_port=32782)
servers = client.repositories.find_fhir_servers()   # optional namespace=, include_disabled=
repos = client.repositories.add_fhir_servers(servers, credentials_name=cred.system_name)
```

`FHIRServer` has `namespace`, `csp_url`, `web_port` (internal, correct for FSB), `fhir_version`. `add_fhir_servers` registers each via `create_from_fhir_server`, skipping ones already registered.

## Gotchas

- `create()` POSTs return the full entity list; methods pick the new one by name. Use unique names.
- `analysis.create`: `selectivity_percentage` OR `max_distinct`, not both.
- Every manager has `list()` / `get(id)` / `delete(id)`.
