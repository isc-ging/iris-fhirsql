from fhirsql import FHIRSQLClient

# Username and password will be read from IRISUSERNAME and IRISPASSWORD env vars if not provided
client = FHIRSQLClient(
    hostname="localhost",
    port=52773,
    username="admin",  # Optional if IRISUSERNAME is set
    password="your_password"  # Optional if IRISPASSWORD is set
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
