from dataclasses import dataclass
from typing import Optional, Dict, Any, List

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
    hostname: Optional[str] = None
    port: Optional[str] = None
    repository_url: Optional[str] = None
    credentials_id: Optional[str] = None
    ssl_config: Optional[str] = None

    def to_dict(self):
        return {k: v for k, v in {
            "id": self.id,
            "name": self.name,
            "hostname": self.hostname,
            "port": self.port,
            "repositoryURL": self.repository_url,
            "credentialsId": self.credentials_id,
            "sslConfig": self.ssl_config
        }.items() if v is not None}

    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data.get("id"),
            name=data.get("name"),
            hostname=data.get("hostname"),
            port=data.get("port"),
            repository_url=data.get("repositoryURL"),
            credentials_id=data.get("credentialsId"),
            ssl_config=data.get("sslConfig")
        )

@dataclass
class Analysis:
    id: Optional[str] = None
    fhir_repository_id: Optional[int] = None
    max_distinct: Optional[int] = None
    selectivity_percentage: Optional[int] = None
    status: Optional[str] = None

    def to_dict(self):
        return {k: v for k, v in {
            "id": self.id,
            "fhirRepositoryId": self.fhir_repository_id,
            "maxDistinct": self.max_distinct,
            "selectivityPercentage": self.selectivity_percentage,
            "status": self.status
        }.items() if v is not None}

    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data.get("id") or data.get("TASKID"),
            fhir_repository_id=data.get("fhirRepositoryId"),
            max_distinct=data.get("maxDistinct"),
            selectivity_percentage=data.get("selectivityPercentage"),
            status=data.get("status")
        )

@dataclass
class TransformSpec:
    id: Optional[str] = None
    name: Optional[str] = None
    scan_id: Optional[int] = None
    spec_data: Optional[Dict] = None  # Should contain 'resources' array with {resourceType, columns[]}

    def to_dict(self):
        data = {}
        if self.id:
            data["id"] = self.id
        if self.name:
            data["name"] = self.name
        if self.scan_id:
            data["scanId"] = self.scan_id
        if self.spec_data:
            data.update(self.spec_data)
        return data

    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data.get("id") or data.get("SPECID"),
            name=data.get("name"),
            scan_id=data.get("scanId"),
            spec_data=data
        )

@dataclass
class Projection:
    id: Optional[str] = None
    name: Optional[str] = None
    spec_id: Optional[str] = None
    fhir_repository_id: Optional[int] = None
    package_name: Optional[str] = None
    users: Optional[List[str]] = None
    status: Optional[str] = None

    def to_dict(self):
        return {k: v for k, v in {
            "id": self.id,
            "name": self.name,
            "specificationId": self.spec_id,
            "fhirRepositoryId": self.fhir_repository_id,
            "packageName": self.package_name,
            "users": self.users,
            "status": self.status
        }.items() if v is not None}

    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data.get("id"),
            name=data.get("name"),
            spec_id=data.get("specificationId"),
            fhir_repository_id=data.get("fhirRepositoryId"),
            package_name=data.get("packageName"),
            users=data.get("users"),
            status=data.get("status")
        )
