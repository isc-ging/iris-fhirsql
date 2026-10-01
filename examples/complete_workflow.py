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
print(f"   Created credential: {cred.system_name}\n")

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
print(f"   Created repository: {repo.id}\n")

# Step 3: Launch Analysis
print("3. Launching analysis task...")
analysis = client.analysis.create(
    repository_id=repo.id,
    selectivity_percentage=100  # 100% for complete analysis
)
print(f"   Analysis started: {analysis.id}")
print(f"   Status: {analysis.status}")

# Poll for analysis completion
print("   Waiting for analysis to complete...")
while True:
    analysis = client.analysis.get(analysis.id)
    print(f"   Status: {analysis.status}")
    if analysis.status in ["complete", "completed", "finished"]:
        break
    elif analysis.status == "error":
        print("   Analysis failed!")
        exit(1)
    time.sleep(5)

print("   Analysis complete!\n")

# Step 4: Define field mappings and create the Transformation Specification
# Paths are full FHIRPath expressions; types match the analysis ("String", "Number", "Boolean")
print("4. Creating transformation specification...")
builder = TransformSpecBuilder("SQLBuilderTransformation", scan_id=analysis.id)

builder.add_field("Patient", "Patient.name.family", "String", name="LastName", length=50)
builder.add_field("Patient", "Patient.name.given", "String", name="FirstName", length=50)
builder.add_field("Patient", "Patient.gender", "String", name="PatientGender", length=10, index=True)
builder.add_field("Patient", "Patient.birthDate", "String", name="PatientBirthDate", length=10)

# Addresses repeat, so project them as a subtable (one row per address).
# Subtable column paths are relative to the subtable path.
builder.add_subtable("Patient", "PatientAddress", path="Patient.address")
builder.add_subtable_field("Patient", "PatientAddress", "city", "String", name="City", length=50)
builder.add_subtable_field("Patient", "PatientAddress", "state", "String", name="State", length=50)
builder.add_subtable_field("Patient", "PatientAddress", "postalCode", "String", name="PostalCode", length=10)
builder.add_subtable_field("Patient", "PatientAddress", "country", "String", name="Country", length=10)

# Save the spec for reference / version control
builder.save("patient_demographics_spec.json")
print("   Saved spec to patient_demographics_spec.json")

spec = client.transform_specs.create_from_builder(builder)
print(f"   Created transform spec: {spec.id}\n")

# Step 5: Create Projection (Generate SQL Schema)
print("5. Launching projection...")
projection = client.projections.create(
    repository_id=repo.id,
    spec_id=spec.id,
    package_name="patientdata",
    users=["_SYSTEM", "SuperUser"],
    name="Patient Demographics Projection"
)
print(f"   Projection launched: {projection.id}")
print(f"   Status: {projection.status}")

# Poll for projection completion
print("   Waiting for projection to build...")
while True:
    projection = client.projections.get(projection.id)
    print(f"   Status: {projection.status}")
    if projection.status in ["Active", "built", "complete", "completed"]:
        break
    elif projection.status == "error":
        print("   Projection failed!")
        exit(1)
    time.sleep(5)

print("   Projection built!\n")

print("=" * 50)
print("Workflow complete!")
print("\nYou can now query your data using SQL:")
print("\nManagement Portal -> FHIRSERVER namespace -> System Explorer -> SQL")
print("Schema: patientdata")
print("\nExample query:")
print("""
SELECT
  p.FirstName,
  p.LastName,
  p.PatientGender,
  p.PatientBirthDate,
  a.City,
  a.State,
  a.PostalCode,
  a.Country
FROM patientdata.PatientAddress a
JOIN patientdata.Patient p ON a.Patient = p.ID
""")
