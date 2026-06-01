# FHIRSQL Python Client

Pythonic wrapper for HS.HC.FHIRSQL REST API - create SQL projections from complex FHIR data.

Based on: [FHIR SQL Builder Step-by-Step](https://community.intersystems.com/post/fhir-sql-builder-step-step)

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

```python
from fhirsql import FHIRSQLClient

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
repo = client.repositories.create(
    name="SQLBuilderConfig",
    host="localhost",
    port=52773,
    fhir_url="/fhir/r4",
    credentials_id=cred.id
)
```

### 3. Launch Analysis
Analyzes FHIR repository structure to discover resources and relationships:

```python
analysis = client.analysis.create(
    repository_id=repo.id,
    max_distinct=1000,
    selectivity_percentage=100  # 0-100, use 100 for complete analysis
)

# Wait for completion
while analysis.status != "complete":
    analysis = client.analysis.get(analysis.id)
```

### 4. Create Transformation Specification
Define how FHIR resources map to SQL columns:

```python
from fhirsql import TransformSpecBuilder

spec = client.transform_specs.create(
    name="Patient Demographics",
    scan_id=analysis.id
)

# Build field mappings
builder = TransformSpecBuilder("Patient Demographics")
builder.add_resource_type("Patient")
builder.add_field("Patient", "name.family", "string", column_name="LastName")
builder.add_field("Patient", "name.given", "string", column_name="FirstName")
builder.add_field("Patient", "gender", "string", column_name="PatientGender")
builder.add_field("Patient", "birthDate", "date", column_name="PatientBirthDate")

# Create subtable for one-to-many relationships
builder.add_resource_type("PatientAddress")
builder.add_field("PatientAddress", "address.city", "string", column_name="City")
builder.add_field("PatientAddress", "address.state", "string", column_name="State")

builder.save("patient_spec.json")
```

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
Access via Management Portal → FHIRSERVER → System Explorer → SQL:

```sql
SELECT
  Patient->PatientNames->FirstName,
  Patient->PatientNames->LastName,
  Patient->PatientGender,
  Patient->PatientBirthDate,
  City,
  State
FROM patientdata.PatientAddresss
```

## Complete Example

See [`examples/complete_workflow.py`](examples/complete_workflow.py) for a full working example.

## API Reference

- `client.credentials` - Manage authentication credentials
- `client.repositories` - Configure FHIR repository connections  
- `client.analysis` - Analyze FHIR repository structure
- `client.transform_specs` - Define FHIR→SQL field mappings
- `client.projections` - Generate SQL schemas from specifications
