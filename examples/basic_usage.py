from fhirsql import FHIRSQLClient

client = FHIRSQLClient(
    base_url="http://localhost:52773/csp/fhirsql/api/ui",
    username="admin",
    password="your_password"
)

# Create credential
cred = client.credentials.create(
    system_name="MyFHIRServer",
    username="fhiruser",
    password="secret"
)
print(f"Created credential: {cred.id}")

# Create repository
repo = client.repositories.create(
    name="Test FHIR Server",
    url="http://localhost:52773/fhir/r4",
    credentials_id=cred.id
)
print(f"Created repository: {repo.id}")

# Start analysis
analysis = client.analysis.create(
    fhir_host=repo.id,
    max_distinct=1000,
    selectivity_percentage=50
)
print(f"Started analysis: {analysis.id}")
