# User Guide

`fhirsql` is a Python client for the InterSystems FHIR SQL Builder (FSB) REST API (`HS.HC.FHIRSQL`, served at
`/csp/fhirsql/api/ui`). It lets you drive the whole FSB workflow from code and end up with plain SQL tables
projected from the resources in a FHIR repository.

Background reading: [FHIR SQL Builder step by step](https://community.intersystems.com/post/fhir-sql-builder-step-step).

Related documents:

- [Transform specs and subtables](transform-specs.md) - designing the FHIR to SQL mapping
- [Cookbook](cookbook.md) - complete, copy-and-run examples
- [API reference](api-reference.md) - every class, method and parameter

## Contents

1. [Installation](#installation)
2. [Concepts](#concepts)
3. [Connecting](#connecting)
4. [The workflow](#the-workflow)
5. [Querying the result](#querying-the-result)
6. [Error handling](#error-handling)
7. [Working with Docker](#working-with-docker)
8. [Known server quirks](#known-server-quirks)

## Installation

```bash
pip install -r requirements.txt   # requests + intersystems-irispython
```

`intersystems-irispython` is only used for FHIR server discovery (`find_fhir_servers`), but it is imported
unconditionally, so it must be installed.

## Concepts

FSB turns FHIR JSON into SQL in five stages. Each stage is one manager on the client:

| Stage | Client manager | What it is |
|-------|----------------|------------|
| 1. Credentials | `client.credentials` | A named username/password FSB uses to call the FHIR server |
| 2. Repository | `client.repositories` | A FHIR server endpoint (host, port, URL, credentials) |
| 3. Analysis | `client.analysis` | A scan of a repository that discovers the resources and fields present |
| 4. Transform spec | `client.transform_specs` | Your mapping of FHIR paths to SQL columns |
| 5. Projection | `client.projections` | The generated SQL package (schema) and tables |

Each stage feeds the next: a repository references a credential, an analysis references a repository, a spec
references an analysis, and a projection references a repository plus a spec.

Two ideas matter most when designing a spec:

- A **resource table** has one row per FHIR resource (for example one row per `Patient`).
- A **subtable** has one row per repetition of a repeating element inside a resource (for example one row per
  `Patient.address`). See [Transform specs and subtables](transform-specs.md).

## Connecting

```python
from fhirsql import FHIRSQLClient

# Credentials from the IRISUSERNAME and IRISPASSWORD environment variables
client = FHIRSQLClient(hostname="localhost", port=52773)

# Or explicit
client = FHIRSQLClient(hostname="localhost", port=52773, username="SuperUser", password="SYS")
```

- `port` is the web server port of the IRIS instance running FSB.
- If neither explicit credentials nor both environment variables are present, the constructor raises
  `ValueError`.
- `superserver_port` (default `None`) is only needed for [FHIR server discovery](#discovering-fhir-servers).
- `verify_ssl` is passed to `requests`. Note the base URL is always built with `http://`.

## The workflow

The snippets below run in order and assume `client` from above. The [cookbook](cookbook.md) has the same
flow as a single script.

### 1. Credentials

```python
cred = client.credentials.create(system_name="SQLBuilderCreds")
```

With no `username`/`password`, the client's own login is stored. Pass them to store a different account, for
example a read-only FHIR user:

```python
cred = client.credentials.create(system_name="FhirReader", username="fhir_readonly", password="secret")
```

### 2. Repository

```python
repo = client.repositories.create(
    name="SQLBuilderConfig",
    host="localhost",
    fhir_url="/fhir/r4",
    credentials_name=cred.system_name,   # the system_name, NOT cred.id
)
```

The repository port defaults to the client's port. For containers with port mapping, see
[Working with Docker](#working-with-docker).

#### Discovering FHIR servers

Instead of typing the URL, you can discover FHIR endpoints on the instance through the DB API. This needs
`superserver_port`:

```python
client = FHIRSQLClient(hostname="localhost", port=32783, superserver_port=32782)

servers = client.repositories.find_fhir_servers()               # every namespace
servers = client.repositories.find_fhir_servers("FHIRSERVER")   # one namespace

for s in servers:
    print(s.namespace, s.csp_url, s.fhir_version, s.web_port)

repos = client.repositories.add_fhir_servers(servers, credentials_name=cred.system_name)
```

`add_fhir_servers` registers each server using its internal web port and skips any already registered with
the same host, port and URL. To register a single one, use `create_from_fhir_server(server, ...)`.

### 3. Analysis

```python
analysis = client.analysis.create(
    repository_id=repo.id,
    max_distinct=1000,             # max distinct values collected per field
    selectivity_percentage=100,    # 0-100; 100 for a complete analysis
)

import time
while analysis.status != "completed":
    time.sleep(5)
    analysis = client.analysis.get(analysis.id)
    print("analysis:", analysis.status)
```

Observed statuses are `running` then `completed`. `client.analysis.get_results(analysis.id)` returns the raw
analysis output, which lists the resources and paths available to map.

### 4. Transform spec

```python
from fhirsql import TransformSpecBuilder

builder = TransformSpecBuilder("Patient Demographics", scan_id=analysis.id)
builder.add_field("Patient", "Patient.name.family", "String", name="LastName", length=50)
builder.add_field("Patient", "Patient.gender", "String", name="Gender", length=10, index=True)

spec = client.transform_specs.create_from_builder(builder)
```

This is the stage with the most design decisions. Read [Transform specs and subtables](transform-specs.md).

### 5. Projection

```python
projection = client.projections.create(
    repository_id=repo.id,
    spec_id=spec.id,
    package_name="patientdata",           # becomes the SQL schema name
    users=["_SYSTEM", "SuperUser"],       # IRIS users granted SELECT
    name="Patient Demographics Projection",
)
projection = client.projections.poll_until_complete(projection.id)
```

`poll_until_complete` returns when the status is `Active` (also accepts `completed`, `complete`, `success`),
raises `RuntimeError` on `failed`/`error`, and raises `TimeoutError` after `max_attempts * interval` seconds
(default 60 x 5s).

## Querying the result

Projected tables live in the package you named, in the namespace where FSB runs (`FHIRSERVER` in the bundled
container). Query them from the Management Portal (System Explorer, SQL), or from Python with the DB API:

```python
import iris

conn = iris.connect("localhost", 32782, "FHIRSERVER", "SuperUser", "SYS")   # superserver port
cur = conn.cursor()
cur.execute("SELECT TOP 5 LastName, Gender FROM patientdata.Patient")
for row in cur.fetchall():
    print(row)
conn.close()
```

Every projected table has these system columns:

| Column | Meaning |
|--------|---------|
| `ID` | IRIS row id |
| `Key` | The FHIR reference form, `Patient/<id>`. Identical to `subject.reference`, so join on it directly |
| `RowNum` | Row number |

Subtables have a different shape; see [Subtable columns](transform-specs.md#what-the-server-generates).

## Error handling

All exceptions derive from `FHIRSQLError`:

| Exception | Raised when |
|-----------|-------------|
| `ValidationError` | Bad input caught client side, before any request (missing name, bad path, duplicate column) |
| `APIError` | The server answered with status >= 400. Has `.status_code` |
| `AuthenticationError`, `ResourceNotFoundError` | Defined for callers; the resource managers currently surface these as `APIError` |

```python
from fhirsql import ValidationError, APIError

try:
    builder.add_subtable_field("Patient", "PatientAddress", "Patient.address.city", "String", name="City")
except ValidationError as e:
    print(e)   # path must be relative to the subtable path

try:
    client.transform_specs.create_from_builder(builder)
except APIError as e:
    print(e.status_code, e)
```

Errors are not swallowed or defaulted anywhere in the builder: a mistake fails at the point it is made.

## Working with Docker

If IRIS runs in a container with a port mapping, the port you connect to from the host differs from the port
FSB itself must use to reach the FHIR server, which is resolved from inside the container.

For the bundled `iris-fhir` container:

| | Host (external) | Container (internal) |
|---|---|---|
| Web | 32783 | 52773 |
| Superserver | 32782 | 1972 |

```python
client = FHIRSQLClient(hostname="localhost", port=32783, superserver_port=32782)

repo = client.repositories.create(
    name="Docker FHIR",
    host="localhost",
    fhir_url="/fhir/r4",
    internal_port=52773,               # the port as seen from inside the container
    credentials_name=cred.system_name,
)
```

Port precedence for a repository is `internal_port`, then `port`, then the client's port. Without
`internal_port`, FSB would try `localhost:32783` from inside the container and fail to connect.

## Known server quirks

- Create endpoints (`POST`) return the whole list of entities, not the created one. The `create()` methods
  pick out the new entity by name (specs: newest match by id).
- Repositories take the credential `system_name`, not its id.
- `GET`/`DELETE` by id use the `ID` query parameter.
- A transform spec with no `resources` fails on the server with a 500 (`<INVALID OREF>ValidateStructure`).
  The client raises `ValidationError` first.
- The server does not validate a column's `type` or `path`. A wrong path produces a table full of NULLs
  rather than an error, so always spot check the projected data.
