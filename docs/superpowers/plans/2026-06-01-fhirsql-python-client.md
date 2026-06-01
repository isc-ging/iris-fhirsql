# FHIRSQL Python Client Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Pythonic wrapper around the HS.HC.FHIRSQL REST API at `/csp/fhirsql/api/ui` for programmatic management of FHIRSQL Builder configuration.

**Architecture:** Object-oriented client with resource managers (credentials, repositories, analysis, transform specs, projections). TransformSpecBuilder for Pythonic spec creation with file import/export.

**Tech Stack:** Python 3.8+, requests, dataclasses

---

## File Structure

```
fhirsql/
├── __init__.py
├── client.py
├── models.py
├── exceptions.py
├── transformspec.py
└── resources/
    ├── __init__.py
    ├── base.py
    ├── credentials.py
    ├── repositories.py
    ├── analysis.py
    ├── transformspecs.py
    └── projections.py
```

---

## Task 1: Exceptions and Models

**Files:**
- Create: `fhirsql/exceptions.py`
- Create: `fhirsql/models.py`
- Create: `requirements.txt`

- [ ] **Step 1: Create requirements.txt**

```
requests>=2.28.0
```

- [ ] **Step 2: Create exceptions**

`fhirsql/exceptions.py`:
```python
class FHIRSQLError(Exception):
    """Base exception."""
    pass

class AuthenticationError(FHIRSQLError):
    pass

class ResourceNotFoundError(FHIRSQLError):
    def __init__(self, resource_type, resource_id):
        super().__init__(f"{resource_type} {resource_id} not found")

class ValidationError(FHIRSQLError):
    pass

class APIError(FHIRSQLError):
    def __init__(self, message, status_code=None):
        self.status_code = status_code
        super().__init__(f"API Error ({status_code}): {message}" if status_code else message)
```

- [ ] **Step 3: Create models**

`fhirsql/models.py`:
```python
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class Credential:
    id: Optional[str] = None
    system_name: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    
    def to_dict(self):
        return {k: v for k, v in {
            "id": self.id,
            "systemName": self.system_name,
            "username": self.username,
            "password": self.password
        }.items() if v is not None}
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data.get("id"),
            system_name=data.get("systemName"),
            username=data.get("username"),
            password=data.get("password")
        )

@dataclass
class Repository:
    id: Optional[str] = None
    name: Optional[str] = None
    url: Optional[str] = None
    credentials_id: Optional[str] = None
    ssl_config: Optional[str] = None
    
    def to_dict(self):
        return {k: v for k, v in {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "credentialsID": self.credentials_id,
            "sslConfig": self.ssl_config
        }.items() if v is not None}
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data.get("id"),
            name=data.get("name"),
            url=data.get("url"),
            credentials_id=data.get("credentialsID"),
            ssl_config=data.get("sslConfig")
        )

@dataclass
class Analysis:
    id: Optional[str] = None
    fhir_host: Optional[str] = None
    max_distinct: Optional[int] = None
    selectivity_percentage: Optional[int] = None
    status: Optional[str] = None
    
    def to_dict(self):
        return {k: v for k, v in {
            "id": self.id,
            "FHIRHost": self.fhir_host,
            "maxDistinct": self.max_distinct,
            "selectivityPercentage": self.selectivity_percentage,
            "status": self.status
        }.items() if v is not None}
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data.get("id") or data.get("TASKID"),
            fhir_host=data.get("FHIRHost"),
            max_distinct=data.get("maxDistinct"),
            selectivity_percentage=data.get("selectivityPercentage"),
            status=data.get("status")
        )

@dataclass
class TransformSpec:
    id: Optional[str] = None
    name: Optional[str] = None
    analysis_id: Optional[str] = None
    spec_data: Optional[Dict] = None
    
    def to_dict(self):
        data = {}
        if self.id:
            data["id"] = self.id
        if self.name:
            data["name"] = self.name
        if self.analysis_id:
            data["analysisID"] = self.analysis_id
        if self.spec_data:
            data.update(self.spec_data)
        return data
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data.get("id") or data.get("SPECID"),
            name=data.get("name"),
            analysis_id=data.get("analysisID"),
            spec_data=data
        )

@dataclass
class Projection:
    id: Optional[str] = None
    name: Optional[str] = None
    spec_id: Optional[str] = None
    status: Optional[str] = None
    
    def to_dict(self):
        return {k: v for k, v in {
            "id": self.id,
            "name": self.name,
            "specID": self.spec_id,
            "status": self.status
        }.items() if v is not None}
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data.get("id"),
            name=data.get("name"),
            spec_id=data.get("specID"),
            status=data.get("status")
        )
```

- [ ] **Step 4: Commit**

```bash
git add fhirsql/ requirements.txt
git commit -m "feat: add exceptions and data models"
```

---

## Task 2: Base Resource Manager

**Files:**
- Create: `fhirsql/resources/__init__.py`
- Create: `fhirsql/resources/base.py`

- [ ] **Step 1: Create base resource manager**

`fhirsql/resources/__init__.py`:
```python
# Empty
```

`fhirsql/resources/base.py`:
```python
from typing import Optional, Dict, Any
from urllib.parse import urlencode
from fhirsql.exceptions import APIError

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
```

- [ ] **Step 2: Commit**

```bash
git add fhirsql/resources/
git commit -m "feat: add base resource manager"
```

---

## Task 3: Resource Managers

**Files:**
- Create: `fhirsql/resources/credentials.py`
- Create: `fhirsql/resources/repositories.py`
- Create: `fhirsql/resources/analysis.py`
- Create: `fhirsql/resources/transformspecs.py`
- Create: `fhirsql/resources/projections.py`

- [ ] **Step 1: Create credentials resource**

`fhirsql/resources/credentials.py`:
```python
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
```

- [ ] **Step 2: Create repositories resource**

`fhirsql/resources/repositories.py`:
```python
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
    
    def create(self, name: str, url: str, credentials_id: Optional[str] = None,
               ssl_config: Optional[str] = None) -> Repository:
        if not all([name, url]):
            raise ValidationError("name and url required")
        
        repo = Repository(name=name, url=url, credentials_id=credentials_id, ssl_config=ssl_config)
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
```

- [ ] **Step 3: Create analysis resource**

`fhirsql/resources/analysis.py`:
```python
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
```

- [ ] **Step 4: Create transform specs resource**

`fhirsql/resources/transformspecs.py`:
```python
from typing import List, Dict, Any
from fhirsql.resources.base import BaseResource
from fhirsql.models import TransformSpec
from fhirsql.exceptions import ValidationError

class TransformSpecResource(BaseResource):
    def list(self) -> List[TransformSpec]:
        data = self._make_request("GET", "/transformspec/")
        return [TransformSpec.from_dict(item) for item in (data if isinstance(data, list) else [])]
    
    def get(self, spec_id: str) -> TransformSpec:
        data = self._make_request("GET", "/transformspec", params={"SPECID": spec_id})
        return TransformSpec.from_dict(data)
    
    def create(self, spec_data: Dict[str, Any]) -> TransformSpec:
        if not spec_data.get("name"):
            raise ValidationError("name required")
        data = self._make_request("POST", "/transformspec", json=spec_data)
        return TransformSpec.from_dict(data)
    
    def create_from_builder(self, builder) -> TransformSpec:
        return self.create(builder.to_dict())
    
    def update(self, spec: TransformSpec) -> TransformSpec:
        if not spec.id:
            raise ValidationError("Transform spec ID required for update")
        data = self._make_request("PUT", "/transformspec", json=spec.to_dict())
        return TransformSpec.from_dict(data)
    
    def delete(self, spec_id: str) -> bool:
        self._make_request("DELETE", "/transformspec", params={"ID": spec_id})
        return True
```

- [ ] **Step 5: Create projections resource**

`fhirsql/resources/projections.py`:
```python
from typing import List
from fhirsql.resources.base import BaseResource
from fhirsql.models import Projection
from fhirsql.exceptions import ValidationError

class ProjectionResource(BaseResource):
    def list(self) -> List[Projection]:
        data = self._make_request("GET", "/projection/")
        return [Projection.from_dict(item) for item in (data if isinstance(data, list) else [])]
    
    def get(self, projection_id: str) -> Projection:
        data = self._make_request("GET", "/projection", params={"ID": projection_id})
        return Projection.from_dict(data)
    
    def create(self, spec_id: str) -> Projection:
        if not spec_id:
            raise ValidationError("spec_id required")
        data = self._make_request("POST", "/projection", json={"specID": spec_id})
        return Projection.from_dict(data)
    
    def update(self, projection_id: str, spec_id: str) -> Projection:
        if not all([projection_id, spec_id]):
            raise ValidationError("projection_id and spec_id required")
        data = self._make_request("PUT", "/projection",
                                 json={"id": projection_id, "specID": spec_id})
        return Projection.from_dict(data)
    
    def delete(self, projection_id: str) -> bool:
        self._make_request("DELETE", "/projection", params={"ID": projection_id})
        return True
```

- [ ] **Step 6: Commit**

```bash
git add fhirsql/resources/
git commit -m "feat: add resource managers for all endpoints"
```

---

## Task 4: Transform Spec Builder

**Files:**
- Create: `fhirsql/transformspec.py`

- [ ] **Step 1: Create transform spec builder**

`fhirsql/transformspec.py`:
```python
import json
from typing import Dict, Any, Optional
from pathlib import Path

class TransformSpecBuilder:
    """Build transform specifications programmatically.
    
    Example:
        builder = TransformSpecBuilder("Patient Demographics")
        builder.set_analysis_id("analysis123")
        builder.add_resource_type("Patient")
        builder.add_field("Patient", "id", "string")
        builder.save("spec.json")
    """
    
    def __init__(self, name: str, spec_data: Optional[Dict] = None):
        self.spec = spec_data.copy() if spec_data else {"name": name, "resourceTypes": {}}
        self.name = name
    
    def set_analysis_id(self, analysis_id: str):
        self.spec["analysisID"] = analysis_id
        return self
    
    def add_resource_type(self, resource_type: str):
        if resource_type not in self.spec["resourceTypes"]:
            self.spec["resourceTypes"][resource_type] = {"fields": {}}
        return self
    
    def add_field(self, resource_type: str, field_path: str, field_type: str, **kwargs):
        if resource_type not in self.spec["resourceTypes"]:
            self.add_resource_type(resource_type)
        
        field_spec = {"type": field_type}
        field_spec.update(kwargs)
        self.spec["resourceTypes"][resource_type]["fields"][field_path] = field_spec
        return self
    
    def remove_field(self, resource_type: str, field_path: str):
        if resource_type in self.spec["resourceTypes"]:
            self.spec["resourceTypes"][resource_type]["fields"].pop(field_path, None)
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        return self.spec.copy()
    
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.spec, indent=indent)
    
    def save(self, file_path: str):
        Path(file_path).write_text(json.dumps(self.spec, indent=2))
    
    @classmethod
    def load(cls, file_path: str):
        spec_data = json.loads(Path(file_path).read_text())
        return cls(name=spec_data.get("name", "Loaded Spec"), spec_data=spec_data)
    
    @classmethod
    def from_dict(cls, spec_data: Dict[str, Any]):
        return cls(name=spec_data.get("name", "Untitled"), spec_data=spec_data)
```

- [ ] **Step 2: Commit**

```bash
git add fhirsql/transformspec.py
git commit -m "feat: add transform spec builder with file I/O"
```

---

## Task 5: Main Client

**Files:**
- Create: `fhirsql/client.py`
- Create: `fhirsql/__init__.py`

- [ ] **Step 1: Create main client**

`fhirsql/client.py`:
```python
import requests
from typing import Optional
from fhirsql.resources.credentials import CredentialResource
from fhirsql.resources.repositories import RepositoryResource
from fhirsql.resources.analysis import AnalysisResource
from fhirsql.resources.transformspecs import TransformSpecResource
from fhirsql.resources.projections import ProjectionResource

class FHIRSQLClient:
    """Client for HS.HC.FHIRSQL REST API.
    
    Example:
        client = FHIRSQLClient(
            base_url="http://localhost:52773/csp/fhirsql/api/ui",
            username="admin",
            password="secret"
        )
        repos = client.repositories.list()
    """
    
    def __init__(self, base_url: str, username: Optional[str] = None,
                 password: Optional[str] = None, verify_ssl: bool = True):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        
        if username and password:
            self.session.auth = (username, password)
        
        self.session.verify = verify_ssl
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        self.credentials = CredentialResource(self)
        self.repositories = RepositoryResource(self)
        self.analysis = AnalysisResource(self)
        self.transform_specs = TransformSpecResource(self)
        self.projections = ProjectionResource(self)
    
    def info(self):
        """Get API version info."""
        response = self.session.get(f"{self.base_url}/")
        response.raise_for_status()
        return response.json()
```

- [ ] **Step 2: Create package init**

`fhirsql/__init__.py`:
```python
"""FHIRSQL Python Client."""

__version__ = "0.1.0"

from fhirsql.client import FHIRSQLClient
from fhirsql.transformspec import TransformSpecBuilder
from fhirsql.exceptions import (
    FHIRSQLError,
    AuthenticationError,
    ResourceNotFoundError,
    ValidationError,
    APIError
)

__all__ = [
    "FHIRSQLClient",
    "TransformSpecBuilder",
    "FHIRSQLError",
    "AuthenticationError",
    "ResourceNotFoundError",
    "ValidationError",
    "APIError",
]
```

- [ ] **Step 3: Commit**

```bash
git add fhirsql/
git commit -m "feat: add main client with all resource managers"
```

---

## Task 6: Examples and Documentation

**Files:**
- Create: `examples/basic_usage.py`
- Create: `examples/transform_spec_example.py`
- Create: `README.md`

- [ ] **Step 1: Create basic example**

`examples/basic_usage.py`:
```python
from fhirsql import FHIRSQLClient

client = FHIRSQLClient(
    base_url="http://localhost:52773/csp/fhirsql/api/ui",
    username="admin",
    password="your_password"
)

# Create credential
cred = client.credentials.create(
    system_name="MyFHIRServer",
    username="fhiruser",
    password="secret"
)
print(f"Created credential: {cred.id}")

# Create repository
repo = client.repositories.create(
    name="Test FHIR Server",
    url="http://localhost:52773/fhir/r4",
    credentials_id=cred.id
)
print(f"Created repository: {repo.id}")

# Start analysis
analysis = client.analysis.create(
    fhir_host=repo.id,
    max_distinct=1000,
    selectivity_percentage=50
)
print(f"Started analysis: {analysis.id}")
```

- [ ] **Step 2: Create transform spec example**

`examples/transform_spec_example.py`:
```python
from fhirsql import FHIRSQLClient, TransformSpecBuilder

client = FHIRSQLClient(
    base_url="http://localhost:52773/csp/fhirsql/api/ui",
    username="admin",
    password="your_password"
)

# Build spec programmatically
builder = TransformSpecBuilder("Patient Demographics")
builder.set_analysis_id("analysis123")
builder.add_resource_type("Patient")
builder.add_field("Patient", "id", "string")
builder.add_field("Patient", "name.family", "string")
builder.add_field("Patient", "birthDate", "date")

# Save to file
builder.save("patient_spec.json")

# Load from file
loaded = TransformSpecBuilder.load("patient_spec.json")

# Create on server
spec = client.transform_specs.create_from_builder(builder)
print(f"Created spec: {spec.id}")

# Build projection
projection = client.projections.create(spec_id=spec.id)
print(f"Created projection: {projection.id}")
```

- [ ] **Step 3: Create README**

`README.md`:
```markdown
# FHIRSQL Python Client

Pythonic wrapper for HS.HC.FHIRSQL REST API.

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

```python
from fhirsql import FHIRSQLClient

client = FHIRSQLClient(
    base_url="http://localhost:52773/csp/fhirsql/api/ui",
    username="admin",
    password="password"
)

# Create repository
repo = client.repositories.create(
    name="FHIR Server",
    url="http://localhost/fhir/r4"
)

# Start analysis
analysis = client.analysis.create(
    fhir_host=repo.id,
    max_distinct=1000,
    selectivity_percentage=50
)
```

## Transform Specs

```python
from fhirsql import TransformSpecBuilder

builder = TransformSpecBuilder("My Spec")
builder.add_resource_type("Patient")
builder.add_field("Patient", "id", "string")
builder.save("spec.json")

spec = client.transform_specs.create_from_builder(builder)
```

## API

- `client.credentials` - Manage credentials
- `client.repositories` - Manage FHIR repositories
- `client.analysis` - Run analysis tasks
- `client.transform_specs` - Manage transform specifications
- `client.projections` - Build database projections
```

- [ ] **Step 4: Commit**

```bash
git add examples/ README.md
git commit -m "docs: add examples and README"
```

---

**Plan complete. Execute with superpowers:executing-plans or superpowers:subagent-driven-development.**
