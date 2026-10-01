# iris-fhirsql

Pythonic wrapper for HS.HC.FHIRSQL REST API - create SQL projections from complex FHIR data.

## Installation

Not on PyPI yet. Install from GitHub:

```bash
pip install git+https://github.com/isc-ging/iris-fhirsql.git

# with the optional extra needed for find_fhir_servers()
pip install "iris-fhirsql[discovery] @ git+https://github.com/isc-ging/iris-fhirsql.git"
```

Pin a branch, tag or commit by appending `@<ref>`, e.g. `git+https://github.com/isc-ging/iris-fhirsql.git@main`.

From a local clone (editable, for development):

```bash
git clone https://github.com/isc-ging/iris-fhirsql.git
cd iris-fhirsql
pip install -e ".[discovery]"
```

## Quick Start

```python
from iris_fhirsql import FHIRSQLClient

# Client automatically reads IRISUSERNAME and IRISPASSWORD env vars
client = FHIRSQLClient(hostname="localhost", port=52773)

# Or pass credentials explicitly
client = FHIRSQLClient(
    hostname="localhost",
    port=52773,
    username="admin",
    password="password"
)
```

## Complete Workflow

FHIR SQL Builder follows a specific workflow to create simplified SQL views from FHIR data:

### 1. Create Credentials
```python
cred = client.credentials.create(
    system_name="SQLBuilderCreds",
    username="SuperUser",
    password="SYS"
)
```

### 2. Configure FHIR Repository
```python
# Simple case - port defaults to client's port
repo = client.repositories.create(
    name="SQLBuilderConfig",
    host="localhost",
    fhir_url="/fhir/r4",
    credentials_name=cred.system_name
)

# Docker containers with port mapping (e.g., 32783 -> 52773)
# Client uses external port 32783, but repository needs internal port 52773
repo = client.repositories.create(
    name="SQLBuilderConfig",
    host="localhost",
    fhir_url="/fhir/r4",
    internal_port=52773,  # Port inside container
    credentials_name=cred.system_name
)
```

### 3. Launch Analysis
Analyzes FHIR repository structure to discover resources and relationships:

```python
analysis = client.analysis.create(
    repository_id=repo.id,
    selectivity_percentage=100  # 0-100, use 100 for complete analysis
)

# Wait for completion
while analysis.status != "completed":
    analysis = client.analysis.get(analysis.id)
```

### 4. Create Transformation Specification
Define how FHIR resources map to SQL columns. Each field needs a full FHIRPath
(starting with the resource type), a type as reported by the analysis
(`String`, `Number`, `Boolean`) and a SQL column name:

```python
from iris_fhirsql import TransformSpecBuilder

builder = TransformSpecBuilder("Patient Demographics", analysis_id=analysis.id)
builder.add_field("Patient", "Patient.name.family", "String", name="LastName", length=50)
builder.add_field("Patient", "Patient.name.given", "String", name="FirstName", length=50)
builder.add_field("Patient", "Patient.gender", "String", name="PatientGender", length=10, index=True)
builder.add_field("Patient", "Patient.birthDate", "String", name="PatientBirthDate", length=10)

builder.save("patient_spec.json")  # optional; reload with TransformSpecBuilder.load()

spec = client.transform_specs.create_from_builder(builder)
```

Repeating elements (e.g. `Patient.address`) are projected as subtables, one row per repetition.
Subtable column paths are relative to the subtable path:

```python
builder.add_subtable("Patient", "PatientAddress", path="Patient.address")
builder.add_subtable_field("Patient", "PatientAddress", "city", "String", name="City", length=50)
builder.add_subtable_field("Patient", "PatientAddress", "postalCode", "String", name="PostalCode", length=10)
```

The subtable gets a `Patient` column (parent `ID`), so `a.Patient->LastName` or
`JOIN patientdata.Patient p ON a.Patient = p.ID` work. Use type `%Numeric` (not `Number`) to keep decimals.

### 5. Launch Projection
Generates actual SQL schema/tables:

```python
projection = client.projections.create(
    repository_id=repo.id,
    spec_id=spec.id,
    package_name="patientdata",  # SQL schema name
    users=["_SYSTEM", "SuperUser"]  # Access control
)

# Wait for SQL schema generation
projection = client.projections.poll_until_complete(projection.id)
```

### 6. Query Your Data
Projected tables are ordinary SQL tables in the FSB namespace. Query them with the Python DB API
(`pip install intersystems-irispython`) over the superserver port:

```python
import iris

username, password = client.session.auth
conn = iris.connect("localhost", 32782, "FHIRSERVER", username, password)  # superserver port
cur = conn.cursor()

cur.execute("""
    SELECT FirstName, LastName, PatientGender, PatientBirthDate
    FROM patientdata.Patient
""")
for first, last, gender, birth_date in cur.fetchall():
    print(first, last, gender, birth_date)

# with the PatientAddress subtable
cur.execute("""
    SELECT p.LastName, a.City, a.PostalCode
    FROM patientdata.PatientAddress a
    JOIN patientdata.Patient p ON a.Patient = p.ID
""")
for last, city, postal_code in cur.fetchall():
    print(last, city, postal_code)

conn.close()
```

You can also run the same SQL in the Management Portal: FHIRSERVER → System Explorer → SQL.

## Documentation

- [User guide](docs/guide.md) - concepts, connecting, the workflow, Docker ports, server quirks
- [Transform specs and subtables](docs/transform-specs.md) - column types, subtables, joins, validation rules
- [Cookbook](docs/cookbook.md) - complete examples: flat, subtables, multi-resource joins, discovery, cleanup
- [API reference](docs/api-reference.md) - every class, method and parameter

## Examples

- [`examples/complete_workflow.py`](examples/complete_workflow.py) - full workflow with a subtable
- [`examples/subtable_workflow.py`](examples/subtable_workflow.py) - address and telecom subtables, queries, optional cleanup
- [`examples/transform_spec_example.py`](examples/transform_spec_example.py) - multi-resource spec with save/load
- [`examples/docker_container_example.py`](examples/docker_container_example.py) - container port mapping

## API Overview

- `client.credentials` - Manage authentication credentials
- `client.repositories` - Configure FHIR repository connections and discover FHIR servers
- `client.analysis` - Analyze FHIR repository structure
- `client.transform_specs` - Define FHIR to SQL field mappings
- `client.projections` - Generate SQL schemas from specifications
