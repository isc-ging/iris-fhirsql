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

# Build projection
projection = client.projections.create(spec_id=spec.id)
print(f"Created projection: {projection.id}")
