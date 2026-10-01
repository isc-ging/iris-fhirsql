"""
Basic FHIR SQL Builder Workflow Example

This example demonstrates the complete workflow:
1. Create credentials for FHIR server authentication
2. Create repository pointing to your FHIR server
3. Run analysis to discover FHIR resources and fields
4. Build field mappings with TransformSpecBuilder
5. Create the transform spec on the server
6. Create projection to generate SQL tables
"""

import time
from fhirsql import FHIRSQLClient, TransformSpecBuilder

# Username and password will be read from IRISUSERNAME and IRISPASSWORD env vars if not provided
client = FHIRSQLClient(
    hostname="localhost",
    port=52773,
    username="admin",  # Optional if IRISUSERNAME is set
    password="your_password"  # Optional if IRISPASSWORD is set
)

# Step 1: Create credentials for FHIR server
# By default uses client's own credentials, or override with different ones
print("Step 1: Creating credentials...")
cred = client.credentials.create(
    system_name="MyFHIRServer"
    # Defaults to client's username/password
    # Override with: username="fhiruser", password="secret"
)
print(f"Created credential: {cred.id}")

# Step 2: Create repository
print("\nStep 2: Creating repository...")
repo = client.repositories.create(
    name="Test FHIR Server",
    host="localhost",
    port=52773,
    fhir_url="/fhir/r4",
    credentials_name=cred.system_name  # Use system_name, not id
)
print(f"Created repository: {repo.id}")

# Step 3: Create and run analysis
print("\nStep 3: Running analysis...")
analysis = client.analysis.create(
    repository_id=repo.id,
    max_distinct=1000,
    selectivity_percentage=50
)
print(f"Started analysis: {analysis.id}")

# Poll until analysis completes
print("Waiting for analysis to complete...")
while analysis.status != "completed":
    time.sleep(5)
    analysis = client.analysis.get(analysis.id)
    print(f"  Status: {analysis.status}")

# Step 4: Build field mappings: (FHIRPath, type, column name, length)
print("\nStep 4: Building field mappings...")
builder = TransformSpecBuilder("Patient Demographics", scan_id=analysis.id)
fields_to_add = [
    ("Patient.name.family", "String", "FamilyName", 50),
    ("Patient.name.given", "String", "GivenName", 50),
    ("Patient.birthDate", "String", "BirthDate", 10),
    ("Patient.gender", "String", "Gender", 10),
    ("Patient.address.city", "String", "City", 50),
    ("Patient.address.state", "String", "State", 50),
    ("Patient.address.postalCode", "String", "PostalCode", 10),
]
for path, field_type, name, length in fields_to_add:
    builder.add_field("Patient", path, field_type, name=name, length=length)
    print(f"  Added field: {path} -> {name} ({field_type})")

# Step 5: Create transform spec on the server
print("\nStep 5: Creating transform spec...")
spec = client.transform_specs.create_from_builder(builder)
print(f"Created transform spec: {spec.id}")

# Step 6: Create projection
print("\nStep 6: Creating projection...")
projection = client.projections.create(
    repository_id=repo.id,
    spec_id=spec.id,
    package_name="PatientDemo",  # SQL schema name
    users=["_SYSTEM", "SuperUser"],  # IRIS users with access
    name="Patient Demographics Projection"
)
print(f"Created projection: {projection.id}")

# Poll until projection completes
print("Waiting for projection to complete...")
completed_projection = client.projections.poll_until_complete(projection.id)
print(f"Projection completed with status: {completed_projection.status}")

print("\nWorkflow complete! You can now query SQL tables in the PatientDemo schema.")
