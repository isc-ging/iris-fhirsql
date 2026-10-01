from typing import List, Optional, Dict, Any
from fhirsql.resources.base import BaseResource
from fhirsql.models import Analysis
from fhirsql.exceptions import ValidationError

class AnalysisResource(BaseResource):
    def list(self) -> List[Analysis]:
        data = self._make_request("GET", "/analysis/")
        return [Analysis.from_dict(item) for item in (data if isinstance(data, list) else [])]

    def get(self, task_id: str) -> Analysis:
        data = self._make_request("GET", "/analysis", params={"ID": task_id})
        return Analysis.from_dict(data)

    def create(self, repository_id: int, max_distinct: Optional[int] = None,
               selectivity_percentage: Optional[int] = None) -> Analysis:
        """
        Create and launch a new FHIR repository analysis task.

        The analysis process scans a FHIR repository to discover resource types,
        fields, and data patterns. Results feed into Transformation Specifications.

        Workflow:
        1. Create/select a Repository using client.repositories.create() or list()
        2. Launch Analysis with the Repository ID
        3. Poll status using get() or update() until complete
        4. Use Analysis ID when creating Transform Specs

        Args:
            repository_id: ID of the FHIR Repository to analyze (from Repository.id).
                          Obtain this from client.repositories.create() or list().
            max_distinct: Maximum number of distinct values to collect per field.
                         Mutually exclusive with selectivity_percentage.
            selectivity_percentage: Selectivity threshold percentage (0-100).
                                   Mutually exclusive with max_distinct.
                                   Defaults to 100 when neither option is given.

        Returns:
            Analysis: Analysis object with task ID and initial status.
                     Use analysis.id to track status and retrieve results.

        Raises:
            ValidationError: If repository_id is missing, both max_distinct and
                           selectivity_percentage are given, or
                           selectivity_percentage is out of range (0-100).

        Example:
            repo = client.repositories.create(name="FHIR Server", url="http://...")
            analysis = client.analysis.create(
                repository_id=repo.id,
                selectivity_percentage=50
            )
            # Poll until complete
            while analysis.status != "completed":
                analysis = client.analysis.get(analysis.id)
            # Get results to inform transform spec design
            results = client.analysis.get_results(analysis.id)
        """
        if not repository_id:
            raise ValidationError("repository_id required")

        if max_distinct is not None and selectivity_percentage is not None:
            raise ValidationError("provide only one of max_distinct or selectivity_percentage")

        if max_distinct is None and selectivity_percentage is None:
            selectivity_percentage = 100

        if selectivity_percentage is not None:
            if not (0 <= selectivity_percentage <= 100):
                raise ValidationError("selectivity_percentage must be between 0 and 100")

        analysis = Analysis(fhir_repository_id=repository_id, max_distinct=max_distinct,
                          selectivity_percentage=selectivity_percentage)
        data = self._make_request("POST", "/analysis", json=analysis.to_dict())

        # API may return a list, handle both cases
        if isinstance(data, list):
            if data:
                return Analysis.from_dict(data[-1])  # Return the last (newly created) one

        return Analysis.from_dict(data)

    def update(self, task_id: str, action: str = "resume") -> Analysis:
        data = self._make_request("PUT", "/analysis", params={"TASKID": task_id},
                                 json={"action": action})
        return Analysis.from_dict(data)

    def delete(self, task_id: str) -> bool:
        self._make_request("DELETE", "/analysis", params={"ID": task_id})
        return True

    def get_results(self, task_id: str) -> Dict[str, Any]:
        return self._make_request("GET", "/analysisresult", params={"ID": task_id})
