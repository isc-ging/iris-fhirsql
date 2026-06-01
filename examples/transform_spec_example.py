from fhirsql import FHIRSQLClient, TransformSpecBuilder

client = FHIRSQLClient(
    hostname="localhost",
    port=52773
    # username and password read from IRISUSERNAME and IRISPASSWORD env vars
)

# Build spec programmatically
builder = TransformSpecBuilder("Patient Demographics")
builder.set_analysis_id("analysis123")
builder.add_resource_type("Patient")
builder.add_field("Patient", "id", "string")
builder.add_field("Patient", "name.family", "string")
builder.add_field("Patient", "birthDate", "date")

# Save to file
builder.save("patient_spec.json")

# Load from file
loaded = TransformSpecBuilder.load("patient_spec.json")

# Create on server
spec = client.transform_specs.create_from_builder(builder)
print(f"Created spec: {spec.id}")

# Build projection with required parameters
# repository_id should be obtained from an existing repository (e.g., repo.id)
# For demonstration, assuming repository ID 1 exists
projection = client.projections.create(
    repository_id=1,  # Replace with actual repository.id from client.repositories.create()
    spec_id=spec.id,
    package_name="PatientData",  # SQL schema name
    users=["_SYSTEM", "SuperUser"],  # IRIS users with access
    name="Patient Demographics Projection"
)
print(f"Created projection: {projection.id}")

# Poll until projection completes (SQL schema generation is async)
print("Waiting for projection to complete...")
completed_projection = client.projections.poll_until_complete(projection.id)
print(f"Projection completed with status: {completed_projection.status}")
