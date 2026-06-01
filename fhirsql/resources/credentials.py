from typing import List, Optional
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

    def create(self, system_name: str, username: Optional[str] = None, password: Optional[str] = None) -> Credential:
        """
        Create a new credential entry.

        By default, uses the client's own login credentials. Override by passing
        explicit username/password.

        Args:
            system_name: Name for this credential entry
            username: Username (defaults to client's login username if not provided)
            password: Password (defaults to client's login password if not provided)

        Returns:
            Credential: Created credential object

        Example:
            # Use client's own credentials
            cred = client.credentials.create(system_name="MyServer")

            # Override with different credentials
            cred = client.credentials.create(
                system_name="MyServer",
                username="different_user",
                password="different_pass"
            )
        """
        # Default to client's own credentials if not provided
        if username is None or password is None:
            if self.client.session.auth:
                client_username, client_password = self.client.session.auth
                username = username or client_username
                password = password or client_password

        if not all([system_name, username, password]):
            raise ValidationError("system_name required, and username/password must be provided or available from client auth")

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
