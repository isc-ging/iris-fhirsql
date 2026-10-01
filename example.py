from fhirsql import FHIRSQLClient

client = FHIRSQLClient(
    host="localhost",
    port=32783
    )


cred = client.credentials