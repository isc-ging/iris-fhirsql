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
               credentials_id: Optional[str] = None, ssl_config: Optional[str] = None) -> Repository:
        if not all([name, host, fhir_url]):
            raise ValidationError("name, host, and fhir_url required")

        if not isinstance(port, int) or port <= 0 or port > 65535:
            raise ValidationError("port must be an integer between 1 and 65535")

        repo = Repository(
            name=name,
            hostname=host,
            port=str(port),
            repository_url=fhir_url,
            credentials_id=credentials_id,
            ssl_config=ssl_config
        )
        data = self._make_request("POST", "/fhirrepository", json=repo.to_dict())
        return Repository.from_dict(data)

    def update(self, repository: Repository) -> Repository:
        if not repository.id:
            raise ValidationError("Repository ID required for update")
        data = self._make_request("PUT", "/fhirrepository", json=repository.to_dict())
        return Repository.from_dict(data)

    def delete(self, repository_id: str) -> bool:
        self._make_request("DELETE", "/fhirrepository", params={"ID": repository_id})
        return True
