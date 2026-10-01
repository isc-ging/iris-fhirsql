from typing import List, Optional
from iris_fhirsql.resources.base import BaseResource
from iris_fhirsql.models import Projection
from iris_fhirsql.exceptions import ValidationError

class ProjectionResource(BaseResource):
    def list(self) -> List[Projection]:
        data = self._make_request("GET", "/projection/")
        return [Projection.from_dict(item) for item in (data if isinstance(data, list) else [])]

    def get(self, projection_id: str) -> Projection:
        data = self._make_request("GET", "/projection", params={"ID": projection_id})
        return Projection.from_dict(data)

    def create(self, repository_id: int, spec_id: str, package_name: str,
               users: Optional[List[str]] = None, name: Optional[str] = None) -> Projection:
        """
        Create and launch a projection to generate SQL schema from transform specification.

        Projections generate actual SQL tables/views in IRIS based on the transformation
        specification. The generated schema is placed in a package namespace with
        controlled user access.

        Workflow:
        1. Create Repository (client.repositories.create)
        2. Run Analysis (client.analysis.create) and wait for completion
        3. Create Transform Spec (client.transform_specs.create) with field mappings
        4. Launch Projection with repository, spec, package name, and users

        Args:
            repository_id: FHIR Repository ID to build projection from
            spec_id: Transformation Specification ID defining the mappings
            package_name: SQL package/schema name (e.g., "patientdata")
            users: List of IRIS users granted access (e.g., ["_SYSTEM", "SuperUser"])
            name: Optional display name for the projection

        Returns:
            Projection: Projection object with status tracking

        Raises:
            ValidationError: If required fields are missing

        Example:
            projection = client.projections.create(
                repository_id=repo.id,
                spec_id=spec.id,
                package_name="patientdata",
                users=["_SYSTEM", "SuperUser"]
            )
        """
        if not all([repository_id, spec_id, package_name]):
            raise ValidationError("repository_id, spec_id, and package_name required")

        projection = Projection(
            name=name,
            fhir_repository_id=repository_id,
            spec_id=spec_id,
            package_name=package_name,
            users=users or []
        )
        data = self._make_request("POST", "/projection", json=projection.to_dict())

        # API may return a list, handle both cases
        if isinstance(data, list):
            for item in data:
                if item.get("packageName") == package_name:
                    return Projection.from_dict(item)
            if data:
                return Projection.from_dict(data[-1])

        return Projection.from_dict(data)

    def update(self, projection_id: str, spec_id: Optional[str] = None,
               package_name: Optional[str] = None, users: Optional[List[str]] = None) -> Projection:
        if not projection_id:
            raise ValidationError("projection_id required")

        update_data = {"id": projection_id}
        if spec_id:
            update_data["specificationId"] = spec_id
        if package_name:
            update_data["packageName"] = package_name
        if users is not None:
            update_data["users"] = users

        data = self._make_request("PUT", "/projection", json=update_data)
        return Projection.from_dict(data)

    def delete(self, projection_id: str) -> bool:
        self._make_request("DELETE", "/projection", params={"ID": projection_id})
        return True

    def get_status(self, projection_id: str) -> str:
        """
        Get the current status of a projection.

        Since projections launch as async tasks, use this to check if the SQL schema
        generation has completed.

        Args:
            projection_id: ID of the projection to check

        Returns:
            str: Current status (e.g., "pending", "running", "completed", "failed")

        Example:
            status = client.projections.get_status(projection.id)
            print(f"Projection status: {status}")
        """
        projection = self.get(projection_id)
        return projection.status or "unknown"

    def poll_until_complete(self, projection_id: str, interval: int = 5, max_attempts: int = 60) -> Projection:
        """
        Poll projection status until completion or timeout.

        Args:
            projection_id: ID of the projection to monitor
            interval: Seconds between status checks (default: 5)
            max_attempts: Maximum number of polling attempts (default: 60, i.e., 5 minutes)

        Returns:
            Projection: Final projection state

        Raises:
            TimeoutError: If projection doesn't complete within max_attempts
            RuntimeError: If projection fails

        Example:
            projection = client.projections.create(...)
            completed = client.projections.poll_until_complete(projection.id)
            print(f"Projection completed with status: {completed.status}")
        """
        import time

        for attempt in range(max_attempts):
            projection = self.get(projection_id)
            status = (projection.status or "").lower()

            # "active" is what FSB reports once a projection is built
            if status in ["active", "completed", "complete", "success"]:
                return projection
            elif status in ["failed", "error"]:
                raise RuntimeError(f"Projection failed with status: {projection.status}")

            if attempt < max_attempts - 1:
                time.sleep(interval)

        raise TimeoutError(f"Projection did not complete within {max_attempts * interval} seconds")
