"""
Transform Spec Builder Example

This example demonstrates using TransformSpecBuilder to:
- Build transform specs programmatically or from JSON files
- Create complex field mappings for multiple resource types
- Generate projections with advanced configurations

The example follows the complete workflow and shows realistic
healthcare data scenarios with Patient and Observation resources.
"""

from fhirsql import FHIRSQLClient, TransformSpecBuilder

# Initialize client (credentials from environment variables)
client = FHIRSQLClient(
    hostname="localhost",
    port=52773
    # username and password read from IRISUSERNAME and IRISPASSWORD env vars
)

# Step 1: Create credentials
print("Step 1: Creating credentials...")
cred = client.credentials.create(
    system_name="HealthcareDataWarehouse",
    username="fhir_readonly",
    password="secure_password"
)
print(f"Created credential: {cred.id}")

# Step 2: Create repository
print("\nStep 2: Creating repository...")
repo = client.repositories.create(
    name="Healthcare Data Warehouse",
    url="http://localhost:52773/fhir/r4",
    credentials_id=cred.id
)
print(f"Created repository: {repo.id}")

# Step 3: Run analysis
print("\nStep 3: Running analysis...")
analysis = client.analysis.create(
    repository_id=repo.id,
    max_distinct=5000,
    selectivity_percentage=75
)
print(f"Started analysis: {analysis.id}")

# Wait for analysis to complete
print("Waiting for analysis to complete...")
completed_analysis = client.analysis.poll_until_complete(analysis.id)
print(f"Analysis completed with status: {completed_analysis.status}")

# Step 4: Build transform spec using TransformSpecBuilder
print("\nStep 4: Building transform spec with TransformSpecBuilder...")
builder = TransformSpecBuilder("Clinical Data Warehouse")
builder.set_analysis_id(completed_analysis.id)

# Add Patient resource with comprehensive demographics
builder.add_resource_type("Patient")
patient_fields = [
    ("id", "string"),
    ("identifier.value", "string"),
    ("identifier.system", "string"),
    ("name.family", "string"),
    ("name.given", "string"),
    ("name.prefix", "string"),
    ("birthDate", "date"),
    ("gender", "string"),
    ("address.line", "string"),
    ("address.city", "string"),
    ("address.state", "string"),
    ("address.postalCode", "string"),
    ("telecom.value", "string"),
    ("telecom.system", "string"),
]
for field_path, field_type in patient_fields:
    builder.add_field("Patient", field_path, field_type)

# Add Observation resource for clinical measurements
builder.add_resource_type("Observation")
observation_fields = [
    ("id", "string"),
    ("status", "string"),
    ("code.coding.code", "string"),
    ("code.coding.display", "string"),
    ("code.coding.system", "string"),
    ("subject.reference", "string"),
    ("effectiveDateTime", "datetime"),
    ("valueQuantity.value", "decimal"),
    ("valueQuantity.unit", "string"),
    ("valueQuantity.system", "string"),
    ("category.coding.code", "string"),
    ("category.coding.display", "string"),
]
for field_path, field_type in observation_fields:
    builder.add_field("Observation", field_path, field_type)

# Save spec to file for version control or reuse
spec_file = "clinical_warehouse_spec.json"
builder.save(spec_file)
print(f"Saved transform spec to {spec_file}")

# Load from file (demonstrates file-based workflow)
loaded_builder = TransformSpecBuilder.load(spec_file)
print(f"Loaded transform spec from file: {loaded_builder.name}")

# Step 5: Create transform spec on server
print("\nStep 5: Creating transform spec on server...")
spec = client.transform_specs.create_from_builder(loaded_builder)
print(f"Created transform spec: {spec.id}")

# Step 6: Create projection with the transform spec
print("\nStep 6: Creating projection...")
projection = client.projections.create(
    repository_id=repo.id,
    spec_id=spec.id,
    package_name="ClinicalWarehouse",  # SQL schema name
    users=["_SYSTEM", "SuperUser", "DataAnalyst"],  # IRIS users with access
    name="Clinical Data Warehouse Projection"
)
print(f"Created projection: {projection.id}")

# Poll until projection completes (SQL schema generation is async)
print("Waiting for projection to complete...")
completed_projection = client.projections.poll_until_complete(projection.id)
print(f"Projection completed with status: {completed_projection.status}")

print("\n" + "="*60)
print("SUCCESS! SQL projection is ready.")
print("="*60)
print(f"\nYou can now query:")
print(f"  - ClinicalWarehouse.Patient")
print(f"  - ClinicalWarehouse.Observation")
print(f"\nExample SQL:")
print("""
  SELECT
    p.name_family,
    p.birthDate,
    o.code_coding_display,
    o.valueQuantity_value,
    o.effectiveDateTime
  FROM ClinicalWarehouse.Patient p
  JOIN ClinicalWarehouse.Observation o
    ON o.subject_reference = CONCAT('Patient/', p.id)
  WHERE o.code_coding_code = '85354-9'  -- Blood pressure
""")
