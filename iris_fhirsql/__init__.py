"""FHIRSQL Python Client."""

__version__ = "0.1.0"

from iris_fhirsql.client import FHIRSQLClient
from iris_fhirsql.transformspec import TransformSpecBuilder
from iris_fhirsql.exceptions import (
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
