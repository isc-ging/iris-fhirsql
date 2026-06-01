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

    def create(self, name: str, host: str, fhir_url: str,
               port: Optional[int] = None,
               internal_port: Optional[int] = None,
               credentials_name: Optional[str] = None,
               ssl_config: Optional[str] = None) -> Repository:
        """
        Create a FHIR repository configuration.

        For Docker containers with port mapping, use internal_port for the container's
        internal port while the client uses the mapped external port.

        Args:
            name: Display name for this repository
            host: Hostname (e.g., "localhost")
            fhir_url: FHIR endpoint path (e.g., "/fhir/r4")
            port: Port to use (defaults to client's port if not specified)
            internal_port: For containers - the port FHIR server runs on internally.
                          If specified, this is used instead of port.
            credentials_name: Credential system_name (not id!) to use for authentication
            ssl_config: Optional SSL configuration name

        Examples:
            # Simple case (no containers) - uses client's port automatically
            repo = client.repositories.create(
                name="My FHIR Server",
                host="localhost",
                fhir_url="/fhir/r4",
                credentials_name="MyCredentials"
            )

            # Docker container with port mapping (external 32783 -> internal 52773)
            # Client connects to 32783, but repo config needs internal port 52773
            repo = client.repositories.create(
                name="Containerized FHIR",
                host="localhost",
                fhir_url="/fhir/r4",
                internal_port=52773,  # Port inside container
                credentials_name="MyCredentials"
            )
        """
        if not all([name, host, fhir_url]):
            raise ValidationError("name, host, and fhir_url required")

        # Determine which port to use
        # Priority: internal_port > port > client's port
        if internal_port is not None:
            final_port = internal_port
        elif port is not None:
            final_port = port
        else:
            # Extract port from client's base_url
            # base_url format: http://hostname:port/csp/fhirsql/api/ui
            import re
            match = re.search(r':(\d+)/', self.client.base_url)
            if match:
                final_port = int(match.group(1))
            else:
                raise ValidationError("Could not determine port - please specify port or internal_port")

        if not isinstance(final_port, int) or final_port <= 0 or final_port > 65535:
            raise ValidationError("port must be an integer between 1 and 65535")

        repo = Repository(
            name=name,
            hostname=host,
            port=str(final_port),
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
