from typing import List, Optional
from fhirsql.resources.base import BaseResource
from fhirsql.models import Repository
from fhirsql.exceptions import ValidationError

class RepositoryResource(BaseResource):
    def list(self) -> List[Repository]:
        data = self._make_request("GET", "/fhirrepository/")
        return [Repository.from_dict(item) for item in (data if isinstance(data, list) else [])]

    def get(self, repository_id: str) -> Repository:
        data = self._make_request("GET", "/fhirrepository", params={"ID": repository_id})
        return Repository.from_dict(data)

    def create(self, name: str, host: str, port: int, fhir_url: str,
               credentials_name: Optional[str] = None, ssl_config: Optional[str] = None) -> Repository:
        """
        Create a FHIR repository configuration.

        Args:
            name: Display name for this repository
            host: Hostname (e.g., "localhost")
            port: Port number (e.g., 52773)
            fhir_url: FHIR endpoint path (e.g., "/fhir/r4")
            credentials_name: Credential system_name (not id!) to use for authentication
            ssl_config: Optional SSL configuration name

        Example:
            cred = client.credentials.create(system_name="MyCredentials")
            repo = client.repositories.create(
                name="My FHIR Server",
                host="localhost",
                port=52773,
                fhir_url="/fhir/r4",
                credentials_name=cred.system_name  # or just "MyCredentials"
            )
        """
        if not all([name, host, fhir_url]):
            raise ValidationError("name, host, and fhir_url required")

        if not isinstance(port, int) or port <= 0 or port > 65535:
            raise ValidationError("port must be an integer between 1 and 65535")

        repo = Repository(
            name=name,
            hostname=host,
            port=str(port),
            repository_url=fhir_url,
            credentials_id=credentials_name,  # API expects system_name, not id
            ssl_config=ssl_config
        )
        data = self._make_request("POST", "/fhirrepository", json=repo.to_dict())

        # API returns a list of all repositories, find the one we just created by name
        if isinstance(data, list):
            for item in data:
                if item.get("name") == name:
                    return Repository.from_dict(item)
            # If not found, return the last one (likely the newly created one)
            if data:
                return Repository.from_dict(data[-1])

        return Repository.from_dict(data)

    def update(self, repository: Repository) -> Repository:
        if not repository.id:
            raise ValidationError("Repository ID required for update")
        data = self._make_request("PUT", "/fhirrepository", json=repository.to_dict())
        return Repository.from_dict(data)

    def delete(self, repository_id: str) -> bool:
        self._make_request("DELETE", "/fhirrepository", params={"ID": repository_id})
        return True
