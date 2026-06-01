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

    def create(self, fhir_host: str, max_distinct: Optional[int] = None,
               selectivity_percentage: Optional[int] = None) -> Analysis:
        if not fhir_host:
            raise ValidationError("fhir_host required")

        analysis = Analysis(fhir_host=fhir_host, max_distinct=max_distinct,
                          selectivity_percentage=selectivity_percentage)
        data = self._make_request("POST", "/analysis", json=analysis.to_dict())
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
