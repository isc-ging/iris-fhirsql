"""
Basic FHIR SQL Builder Workflow Example

This example demonstrates the complete workflow:
1. Create credentials for FHIR server authentication
2. Create repository pointing to your FHIR server
3. Run analysis to discover FHIR resources and fields
4. Create transform spec defining desired SQL projection
5. Build field mappings for the transform spec
6. Create projection to generate SQL tables
"""

from fhirsql import FHIRSQLClient

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
    url="http://localhost:52773/fhir/r4",
    credentials_id=cred.id
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
completed_analysis = client.analysis.poll_until_complete(analysis.id)
print(f"Analysis completed with status: {completed_analysis.status}")

# Step 4: Create transform spec
print("\nStep 4: Creating transform spec...")
spec = client.transform_specs.create(
    name="Patient Demographics",
    analysis_id=completed_analysis.id
)
print(f"Created transform spec: {spec.id}")

# Step 5: Build field mappings
print("\nStep 5: Adding field mappings...")
# Add Patient resource type
client.transform_specs.add_resource_type(spec.id, "Patient")

# Add individual fields with appropriate types
fields_to_add = [
    ("id", "string"),
    ("name.family", "string"),
    ("name.given", "string"),
    ("birthDate", "date"),
    ("gender", "string"),
    ("address.city", "string"),
    ("address.state", "string"),
    ("address.postalCode", "string"),
]

for field_path, field_type in fields_to_add:
    client.transform_specs.add_field(spec.id, "Patient", field_path, field_type)
    print(f"  Added field: Patient.{field_path} ({field_type})")

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
