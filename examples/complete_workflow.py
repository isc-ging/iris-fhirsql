"""
Complete FHIR SQL Builder workflow example.

This demonstrates the full workflow from the InterSystems article:
https://community.intersystems.com/post/fhir-sql-builder-step-step
"""
from fhirsql import FHIRSQLClient, TransformSpecBuilder
import time

# Initialize client - credentials from env vars IRISUSERNAME and IRISPASSWORD
client = FHIRSQLClient(
    hostname="localhost",
    port=52773
)

print("=== FHIR SQL Builder Workflow ===\n")

# Step 1: Create Credentials
# By default, uses the client's own login credentials
print("1. Creating credentials...")
cred = client.credentials.create(
    system_name="SQLBuilderCreds"
    # username and password default to client's credentials
    # Override with: username="OtherUser", password="OtherPass"
)
print(f"   ✓ Created credential: {cred.id}\n")

# Step 2: Configure FHIR Repository
print("2. Configuring FHIR repository...")
repo = client.repositories.create(
    name="SQLBuilderConfig",
    host="localhost",
    fhir_url="/fhir/r4",
    credentials_name=cred.system_name,  # Use system_name, not id
    # port automatically uses client's port
    # For Docker containers with port mapping, use: internal_port=52773
)
print(f"   ✓ Created repository: {repo.id}\n")

# Step 3: Launch Analysis
print("3. Launching analysis task...")
analysis = client.analysis.create(
    repository_id=repo.id,
    max_distinct=1000,
    selectivity_percentage=100  # 100% for complete analysis
)
print(f"   ✓ Analysis started: {analysis.id}")
print(f"   ⏳ Status: {analysis.status}")

# Poll for analysis completion
print("   Waiting for analysis to complete...")
while True:
    analysis = client.analysis.get(analysis.id)
    print(f"   Status: {analysis.status}")
    if analysis.status in ["complete", "completed", "finished"]:
        break
    elif analysis.status == "error":
        print("   ✗ Analysis failed!")
        exit(1)
    time.sleep(5)

print("   ✓ Analysis complete!\n")

# Step 4: Create Transformation Specification
print("4. Creating transformation specification...")
spec = client.transform_specs.create(
    name="SQLBuilderTransformation",
    scan_id=analysis.id
)
print(f"   ✓ Created transform spec: {spec.id}\n")

# Step 5: Define Field Mappings using TransformSpecBuilder
print("5. Defining field mappings...")
builder = TransformSpecBuilder("Patient Demographics", spec_data={"scanId": analysis.id})

# Map Patient name fields
builder.add_resource_type("Patient")
builder.add_field("Patient", "name.family", "string", column_name="LastName")
builder.add_field("Patient", "name.given", "string", column_name="FirstName")
builder.add_field("Patient", "gender", "string", column_name="PatientGender")
builder.add_field("Patient", "birthDate", "date", column_name="PatientBirthDate")
builder.add_field("Patient", "telecom", "string", column_name="PatientPhone")

# Create subtable for addresses (one-to-many relationship)
builder.add_resource_type("PatientAddress")
builder.add_field("PatientAddress", "address.latitude.valueDecimal", "decimal", column_name="AddressLat")
builder.add_field("PatientAddress", "address.longitude.valueDecimal", "decimal", column_name="AddressLong")
builder.add_field("PatientAddress", "address.line", "string", column_name="Street")
builder.add_field("PatientAddress", "address.city", "string", column_name="City")
builder.add_field("PatientAddress", "address.state", "string", column_name="State")
builder.add_field("PatientAddress", "address.postalCode", "string", column_name="PostalCode")
builder.add_field("PatientAddress", "address.country", "string", column_name="Country")

print("   ✓ Field mappings defined")
print(f"   - Patient fields: {len(builder.spec['resourceTypes']['Patient']['fields'])}")
print(f"   - PatientAddress subtable fields: {len(builder.spec['resourceTypes']['PatientAddress']['fields'])}\n")

# Save the spec for reference
builder.save("patient_demographics_spec.json")
print("   ✓ Saved spec to patient_demographics_spec.json\n")

# Step 6: Create Projection (Generate SQL Schema)
print("6. Launching projection...")
projection = client.projections.create(
    repository_id=repo.id,
    spec_id=spec.id,
    package_name="patientdata",
    users=["_SYSTEM", "SuperUser"],
    name="Patient Demographics Projection"
)
print(f"   ✓ Projection launched: {projection.id}")
print(f"   ⏳ Status: {projection.status}")

# Poll for projection completion
print("   Waiting for projection to build...")
while True:
    projection = client.projections.get(projection.id)
    print(f"   Status: {projection.status}")
    if projection.status in ["built", "complete", "completed"]:
        break
    elif projection.status == "error":
        print("   ✗ Projection failed!")
        exit(1)
    time.sleep(5)

print("   ✓ Projection built!\n")

print("=" * 50)
print("✓ Workflow complete!")
print("\nYou can now query your data using SQL:")
print("\nManagement Portal → FHIRSERVER namespace → System Explorer → SQL")
print("Schema: patientdata")
print("\nExample query:")
print("""
SELECT
  Patient->PatientNames->FirstName,
  Patient->PatientNames->LastName,
  Patient->PatientGender,
  Patient->PatientBirthDate,
  Patient->PatientPhone,
  AddressLong,
  AddressLat,
  City,
  Country,
  PostalCode,
  State,
  Street
FROM patientdata.PatientAddresss
""")
