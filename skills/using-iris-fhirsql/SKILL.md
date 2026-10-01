---
name: using-iris-fhirsql
description: Use when writing Python that drives the InterSystems FHIR SQL Builder (FSB, HS.HC.FHIRSQL) via the iris_fhirsql package, or when projecting FHIR resources (Patient, Observation) into SQL tables, building transformation specs, subtables, or hitting FSB errors like 500 INVALID OREF ValidateStructure, 406 on GET by id, all-NULL subtable columns.
---

# Using iris_fhirsql

## Overview

`iris_fhirsql.FHIRSQLClient` wraps the FSB REST API (`/csp/fhirsql/api/ui`). Workflow is a fixed chain: credentials -> repository -> analysis -> transform spec -> projection (generated SQL schema). Each step needs output of the previous one.

## Workflow

```python
from iris_fhirsql import FHIRSQLClient, TransformSpecBuilder

# username/password fall back to IRISUSERNAME / IRISPASSWORD env vars; raises if neither
client = FHIRSQLClient(hostname="localhost", port=32783)

cred = client.credentials.create(system_name="SQLBuilderCreds")   # defaults to client login
repo = client.repositories.create(
    name="Repo", host="localhost", fhir_url="/fhir/r4",
    credentials_name=cred.system_name,     # system_name, NOT id
    internal_port=52773,                   # port as seen from INSIDE the IRIS container
)
analysis = client.analysis.create(repository_id=repo.id, selectivity_percentage=100)
# poll client.analysis.get(analysis.id).status: "running" -> "completed"

b = TransformSpecBuilder("MySpec", scan_id=analysis.id)
b.add_field("Patient", "Patient.name.family", "String", name="LastName", length=50)
b.add_field("Patient", "Patient.gender", "String", name="Gender", length=10, index=True)
b.add_subtable("Patient", "PatientAddress", path="Patient.address")
b.add_subtable_field("Patient", "PatientAddress", "city", "String", name="City", length=50)  # RELATIVE path
spec = client.transform_specs.create_from_builder(b)

proj = client.projections.create(repository_id=repo.id, spec_id=spec.id,
                                 package_name="patientdata", users=["_SYSTEM", "SuperUser"])
# status goes straight to "Active"; or client.projections.poll_until_complete(proj.id)
```

Query result: `SELECT p.LastName, a.City FROM patientdata.PatientAddress a JOIN patientdata.Patient p ON a.Patient = p.ID`

Full runnable versions: `examples/complete_workflow.py`, `examples/subtable_workflow.py`. Real request bodies: `payload-examples/*.body`.

## Quick Reference

| Need | Call |
|---|---|
| List/get/delete | `client.<credentials\|repositories\|analysis\|transform_specs\|projections>.list()/get(id)/delete(id)` |
| Save/load spec JSON | `builder.save(path)`, `TransformSpecBuilder.load(path)` |
| Find FHIR servers on instance | `client.repositories.find_fhir_servers()` (needs `pip install intersystems-irispython` and `FHIRSQLClient(superserver_port=...)`) |
| Register discovered servers | `add_fhir_servers(servers, credentials_name=...)` (skips duplicates) |

## Gotchas

- `create()` POST returns full entity list; the resource methods pick the new one by name. Names must be unique.
- Containers: client connects on mapped external port (32783), repository needs `internal_port` (52773). Omit both and client port is used, which is wrong behind a port map.
- Column `path` is full FHIRPath (`Patient.name.family`). Server does not validate `type` or `path`; bad path = silent NULLs.
- Subtable column paths MUST be relative (`city`). Full paths are accepted but give all-NULL columns.
- Spec with no resources fails: 500 `<INVALID OREF>ValidateStructure`.
- Table names unique across whole spec, case-insensitive.
- Types: `string`/`reference` -> %String, `number`/`integer` -> %Integer (ROUNDS decimals: 39.696 -> 40), `boolean` -> %Boolean. For decimals pass `%Numeric`. `length` optional (default 250).
- Subtable table `<package>.<name>` has `Patient` (parent ID, so `a.Patient->FamilyName` works), `ID`, `<name>Number`. Main tables have `ID`, `Key` (`Patient/<id>`, joins directly to `subject.reference`), `RowNum`.
- GET/DELETE by id use `ID` query param. Analysis update uses `TASKID` (unverified).

## Writing new code in this package

Existing code uses `.get()` and fallbacks when parsing responses. Do not copy. Fail loudly on missing expected fields (`d["key"]`).
