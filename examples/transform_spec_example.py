"""
Transform Spec Builder Example

This example demonstrates using TransformSpecBuilder to:
- Build transform specs programmatically or from JSON files
- Create complex field mappings for multiple resource types
- Generate projections with advanced configurations

The example follows the complete workflow and shows realistic
healthcare data scenarios with Patient and Observation resources.
"""

import time
from iris_fhirsql import FHIRSQLClient, TransformSpecBuilder

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
print(f"Created credential: {cred.system_name}")

# Step 2: Create repository
print("\nStep 2: Creating repository...")
repo = client.repositories.create(
    name="Healthcare Data Warehouse",
    host="localhost",
    fhir_url="/fhir/r4",
    credentials_name=cred.system_name
)
print(f"Created repository: {repo.id}")

# Step 3: Run analysis
print("\nStep 3: Running analysis...")
analysis = client.analysis.create(
    repository_id=repo.id,
    selectivity_percentage=75
)
print(f"Started analysis: {analysis.id}")

# Wait for analysis to complete
print("Waiting for analysis to complete...")
while analysis.status != "completed":
    time.sleep(5)
    analysis = client.analysis.get(analysis.id)
    print(f"  Status: {analysis.status}")

# Step 4: Build transform spec using TransformSpecBuilder
print("\nStep 4: Building transform spec with TransformSpecBuilder...")
builder = TransformSpecBuilder("Clinical Data Warehouse", analysis_id=analysis.id)

# Add Patient resource with demographics: (path, type, column name, length)
patient_fields = [
    ("Patient.identifier.value", "String", "IdentifierValue", 50),
    ("Patient.identifier.system", "String", "IdentifierSystem", 100),
    ("Patient.name.family", "String", "FamilyName", 50),
    ("Patient.name.given", "String", "GivenName", 50),
    ("Patient.name.prefix", "String", "NamePrefix", 10),
    ("Patient.birthDate", "String", "BirthDate", 10),
    ("Patient.gender", "String", "Gender", 10),
    ("Patient.address.line", "String", "AddressLine", 100),
    ("Patient.address.city", "String", "City", 50),
    ("Patient.address.state", "String", "State", 50),
    ("Patient.address.postalCode", "String", "PostalCode", 10),
    ("Patient.telecom.value", "String", "TelecomValue", 50),
    ("Patient.telecom.system", "String", "TelecomSystem", 10),
]
for path, field_type, name, length in patient_fields:
    builder.add_field("Patient", path, field_type, name=name, length=length)

# Add Observation resource for clinical measurements
observation_fields = [
    ("Observation.status", "String", "Status", 10),
    ("Observation.code.coding.code", "String", "Code", 10),
    ("Observation.code.coding.display", "String", "Description", 250),
    ("Observation.code.coding.system", "String", "CodeSystem", 100),
    ("Observation.effectiveDateTime", "String", "EffectiveDateTime", 50),
    ("Observation.valueQuantity.unit", "String", "ValueUOM", 50),
    ("Observation.valueQuantity.system", "String", "ValueSystem", 100),
    ("Observation.category.coding.code", "String", "CategoryCode", 50),
    ("Observation.category.coding.display", "String", "CategoryDisplay", 100),
]
for path, field_type, name, length in observation_fields:
    builder.add_field("Observation", path, field_type, name=name, length=length)

# Number columns take no length; index columns used for joins/filters
builder.add_field("Observation", "Observation.valueQuantity.value", "Number", name="ValueQuantity")
builder.add_field("Observation", "Observation.subject.reference", "String",
                  name="Patient", length=50, index=True)

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
    users=["_SYSTEM", "SuperUser"],  # IRIS users with access
    name="Clinical Data Warehouse Projection"
)
print(f"Created projection: {projection.id} (status: {projection.status})")

print("\n" + "="*60)
print("SUCCESS! SQL projection is ready.")
print("="*60)
print(f"\nYou can now query:")
print(f"  - ClinicalWarehouse.Patient")
print(f"  - ClinicalWarehouse.Observation")
print(f"\nExample SQL:")
print("""
  SELECT
    p.FamilyName,
    p.BirthDate,
    o.Description,
    o.ValueQuantity,
    o.EffectiveDateTime
  FROM ClinicalWarehouse.Patient p
  JOIN ClinicalWarehouse.Observation o
    ON o.Patient = p.Key  -- Key is 'Patient/<id>', same form as subject.reference
  WHERE o.Code = '85354-9'  -- Blood pressure
""")
