import os
import requests
from typing import Optional
from iris_fhirsql.resources.credentials import CredentialResource
from iris_fhirsql.resources.repositories import RepositoryResource
from iris_fhirsql.resources.analysis import AnalysisResource
from iris_fhirsql.resources.transformspecs import TransformSpecResource
from iris_fhirsql.resources.projections import ProjectionResource

class FHIRSQLClient:
    """Client for HS.HC.FHIRSQL REST API.

    Example:
        client = FHIRSQLClient(
            hostname="localhost",
            port=52773,
            username="admin",
            password="secret"
        )
        repos = client.repositories.list()
    """

    def __init__(self, hostname: str, port: int = 52773,
                 superserver_port: Optional[int] = None,
                 username: Optional[str] = None,
                 password: Optional[str] = None, verify_ssl: bool = True):
        # Construct base URL with constant path
        self.hostname = hostname
        # Superserver (DB API) port, only needed for FHIR server discovery
        self.superserver_port = superserver_port
        self.base_url = f"http://{hostname}:{port}/csp/fhirsql/api/ui"

        # Default to environment variables if not provided
        username = username or os.getenv('IRISUSERNAME')
        password = password or os.getenv('IRISPASSWORD')

        # Validate that credentials are available
        if not username or not password:
            raise ValueError(
                "Credentials required: either pass username/password parameters or set "
                "IRISUSERNAME and IRISPASSWORD environment variables"
            )

        self.session = requests.Session()

        if username and password:
            self.session.auth = (username, password)

        self.session.verify = verify_ssl
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

        self.credentials = CredentialResource(self)
        self.repositories = RepositoryResource(self)
        self.analysis = AnalysisResource(self)
        self.transform_specs = TransformSpecResource(self)
        self.projections = ProjectionResource(self)

    def info(self):
        """Get API version info."""
        response = self.session.get(f"{self.base_url}/")
        response.raise_for_status()
        return response.json()
