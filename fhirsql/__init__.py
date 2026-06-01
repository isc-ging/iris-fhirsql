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
