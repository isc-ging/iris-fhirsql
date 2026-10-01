from unittest.mock import MagicMock

import pytest

from iris_fhirsql.exceptions import ValidationError
from iris_fhirsql.resources.analysis import AnalysisResource


def _resource():
    res = AnalysisResource(MagicMock())
    res._make_request = MagicMock(return_value={"id": "1", "status": "running"})
    return res


def test_defaults_to_selectivity_100():
    res = _resource()
    res.create(repository_id=1)
    assert res._make_request.call_args.kwargs["json"] == {
        "fhirRepositoryId": 1, "selectivityPercentage": 100}


def test_max_distinct_only():
    res = _resource()
    res.create(repository_id=1, max_distinct=500)
    assert res._make_request.call_args.kwargs["json"] == {
        "fhirRepositoryId": 1, "maxDistinct": 500}


def test_both_rejected():
    with pytest.raises(ValidationError):
        _resource().create(repository_id=1, max_distinct=500, selectivity_percentage=50)
