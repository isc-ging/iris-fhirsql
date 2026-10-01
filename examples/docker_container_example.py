"""
Example for using FHIR SQL Builder with a containerized FHIR server.

This shows how to handle Docker port mapping where:
- External port (what you connect to): 32783
- Internal port (what FHIR runs on inside container): 52773
"""
from iris_fhirsql import FHIRSQLClient

# Client connects to the EXTERNAL mapped port (32783)
client = FHIRSQLClient(
    hostname="localhost",
    port=32783  # External Docker port mapping
)

print("=== Docker Container Example ===\n")

# Create credentials using client's credentials by default
print("1. Creating credentials...")
cred = client.credentials.create(
    system_name="DockerFHIRCreds"
)
print(f"   ✓ Credential created: {cred.system_name}\n")

# Create repository
# Use internal_port for the container's INTERNAL port (52773)
print("2. Creating repository...")
repo = client.repositories.create(
    name="Docker FHIR Repository",
    host="localhost",
    fhir_url="/fhir/r4",
    internal_port=52773,  # Port INSIDE the container
    credentials_name=cred.system_name
)
print(f"   ✓ Repository created: {repo.id}")
print(f"   Client connects to: localhost:32783")
print(f"   Repository configured for: localhost:{repo.port}\n")

print("✓ Configuration complete!")
print("\nKey concept:")
print("  - Client uses EXTERNAL port (32783) to connect to host")
print("  - Repository uses INTERNAL port (52773) for FHIR server config")
print("  - The internal_port parameter makes this explicit and intuitive")
