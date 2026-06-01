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
