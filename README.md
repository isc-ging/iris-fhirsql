# FHIRSQL Python Client

Pythonic wrapper for HS.HC.FHIRSQL REST API.

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

```python
from fhirsql import FHIRSQLClient

client = FHIRSQLClient(
    base_url="http://localhost:52773/csp/fhirsql/api/ui",
    username="admin",
    password="password"
)

# Create repository
repo = client.repositories.create(
    name="FHIR Server",
    url="http://localhost/fhir/r4"
)

# Start analysis
analysis = client.analysis.create(
    fhir_host=repo.id,
    max_distinct=1000,
    selectivity_percentage=50
)
```

## Transform Specs

```python
from fhirsql import TransformSpecBuilder

builder = TransformSpecBuilder("My Spec")
builder.add_resource_type("Patient")
builder.add_field("Patient", "id", "string")
builder.save("spec.json")

spec = client.transform_specs.create_from_builder(builder)
```

## API

- `client.credentials` - Manage credentials
- `client.repositories` - Manage FHIR repositories
- `client.analysis` - Run analysis tasks
- `client.transform_specs` - Manage transform specifications
- `client.projections` - Build database projections
