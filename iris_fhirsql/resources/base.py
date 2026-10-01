from typing import Optional, Dict, Any
from urllib.parse import urlencode
from iris_fhirsql.exceptions import APIError

class BaseResource:
    def __init__(self, client):
        self.client = client

    def _make_request(self, method, path, json=None, params=None):
        url = self._build_url(path, **(params or {}))

        response = self.client.session.request(method=method, url=url, json=json)

        if response.status_code >= 400:
            try:
                error_data = response.json()
            except ValueError:
                error_data = {"error": response.text}

            raise APIError(
                message=error_data.get("error", response.text),
                status_code=response.status_code
            )

        if response.status_code == 204:
            return {}

        try:
            return response.json()
        except ValueError:
            return {}

    def _build_url(self, path, **params):
        url = f"{self.client.base_url}{path}"
        if params:
            query = urlencode({k: v for k, v in params.items() if v is not None})
            if query:
                url = f"{url}?{query}"
        return url
