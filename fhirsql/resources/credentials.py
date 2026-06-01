from typing import List
from fhirsql.resources.base import BaseResource
from fhirsql.models import Credential
from fhirsql.exceptions import ValidationError

class CredentialResource(BaseResource):
    def list(self) -> List[Credential]:
        data = self._make_request("GET", "/credentials/")
        return [Credential.from_dict(item) for item in (data if isinstance(data, list) else [])]

    def get(self, credential_id: str) -> Credential:
        data = self._make_request("GET", "/credentials", params={"ID": credential_id})
        return Credential.from_dict(data)

    def create(self, system_name: str, username: str, password: str) -> Credential:
        if not all([system_name, username, password]):
            raise ValidationError("system_name, username, and password required")

        cred = Credential(system_name=system_name, username=username, password=password)
        data = self._make_request("POST", "/credentials", json=cred.to_dict())
        return Credential.from_dict(data)

    def update(self, credential: Credential) -> Credential:
        if not credential.id:
            raise ValidationError("Credential ID required for update")
        data = self._make_request("PUT", "/credentials", json=credential.to_dict())
        return Credential.from_dict(data)

    def delete(self, credential_id: str) -> bool:
        self._make_request("DELETE", "/credentials", params={"ID": credential_id})
        return True
